"""按 Emby 可见的电影版本和单集片源清点字幕。"""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import re

import httpx

from .media import CHINESE_LABEL as ZH, LIMITED, TEXT_CODECS, chinese_script
from . import library

TYPES = ("Movie", "Episode")
STATES = ("present", "missing", "unknown", "disc")
PAGE_SIZE = 100
CATALOG_VERSION = 2
SIDECARS = {".srt", ".ass", ".ssa", ".vtt", ".sup", ".idx", ".smi", ".ttml"}
UNKNOWN = {"", "und", "unk", "unknown", "mul", "mis", "zxx"}
EN = re.compile(r"(?<![a-z0-9])(?:en|eng|english)(?![a-z0-9])|英文|英语|英語", re.I)
BILINGUAL = re.compile(r"中英|英中|简英|繁英|英简|英繁|簡英|英簡|中上英下|英上中下|上中下英|上英下中")
RESTRICTED = re.compile(r"强制|強制|导演评[论述]|導演評[論述]|(?<![a-z])signs?(?![a-z])", re.I)



def configured_servers():
    try:
        from app.application.mediaserver import get_mediaserver_configs
        configs = get_mediaserver_configs()
    except ImportError:
        from app.helper.mediaserver import MediaServerHelper
        configs = MediaServerHelper().get_configs().values()
    servers = [(conf.name or "Emby", conf.config or {}) for conf in configs
               if conf.type == "emby" and conf.enabled]
    if not servers:
        raise ValueError("请在 MoviePilot 的媒体服务器设置中启用 Emby")
    return servers


def emby_url(host):
    host = str(host or "").strip().rstrip("/")
    url = httpx.URL(host if "://" in host else "http://" + host)
    if url.scheme not in ("http", "https") or not url.host or url.userinfo or url.query or url.fragment:
        raise ValueError("Emby 服务地址无效")
    return str(url).rstrip("/") + ("/" if url.path.lower().rstrip("/").endswith("/emby") else "/emby/")


def item_pages(client):
    start = 0
    total = None
    seen = set()
    while total is None or start < total:
        response = client.get("Items", params={
            "Recursive": "true", "IsMissing": "false", "IncludeItemTypes": ",".join(TYPES),
            "Fields": "Path,MediaSources,MediaStreams,OriginalTitle,ProductionYear,DateCreated",
            "EnableTotalRecordCount": "true", "SortBy": "SortName", "StartIndex": start, "Limit": 250,
        })
        response.raise_for_status()
        data = response.json()
        rows, count = data.get("Items"), data.get("TotalRecordCount")
        if not isinstance(rows, list) or type(count) is not int or count < 0:
            raise ValueError("Emby 没有返回完整的片库分页")
        if total is not None and count != total:
            raise ValueError("扫描期间 Emby 片库总数发生变化，请重试")
        total = count
        ids = {str(row.get("Id") or "") for row in rows}
        if "" in ids or len(ids) != len(rows) or ids & seen or start + len(rows) > total or (not rows and start < total):
            raise ValueError("Emby 片库分页有重复或缺失，请重试")
        seen.update(ids)
        start += len(rows)
        yield rows, start, total


def basename(path):
    return PurePosixPath(str(path or "").replace("\\", "/")).name


def sidecar_tag(path, video):
    stem = PurePosixPath(basename(path)).stem
    video_stem = PurePosixPath(basename(video)).stem
    if video_stem and stem.casefold().startswith(video_stem.casefold() + "."):
        return stem[len(video_stem) + 1:]
    return ""


def track_language(track, video):
    language = str(track.get("Language") or "").strip().lower()
    title = " ".join(str(track.get(k) or "") for k in ("Title", "DisplayTitle"))
    if track.get("IsExternal"):
        title += " " + sidecar_tag(track.get("Path"), video)
    limited = bool(track.get("IsForced") or LIMITED.search(title) or RESTRICTED.search(title))
    labels = language + " " + title
    if BILINGUAL.search(labels) or (ZH.search(labels) and EN.search(labels)):
        return "bilingual", limited
    if ZH.search(language) or (language in UNKNOWN and ZH.search(title)):
        return "zh", limited
    if EN.search(language) or (language in UNKNOWN and EN.search(title)):
        return "en", limited
    return ("unknown" if language in UNKNOWN or not re.fullmatch(r"[a-z]{2,3}(?:[-_][a-z0-9]+)*", language) else "other"), limited


def unindexed_sidecar(video, indexed, directories):
    path = Path(video)
    if path.parent not in directories:
        try:
            directories[path.parent] = [p for p in path.parent.iterdir()
                                        if p.suffix.lower() in SIDECARS and not p.is_symlink()]
        except OSError:
            directories[path.parent] = []
    prefix = path.stem.casefold()
    for file in directories[path.parent]:
        if file.name in indexed or (file.stem.casefold() != prefix and not file.stem.casefold().startswith(prefix + ".")):
            continue
        language, limited = track_language({"Title": sidecar_tag(file, path)}, video)
        if not limited and language in ("zh", "bilingual", "unknown"):
            try:
                if file.is_file() and file.stat().st_size:
                    return True
            except OSError:
                continue
    return False


def classify(streams, video, local_paths, directories):
    folders = {part.casefold() for part in PurePosixPath(video.replace("\\", "/")).parts[:-1]}
    if folders & {"bdmv", "video_ts"}:
        return {"state": "disc", "reason": "原盘目录内部文件", "english": False, "bilingual": False, "chinese": [], "chinese_scripts": []}
    chinese, chinese_scripts = set(), set()
    english = bilingual = unlabeled = forced_chinese = False
    external = set()
    for track in streams:
        if track.get("Type") != "Subtitle":
            continue
        if track.get("IsExternal") and track.get("Path"):
            external.add(basename(track["Path"]))
        language, limited = track_language(track, video)
        if limited:
            forced_chinese |= language in ("zh", "bilingual")
            continue
        if language in ("zh", "bilingual"):
            chinese.add("external" if track.get("IsExternal") else "embedded")
            bilingual |= language == "bilingual"
            if not track.get("IsExternal"):
                tags = " ".join(str(track.get(key) or "") for key in ("Language", "Title", "DisplayTitle"))
                script = chinese_script(tags)
                if script:
                    chinese_scripts.add(script)
        elif language == "en":
            english |= str(track.get("Codec") or "").lower() in TEXT_CODECS
        elif language == "unknown":
            unlabeled = True
    if chinese:
        state, reason = "present", ""
    elif video in local_paths and unindexed_sidecar(video, external, directories):
        state, reason = "unknown", "发现 Emby 尚未收录的外挂"
    elif unlabeled:
        state, reason = "unknown", "有字幕轨未标明语言"
    elif not any(track.get("Type") == "Video" for track in streams):
        state, reason = "unknown", "Emby 未提供完整轨道信息"
    else:
        state, reason = "missing", "只有强制或附注中文" if forced_chinese else "未发现完整中文字幕"
    return {"state": state, "reason": reason, "english": english, "bilingual": bilingual,
            "chinese": sorted(chinese), "chinese_scripts": sorted(chinese_scripts)}


def item_versions(item, server, local_paths, directories):
    kind = item.get("Type")
    if kind not in TYPES:
        raise ValueError("Emby 返回了非电影或剧集条目")
    sources = item.get("MediaSources") or [{}]
    seen = set()
    for index, source in enumerate(sources):
        path = source.get("Path") if source.get("Protocol") in (None, "File") else ""
        path = str(path or item.get("Path") or "")
        if "://" in path:
            path = ""
        identity = (source.get("Id") or path or index, path)
        if identity in seen:
            continue
        seen.add(identity)
        streams = source.get("MediaStreams")
        if not streams and len(sources) == 1:
            streams = item.get("MediaStreams")
        facts = classify(streams or [], path, local_paths, directories)
        container = str(source.get("Container") or item.get("Container") or "").lower()
        folder = container in ("bluray", "dvd") and not PurePosixPath(path).suffix
        yield {
            "server": server, "item": str(item["Id"]), "type": kind, "title": item.get("Name") or "未命名",
            "original": item.get("OriginalTitle") or "", "year": item.get("ProductionYear"),
            "series": item.get("SeriesName") or "", "series_id": item.get("SeriesId"),
            "season": item.get("ParentIndexNumber"), "episode": item.get("IndexNumber"),
            "episode_end": item.get("IndexNumberEnd"), "file": basename(path), "path": library.emby_path(path),
            "version": index, "added": library.timestamp(item.get("DateCreated"), utc=True),
            "seconds": (source.get("RunTimeTicks") or item.get("RunTimeTicks") or 0) / 10_000_000,
            "original_disk": folder or PurePosixPath(path).suffix.lower() == ".iso", "disk_folder": folder,
            "disc_coverage": classify(streams or [], basename(path), set(), {}) if facts["state"] == "disc" else {},
            **facts,
        }


def summarize(rows):
    summary = {}
    for kind in ("all", *TYPES):
        selected = [row for row in rows if kind == "all" or row["type"] == kind]
        counts = Counter(row["state"] for row in selected)
        summary[kind] = {"total": len(selected), **{state: counts[state] for state in STATES},
                         "items": len({(r["server"], r["item"]) for r in selected}),
                         "missing_items": len({(r["server"], r["item"]) for r in selected if r["state"] == "missing"}),
                         "bilingual": sum(r["bilingual"] for r in selected),
                         "english_ready": sum(r["state"] == "missing" and r["english"] for r in selected)}
    summary["series"] = len({(r["server"], r["series_id"] or r["series"]) for r in rows
                             if r["type"] == "Episode" and (r["series_id"] or r["series"])})
    return summary


def scan(servers, local_paths, progress, stopped, mappings=""):
    rows = []
    directories = {}
    locations = {}
    path_maps = library.directory_maps(mappings)
    for server, config in servers:
        key = config.get("apikey")
        if not key:
            raise ValueError("Emby 缺少 API 密钥")
        with httpx.Client(base_url=emby_url(config.get("host")), headers={"X-Emby-Token": key},
                          trust_env=False, timeout=40, transport=httpx.HTTPTransport(retries=1)) as client:
            folders = client.get("Library/VirtualFolders").raise_for_status().json()
            locations[server] = [path for folder in folders for path in folder.get("Locations", [])
                                 if library.emby_path(path) and path != "/"]
            for items, done, total in item_pages(client):
                if stopped():
                    return None
                for item in items:
                    rows.extend(item_versions(item, server, local_paths, directories))
                progress(f"{server} · 已读取 {done} / {total} 条")
    rows.sort(key=lambda r: (r["type"] != "Movie", (r["series"] or r["title"]).casefold(),
                             r["season"] or 0, r["episode"] or 0, r["title"].casefold(), r["file"]))
    progress("正在核对原盘主播放列表")
    return {"created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "servers": [name for name, _ in servers],
            "summary": summarize(rows), "rows": rows, "mapping": mappings, "catalog_version": CATALOG_VERSION,
            "catalog": library.catalog(rows, locations, path_maps)}


def page(snapshot, state, kind, query, offset):
    if state not in ("all", *STATES) or kind not in ("all", *TYPES):
        raise ValueError("字幕清单筛选条件无效")
    words = query.casefold().split()
    matches = []
    for row in snapshot.get("rows", []):
        if (state != "all" and row["state"] != state) or (kind != "all" and row["type"] != kind):
            continue
        episode = f"S{row['season'] or 0:02}E{row['episode'] or 0:02}" if row["episode"] is not None else ""
        key = " ".join((row["title"], row["series"], row["original"], row["file"], episode)).casefold()
        if all(word in key for word in words):
            matches.append(row)
    return {k: v for k, v in snapshot.items() if k != "rows"} | {
        "matches": len(matches), "rows": matches[offset:offset + PAGE_SIZE], "page_size": PAGE_SIZE}
