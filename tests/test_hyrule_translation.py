"""新字幕管线的轴、断点与非覆盖写入回归。无需 MoviePilot 运行环境。"""
import codecs
import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import types
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "plugins.v3" / "subtitlemanualupload"
module = types.ModuleType("hyrule_test")
module.__path__ = [str(PACKAGE)]
sys.modules[module.__name__] = module
from hyrule_test.subtitles import Cue, ass_time, parse, render, upload_member, write_file
from hyrule_test.translation import batches, check_item, translate, validated_glossary
from hyrule_test.studio import EMPTY, Studio
from hyrule_test import task_history


SAMPLE = b"3\n00:00:59,995 --> 00:01:00,001\n<i>JOHN: [sighs] Hello.</i>\n\n7\n00:01:00,600 --> 00:01:01,600\n[gunshot]\n\n8\n00:01:05,000 --> 00:01:06,100\n[ambient music]\n"
def item(i, zh, kind="dialogue", note=""):
    return {"id": i, "type": kind, "zh": zh, "note": note}


class Subtitles(unittest.TestCase):
    def test_render_sdh_time_escape_and_numbering(self):
        cues = parse(SAMPLE, ".srt")
        self.assertEqual([(c.id, c.en, c.italic) for c in cues], [(1, "Hello.", True), (2, "", False), (3, "", False)])
        ass, srt = render(cues, {1:item(1, r"你{\N}好", note="示例"), 2:item(2, "枪声","key_sfx"), 3:item(3,"","sdh_drop")})
        self.assertTrue(ass.startswith(codecs.BOM_UTF8))
        self.assertIn(r"{\b500}你｛＼N｝好\N{\rEng}{\i1}Hello.", ass.decode("utf-8-sig"))
        self.assertIn("0:01:00.00,0:01:00.01",ass.decode())
        self.assertIn("Dialogue: 1,",ass.decode())
        self.assertEqual([c.id for c in parse(srt,".srt")], [1,2])
        self.assertNotIn("示例",srt.decode())
        self.assertIn("【枪声】",srt.decode())

    def test_ass_format_and_english(self):
        source = "[Events]\nFormat: Start, End, Text\nDialogue: 0:00:00.10,0:00:01.20,{\\i1}My (real) name,\\Nis Alex{\\i0}"
        cue = parse(source.encode(),".ass")[0]
        self.assertEqual((cue.en,cue.italic),("My (real) name, is Alex",True))
        with self.assertRaises(ValueError):
            parse(b"<html>not subtitles</html>",".srt")
        self.assertEqual(ass_time(360000),"1:00:00.00")

    def test_targeted_validation(self):
        c = Cue(1,0,1000,"Hello.","Hello.",False)
        self.assertTrue(check_item(c,item(1,"TMD，你好"),[])[0])
        self.assertTrue(check_item(c,item(1,"","sdh_drop"),[])[0])
        r=item(1,"老铁。")
        self.assertIn("命中禁用词",check_item(c,r,["老铁"])[1])
        self.assertEqual(r["zh"],"老铁")
        r=item(1,"<i>您好，先生。</i>")
        check_item(c,r,[])
        self.assertEqual(r["zh"],"您好 先生")
        r=item(1,"【（门后传来一声枪响）】","key_sfx")
        self.assertTrue(check_item(Cue(1,0,2000,"[gunshot]","",False),r,[])[0])
        self.assertEqual(r["zh"],"门后传来一声枪响")
        for phrase in ("（叹气）可真好", "[sighs] 又来了", "可算完了【轻笑】"):
            self.assertTrue(check_item(c,item(1,phrase),[])[0])
        self.assertFalse(check_item(c,item(1,"查纽约（州）那笔账"),[])[0])

    def test_no_clobber_and_archive_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"movie.srt"
            write_file(path,b"old")
            with self.assertRaises(FileExistsError):
                write_file(path,b"new")
            self.assertEqual(path.read_bytes(),b"old")
        f=io.BytesIO()
        with zipfile.ZipFile(f,"w") as z:
            z.writestr("../../outside.srt",SAMPLE)
            z.writestr("E02.srt",SAMPLE)
        # 点路径不列出，也不解压到文件系统。
        self.assertEqual(upload_member("test.zip",f.getvalue()),(".srt",SAMPLE))
        with self.assertRaises(ValueError):
            upload_member("test.zip",f.getvalue(),"missing")

    def test_sequential_batches_retry_then_episode_review(self):
        cues=[Cue(i,3000*i,3000*i+2000,"Hello","Hello",False) for i in range(1,165)]
        calls=[]
        failed=[True]
        def ask(stage, instructions, data, schema, search):
            calls.append((stage,data))
            if stage=="research":
                self.assertEqual(len(data["episode"]),len(cues))
                return "官方资料",["https://example.org/work"]
            if stage=="glossary": return {"context":"剧情","terms":[]},[]
            if stage=="translate":
                ids=[r["id"] for r in data["translate"]]
                if len(ids)==82 and ids[0]==83:
                    self.assertEqual(len(data["previous_zh"]),5)
                    if failed[0]:
                        failed[0]=False
                        raise RuntimeError("中断")
                if ids[0]==1:
                    self.assertEqual(len(data["following_en"]),5)
                values=[item(i,"你好。") for i in ids if not (i==7 and len(ids)>1)]
                return {"items":values,"new_terms":[],"ambiguities":[]},[]
            if stage=="review":
                return {"edits":[{"id":164,"zh_new":"您好","reason":"称谓"}]},[]
            self.fail(stage)
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint=Path(tmp)/"checkpoint.json"
            arguments=dict(model="test/high",banned=[],progress=lambda _:None)
            with self.assertRaises(RuntimeError):
                translate(cues,{},EMPTY,ask,checkpoint,**arguments)
            rows,_,report=translate(cues,{},EMPTY,ask,checkpoint,**arguments)
            self.assertEqual([len(x[1]["translate"]) for x in calls if x[0]=="translate"],[82,1,82,82])
            self.assertEqual(rows[164]["zh"],"您好")
            self.assertEqual(rows[7]["zh"],"你好")
            self.assertEqual(report["warnings"],{})
            self.assertEqual(sum(s=="research" for s,_ in calls),1)
        self.assertEqual([len(b) for b in batches(cues)],[82,82])

    def test_target_selection_and_safe_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            studio=Studio(root,{},None)
            movie=root/"Film S01E04.mkv"
            movie.touch()
            key=studio.register(movie)
            self.assertIsNone(studio.register(root/"no-file"))
            self.assertIn("S01E04",studio.targets()["targets"][0]["search_url"])
            self.assertEqual(studio.submit(key),studio.submit(key))
            self.assertEqual(len(studio.history()),1)
            stored=studio.upload(key,"../../elsewhere.srt",SAMPLE,"","eng")
            self.assertEqual(stored["file"],"Film S01E04.eng.manual.srt")
            with self.assertRaises(ValueError):
                studio.upload(key,"x.srt",SAMPLE.replace(b"Hello",b"Goodbye"),"","eng")
            with self.assertRaises(ValueError):
                studio.upload(str(root/"a"),"x.srt",SAMPLE,"","eng")
            with self.assertRaises(ValueError):
                validated_glossary({"context":"","terms":[{}]})
            _,meta=studio.target(key)
            studio.set_glossary(meta,{"context":"新", "terms":[]})
            self.assertEqual(json.loads(studio.glossary_path(meta).read_text(encoding="utf-8"))["context"],"新")

    def test_subscription_requires_real_search_even_when_completion_output_is_empty(self):
        spec = importlib.util.spec_from_file_location("hyrule_response", PACKAGE / "subscription" / "quality.py")
        quality = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(quality)
        output = {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "调研",
                  "annotations": [{"type": "url_citation", "url": "https://example.org/page"}]}]}
        events = [{"type": "response.output_item.done", "item":{"type":"web_search_call","status":"completed","action":{"type":"search"}}},
                  {"type": "response.output_item.done", "item":output},
                  {"type": "response.completed", "response":{"status":"completed","output":[]}}]
        def response(rows):
            return types.SimpleNamespace(iter_lines=lambda: ("data: " + json.dumps(e) for e in rows))
        actual = quality.response_text(response(events), True)
        self.assertEqual(actual, {"text":"调研","sources":["https://example.org/page"]})
        with self.assertRaises(ValueError):
            quality.response_text(response(events[1:]), True)
        with self.assertRaises(ValueError):
            quality.response_text(response(events[:-1]), True)


class TaskHistory(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.movie = self.root / "验收片 S01E04.mkv"
        self.movie.touch()
        self.config = {"model": "test", "effort": "high", "whisper": ""}

    def start(self, studio):
        studio.start()
        def shutdown():
            studio.close()
            studio.worker.join(10)
            self.assertFalse(studio.worker.is_alive())
        self.addCleanup(shutdown)

    def wait_for_job(self, studio, number, state):
        until = time.monotonic() + 10
        while time.monotonic() < until:
            row = next(r for r in studio.history() if r["id"] == number)
            if row["state"] == state:
                return row
            time.sleep(.02)
        self.fail(str(row))

    def test_20_upgrade_preserves_rows_and_only_recovers_the_recorded_export_time(self):
        directory = self.root / "ai_studio"
        artifact = directory / "jobs" / "1" / "export.json"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("{}", encoding="utf-8")
        os.utime(artifact, (1704067200, 1704067200))
        with closing(sqlite3.connect(directory / "studio.sqlite")) as old, old:
            old.executescript("""
                CREATE TABLE target (id TEXT PRIMARY KEY,path TEXT UNIQUE,meta TEXT,edited INTEGER DEFAULT 0);
                CREATE TABLE job (id INTEGER PRIMARY KEY,target TEXT,state TEXT,detail TEXT DEFAULT '',
                                  report TEXT DEFAULT '{}',created TEXT DEFAULT CURRENT_TIMESTAMP);
            """)
            old.execute("INSERT INTO target(id,path,meta) VALUES ('original',?,'{}')", (str(self.movie),))
            old.executemany("INSERT INTO job(target,state) VALUES ('original',?)", [("done",), ("failed",)])
        for _ in range(2):
            studio = Studio(self.root, self.config, None)
            failed, done = studio.history()
            self.assertEqual((failed["state"], failed["finished"]), ("failed", ""))
            self.assertNotIn("rendered", failed["report"])
            self.assertEqual((done["state"], done["finished"]), ("done", ""))
            self.assertEqual(done["report"]["rendered"], "2024-01-01 00:00:00")

    def test_finished_legacy_history_counts_time_filters_and_deleted_records(self):
        studio = Studio(self.root, self.config, None)
        statuses = ["completed"] * 16 + ["failed"] * 19 + ["ignored"] * 47 + ["no_audio"]
        records = {str(i): {"video_file": str(self.movie), "source": "subtitle_manual_upload", "status": status,
                            "resolved_source": "embedded", "output_path": str(self.movie.with_suffix(".srt")),
                            "add_time": f"2026-11-24T14:{i // 60:02d}:{i % 60:02d}+08:00",
                            "complete_time": "2026-11-24T14:02:00+08:00",
                            "error_message": "原错误" if status == "failed" else ""}
                   for i, status in enumerate(statuses)}
        records["83"] = {"video_file": str(self.movie), "status": "pending"}
        records["84"] = {"video_file": str(self.movie), "status": "in_progress"}
        records["85"] = {"video_file": str(self.movie), "status": {}}
        records["82"]["video_file"] = str(self.root / "已归档.旧格式")
        for _ in range(2):
            with studio.db() as db:
                task_history.import_finished(db, records)
        with studio.db() as db:
            latest = task_history.page(db)
            oldest = task_history.page(db, order="asc", limit=1)
            failures = task_history.page(db, state="failed", order="asc", offset=1, limit=1)
        self.assertEqual(latest["counts"], {"done": 16, "failed": 19, "skipped": 48})
        self.assertEqual(latest["total"], 83)
        first = oldest["jobs"][0]
        self.assertEqual((first["created"], first["finished"]), ("2026-11-24 06:00:00", "2026-11-24 06:02:00"))
        self.assertEqual((first["origin"], first["report"]["source"]), ("字幕匹配联动", "视频内嵌字幕"))
        self.assertEqual(first["report"]["files"], [self.movie.with_suffix(".srt").name])
        self.assertTrue(first["legacy"] and oldest["more"])
        last = latest["jobs"][0]
        self.assertEqual(last["created"], "2026-11-24 06:01:22")
        self.assertIn("音轨", last["detail"])
        self.assertIn("不支持", studio.manage("restart", [last["id"]])["skipped"][0]["reason"])
        self.assertEqual((failures["jobs"][0]["detail"], failures["jobs"][0]["created"]), ("原错误", "2026-11-24 06:00:17"))
        self.assertEqual(studio.targets()["targets"], [])
        self.assertEqual(studio.history(), [])
        studio.manage("delete", [first["id"]])
        with studio.db() as db:
            task_history.import_finished(db, records)
            self.assertEqual(task_history.page(db)["total"], 82)
        self.assertTrue(studio.register(self.movie))
        self.assertEqual(len(studio.targets()["targets"]), 1)

    def test_queue_cancellation_and_two_simultaneous_restart_requests(self):
        studio = Studio(self.root, self.config, None)
        key = studio.register(self.movie)
        job = studio.submit(key, automatic=True)
        self.assertEqual(studio.manage("cancel", [job, job])["changed"], [job])
        self.assertEqual(studio.submit(key, automatic=True), job)
        self.assertEqual(studio.history()[0]["state"], "cancelled")
        with ThreadPoolExecutor(max_workers=2) as pool:
            runs = list(pool.map(lambda _: studio.manage("restart", [job]), range(2)))
        self.assertEqual(sum(len(r["new_jobs"]) for r in runs), 1)
        self.assertEqual(sum(len(r["skipped"]) for r in runs), 1)
        rerun = next(r["new_jobs"][0] for r in runs if r["new_jobs"])
        self.assertEqual(studio.submit(key), rerun)
        self.assertEqual(studio.manage("delete", [rerun])["changed"], [])
        self.assertEqual(studio.manage("cancel", [rerun])["changed"], [rerun])
        self.assertGreater(studio.submit(key), rerun)
        with self.assertRaises(ValueError):
            studio.manage("cancel", [True])

    def test_cooperative_cancellation_before_publish(self):
        studio = Studio(self.root, self.config, None)
        key = studio.register(self.movie)
        studio.upload(key, "稿件.srt", SAMPLE, "", "eng")
        reached, release = threading.Event(), threading.Event()
        def translate(*args, **kwargs):
            reached.set()
            if not release.wait(5):
                raise TimeoutError()
            kwargs["progress"]("翻译下一批")
            self.fail("已取消的任务仍在执行")
        with patch("hyrule_test.studio.translate", translate):
            job = studio.submit(key)
            self.start(studio)
            try:
                self.assertTrue(reached.wait(5))
                self.assertEqual(studio.manage("cancel", [job])["changed"], [job])
                self.assertTrue(studio.history()[0]["cancelling"])
            finally:
                release.set()
            result = self.wait_for_job(studio, job, "cancelled")
        self.assertTrue(result["finished"])
        self.assertIn("人工英文稿", result["report"]["source"])
        self.assertEqual(list(self.root.glob("*.zh-en.ai.*")), [])

    def test_partial_export_recovers_after_restart_and_protects_original_subtitles(self):
        studio = Studio(self.root, self.config, None)
        original = self.movie.with_suffix(".zh-en.ai.ass")
        original.write_bytes(b"previous edition")
        key = studio.register(self.movie)
        old = studio.submit(key)
        studio.manage("cancel", [old])
        blocker_file = self.root / "blocker.mkv"
        blocker_file.touch()
        blocker = studio.submit(studio.register(blocker_file))
        rerun = studio.manage("restart", [old])["new_jobs"][0]
        work = studio.root / "jobs" / str(rerun)
        work.mkdir(parents=True)
        _, meta = studio.target(key)
        outputs = [self.movie.with_suffix(f".r{rerun}.zh-en.ai.{ext}") for ext in ("ass", "srt")]
        report = {"files": [p.name for p in outputs]}
        (work / "export.json").write_text(json.dumps({"report": report, "meta": meta, "baseline": EMPTY, "glossary": EMPTY}), encoding="utf-8")
        for out in outputs:
            (work / ("result" + out.suffix)).write_bytes(out.suffix.encode())
        outputs[0].write_bytes(b".ass")
        with studio.db() as db:
            db.execute("UPDATE job SET state='running',publishing=1 WHERE id=?", (rerun,))
        reached, release = threading.Event(), threading.Event()
        run = studio.run_job
        def process(job):
            if job["id"] == blocker:
                reached.set()
                if not release.wait(5):
                    raise TimeoutError()
                return "done", "", {}
            return run(job)
        with patch.object(studio, "run_job", process):
            self.start(studio)
            try:
                self.assertTrue(reached.wait(5))
                row = self.wait_for_job(studio, rerun, "queued")
                self.assertTrue(row["publishing"])
                self.assertEqual(studio.manage("cancel", [rerun])["changed"], [])
            finally:
                release.set()
            result = self.wait_for_job(studio, rerun, "done")
        self.assertEqual(result["report"]["files"], report["files"])
        self.assertEqual([p.read_bytes() for p in outputs], [b".ass", b".srt"])
        self.assertEqual(original.read_bytes(), b"previous edition")
        if os.name != "nt":
            self.assertEqual(outputs[1].stat().st_mode & 0o777, 0o600 | self.movie.stat().st_mode & 0o044)
        studio.manage("delete", [rerun])
        self.assertTrue(all(p.exists() for p in outputs))

    def test_restart_uses_new_files_and_retry_finishes_a_partial_pair(self):
        studio = Studio(self.root, self.config, None)
        key = studio.register(self.movie)
        studio.upload(key, "source.srt", SAMPLE, "", "eng")
        originals = [self.movie.with_suffix(".zh-en.ai." + ext) for ext in ("ass", "srt")]
        for f in originals:
            f.write_bytes(b"original")
        job = studio.submit(key)
        studio.manage("cancel", [job])
        rerun = studio.manage("restart", [job])["new_jobs"][0]
        calls, refused = [], []
        fail_at = self.movie.with_suffix(f".r{rerun}.zh-en.ai.srt")
        def translate(cues, *args, **kwargs):
            calls.append(len(cues))
            return ({c.id: item(c.id, f"第{len(calls)}版") if c.en else item(c.id, "", "sdh_drop")
                     for c in cues}, EMPTY, {})
        def write(path, data, **kwargs):
            if path == fail_at and not refused:
                refused.append(studio.manage("cancel", [rerun])["changed"])
                raise OSError("模拟第二个文件写入失败")
            return write_file(path, data, **kwargs)
        with patch("hyrule_test.studio.translate", translate), patch("hyrule_test.studio.write_file", write):
            self.start(studio)
            failed = self.wait_for_job(studio, rerun, "failed")
            self.assertIn("模拟第二个文件", failed["detail"])
            self.assertEqual(refused, [[]])
            partial = fail_at.with_suffix(".ass").read_bytes()
            self.assertFalse(fail_at.exists())
            studio.retry(rerun)
            self.wait_for_job(studio, rerun, "done")
            self.assertEqual(calls, [3])
            self.assertEqual(fail_at.with_suffix(".ass").read_bytes(), partial)
            second = studio.manage("restart", [rerun])["new_jobs"][0]
            final = self.wait_for_job(studio, second, "done")
        self.assertEqual(calls, [3, 3])
        self.assertIn("第1版", fail_at.read_text(encoding="utf-8-sig"))
        self.assertIn("第2版", (self.root / final["report"]["files"][1]).read_text(encoding="utf-8-sig"))
        self.assertEqual([f.read_bytes() for f in originals], [b"original", b"original"])


if __name__ == "__main__":
    unittest.main()
