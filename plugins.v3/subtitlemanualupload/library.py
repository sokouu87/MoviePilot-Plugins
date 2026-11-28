"""统一 Emby 片源、整理记录和字幕任务；原盘按目录归组。"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from . import disc, task_history
from .media import VIDEO, metadata

PAGE_SIZE = 50
TASK_STATES = ("queued", "running", "done", "failed", "cancelled", "skipped")
FILTERS = ("all", "recent", "present", "missing", "unknown", "disc", *TASK_STATES)


def timestamp(value, *, utc=False):
    try:
        instant = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        if utc and instant.tzinfo is None:
            instant = instant.replace(tzinfo=timezone.utc)
        return instant.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (ValueError, OSError, OverflowError):
        return ""


def emby_path(value):
    text = str(value or "")
    path = PurePosixPath(text)
    return str(path) if path.is_absolute() and ".." not in path.parts and "://" not in text and "\x00" not in text else ""


def directory_maps(value):
    pairs = []
    for line in str(value or "").splitlines():
        if not line.strip():
            continue
        source, sep, local = (part.strip() for part in line.partition("="))
        if not sep or not emby_path(source) or not Path(local).is_absolute() or ".." in Path(local).parts:
            raise ValueError("Emby 目录映射请填写绝对路径，格式为 /Emby目录=/MoviePilot目录")
        pairs.append((PurePosixPath(source), Path(local)))
    return sorted(pairs, key=lambda pair: len(pair[0].parts), reverse=True)


def location(value, roots, mappings):
    if not emby_path(value):
        return "", ""
    path = PurePosixPath(value)
    library = next((p for p in sorted(map(PurePosixPath, roots), key=lambda p: -len(p.parts)) if path.is_relative_to(p)), None)
    if library is None:
        return "", ""

    for remote_root, local_root in mappings:
        if path.is_relative_to(remote_root):
            scope = library if library.is_relative_to(remote_root) else remote_root
            return (str(local_root.joinpath(*path.relative_to(remote_root).parts)),
                    str(local_root.joinpath(*scope.relative_to(remote_root).parts)))
    return str(path), str(library)


def mounted(path, root):
    if not path or not root:
        return False
    try:
        p, r = Path(path).resolve(strict=True), Path(root).resolve(strict=True)
        return r.is_dir() and p.is_relative_to(r) and (p.is_file() or p.is_dir())
    except (OSError, RuntimeError):
        return False


def key_for(path, fallback=""):
    return hashlib.sha256(os.path.normcase(path or fallback).encode("utf-8")).hexdigest()


def title_label(title, year, season, episode):
    number = f"S{season or 0:02}E{episode:02}" if episode is not None else ""
    return " ".join(str(v) for v in (title, year, number) if v)


def entry(row, roots, mappings):
    raw = row["path"]
    path, root = location(raw, roots, mappings)
    title = row["series"] or row["title"]
    original = row.get("original_disk", False)
    return {
        "id": key_for(path or raw, f"{row['server']}:{row['item']}:{row['version']}"),
        "path": path, "root": root, "display": raw, "file": row["file"], "kind": row["type"],
        "title": title_label(title, row["year"], row["season"], row["episode"]),
        "alias": " ".join((row["original"], row["title"])),
        "meta": {"title": title, "year": str(row["year"] or ""), "season": row["season"],
                 "episode": row["episode"], "series_id": str(row["series_id"] or "")},
        "original": original, "folder": row.get("disk_folder", False), "added": row["added"],
        "status": row["state"], "reason": row["reason"], "chinese": row["chinese"],
        "chinese_scripts": row.get("chinese_scripts", []), "bilingual": row["bilingual"], "english": row["english"], "emby": True,
    }


def original_entry(members, raw, roots, mappings):
    path, root = location(raw, roots, mappings)
    title, year = disc.title(raw)
    name = title_label(title, year, None, None)
    options = sorted((row for row in members if PurePosixPath(row["path"]).parent.name.lower() == "stream"
                      and PurePosixPath(row["path"]).suffix.lower() in (".m2ts", ".strm") and row["seconds"] >= 600),
                     key=lambda row: (-row["seconds"], row["path"]))
    clips = disc.main_playlist(path) if mounted(path, root) else []
    primary = ""
    state, chinese, bilingual = "unknown", [], False
    chinese_scripts = []
    reason = "主片字幕待确认，可上传到原盘目录"
    streams = set()
    if clips:
        significant = [languages for _, duration, languages in clips if duration >= 30] or [clips[0][2]]
        streams = set().union(*significant)
        if all(langs & disc.CHINESE for langs in significant):
            state, chinese, reason = "present", ["embedded"], "蓝光主播放列表含中文轨"
        elif not streams.intersection(disc.CHINESE | {"", "und", "mul", "zxx"}):
            state, reason = "missing", "蓝光主播放列表未标出中文轨"
        else:
            reason = "蓝光主播放列表有未标语言或覆盖不同的轨道"
        ids = {clip for clip, _, _ in clips}
        if len(ids) == 1:
            target = next((row for row in members if PurePosixPath(row["path"]).stem in ids
                           and PurePosixPath(row["path"]).parent.name.lower() == "stream"), None)
            if target:
                primary, _ = location(target["path"], roots, mappings)
                coverage = target["disc_coverage"]
                if coverage["chinese"]:
                    state = "present"
                    reason = "Emby 已识别主片的中文外挂" if "external" in coverage["chinese"] else "Emby 已识别主片的中文内嵌轨"
                    chinese = sorted(set(chinese) | set(coverage["chinese"]))
                    bilingual = coverage["bilingual"]
                    chinese_scripts = coverage.get("chinese_scripts", [])
    elif options and (len(options) == 1 or options[0]["seconds"] >= options[1]["seconds"] * 1.45):
        first = options[0]
        primary, _ = location(first["path"], roots, mappings)
        info = first["disc_coverage"]
        if info["state"] == "present":
            state, chinese, bilingual = "present", info["chinese"], info["bilingual"]
            chinese_scripts = info.get("chinese_scripts", [])
            reason = "Emby 已识别最长主片的中文轨"
        elif info["state"] == "missing":
            reason = "最长片段未识别中文，原盘主片字幕待确认"
    elif any(row["disc_coverage"]["chinese"] for row in members):
        reason = "原盘片段有中文轨，主片对应关系待确认"
    return {
        "id": key_for(path or raw), "path": path, "root": root, "display": raw,
        "file": PurePosixPath(raw).name, "title": name, "alias": "", "kind": "Disc",
        "meta": {"title": title, "year": year, "season": None, "episode": None, "series_id": ""},
        "original": True, "folder": True, "primary": primary, "added": max(row["added"] for row in members),
        "status": state, "reason": reason, "chinese": chinese, "chinese_scripts": chinese_scripts,
        "bilingual": bilingual, "english": False, "emby": True,
    }


def catalog(rows, locations, mappings):
    result, originals = {}, defaultdict(list)
    for row in rows:
        folder = disc.parent(row["path"])
        if folder is not None:
            originals[(row["server"], str(folder))].append(row)
        else:
            media = entry(row, locations.get(row["server"], []), mappings)
            result[media["id"]] = media
    for (server, path), members in originals.items():
        media = original_entry(members, path, locations.get(server, []), mappings)
        existing = result.get(media["id"], {})
        if existing.get("status") == "present" and media["status"] != "present":
            for field in ("status", "chinese", "chinese_scripts", "bilingual", "reason"):
                media[field] = existing[field]
        result[media["id"]] = media
    return result


def merge(conn, snapshot):
    rows = {key: {**row, "recent": False, "task": None} for key, row in snapshot.get("catalog", {}).items()}
    jobs = task_history.by_target(conn)
    for target in conn.execute("SELECT id,path,meta,edited FROM target WHERE listed=1 OR id IN (SELECT target FROM job WHERE hidden=0)"):
        path = Path(target["path"])
        if disc.parent(path) is not None:
            continue
        target_meta = json.loads(target["meta"])
        key = key_for(str(path))
        task, count = jobs.get(target["id"], (None, 0))
        row = rows.get(key)
        if row is None:
            row = {"id": key, "path": str(path), "root": "", "display": str(path), "file": path.name,
                   "title": title_label(target_meta["title"], target_meta.get("year"), target_meta.get("season"), target_meta.get("episode")),
                   "alias": "", "meta": target_meta, "status": "unknown", "reason": "",
                   "original": disc.is_original(path) or bool(target_meta.get("disc_folder")),
                   "folder": bool(target_meta.get("disc_folder")), "chinese": [], "bilingual": False, "english": False,
                   "kind": "Disc" if target_meta.get("disc_folder") else "Episode" if target_meta.get("episode") is not None else "Movie",
                   "emby": False, "added": "", "recent": False}
            rows[key] = row
        row["added"] = max(row["added"], target_meta.get("added", ""))
        row["recent"] = bool(target_meta.get("added"))
        if target["edited"]:
            row["alias"] += " " + row["title"]
            row["title"] = title_label(target_meta["title"], target_meta.get("year"), target_meta.get("season"), target_meta.get("episode"))
            row["meta"] = target_meta
        row.update(target=target["id"], task=task, task_count=count)
    return rows


def page(conn, snapshot, query, state, order, offset, kind="all"):
    if state not in FILTERS or order not in ("asc", "desc") or kind not in ("all", "Movie", "Episode"):
        raise ValueError("筛选或排序无效")
    words = query.casefold().split()
    counted, found = Counter(), []
    for row in merge(conn, snapshot).values():
        if kind != "all" and row["kind"] != kind:
            continue
        if not all(word in (row["title"] + " " + row["alias"] + " " + row["file"]).casefold() for word in words):
            continue
        task = row.get("task")
        tags = {"all", row["status"]}
        if row["recent"]:
            tags.add("recent")
        if row["original"]:
            tags.add("disc")
        if task:
            tags.add(task["state"])
        counted.update(tags)
        if state in tags:
            found.append(row)
    found.sort(key=lambda row: (max(row["added"], timestamp((row.get("task") or {}).get("created"), utc=True)),
                                row["title"].casefold()), reverse=order == "desc")
    visible = []
    for row in found[offset:offset + PAGE_SIZE]:
        path = Path(row["path"]) if row["path"] else None
        label = str(path if row["folder"] else path.parent) if path else str(PurePosixPath(row["display"]).parent)
        if row["folder"] and not path:
            label = row["display"]
        available = bool(path) and (row["folder"] or path.suffix.lower() in VIDEO)
        if available:
            available = (not row["root"] or mounted(path, row["root"])) and (path.is_dir() if row["folder"] else path.is_file())
        visible.append({**{k: v for k, v in row.items() if k not in ("root", "meta", "primary", "alias")},
                        "directory": label, "available": available,
                        "search_url": "https://subhd.tv/search/" + quote(row["title"], safe="")})
    return {"rows": visible, "counts": dict(counted), "matches": len(found), "page_size": PAGE_SIZE,
            "more": offset + PAGE_SIZE < len(found), "scanned": snapshot.get("created")}


def prepare(studio, snapshot, key, include_emby=False):
    with studio.db() as conn:
        row = merge(conn, snapshot).get(key)
    if not row or not row["path"]:
        raise ValueError("MoviePilot 尚未连接这个片源的目录")
    path = Path(row["path"])
    if row["root"] and not mounted(path, row["root"]):
        raise ValueError("片源离线或 Emby 目录映射不匹配")
    directory = path if row["folder"] else path.parent
    selected = row.get("primary")
    if row["folder"] and selected:
        member = Path(selected)
        if mounted(member, row["root"]) and member.is_file() and disc.parent(member) == path:
            path = member
    target = row.get("target") if str(path) == row["path"] else None
    if not target:
        values = {**row["meta"], "disc_folder": path.is_dir(), "library_root": row["root"]}
        target = studio.register(path, values)
    if not target:
        raise ValueError("影片目录或主片暂不可用")
    media, _ = studio.target(target)
    if not os.access(media if media.is_dir() else media.parent, os.W_OK):
        raise ValueError("MoviePilot 对字幕保存目录没有写入权限")
    result = {"target": target, "directory": str(directory), "destination": str(media if media.is_dir() else media.parent),
              "file": media.name, "folder": media.is_dir(), "original": row["original"]}
    if include_emby and row["emby"] and row["display"] and not row["original"]:
        sources = {(item["server"], item["item"]) for item in snapshot.get("rows", ())
                   if item["path"] == row["display"] and item["server"] and item["item"]}
        if len(sources) == 1:
            result["emby_source"] = sources.pop()
    return result
