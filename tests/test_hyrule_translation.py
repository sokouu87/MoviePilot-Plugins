"""新字幕管线的轴、断点与非覆盖写入回归。无需 MoviePilot 运行环境。"""
import codecs
import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "plugins.v3" / "subtitlemanualupload"
module = types.ModuleType("hyrule_test")
module.__path__ = [str(PACKAGE)]
sys.modules[module.__name__] = module
from hyrule_test.subtitles import Cue, ass_time, parse, render, upload_member, write_file
from hyrule_test.translation import batches, check_item, translate, validated_glossary
from hyrule_test.studio import EMPTY, Studio


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


if __name__ == "__main__":
    unittest.main()
