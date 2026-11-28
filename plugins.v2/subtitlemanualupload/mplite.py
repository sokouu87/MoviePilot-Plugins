"""将 MPLite 的原生字幕界面接到海拉鲁的统一片库和任务队列。"""
import json
import re
import threading
import time
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

from . import task_history
from .emby_subtitles import EmbySubtitles
from .media import chinese_script, english_text
from .subtitles import MAX_SUBTITLE, parse, upload_member

KINDS = {"movie": "Movie", "tv": "Episode"}
STATES = {"queued": "pending", "running": "in_progress", "done": "completed",
          "failed": "failed", "cancelled": "cancelled", "skipped": "ignored"}
ROLES = {"zh": "zh-Hans", "chs": "zh-Hans", "chi": "zh-Hans", "zh-hans": "zh-Hans", "zh-cn": "zh-Hans",
         "cht": "zh-Hant", "zh-hant": "zh-Hant", "zh-tw": "zh-Hant", "bilingual": "zh-en",
         "zh-en": "zh-en", "en": "eng", "eng": "eng"}
TARGET = re.compile(r"[0-9a-f]{64}")


def config_update(previous, incoming):
    if not previous or "model" in incoming or not all(incoming.get(key) is True for key in (
        "online_proxy_migrated", "assrt_provider_migrated"
    )):
        return None
    updated = dict(previous)
    for native, key in (("enabled", "enabled"), ("show_sidebar_nav", "show_sidebar_nav"),
                        ("auto_search_on_transfer", "auto_translate")):
        if type(incoming.get(native)) is bool:
            updated[key] = incoming[native]
    return updated


def media(row):
    return {"title": row["title"], "name": row["title"], "media_type": "tv" if row["kind"] == "Episode" else "movie",
            "target_count": 1, "text_only": True}


def ids(body):
    value = body.get("target_ids") or []
    if not isinstance(value, list) or len(value) > 50 or any(not isinstance(i, str) or not TARGET.fullmatch(i) for i in value):
        raise HTTPException(422, "请选择有效片源")
    return list(dict.fromkeys(value))


def job_view(job, key):
    return {"id": str(job["id"]), "target_id": key, "video_file": job["file"], "file_name": job["file"],
            "status": STATES[job["state"]], "message": job["detail"], "error": job["detail"] if job["state"] == "failed" else "",
            "active": job["state"] in ("queued", "running"), "add_time": job["created"],
            "output_path": " · ".join(job["report"].get("files") or [])}


class MPLite:
    def __init__(self, plugin):
        self.plugin = plugin
        self.lock = threading.Lock()
        self.previews = {}
        self.emby_subtitles = EmbySubtitles()

    def status(self):
        studio = self.plugin._active()
        snapshot = self.plugin._inventory_snapshot
        count = len(snapshot.get("catalog", {}))
        return {"enabled": True, "index": {"ready": bool(count), "refreshing": self.plugin._inventory_lock.locked(),
                                         "media_count": count, "entry_count": count},
                "archive_support": {"zip": True}, "timeline_fixer": {"available": False},
                "ai_subtitle": {"available": bool(studio.key), "model": studio.config["model"]}}

    def refresh_index(self, body: dict):
        return self.plugin.inventory_scan()

    def search(self, keyword: str = "", media_type: str = "all", page: int = 1, page_size: int = 20):
        page, size = max(1, page), min(50, max(1, page_size))
        offset = (page - 1) * size
        result = self.plugin.library_page(keyword, offset=offset, kind=KINDS.get(media_type, "all"))
        return {"medias": [media(row) for row in result["rows"][:size]], "page": page, "total": result["matches"],
                "has_more": offset + size < result["matches"]}

    def targets(self, media_type, title):
        result = self.plugin.library_page(title, kind=KINDS.get(media_type, "all"))
        rows = [row for row in result["rows"] if row["title"].casefold() == title.casefold()]
        targets = [{"id": row["id"], "name": row["file"], "title": row["title"], "path": row["display"],
                    "writable": row["available"], "subtitles": [], "original": row["original"]} for row in rows]
        return {"media": media(rows[0]) if rows else {"title": title, "media_type": media_type},
                "targets": targets, "seasons": [], "selected_season": "all"}

    def match_history(self, keyword: str = "", media_type: str = "all", page: int = 1, page_size: int = 20):
        page, size = max(1, page), min(50, max(1, page_size))
        offset = (page - 1) * size
        result = self.plugin.library_page(keyword, state="done", offset=offset, kind=KINDS.get(media_type, "all"))
        rows = [{**media(row), **job_view(row["task"], row["id"])} for row in result["rows"][:size]]
        return {"items": rows, "page": page, "total": result["matches"], "has_more": offset + size < result["matches"]}

    def auto_transfer_queue(self):
        studio = self.plugin._active()
        with studio.db() as connection:
            history = task_history.page(connection, limit=40, native_only=True)
        return {"tasks": [job_view(job, job["target"]) for job in history["jobs"] if job["origin"] == "入库触发"],
                "enabled": bool(studio.config["auto_translate"])}

    @staticmethod
    def online_status():
        return {"enabled_providers": ["subhd"], "providers": [{"id": "subhd", "name": "SubHD", "available": True}]}

    def online_manual_links(self, body: dict):
        ids(body)
        selected = body.get("media") or {}
        if not isinstance(selected, dict):
            raise HTTPException(422, "请选择片源")
        keyword = str(body.get("keyword") or selected.get("title") or "").strip()[:240]
        link = "https://subhd.tv/search/" + quote(keyword, safe="")
        return {"keywords": [keyword] if keyword else [], "links": [{"provider": "subhd", "name": "SubHD",
                "host": "subhd.tv", "links": [{"url": link, "keyword": keyword, "title": "前往 SubHD"}]}]}

    @staticmethod
    def online_search(body: dict):
        return {"results": [], "messages": [{"provider": "subhd", "message": "请点手动搜索前往 SubHD，下载后返回上传"}]}

    @staticmethod
    def timeline_tasks(body: dict):
        return {"tasks": []}

    def _job(self, studio, key):
        with studio.db() as connection:
            jobs = task_history.page(connection, limit=1, native_only=True, target=key)["jobs"]
        return jobs[0] if jobs else None

    def ai_tasks(self, body: dict):
        studio = self.plugin._active()
        return {"tasks": [job_view(job, key) for key in ids(body) if (job := self._job(studio, key))]}

    def ai_submit(self, body: dict):
        studio = self.plugin._active()
        if not studio.key:
            raise HTTPException(409, "订阅线路未配置")
        selected = ids(body)
        find_english = body.get("find_english") is True
        choice = body.get("english_choice")
        interactive = find_english or choice is not None
        if interactive and len(selected) != 1:
            raise HTTPException(422, "请选择一个片源来查找英文字幕")
        source_notice = ""
        for ident in selected:
            target = (self.plugin._prepare_library_target(ident, True) if interactive
                      else self.plugin.library_target({"id": ident}))
            if target["original"]:
                raise HTTPException(422, "原盘请下载后手动上传字幕")
            key = target["target"]
            last = self._job(studio, key)
            active = last and last["state"] in ("queued", "running")
            source = target.get("emby_source")
            if choice is not None:
                if active:
                    raise HTTPException(409, "此片源已有 AI 字幕任务")
                online = self.plugin._check(self.emby_subtitles.download, key, source, choice)
                self.plugin._check(studio.submit, key, False, online)
                continue
            if find_english and source and not active and not (last and studio.has_online_source(last["id"])):
                if not self.plugin._check(studio.has_local_source, key):
                    try:
                        options = self.emby_subtitles.search(key, source, target["file"])
                    except ValueError as exc:
                        source_notice = str(exc)
                    else:
                        if options:
                            return {"english_options": options}
                        source_notice = "Emby 未找到英文 SRT"
                    if str(target["file"]).lower().endswith(".strm"):
                        raise HTTPException(422, source_notice + "，可上传英文原稿后再试")
            if last and last["state"] == "failed":
                self.plugin._check(studio.retry, last["id"])
            elif last and last["state"] == "done":
                self.plugin._check(studio.manage, "restart", [last["id"]])
            else:
                self.plugin._check(studio.submit, key)
        result = self.ai_tasks(body)
        if source_notice:
            result["source_notice"] = source_notice + "，已提交本地字幕任务"
        return result

    def ai_cancel(self, body: dict):
        studio = self.plugin._active()
        running = [job["id"] for key in ids(body) if (job := self._job(studio, key))
                   and job["state"] in ("queued", "running")]
        if running:
            self.plugin._check(studio.manage, "cancel", running)
        return self.ai_tasks(body)

    async def prepare_upload(self, request: Request):
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_SUBTITLE + 65536:
            raise HTTPException(413, "字幕文件超过 12 MiB")
        async with request.form(max_files=1, max_fields=4) as form:
            try:
                selected = ids({"target_ids": json.loads(str(form.get("target_ids") or "[]"))})
            except ValueError as exc:
                raise HTTPException(422, "请选择一个片源") from exc
            upload = form.get("files")
            if len(selected) != 1 or not getattr(upload, "filename", None):
                raise HTTPException(422, "请一次选择一个片源和一个字幕文件")
            data = await upload.read(MAX_SUBTITLE + 1)
            if len(data) > MAX_SUBTITLE:
                raise HTTPException(413, "字幕文件超过 12 MiB")
            return await run_in_threadpool(self.plugin._check, self._prepare, selected[0], upload.filename, data)

    def _prepare(self, ident, filename, data):
        target = self.plugin.library_target({"id": ident})
        ext, contents = upload_member(filename, data)
        members = [""] if ext else contents
        if len(members) > 50:
            raise ValueError("字幕包内容过多，请在本地解压后选择需要的字幕")
        english = bool(ext and english_text(parse(contents, ext)))
        preview, options = [], {}
        for member in members:
            source = member or filename
            extension = ext or Path(source).suffix.lower()
            script = chinese_script(source)
            role = ("zh-en" if re.search(r"zh[-_.]en|双语|雙語|中英", source, re.I) else
                    "zh-Hant" if script == "hant" else
                    "eng" if english or re.search(r"(?<![a-z])eng(?:lish)?(?![a-z])", source, re.I) else "zh-Hans")
            upload_id = uuid4().hex
            options[upload_id] = (member, role)
            prefix = target["file"] if target["folder"] else Path(target["file"]).stem
            preview.append({"upload_id": upload_id, "target_id": ident, "name": source, "filename": source,
                            "ext": extension, "language_suffix": role, "selected": len(members) == 1,
                            "output_name": f"{prefix}.{role}.manual{extension}"})
        token, now = uuid4().hex, time.monotonic()
        with self.lock:
            self.previews = {key: item for key, item in self.previews.items() if item[0] > now}
            if len(self.previews) >= 8:
                raise ValueError("暂存字幕过多，请稍后重试")
            self.previews[token] = (now + 600, ident, filename, data, options)
        return {"session_id": token, "items": preview, "source": "manual"}

    def apply_upload(self, body: dict):
        token, items = body.get("session_id"), body.get("items")
        if not isinstance(token, str) or not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
            raise HTTPException(422, "请确认一份字幕后上传")
        with self.lock:
            draft = self.previews.get(token)
            if not draft or draft[0] <= time.monotonic():
                self.previews.pop(token, None)
                raise HTTPException(422, "上传预览已过期，请重新选择文件")
            _, ident, filename, data, options = draft
            item = items[0]
            option = options.get(str(item.get("upload_id")))
            if item.get("target_id") != ident or not option:
                raise HTTPException(422, "字幕文件或片源校验失败")
            member, default = option
            role = ROLES.get(str(item.get("language_suffix") or "").casefold(), default)
            target = self.plugin.library_target({"id": ident})
            result = self.plugin._check(self.plugin._active().upload, target["target"], filename, data, member, role)
            self.previews.pop(token, None)
        return {"written": [{"target_id": ident, "filename": result["file"], **result}]}
