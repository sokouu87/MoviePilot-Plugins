"""统一搜索、原盘归组和字幕写入路径回归。"""

import sys
import types
from pathlib import Path

import pytest

module = types.ModuleType("hyrule_library_test")
module.__path__ = [str(Path(__file__).resolve().parents[1] / "plugins.v3" / "subtitlemanualupload")]
sys.modules[module.__name__] = module
from hyrule_library_test import disc, inventory, library
from hyrule_library_test.media import metadata
from hyrule_library_test.studio import Studio

SRT = b"1\n00:00:00,000 --> 00:00:02,000\nSample.\n"
VIDEO = {"Type": "Video"}


def playlist(clip, language):
    def word(n, size=2):
        return n.to_bytes(size, "big")
    entries = b"\x03\x01\x12\x00\x04\x90" + language
    table = b"\0\0" + bytes([0, 0, 1, 0, 0, 0, 0, 0]) + b"\0" * 4 + entries
    item = clip + b"M2TS\0\x01\0" + word(0, 4) + word(45000 * 1200, 4) + b"\0" * 12 + word(len(table)) + table
    body = b"\0\0" + word(1) + word(0) + word(len(item)) + item
    return b"MPLS0200" + word(20, 4) + b"\0" * 8 + word(len(body), 4) + body


def emby(kind, key, path, title, *, source=None, **fields):
    return {"Type": kind, "Id": key, "Name": title, "Path": path, "DateCreated": "2026-11-24T07:00:00Z",
            "RunTimeTicks": 12_000_000_000, "MediaStreams": [VIDEO], "MediaSources": [source] if source else [],
            **fields}


def snapshot(root, *items):
    rows = [row for item in items for row in inventory.item_versions(item, "test", set(), {})]
    maps = library.directory_maps(f"/emby-media={root}")
    return {"catalog": library.catalog(rows, {"test": ["/emby-media"]}, maps)}


def test_reads_primary_playlist_languages_and_rejects_truncation():
    data = playlist(b"00213", b"zho")
    assert disc.read_playlist(data) == [("00213", 1200, {"zho"})]
    with pytest.raises(ValueError):
        disc.read_playlist(data[:-1])


def test_combines_recent_task_and_emby_with_one_search_result(tmp_path):
    root = tmp_path / "movies"
    root.mkdir()
    file = root / "片源.mkv"
    file.touch()
    another = root / "库存.mkv"
    another.touch()
    studio = Studio(tmp_path / "state", {}, None)
    key = studio.register(file, {**metadata(file, title="片源"), "added": "2026-11-24T08:00:00+00:00"})
    with studio.db() as conn:
        conn.execute("INSERT INTO job(target,state,detail) VALUES (?,'done','已生成双语 ASS 和 SRT')", (key,))
    state = snapshot(root, emby("Movie", "1", "/emby-media/片源.mkv", "片源", OriginalTitle="English Title"),
                     emby("Movie", "2", "/emby-media/库存.mkv", "库存"))
    with studio.db() as conn:
        result = library.page(conn, state, "english title", "all", "desc", 0)
        assert result["matches"] == 1
        combined = result["rows"][0]
        assert combined["recent"] and combined["emby"] and combined["task"]["state"] == "done"
        assert library.page(conn, state, "库存", "all", "desc", 0)["matches"] == 1
        assert library.page(conn, state, "", "recent", "desc", 0)["matches"] == 1
        assert library.page(conn, state, "", "all", "desc", 0, "Episode")["matches"] == 0
    before = library.prepare(studio, state, library.key_for(str(another)))
    assert studio.target(before["target"])[0] == another


def test_disc_hides_failed_fragments_and_uploads_to_verified_primary(tmp_path):
    root = tmp_path / "movies"
    folder = root / "某部电影 (2024)"
    streams = folder / "BDMV" / "STREAM"
    playlists = folder / "BDMV" / "PLAYLIST"
    streams.mkdir(parents=True)
    playlists.mkdir(parents=True)
    (playlists / "00001.mpls").write_bytes(playlist(b"00002", b"zho"))
    main, fragment = streams / "00002.m2ts", streams / "00003.m2ts"
    main.touch()
    fragment.touch()
    studio = Studio(tmp_path / "state", {}, None)
    key = studio.register(fragment)
    with studio.db() as conn:
        conn.execute("INSERT INTO job(target,state,detail) VALUES (?,'failed','缺少英文字幕')", (key,))
    state = snapshot(root, *(emby("Episode", str(n), f"/emby-media/某部电影 (2024)/BDMV/STREAM/{file.name}", "分段")
                             for n, file in enumerate((main, fragment), 1)))
    with studio.db() as conn:
        results = library.page(conn, state, "某部电影", "all", "desc", 0)
        assert results["matches"] == 1
        assert library.page(conn, state, "", "failed", "desc", 0)["matches"] == 0
        result = results["rows"][0]
        assert result["original"] and result["status"] == "present" and result["task"] is None
        assert result["directory"] == str(folder)
    ready = library.prepare(studio, state, result["id"])
    assert ready["file"] == main.name and ready["directory"] == str(folder)
    label = studio.upload(ready["target"], "match.srt", SRT, "", "zh-Hans")
    assert (streams / label["file"]).read_bytes() == SRT
    assert label["file"] == "00002.zh-Hans.manual.srt"
    with pytest.raises(ValueError, match="原盘"):
        studio.submit(ready["target"])


def test_unresolved_disc_saves_in_movie_folder_without_guessing_part(tmp_path):
    root = tmp_path / "media"
    volume = root / "电影"
    stream = volume / "BDMV" / "STREAM"
    stream.mkdir(parents=True)
    (stream / "00001.strm").touch()
    state = snapshot(root, emby("Episode", "d1", "/emby-media/电影/BDMV/STREAM/00001.strm", "00001", RunTimeTicks=0))
    studio = Studio(tmp_path / "state", {}, None)
    ready = library.prepare(studio, state, library.key_for(str(volume)))
    assert ready["folder"] and ready["destination"] == str(volume)
    result = studio.upload(ready["target"], "match.srt", SRT, "", "zh-Hans")
    assert (volume / result["file"]).is_file()


def test_path_mapping_checks_root_and_rejects_parent_traversal(tmp_path):
    allowed = tmp_path / "media"
    allowed.mkdir()
    outside = tmp_path / "outside.mkv"
    outside.touch()
    maps = library.directory_maps(f"/emby-media={allowed}")
    assert library.location("/emby-media/safe.mkv", ["/emby-media"], maps) == (str(allowed / "safe.mkv"), str(allowed))
    assert library.location("/emby-media/../outside.mkv", ["/emby-media"], maps) == ("", "")
    assert not library.mounted(str(outside), str(allowed))
