"""海拉鲁 AI 字幕。V2/V3 使用同一个插件标识和发行包。"""
import json
import threading
import zipfile
from pathlib import Path

from fastapi import HTTPException, Request
from app.plugins import _PluginBase
from app.schemas.types import EventType
from app.db.models.transferhistory import TransferHistory
try:
    from app.sdk.events import eventmanager
    from app.sdk.logging import logger
    from app.db.session import SessionFactory
except ImportError:
    from app.core.event import eventmanager
    from app.log import logger
    SessionFactory = None

from .media import metadata
from .studio import BRIDGE, EMPTY, MODEL, Studio
from .translation import DEFAULT_BANNED, read_state
from . import task_history

DEFAULT = {"enabled": False, "auto_translate": True, "show_sidebar_nav": True, "model": MODEL, "effort": "high",
           "whisper": "", "bridge_key": "", "banned": DEFAULT_BANNED, "manual_dirs": ""}
MAX_UPLOAD = 24 * 1024 * 1024


def field(obj, name, default=None):
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def series_identity(info):
    identity = field(info, "media_id") or field(info, "tmdbid") or field(info, "tmdb_id")
    if identity:
        kind = field(info, "type", "")
        source = field(info, "media_source") or "tmdb"
        return f"{getattr(kind, 'value', kind)}|{getattr(source, 'value', source)}|{identity}"
    return ""


class SubtitleManualUpload(_PluginBase):
    plugin_name = "海拉鲁 AI 字幕"
    plugin_desc = "用 ChatGPT 订阅调研、精翻并审校双语字幕，支持前往 SubHD 官网下载后手动上传。"
    plugin_icon = "https://raw.githubusercontent.com/sokouu87/moviepilot-plugins/main/icons/hyrule-subtitle-master.png"
    plugin_version = "2.1.1"
    plugin_author = "sokouu87"
    author_url = "https://github.com/sokouu87"
    plugin_config_prefix = "subtitlemanualupload_"
    plugin_order = 48
    auth_level = 1
    _studio = None
    _enabled = False
    # 已安装的 AutoSubv3 用这三个字段判断本插件是否接管入库。
    _auto_search_on_transfer = False
    _ai_link_enabled = True
    _auto_transfer_subtitle_strategy = "ai_source_only"

    def init_plugin(self, config=None):
        self.stop_service()
        original = config or {}
        current = {**DEFAULT, **{k: v for k, v in original.items() if k in DEFAULT}}
        current["auto_translate"] = original.get("auto_translate", original.get("auto_search_on_transfer", True))
        if "manual_dirs" not in original and original.get("manual_strm_enabled"):
            dirs = original.get("manual_strm_paths", "")
            current["manual_dirs"] = "\n".join(dirs) if isinstance(dirs, list) else str(dirs or "")
        self._config = current
        self._enabled = bool(current["enabled"])
        self._auto_search_on_transfer = self._enabled and bool(current["auto_translate"])
        self._index_lock = threading.Lock()
        self._indexing = False
        self._index_error = ""
        self._history_error = ""
        if not self._enabled:
            return
        legacy = self.get_config("AutoSubv3") or {}
        key = current.get("bridge_key") or ""
        if not key:
            endpoints = legacy.get("openai_endpoints") or []
            if isinstance(endpoints, str):
                try:
                    endpoints = json.loads(endpoints)
                except ValueError:
                    endpoints = []
            for item in endpoints if isinstance(endpoints, list) else []:
                if isinstance(item, dict) and item.get("model") == "chatgpt-subscription" and str(item.get("api_url", "")).rstrip("/") == BRIDGE:
                    key = item.get("api_key")
                    break
            if not key and legacy.get("openai_model") == "chatgpt-subscription" and str(legacy.get("openai_url", "")).rstrip("/") == BRIDGE:
                key = legacy.get("openai_key")
        if not current["whisper"]:
            cache = self.get_data_path("AutoSubv3") / "faster-whisper-models" / "cache"
            candidates = sorted(cache.glob("models--*/snapshots/*/model.bin"), key=lambda p: ("large-v3" not in str(p), str(p)))
            if candidates:
                current["whisper"] = str(candidates[0].parent)
        self._studio = Studio(self.get_data_path(), current, key)
        self._studio.start()
        self._refresh()

    def stop_service(self):
        if self._studio:
            self._studio.close()
            self._studio = None

    def get_state(self):
        return self._enabled

    @staticmethod
    def get_render_mode():
        return "vue", "dist/assets"

    @staticmethod
    def get_command():
        return []

    def get_page(self):
        return []

    def get_form(self):
        return [], dict(DEFAULT)

    def get_sidebar_nav(self):
        return ([{"nav_key": "main", "title": self.plugin_name, "icon": "mdi-subtitles-outline", "section": "organize",
                  "permission": "manage", "order": 48}] if self._enabled and self._config.get("show_sidebar_nav") else [])

    def _active(self):
        if not self._studio:
            raise HTTPException(409, "请先启用海拉鲁 AI 字幕")
        return self._studio

    def _refresh(self):
        studio = self._active()
        lock = self._index_lock
        if not lock.acquire(blocking=False):
            return
        self._indexing = True
        self._index_error = ""

        def index():
            session = None
            try:
                try:
                    old = self.get_data("tasks", plugin_id="AutoSubv3")
                    with studio.db() as db:
                        task_history.import_finished(db, old)
                    self._history_error = ""
                except Exception as exc:
                    self._history_error = "旧联动任务记录暂时无法读取"
                    logger.warning("[海拉鲁 AI 字幕] 旧任务读取失败：%s", type(exc).__name__)
                session = SessionFactory() if SessionFactory else None
                page, previous = 1, None
                while not studio.stop.is_set():
                    rows = TransferHistory.list_by_page(db=session, page=page, count=250, status=True)
                    if not rows:
                        break
                    signature = (rows[0].id, rows[-1].id)
                    if signature == previous:
                        raise ValueError("整理历史的分页没有前进")
                    previous = signature
                    for r in rows:
                        if studio.stop.is_set():
                            return
                        item = r.dest_fileitem or {}
                        path = Path(item.get("path") or r.dest or "")
                        if (item.get("storage") or getattr(r, "dest_storage", None) or "local") == "local":
                            studio.register(path, metadata(path, title=r.title, year=r.year, season=r.seasons,
                                                          episode=r.episodes, series_id=series_identity(r)))
                    if len(rows) < 250:
                        break
                    page += 1
                for line in str(studio.config["manual_dirs"] or "").splitlines():
                    folder = Path(line.strip())
                    if not line.strip() or not folder.is_absolute() or not folder.is_dir():
                        continue
                    for file in folder.rglob("*.strm"):
                        if studio.stop.is_set():
                            return
                        studio.register(file)
            except Exception as exc:
                if self._studio is studio:
                    self._index_error = f"索引读取失败：{type(exc).__name__}"
                logger.warning("[海拉鲁 AI 字幕] 整理历史读取失败：%s", type(exc).__name__)
            finally:
                if session is not None:
                    session.close()
                if self._studio is studio:
                    self._indexing = False
                lock.release()
        threading.Thread(target=index, name="hyrule-media-index", daemon=True).start()

    @eventmanager.register(EventType.TransferComplete)
    def on_transfer(self, event):
        studio = self._studio
        if not studio:
            return
        data = field(event, "event_data") or {}
        transfer = field(data, "transferinfo")
        if not transfer or field(transfer, "success", True) is False:
            return
        item = field(transfer, "target_item") or field(transfer, "target_diritem")
        if field(item, "storage", "local") not in (None, "", "local"):
            return
        files = field(transfer, "file_list_new") or []
        if isinstance(files, (str, Path)):
            files = [files]
        fallback = field(item, "path") or field(transfer, "target_path")
        if not files and fallback:
            files = [fallback]
        info, meta = field(data, "mediainfo"), field(data, "meta")
        for file in files:
            if not isinstance(file, (str, Path)):
                continue
            path = Path(file)
            m = metadata(path, title=field(info, "title") or field(meta, "name"), year=field(info, "year"),
                         season=field(meta, "begin_season") if len(files) == 1 else None,
                         episode=field(meta, "begin_episode") if len(files) == 1 else None, series_id=series_identity(info))
            key = studio.register(path, m)
            if key and self._auto_search_on_transfer:
                studio.submit(key, automatic=True)

    def get_api(self):
        routes = [("/targets", self.targets, "GET"), ("/target", self.target, "GET"), ("/refresh", self.refresh, "POST"), ("/jobs", self.jobs, "GET"),
                  ("/translate", self.submit, "POST"), ("/retry", self.retry, "POST"), ("/upload", self.upload, "POST"),
                  ("/glossary", self.glossary, "GET"), ("/glossary", self.save_glossary, "POST"),
                  ("/metadata", self.save_metadata, "POST"), ("/task_page", self.task_page, "GET"),
                  ("/task_actions", self.task_actions, "POST")]
        return [{"path": p, "endpoint": f, "methods": [m], "auth": "bear", "summary": f.__doc__ or self.plugin_name} for p, f, m in routes]

    def targets(self, q: str = "", offset: int = 0):
        return {**self._active().targets(q[:240], max(0, offset)), "indexing": self._indexing, "error": self._index_error}

    def target(self, id: str):
        studio = self._active()
        return studio.describe(id, *self._check(studio.target, id))

    def refresh(self):
        self._refresh()
        return {"ok": True}

    def jobs(self):
        studio = self._active()
        return {"jobs": studio.history(), "configured": bool(studio.key), "model": studio.config["model"], "effort": studio.config["effort"]}

    def task_page(self, state: str = "all", order: str = "desc", offset: int = 0):
        studio = self._active()
        with studio.db() as conn:
            result = self._check(task_history.page, conn, state, order, offset)
        return {**result, "auto": self._auto_search_on_transfer, "model": studio.config["model"],
                "effort": studio.config["effort"], "history_error": self._history_error}

    def task_actions(self, body: dict):
        return self._check(self._active().manage, body.get("action"), body.get("ids"))

    @staticmethod
    def _check(call, *args):
        try:
            return call(*args)
        except (ValueError, OSError, zipfile.BadZipFile, NotImplementedError) as exc:
            raise HTTPException(422, str(exc)[:300]) from exc

    def submit(self, body: dict):
        return {"id": self._check(self._active().submit, str(body.get("target", "")))}

    def retry(self, body: dict):
        self._check(self._active().retry, body.get("id"))
        return {"ok": True}

    def glossary(self, target: str):
        studio = self._active()
        _, meta = self._check(studio.target, target)
        return {"glossary": read_state(studio.glossary_path(meta), EMPTY)}

    def save_glossary(self, body: dict):
        studio = self._active()
        _, meta = self._check(studio.target, str(body.get("target", "")))
        self._check(studio.set_glossary, meta, body.get("glossary"))
        return {"ok": True}

    def save_metadata(self, body: dict):
        studio = self._active()
        key = str(body.get("target", ""))
        path, old = self._check(studio.target, key)
        edits = {k: str(body.get(k) or "").strip()[:180] for k in ("title", "year", "season", "episode")}
        meta = metadata(path, **edits, series_id=old.get("series_id", ""))
        studio.override_meta(key, meta)
        return {"ok": True}

    async def upload(self, request: Request):
        studio = self._active()
        size = request.headers.get("content-length")
        if size and size.isdigit() and int(size) > MAX_UPLOAD + 65536:
            raise HTTPException(413, "上传超过 24 MiB")
        async with request.form() as form:
            f = form.get("file")
            if not getattr(f, "filename", None):
                raise HTTPException(422, "请选择字幕文件")
            data = await f.read(MAX_UPLOAD + 1)
            if len(data) > MAX_UPLOAD:
                raise HTTPException(413, "上传超过 24 MiB")
            from starlette.concurrency import run_in_threadpool
            return await run_in_threadpool(self._check, studio.upload, str(form.get("target", "")), f.filename,
                                           data, str(form.get("member") or ""), str(form.get("role") or "zh-Hans"))
