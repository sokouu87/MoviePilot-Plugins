import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

module = types.ModuleType("hyrule_bilingual_test")
module.__path__ = [str(Path(__file__).resolve().parents[1] / "plugins.v3" / "subtitlemanualupload")]
sys.modules[module.__name__] = module
from hyrule_bilingual_test.bilingual import combine
from hyrule_bilingual_test.media import embedded_chinese
from hyrule_bilingual_test.studio import Studio
from hyrule_bilingual_test.subtitles import Cue, render


def cue(number, start, end, text):
    return Cue(number, start, end, text, text, False)


def test_prefers_simplified_and_ignores_limited_tracks():
    def track(index, title, **flags):
        return {"codec_type": "subtitle", "codec_name": "subrip", "index": index,
                "tags": {"language": "chi", "title": title}, "disposition": flags}

    streams = [track(2, "Simplified", forced=1), track(3, "Traditional"), track(4, "Simplified")]
    with patch("hyrule_bilingual_test.media.extract_track", return_value=[cue(1, 0, 1000, "这是字幕")]) as read:
        assert embedded_chinese(Path("test.mkv"), streams)[1:] == ("hans", "内封简中轨 #4")
    assert read.call_args.args[1]["index"] == 4


def test_existing_tracks_keep_chinese_timing_and_convert_traditional(tmp_path):
    zh = [cue(1, 1000, 3000, "<i>這是繁體中文</i>"), cue(2, 3010, 4100, "謝謝")]
    en = [cue(1, 1040, 2950, "This is Chinese."), cue(2, 3000, 4130, "Thank you.")]

    def unexpected(*args):
        pytest.fail("对齐的已有英文无需调用模型")

    rows, items, stats = combine(zh, "hant", en, {}, unexpected, tmp_path / "cache",
                                 model="test", progress=unexpected)
    assert [(row.start, row.end, row.en) for row in rows] == [(1000, 3000, "This is Chinese."), (3010, 4100, "Thank you.")]
    assert [item["zh"] for item in items.values()] == ["这是繁体中文", "谢谢"]
    assert stats == {"existing_english": 2, "generated_english": 0}
    ass, srt = render(rows, items)
    assert "这是繁体中文" in ass.decode()
    assert "谢谢\nThank you." in srt.decode()


def test_only_missing_english_calls_model_and_reuses_checkpoint(tmp_path):
    zh = [cue(1, 1000, 3000, "这是字幕"), cue(2, 4000, 5100, "谢谢")]
    en = [cue(1, 1020, 2950, "These are subtitles.")]
    requests = []

    def ask(stage, instruction, data, schema, search):
        requests.append(data)
        return {"items": [{"id": 2, "en": "Thanks."}]}, []

    args = (zh, "hans", en, {}, ask, tmp_path / "english-checkpoint.json")
    for _ in range(2):
        rows, _, stats = combine(*args, model="test", progress=lambda _: None)
        assert [c.en for c in rows] == ["These are subtitles.", "Thanks."]
        assert stats == {"existing_english": 1, "generated_english": 1}
    assert len(requests) == 1
    assert [row["id"] for row in requests[0]["translate"]] == [2]


def test_failed_job_becomes_done_only_after_dual_outputs(tmp_path):
    movie = tmp_path / "片源 S01E12.mkv"
    movie.touch()
    studio = Studio(tmp_path, {"model": "test", "effort": "high", "whisper": ""}, "local")
    key = studio.register(movie)
    number = studio.submit(key)
    with studio.db() as db:
        db.execute("UPDATE job SET state='failed',detail='没有英文字幕' WHERE id=?", (number,))
    studio.retry(number)
    cn = [cue(1, 1000, 3000, "谢谢")]
    with (patch("hyrule_bilingual_test.studio.probe_streams", return_value=[]),
          patch("hyrule_bilingual_test.studio.embedded_chinese", return_value=(cn, "hans", "内封简中轨 #5")),
          patch.object(studio, "ask", return_value=({"items": [{"id": 1, "en": "Thank you."}]}, []))):
        studio.current_job = number
        with studio.db() as db:
            db.execute("UPDATE job SET state='running' WHERE id=?", (number,))
            job = db.execute("SELECT * FROM job WHERE id=?", (number,)).fetchone()
        result, _, report = studio.run_job(job)
    assert result == "done" and report["generated_english"] == 1
    srt = movie.with_suffix(".zh-en.ai.srt").read_text(encoding="utf-8-sig")
    assert "00:00:01,000 --> 00:00:03,000\n谢谢\nThank you." in srt
    assert movie.with_suffix(".zh-en.ai.ass").is_file()
