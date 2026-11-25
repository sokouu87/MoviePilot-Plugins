"""本地文件索引、持久任务队列及译稿发布。"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

import httpx
from filelock import FileLock, Timeout

from .bilingual import combine
from .media import VIDEO, embedded_chinese, english_subtitles, metadata, probe_streams, source_cues
from .subtitles import MAX_SUBTITLE, parse, render, save_json, upload_member, write_file
from .translation import DEFAULT_BANNED, read_state, translate, validated_glossary
from . import disc, task_history

MODEL = "gpt-6.2-astra"
BRIDGE = "http://127.0.0.1:18743/v1"
EMPTY = {"context": "", "terms": []}


class CancelledJob(Exception):
    pass


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class Studio:
    def __init__(self, directory, config, key, *, bridge=BRIDGE):
        self.root = Path(directory) / "ai_studio"
        self.root.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.key, self.bridge = key, bridge.rstrip("/")
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.worker = None
        self.current_job = None
        with self.db() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS target (
                    id TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE, meta TEXT NOT NULL, edited INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS job (
                    id INTEGER PRIMARY KEY, target TEXT NOT NULL REFERENCES target(id), state TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '', report TEXT NOT NULL DEFAULT '{}',
                    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE UNIQUE INDEX IF NOT EXISTS active_job ON job(target) WHERE state IN ('queued','running');
                CREATE TABLE IF NOT EXISTS manuscript(target TEXT PRIMARY KEY REFERENCES target(id), extension TEXT NOT NULL);
            """)
            task_history.migrate(conn, self.root / "jobs")

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.root / "studio.sqlite", timeout=20)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def register(self, path, meta=None):
        path = Path(path)
        if not path.is_absolute():
            return None
        folder = disc.structure(path) if path.is_dir() else None
        if folder is None and (path.suffix.lower() not in VIDEO or not path.is_file()):
            return None
        if folder is not None:
            name, year = disc.title(path)
            meta = {**(meta or metadata(path, title=name, year=year)), "disc_folder": True}
        path = path.absolute()
        key = digest(os.path.normcase(str(path)))
        with self.db() as conn:
            if meta is None:
                conn.execute("INSERT INTO target(id,path,meta) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET listed=1 WHERE target.listed=0",
                             (key, str(path), json.dumps(metadata(path))))
            else:
                conn.execute("""INSERT INTO target(id,path,meta) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET listed=1,
                    meta=json_set(CASE WHEN target.edited=0 THEN excluded.meta ELSE target.meta END, '$.added',
                    max(coalesce(json_extract(target.meta,'$.added'),''),coalesce(json_extract(excluded.meta,'$.added'),'')))""",
                    (key, str(path), json.dumps(meta, ensure_ascii=False)))
        return key

    def override_meta(self, key, meta):
        with self.db() as conn:
            conn.execute("UPDATE target SET meta=?,edited=1 WHERE id=?", (json.dumps(meta, ensure_ascii=False), key))

    def target(self, key):
        with self.db() as conn:
            row = conn.execute("SELECT * FROM target WHERE id=?", (key,)).fetchone()
        if not row:
            raise ValueError("目标不存在，请刷新媒体列表")
        path = Path(row["path"])
        meta = json.loads(row["meta"])
        folder = bool(meta.get("disc_folder")) and disc.structure(path) is not None
        if not path.is_absolute() or (not folder and (path.suffix.lower() not in VIDEO or not path.is_file())):
            raise ValueError("目标文件已移动或离线，请刷新媒体列表")
        if meta.get("library_root") and not path.resolve().is_relative_to(Path(meta["library_root"]).resolve()):
            raise ValueError("媒体文件已移出可访问的库目录")
        return path, meta

    def targets(self, query="", offset=0):
        pattern = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        with self.db() as conn:
            rows = conn.execute(r"SELECT * FROM target WHERE listed=1 AND (path LIKE ? ESCAPE '\' OR meta LIKE ? ESCAPE '\') ORDER BY rowid DESC LIMIT 51 OFFSET ?",
                                (pattern, pattern, offset)).fetchall()
        results = []
        for row in rows[:50]:
            results.append(self.describe(row["id"], Path(row["path"]), json.loads(row["meta"])))
        return {"targets": results, "more": len(rows) > 50}

    @staticmethod
    def describe(key, path, meta):
        season = meta["season"] if meta["season"] is not None else 1
        episode = f"S{season:02}E{meta['episode']:02}" if meta["episode"] is not None else ""
        label = " ".join(filter(None, (meta["title"], meta["year"], episode)))
        return {"id": key, "label": label, "file": path.name, "search_url": "https://subhd.tv/search/" + quote(label, safe=""), "meta": meta}

    def submit(self, key, automatic=False):
        video, meta = self.target(key)
        if disc.is_original(video) or meta.get("disc_folder"):
            raise ValueError("原盘请前往 SubHD 下载后手动上传")
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            active = conn.execute("SELECT id FROM job WHERE target=? AND state IN ('queued','running')", (key,)).fetchone()
            if active:
                return active["id"]
            if automatic:
                last = conn.execute("SELECT id,state FROM job WHERE target=? AND hidden=0 AND legacy_id IS NULL ORDER BY id DESC LIMIT 1", (key,)).fetchone()
                if last and (last["state"] in ("failed", "cancelled") or all(video.with_name(f"{video.stem}.zh-en.ai.{ext}").is_file() for ext in ("ass","srt"))):
                    return last["id"]
            job = conn.execute("INSERT INTO job(target,state,origin) VALUES (?,'queued',?)", (key,"入库触发" if automatic else "手动提交")).lastrowid
        self.wake.set()
        return job

    def history(self):
        with self.db() as conn:
            return task_history.page(conn, limit=80, native_only=True)["jobs"]

    def manage(self, action, ids):
        with self.db() as conn:
            result = task_history.operate(conn, action, ids)
        self.wake.set()
        return result

    def glossary_path(self, meta):
        title = re.sub(r"[^a-z0-9\u0080-\uffff]+", " ", meta["title"].casefold()).strip()
        identity = meta["series_id"] or f"{title}|{meta['year']}"
        return self.root / "series" / digest(identity) / "glossary.json"

    def upload(self, key, filename, data, member, role):
        video, meta = self.target(key)
        ext, contents = upload_member(filename, data, member)
        if not ext:
            return {"members": contents}
        rows = parse(contents, ext)
        if role not in ("eng", "zh-Hans", "zh-Hant", "zh-en"):
            raise ValueError("字幕语言无效")
        path = (video / f"{video.name}.{role}.manual{ext}" if meta.get("disc_folder")
                else video.with_name(f"{video.stem}.{role}.manual{ext}"))
        # 英文稿有明确用途，下次翻译优先读取。人工成品永远单独保存。
        try:
            write_file(path, contents, mode=0o600 | (video.stat().st_mode & 0o044))
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != contents:
                raise ValueError(f"已有不同的同名字幕，已保留原文件：{path.name}")
        if role == "eng" and not (meta.get("disc_folder") or disc.is_original(video)):
            with self.db() as conn:
                conn.execute("INSERT OR REPLACE INTO manuscript(target,extension) VALUES (?,?)", (key, ext))
        return {"file": path.name, "cues": len(rows)}

    def ask(self, stage, instruction, data, schema, search):
        self.check_running()
        if not self.key:
            raise ValueError("尚未配置订阅线路密钥，可继承现有 AutoSubv3 的本机 OAuth 线路")
        request = {"model": self.config["model"], "effort": self.config["effort"], "instructions": instruction,
                   "input": json.dumps(data, ensure_ascii=False, separators=(",", ":")), "schema": schema, "search": search}
        with httpx.Client(timeout=httpx.Timeout(510, connect=8), trust_env=False) as client:
            try:
                result = client.post(self.bridge + "/subtitle", headers={"Authorization": "Bearer " + self.key}, json=request)
            except httpx.RequestError as exc:
                raise ValueError("无法连接本机订阅服务，请检查服务运行状态") from exc
        if result.status_code == 404:
            raise ValueError("订阅服务需升级至 2.0，旧服务只支持简单文本翻译")
        if result.status_code != 200:
            detail = {401: "请检查本地线路密钥或重新授权", 403: "订阅无权使用此模型", 429: "套餐已限流，请稍后重试",
                      413: "整集文本超过线路容量"}.get(result.status_code, "请检查订阅线路与模型支持")
            if result.status_code == 502:
                message = result.json().get("error", {}).get("message", "") if "json" in result.headers.get("content-type", "") else ""
                if message.startswith(("ChatGPT ", "本次调研", "订阅未完成", "未收到")):
                    detail = message
            raise ValueError(f"{stage} HTTP {result.status_code} · {detail}")
        response = result.json()
        self.check_running()
        return (json.loads(response["text"]) if schema else response["text"]), response["sources"]

    def check_running(self):
        if self.stop.is_set():
            raise InterruptedError("插件已暂停")
        if self.current_job is not None:
            with self.db() as conn:
                row = conn.execute("SELECT cancel_requested FROM job WHERE id=?", (self.current_job,)).fetchone()
            if row and row[0]:
                raise CancelledJob()

    def run_job(self, job):
        key = job["target"]
        video, meta = self.target(key)
        if disc.is_original(video) or meta.get("disc_folder"):
            return "skipped", "原盘请使用手动字幕", {}
        number = job["id"]
        variant = f".r{number}" if job["rerun_of"] is not None else ""
        out = [video.with_name(f"{video.stem}{variant}.zh-en.ai.{ext}") for ext in ("ass", "srt")]
        workspace = self.root / "jobs" / str(number)
        workspace.mkdir(parents=True, exist_ok=True)
        manifest = workspace / "export.json"

        def progress(message):
            self.check_running()
            with self.db() as conn:
                conn.execute("UPDATE job SET detail=? WHERE id=?", (message, number))

        if not manifest.is_file():
            if any(p.exists() or p.is_symlink() for p in out):
                return "skipped", "已有同名 AI 字幕，可在查看数据中重新生成独立版本", {}
            progress("选择字幕原稿")
            with self.db() as conn:
                picked = conn.execute("SELECT extension FROM manuscript WHERE target=?", (key,)).fetchone()
            extensions = [picked[0]] if picked else [".srt", ".ass", ".ssa"]
            manual = next((f for ext in extensions
                           if (f := video.with_name(video.stem + ".eng.manual" + ext)).is_file() and not f.is_symlink()), None)
            if picked and not manual:
                raise ValueError("选用的人工英文稿已被移动，请重新上传")
            english = None
            if manual:
                if manual.stat().st_size > MAX_SUBTITLE:
                    raise ValueError("英文原稿超过 12 MiB")
                english = parse(manual.read_bytes(), manual.suffix), "人工英文稿 · " + manual.name
            try:
                streams = probe_streams(video)
            except (OSError, ValueError, subprocess.SubprocessError):
                english = english or english_subtitles(video, [])
                if not english:
                    raise
                streams = []
            chinese = embedded_chinese(video, streams)
            model = self.config["model"] + "/" + self.config["effort"]
            if chinese:
                cues, script, source = chinese
                english = english or english_subtitles(video, streams)
                report = {"source": source, "cues": len(cues), "translation_mode": "embedded_chinese"}
                if english:
                    report["english_source"] = english[1]
                with self.db() as conn:
                    conn.execute("UPDATE job SET report=? WHERE id=?", (json.dumps(report, ensure_ascii=False), number))
                cues, items, stats = combine(cues, script, english[0] if english else [], meta, self.ask,
                                             workspace / "english-checkpoint.json", model=model, progress=progress)
                baseline = glossary = None
                report.update(stats, cues=len(cues))
                if stats["generated_english"]:
                    report["model"] = self.config["model"]
            else:
                cues, source = english or source_cues(video, self.config["whisper"], progress, streams=streams)
                report = {"source": source, "model": self.config["model"], "cues": len(cues)}
                with self.db() as conn:
                    conn.execute("UPDATE job SET report=? WHERE id=?", (json.dumps(report, ensure_ascii=False), number))
                baseline = validated_glossary(read_state(self.glossary_path(meta), EMPTY))
                banned = [w.strip() for w in re.split(r"[,，、\n]", self.config.get("banned", DEFAULT_BANNED)) if w.strip()]
                items, glossary, checks = translate(cues, meta, baseline, self.ask, workspace / "checkpoint.json",
                                                    model=model, banned=banned, progress=progress)
                report.update(checks)
            progress("校验双语字幕并写入")
            for ext, data in zip(("ass", "srt"), render(cues, items)):
                write_file(workspace / ("result." + ext), data, replace=True)
            report["files"] = [p.name for p in out]
            save_json(manifest, {"report": report, "baseline": baseline, "glossary": glossary, "meta": meta})

        bundle = read_state(manifest, {})
        if not job["publishing"]:
            self.check_running()
        with self.db() as conn:
            if not conn.execute("UPDATE job SET publishing=1 WHERE id=? AND state='running' AND cancel_requested=0", (number,)).rowcount:
                raise CancelledJob()
        for target in out:
            data = (workspace / ("result" + target.suffix)).read_bytes()
            try:
                write_file(target, data, mode=0o600 | (video.stat().st_mode & 0o044))
            except FileExistsError:
                if target.is_symlink() or target.read_bytes() != data:
                    raise ValueError("目标同名文件已变化，保留已有文件，请核对后重试")
        if bundle["glossary"] is not None:
            self.set_glossary(bundle["meta"], bundle["glossary"], baseline=bundle["baseline"])
        return "done", "已生成双语 ASS 和 SRT", bundle["report"]

    def set_glossary(self, meta, value, baseline=None):
        path = self.glossary_path(meta)
        path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(path) + ".lock", timeout=15):
            value = validated_glossary(value)
            current = read_state(path, EMPTY)
            if baseline is not None and current != baseline:
                # 人工编辑优先，保留翻译期间用户做的改名或删除。
                known = {t["en"].casefold() for t in baseline["terms"] + current["terms"]}
                value = {"context": current["context"], "terms": current["terms"] + [t for t in value["terms"] if t["en"].casefold() not in known]}
            save_json(path, value)

    def retry(self, number):
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""SELECT j.target,t.path FROM job j JOIN target t ON t.id=j.target
                WHERE j.id=? AND j.state='failed' AND j.hidden=0 AND j.legacy_id IS NULL""", (number,)).fetchone()
            if not row:
                raise ValueError("仅失败的任务可续跑")
            if disc.is_original(row["path"]):
                raise ValueError("原盘请使用手动字幕")
            if conn.execute("SELECT 1 FROM job WHERE target=? AND state IN ('running','queued')", (row["target"],)).fetchone():
                raise ValueError("同一目标已有任务")
            conn.execute("UPDATE job SET state='queued',detail='',finished='',cancel_requested=0,publishing=0 WHERE id=?", (number,))
        self.wake.set()

    def start(self):
        self.worker = threading.Thread(target=self.consume, name="hyrule-subtitles", daemon=True)
        self.worker.start()

    def consume(self):
        # 插件热重载与旧线程退出可以重叠。持有文件锁的工作线程独占队列和断点恢复。
        lock = FileLock(str(self.root / "worker.lock"))
        while not self.stop.is_set():
            try:
                lock.acquire(timeout=1)
                break
            except Timeout:
                continue
        else:
            return
        try:
            with self.db() as conn:
                conn.execute("UPDATE job SET state='cancelled',finished=CURRENT_TIMESTAMP,detail='已取消',cancel_requested=0 WHERE state='running' AND cancel_requested=1 AND publishing=0")
                # 发布可能恰好在两份字幕之间中断，恢复时须继续发布，期间保持不可取消。
                conn.execute("UPDATE job SET state='queued',cancel_requested=0 WHERE state='running'")
            while not self.stop.is_set():
                with self.db() as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    job = conn.execute("SELECT * FROM job WHERE state='queued' ORDER BY id LIMIT 1").fetchone()
                    if job:
                        conn.execute("UPDATE job SET state='running' WHERE id=?", (job["id"],))
                if not job:
                    self.wake.wait(5)
                    self.wake.clear()
                    continue
                self.current_job = job["id"]
                try:
                    state, detail, report = self.run_job(job)
                except CancelledJob:
                    state, detail, report = "cancelled", "已取消翻译", None
                except InterruptedError:
                    state, detail, report = "queued", "等待继续", None
                except Exception as exc:
                    state, detail, report = "failed", str(exc)[:500], None
                with self.db() as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    flags = conn.execute("SELECT cancel_requested,publishing FROM job WHERE id=?", (job["id"],)).fetchone()
                    if flags[0] and not flags[1]:
                        state, detail, report = "cancelled", "已取消翻译", None
                    conn.execute("""UPDATE job SET state=?,detail=?,report=COALESCE(?,report),
                                    finished=CASE WHEN ?='queued' THEN '' ELSE CURRENT_TIMESTAMP END,
                                    cancel_requested=0,publishing=CASE WHEN ?='queued' THEN publishing ELSE 0 END WHERE id=?""",
                                 (state, detail, json.dumps(report, ensure_ascii=False) if report is not None else None, state, state, job["id"]))
                self.current_job = None
        finally:
            lock.release()

    def close(self):
        self.stop.set()
        self.wake.set()
