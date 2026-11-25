import sys
import threading
import types
from pathlib import Path

import pytest
from fastapi import HTTPException

module = types.ModuleType("hyrule_mplite_test")
module.__path__ = [str(Path(__file__).resolve().parents[1] / "plugins.v3" / "subtitlemanualupload")]
sys.modules[module.__name__] = module
from hyrule_mplite_test.mplite import MPLite, config_update
from hyrule_mplite_test.studio import Studio


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
