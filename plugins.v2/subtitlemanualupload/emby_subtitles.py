"""通过现有 Emby 连接为已确认的片源获取英文原稿。"""

from dataclasses import dataclass
from threading import Lock
from time import monotonic
from urllib.parse import quote
from uuid import uuid4

import httpx

from . import inventory
from .media import ENGLISH, LIMITED, english_text
from .subtitles import MAX_SUBTITLE, parse


@dataclass(frozen=True)
class Offer:
    target: str
    source: tuple[str, str]
    expires: float
    candidates: list[dict]


class EmbySubtitles:
    def __init__(self):
        self.offers: dict[str, Offer] = {}
        self.lock = Lock()

    @staticmethod
    def client(server):
        config = dict(inventory.configured_servers()).get(server)
        if not config:
            raise ValueError("片源对应的 Emby 连接已更新，请刷新片库")
        return inventory.emby_client(config, timeout=httpx.Timeout(20, connect=5))

    def search(self, target, source, filename):
        server, item = source
        try:
            with self.client(server) as client:
                rows = client.get(f"Items/{quote(item, safe='')}/RemoteSearch/Subtitles/en").raise_for_status().json()
        except httpx.HTTPError as exc:
            raise ValueError("Emby 英文字幕搜索暂不可用") from exc
        if not isinstance(rows, list):
            raise ValueError("Emby 返回了无效的字幕列表")
        candidates = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            ident = row.get("Id")
            language = str(row.get("Language") or row.get("ThreeLetterISOLanguageName") or "").lower()
            title = str(row.get("Name") or row.get("Comment") or "英文字幕")[:350]
            if (not isinstance(ident, str) or not 0 < len(ident) <= 1024 or ident in seen
                    or language not in ENGLISH or str(row.get("Format") or "").lower() != "srt"
                    or row.get("IsForced") is True or LIMITED.search(title)):
                continue
            seen.add(ident)
            candidates.append({"id": ident, "title": title, "provider": str(row.get("ProviderName") or "Emby")[:80],
                               "hash_match": row.get("IsHashMatch") is True})
        if not candidates:
            return None
        candidates.sort(key=lambda row: not row["hash_match"])
        candidates = candidates[:50]
        token = uuid4().hex
        now = monotonic()
        with self.lock:
            self.offers = {key: offer for key, offer in self.offers.items() if offer.expires > now}
            if len(self.offers) >= 64:
                self.offers.pop(next(iter(self.offers)))
            self.offers[token] = Offer(target, source, now + 600, candidates)
        return {"token": token, "file": filename, "candidates": [
            {"index": index, "title": row["title"], "provider": row["provider"], "hash_match": row["hash_match"]}
            for index, row in enumerate(candidates)
        ]}

    def download(self, target, source, selection):
        token = selection.get("token") if isinstance(selection, dict) else None
        index = selection.get("index") if isinstance(selection, dict) else None
        with self.lock:
            offer = self.offers.get(token) if isinstance(token, str) else None
        if (not offer or offer.expires <= monotonic() or offer.target != target or offer.source != source
                or type(index) is not int or not 0 <= index < len(offer.candidates)):
            raise ValueError("英文字幕候选已失效，请重新搜索")
        row = offer.candidates[index]
        data = bytearray()
        try:
            with self.client(offer.source[0]) as client, client.stream(
                "GET", "Providers/Subtitles/Subtitles/" + quote(row["id"], safe="")
            ) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes(chunk_size=65536):
                    data.extend(chunk)
                    if len(data) > MAX_SUBTITLE:
                        raise ValueError("英文字幕超过 12 MiB，请选择其他候选")
        except httpx.HTTPError as exc:
            raise ValueError("Emby 下载英文字幕失败，请重试或选择其他版本") from exc
        content = bytes(data)
        try:
            rows = parse(content, ".srt")
        except ValueError as exc:
            raise ValueError("Emby 返回的字幕文件无法读取，请选择其他候选") from exc
        if not english_text(rows):
            raise ValueError("这份字幕没有通过英文原稿校验，请选择其他候选")
        return f"Emby · {row['provider']} · {row['title']}", content
