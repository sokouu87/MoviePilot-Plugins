"""清点口径与 Emby 分页回归。"""

import sys
import types
from pathlib import Path

import httpx
import pytest

module = types.ModuleType("hyrule_inventory_test")
module.__path__ = [str(Path(__file__).resolve().parents[1] / "plugins.v3" / "subtitlemanualupload")]
sys.modules[module.__name__] = module
from hyrule_inventory_test.inventory import classify, emby_url, item_pages, item_versions, page, summarize


VIDEO = {"Type": "Video"}


def track(language=None, **fields):
    return {"Type": "Subtitle", "Language": language, "Codec": "subrip", **fields}


def test_full_chinese_bilingual_and_limited_tracks():
    path = "/media/影片.mkv"
    result = classify([
        VIDEO, track("zh", IsExternal=True, Path="/media/影片.zh-en.ai.ass"),
        track("zh-CN", IsExternal=True, Path="/media/影片.zh-en.ai.srt"),
        track("chi", Codec="PGSSUB"), track("eng", Title="English SDH"),
    ], path, set(), {})
    assert result == {"state": "present", "reason": "", "english": True, "bilingual": True,
                      "chinese": ["embedded", "external"], "chinese_scripts": []}
    limited = classify([VIDEO, track("chi", IsForced=True), track("eng")], path, set(), {})
    assert limited["state"] == "missing" and limited["english"]
    assert limited["reason"] == "只有强制或附注中文"
    assert not classify([VIDEO, track("eng", Codec="PGSSUB")], path, set(), {})["english"]


def test_embedded_chinese_scripts_require_marked_full_tracks():
    path = "/media/影片.mkv"
    result = classify([VIDEO, track("chi", Title="Traditional"), track("chi", Title="Simplified")], path, set(), {})
    assert result["chinese"] == ["embedded"] and result["chinese_scripts"] == ["hans", "hant"]
    result = classify([VIDEO, track("zh-Hant"), track("und", Title="简中")], path, set(), {})
    assert result["chinese_scripts"] == ["hans", "hant"]
    result = classify([VIDEO, track("chi", IsForced=True, Title="Simplified"),
                       track("zh-Hant", IsExternal=True), track("chi"), track("eng", Title="Traditional")], path, set(), {})
    assert result["chinese"] == ["embedded", "external"] and result["chinese_scripts"] == []


def test_unknown_tracks_and_unindexed_sidecars(tmp_path):
    video = tmp_path / "片源.mkv"
    other = tmp_path / "片源2.zh.srt"
    other.write_text("other", encoding="utf-8")
    assert classify([], str(video), set(), {})["state"] == "unknown"
    assert classify([VIDEO, track("und")], str(video), set(), {})["state"] == "unknown"
    assert classify([VIDEO, track("jpn")], str(video), {str(video)}, {})["state"] == "missing"
    same_file = tmp_path / "片源.zh.srt"
    same_file.write_text("本片字幕", encoding="utf-8")
    info = classify([VIDEO], str(video), {str(video)}, {})
    assert info["state"] == "unknown" and info["reason"] == "发现 Emby 尚未收录的外挂"
    assert classify([VIDEO], str(video), set(), {})["state"] == "missing"


def test_disc_parts_are_separate_from_the_main_video():
    assert classify([VIDEO], "/media/电影/BDMV/STREAM/00001.m2ts", set(), {})["state"] == "disc"
    assert classify([], "/media/电影/BDMV/BACKUP/JAR/bluray_project.bin", set(), {})["state"] == "disc"
    assert classify([VIDEO, track("zho")], "/115/电影/VIDEO_TS/00001.strm", set(), {})["state"] == "disc"
    assert classify([VIDEO], "/media/电影/电影.m2ts", set(), {})["state"] == "missing"


def test_each_version_and_episode_keeps_its_own_status():
    item = {"Type": "Movie", "Id": "movie", "Name": "暗夜", "OriginalTitle": "Dark Night",
            "Path": "/film/暗夜 1080p.mkv", "MediaStreams": [VIDEO, track("chi")],
            "MediaSources": [
                {"Id": "hd", "Path": "/film/暗夜 1080p.mkv", "MediaStreams": [VIDEO, track("chi")]},
                {"Id": "uhd", "Path": "/film/暗夜 4k.mkv", "MediaStreams": [VIDEO, track("eng")]},
            ]}
    rows = list(item_versions(item, "emby", set(), {}))
    rows += list(item_versions({"Type": "Episode", "Id": "e3", "Name": "第三集", "SeriesName": "海洋",
                                "SeriesId": "s", "ParentIndexNumber": 1, "IndexNumber": 3,
                                "Path": "/115/episode.strm", "MediaSources": [
                                    {"Id": "r1", "Protocol": "Http", "Path": "https://example.org/private",
                                     "MediaStreams": []},
                                ]}, "emby", set(), {}))
    snap = {"summary": summarize(rows), "rows": rows}
    assert snap["summary"]["all"] == {
        "total": 3, "items": 2, "missing_items": 1, "present": 1, "missing": 1,
        "unknown": 1, "disc": 0, "bilingual": 0, "english_ready": 1,
    }
    assert snap["summary"]["series"] == 1
    assert page(snap, "missing", "Movie", "dark 4k", 0)["rows"][0]["file"] == "暗夜 4k.mkv"
    assert page(snap, "unknown", "Episode", "海洋 S01E03", 0)["rows"][0]["file"] == "episode.strm"


@pytest.mark.parametrize("page_two,count,reason", [
    ([{"Id": "2"}], 2, None),
    ([{"Id": "1"}], 2, "重复"),
    ([], 3, "总数发生变化"),
    ([], 2, "缺失"),
])
def test_uses_reported_total_and_rejects_incomplete_scans(page_two, count, reason):
    def respond(req):
        assert req.url.params["IsMissing"] == "false"
        assert req.url.params["IncludeItemTypes"] == "Movie,Episode"
        first = req.url.params["StartIndex"] == "0"
        return httpx.Response(200, json={"Items": [{"Id": "1"}] if first else page_two,
                                         "TotalRecordCount": 2 if first else count})
    with httpx.Client(base_url="http://emby.test/emby/", transport=httpx.MockTransport(respond)) as client:
        if reason:
            with pytest.raises(ValueError, match=reason):
                list(item_pages(client))
        else:
            assert [done for _, done, _ in item_pages(client)] == [1, 2]


def test_uses_configured_emby_host_and_never_accepts_credentials_in_the_url():
    assert emby_url("192.168.1.3:8096") == "http://192.168.1.3:8096/emby/"
    assert emby_url("https://example.org/media/emby/") == "https://example.org/media/emby/"
    with pytest.raises(ValueError):
        emby_url("https://user:secret@example.org")
