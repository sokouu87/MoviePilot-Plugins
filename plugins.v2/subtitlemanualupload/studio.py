"""本地文件索引、持久任务队列及译稿发布。"""
import hashlib
import json
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

import httpx
from filelock import FileLock, Timeout

from .media import VIDEO, metadata, source_cues
from .subtitles import MAX_SUBTITLE, parse, render, save_json, upload_member, write_file
from .translation import DEFAULT_BANNED, read_state, translate, validated_glossary

MODEL = "gpt-6.2-astra"
BRIDGE = "http://127.0.0.1:18743/v1"
EMPTY = {"context": "", "terms": []}


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
        if not path.is_absolute() or path.suffix.lower() not in VIDEO or not path.is_file():
            return None
        path = path.absolute()
        key = digest(os.path.normcase(str(path)))
        with self.db() as conn:
            if meta is None:
                conn.execute("INSERT OR IGNORE INTO target(id,path,meta) VALUES (?,?,?)", (key, str(path), json.dumps(metadata(path))))
            else:
                conn.execute("INSERT INTO target(id,path,meta) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET meta=excluded.meta WHERE target.edited=0",
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
        if path.suffix.lower() not in VIDEO or not path.is_file():
            raise ValueError("目标文件已移动或离线，请刷新媒体列表")
        return path, json.loads(row["meta"])

    def targets(self, query="", offset=0):
        pattern = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        with self.db() as conn:
            rows = conn.execute(r"SELECT * FROM target WHERE path LIKE ? ESCAPE '\' OR meta LIKE ? ESCAPE '\' ORDER BY rowid DESC LIMIT 51 OFFSET ?",
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
        video, _ = self.target(key)
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            active = conn.execute("SELECT id FROM job WHERE target=? AND state IN ('queued','running')", (key,)).fetchone()
            if active:
                return active["id"]
            if automatic:
                last = conn.execute("SELECT id,state FROM job WHERE target=? ORDER BY id DESC LIMIT 1", (key,)).fetchone()
                if last and (last["state"] == "failed" or all(video.with_name(f"{video.stem}.zh-en.ai.{ext}").is_file() for ext in ("ass","srt"))):
                    return last["id"]
            job = conn.execute("INSERT INTO job(target,state) VALUES (?,'queued')", (key,)).lastrowid
        self.wake.set()
        return job

    def history(self):
        with self.db() as conn:
            rows = conn.execute("SELECT j.*,t.path FROM job j JOIN target t ON t.id=j.target ORDER BY j.id DESC LIMIT 80").fetchall()
        return [{**{k: row[k] for k in ("id", "target", "state", "detail", "created")}, "file": Path(row["path"]).name,
                 "report": json.loads(row["report"])} for row in rows]

    def glossary_path(self, meta):
        title = re.sub(r"[^a-z0-9\u0080-\uffff]+", " ", meta["title"].casefold()).strip()
        identity = meta["series_id"] or f"{title}|{meta['year']}"
        return self.root / "series" / digest(identity) / "glossary.json"

    def upload(self, key, filename, data, member, role):
        video, _ = self.target(key)
        ext, contents = upload_member(filename, data, member)
        if not ext:
            return {"members": contents}
        rows = parse(contents, ext)
        if role not in ("eng", "zh-Hans", "zh-Hant", "zh-en"):
            raise ValueError("字幕语言无效")
        path = video.with_name(f"{video.stem}.{role}.manual{ext}")
        # 英文稿有明确用途，下次翻译优先读取。人工成品永远单独保存。
        try:
            write_file(path, contents, mode=0o600 | (video.stat().st_mode & 0o044))
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != contents:
                raise ValueError(f"已有不同的同名字幕，已保留原文件：{path.name}")
        if role == "eng":
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
        return (json.loads(response["text"]) if schema else response["text"]), response["sources"]

    def check_running(self):
        if self.stop.is_set():
            raise InterruptedError("插件已暂停")

    def run_job(self, job):
        key = job["target"]
        video, meta = self.target(key)
        number = job["id"]
        out = [video.with_name(f"{video.stem}.zh-en.ai.{ext}") for ext in ("ass", "srt")]
        workspace = self.root / "jobs" / str(number)
        workspace.mkdir(parents=True, exist_ok=True)
        manifest = workspace / "export.json"

        def progress(message):
            self.check_running()
            with self.db() as conn:
                conn.execute("UPDATE job SET detail=? WHERE id=?", (message, number))

        if not manifest.is_file():
            if any(p.exists() or p.is_symlink() for p in out):
                return "skipped", "已保留同名 AI 字幕，如需重译请先移走同名文件", {}
            progress("选择英文原稿")
            with self.db() as conn:
                picked = conn.execute("SELECT extension FROM manuscript WHERE target=?", (key,)).fetchone()
            extensions = [picked[0]] if picked else [".srt", ".ass", ".ssa"]
            manual = next((f for ext in extensions
                           if (f := video.with_name(video.stem + ".eng.manual" + ext)).is_file() and not f.is_symlink()), None)
            if picked and not manual:
                raise ValueError("选用的人工英文稿已被移动，请重新上传")
            if manual:
                if manual.stat().st_size > MAX_SUBTITLE:
                    raise ValueError("英文原稿超过 12 MiB")
                cues, source = parse(manual.read_bytes(), manual.suffix), "人工英文稿 · " + manual.name
            else:
                cues, source = source_cues(video, self.config["whisper"], progress)
            glossary_path = self.glossary_path(meta)
            baseline = validated_glossary(read_state(glossary_path, EMPTY))
            banned = [w.strip() for w in re.split(r"[,，、\n]", self.config.get("banned", DEFAULT_BANNED)) if w.strip()]
            items, glossary, report = translate(cues, meta, baseline, self.ask, workspace / "checkpoint.json",
                                               model=self.config["model"] + "/" + self.config["effort"], banned=banned, progress=progress)
            progress("校验双语字幕并写入")
            for ext, data in zip(("ass", "srt"), render(cues, items)):
                write_file(workspace / ("result." + ext), data, replace=True)
            report.update(source=source, model=self.config["model"], cues=len(cues), files=[p.name for p in out])
            save_json(manifest, {"report": report, "baseline": baseline, "glossary": glossary, "meta": meta})

        bundle = read_state(manifest, {})
        for target in out:
            self.check_running()
            data = (workspace / ("result" + target.suffix)).read_bytes()
            try:
                write_file(target, data, mode=0o600 | (video.stat().st_mode & 0o044))
            except FileExistsError:
                if target.is_symlink() or target.read_bytes() != data:
                    raise ValueError("目标同名文件已变化，保留已有文件，请核对后重试")
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
            row = conn.execute("SELECT target FROM job WHERE id=? AND state='failed'", (number,)).fetchone()
            if not row:
                raise ValueError("仅失败的任务可续跑")
            if conn.execute("SELECT 1 FROM job WHERE target=? AND state IN ('running','queued')", (row["target"],)).fetchone():
                raise ValueError("同一目标已有任务")
            conn.execute("UPDATE job SET state='queued',detail='' WHERE id=?", (number,))
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
                conn.execute("UPDATE job SET state='queued' WHERE state='running'")
            while not self.stop.is_set():
                with self.db() as conn:
                    job = conn.execute("SELECT * FROM job WHERE state='queued' ORDER BY id LIMIT 1").fetchone()
                    if job:
                        conn.execute("UPDATE job SET state='running' WHERE id=?", (job["id"],))
                if not job:
                    self.wake.wait(5)
                    self.wake.clear()
                    continue
                try:
                    state, detail, report = self.run_job(job)
                except InterruptedError:
                    state, detail, report = "queued", "等待继续", {}
                except Exception as exc:
                    state, detail, report = "failed", str(exc)[:500], {}
                with self.db() as conn:
                    conn.execute("UPDATE job SET state=?,detail=?,report=? WHERE id=?",
                                 (state, detail, json.dumps(report, ensure_ascii=False), job["id"]))
        finally:
            lock.release()

    def close(self):
        self.stop.set()
        self.wake.set()
