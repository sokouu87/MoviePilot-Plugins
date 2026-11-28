import sys
import threading
import types
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException

module = types.ModuleType("hyrule_mplite_test")
module.__path__ = [str(Path(__file__).resolve().parents[1] / "plugins.v3" / "subtitlemanualupload")]
sys.modules[module.__name__] = module
from hyrule_mplite_test.mplite import MPLite, config_update
from hyrule_mplite_test import inventory
from hyrule_mplite_test.studio import EMPTY, Studio


def test_native_config_only_updates_shared_options():
    before = {"model": "gpt-6.2-sol", "effort": "medium", "auto_translate": True, "bridge_key": "existing"}
    incoming = {"auto_search_on_transfer": False, "subhd_url": "https://example.org",
                "online_proxy_migrated": True, "assrt_provider_migrated": True}
    assert config_update(before, incoming) == {**before, "auto_translate": False}
    assert config_update(before, {**incoming, "model": "gpt-6.2-astra"}) is None


def test_native_client_search_status_subhd_and_actions(tmp_path):
    movie = tmp_path / "验收片 (2026) S01E12.mkv"
    movie.touch()
    studio = Studio(tmp_path, {"model": "test", "auto_translate": True}, "local")
    key = studio.register(movie)
    title = "验收片 2026 S01E12"
    row = {"id": key, "title": title, "kind": "Episode", "file": movie.name, "display": str(movie),
           "available": True, "original": False}

    class Plugin:
        _inventory_snapshot = {"catalog": {key: row}}
        _inventory_lock = threading.Lock()

        @staticmethod
        def _active():
            return studio

        @staticmethod
        def _check(call, *args):
            return call(*args)

        @staticmethod
        def library_page(query, **kwargs):
            matches = [row] if not query or title.casefold() == query.casefold() else []
            return {"rows": matches, "matches": len(matches)}

        @staticmethod
        def library_target(body):
            assert body["id"] == key
            return {"target": key, "original": False, "file": movie.name, "folder": False}

    mobile = MPLite(Plugin())
    assert mobile.status()["ai_subtitle"]["available"]
    media = mobile.search(title, media_type="tv")["medias"][0]
    native = mobile.targets(media["media_type"], media["title"])["targets"][0]
    assert native["writable"] and native["id"] == key
    selection = {"target_ids": [key], "media": media}
    assert mobile.online_manual_links(selection)["links"][0]["links"][0]["url"].startswith("https://subhd.tv/search/")
    assert mobile.online_search(selection)["results"] == []
    assert mobile.ai_submit(selection)["tasks"][0]["status"] == "pending"
    assert mobile.ai_cancel(selection)["tasks"][0]["status"] == "cancelled"

    original = "1\n00:00:01,000 --> 00:00:02,000\n中文字幕\n".encode()
    draft = mobile._prepare(key, "sample.chi.srt", original)
    item = draft["items"][0]
    with pytest.raises(HTTPException):
        mobile.apply_upload({"session_id": draft["session_id"], "items": [{**item, "target_id": "0" * 64}]})
    written = mobile.apply_upload({"session_id": draft["session_id"], "items": [item]})["written"][0]
    assert written["filename"] == movie.with_suffix(".zh-Hans.manual.srt").name
    assert movie.with_suffix(".zh-Hans.manual.srt").read_bytes() == original
    with pytest.raises(HTTPException):
        mobile.apply_upload({"session_id": draft["session_id"], "items": [item]})


def test_select_emby_english_for_exact_target_and_reuse_on_rerun(tmp_path, monkeypatch):
    studio = Studio(tmp_path, {"model": "test", "effort": "low", "whisper": ""}, "local")
    movie = tmp_path / "episode.s01e02.strm"
    movie.write_text("https://example.invalid/episode")
    key = studio.register(movie)
    other = tmp_path / "local.strm"
    other.touch()
    local_key = studio.register(other)
    manuscript = b"1\n00:00:01,250 --> 00:00:02,500\nHello there.\n"
    other.with_suffix(".en.srt").write_bytes(manuscript)
    requests = []

    def respond(request):
        requests.append(request.url.path)
        if request.url.path.endswith("/Subtitles/en"):
            return httpx.Response(200, json=[
                {"Id": "en1", "Name": "Episode.WEB", "Format": "srt", "Language": "English",
                 "ProviderName": "Open Subtitles", "IsHashMatch": False},
                {"Id": "zh", "Name": "Episode.WEB", "Format": "srt", "Language": "Chinese"},
                {"Id": "forced", "Name": "Episode.Forced", "Format": "srt", "Language": "en"},
            ])
        assert request.url.path.endswith("/Providers/Subtitles/Subtitles/en1")
        return httpx.Response(200, content=manuscript)

    class Plugin:
        _active = staticmethod(lambda: studio)
        _check = staticmethod(lambda call, *args: call(*args))

        @staticmethod
        def _prepare_library_target(ident, include_emby):
            assert include_emby
            return {"target": ident, "original": False, "file": studio.target(ident)[0].name,
                    "emby_source": ("Emby", "12")}

    monkeypatch.setattr(inventory, "configured_servers", lambda: [("Emby", {"host": "fixture"})])
    monkeypatch.setattr(inventory, "emby_client", lambda config, timeout: httpx.Client(
        base_url="https://emby.invalid/emby/", transport=httpx.MockTransport(respond)))
    mobile = MPLite(Plugin())
    options = mobile.ai_submit({"target_ids": [key], "find_english": True})["english_options"]
    assert options["candidates"] == [
        {"index": 0, "title": "Episode.WEB", "provider": "Open Subtitles", "hash_match": False}
    ]
    assert studio.history() == []
    choice = {"token": options["token"], "index": 0}
    with pytest.raises(ValueError, match="候选已失效"):
        mobile.ai_submit({"target_ids": [local_key], "english_choice": choice})
    assert len(requests) == 1
    assert mobile.ai_submit({"target_ids": [local_key], "find_english": True})["tasks"][0]["status"] == "pending"
    assert len(requests) == 1

    job_id = int(mobile.ai_submit({"target_ids": [key], "english_choice": choice})["tasks"][0]["id"])
    assert studio.has_online_source(job_id)

    def translate(cues, *_args, **_kwargs):
        assert [cue.en for cue in cues] == ["Hello there."]
        return {c.id: {"id": c.id, "type": "dialogue", "zh": "你好。", "note": ""} for c in cues}, EMPTY, {}

    monkeypatch.setattr("hyrule_mplite_test.studio.translate", translate)
    with studio.db() as conn:
        conn.execute("UPDATE job SET state='running' WHERE id=?", (job_id,))
        job = conn.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()
    state, _, report = studio.run_job(job)
    assert state == "done" and report["source"] == "Emby · Open Subtitles · Episode.WEB"
    assert "00:00:01,250 --> 00:00:02,500" in movie.with_suffix(".zh-en.ai.srt").read_text(encoding="utf-8-sig")
    assert not movie.with_suffix(".eng.manual.srt").exists()
    with studio.db() as conn:
        conn.execute("UPDATE job SET state='done' WHERE id=?", (job_id,))
    restarted = int(mobile.ai_submit({"target_ids": [key], "find_english": True})["tasks"][0]["id"])
    assert restarted != job_id and studio.has_online_source(restarted)
    assert len(requests) == 2
