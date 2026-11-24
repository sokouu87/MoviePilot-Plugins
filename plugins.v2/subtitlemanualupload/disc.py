"""识别原盘目录及蓝光主播放列表。"""

import re
from pathlib import Path, PurePath, PurePosixPath

DISC_DIRS = {"bdmv", "video_ts"}
CHINESE = {"chi", "zho", "cmn", "yue", "chs", "cht", "zh"}


def parent(path):
    path = path if isinstance(path, PurePath) else PurePosixPath(str(path).replace("\\", "/"))
    for i, name in enumerate(path.parts[:-1]):
        if name.casefold() in DISC_DIRS and i > 0:
            return type(path)(*path.parts[:i])
    return None


def structure(path):
    path = Path(path)
    if path.is_dir():
        return next((p for p in path.iterdir() if p.name.casefold() in DISC_DIRS and p.is_dir()), None)
    return None


def is_original(path):
    path = Path(path)
    return path.suffix.lower() == ".iso" or parent(path) is not None


def title(path):
    path = Path(path)
    name = path.name if path.suffix.lower() != ".iso" else path.stem
    if re.fullmatch(r"(?i)(?:disc|disk|cd|盘)[ ._-]*\d+", name):
        name = path.parent.name + " " + name
    name = re.sub(r"\s*[{\[](?:tmdbid=|tmdb-|imdbid=)[^}\]]+[}\]]", "", name, flags=re.I)
    year = re.search(r"\s+\(((?:19|20)\d{2})\)", name)
    return (name[:year.start()].rstrip() if year else name).strip(), year.group(1) if year else ""


def read_playlist(data):
    if len(data) < 20 or data[:4] != b"MPLS":
        raise ValueError("不是蓝光播放列表")

    def number(offset, size, end):
        if offset < 0 or offset + size > end:
            raise ValueError("播放列表不完整")
        return int.from_bytes(data[offset:offset + size], "big")

    section = number(8, 4, len(data))
    end = section + 4 + number(section, 4, len(data))
    if end > len(data):
        raise ValueError("播放列表长度无效")
    count = number(section + 6, 2, end)
    at = section + 10
    clips = []
    for _ in range(count):
        pos = at + 2
        at = pos + number(at, 2, end)
        if at > end or at - pos < 46 or not data[pos:pos + 5].isdigit():
            raise ValueError("播放列表片段无效")
        flags = number(pos + 9, 2, at)
        length = number(pos + 16, 4, at) - number(pos + 12, 4, at)
        table = pos + 32
        if flags & 0x10:
            table += 2 + max(0, number(table, 1, at) - 1) * 10
        limit = table + 2 + number(table, 2, at)
        if limit > at or limit < table + 16:
            raise ValueError("轨道表长度无效")
        video = number(table + 4, 1, limit)
        audio = number(table + 5, 1, limit)
        subtitles = number(table + 6, 1, limit)
        languages = set()
        cursor = table + 16
        for index in range(video + audio + subtitles):
            attr_len = cursor + 1 + number(cursor, 1, limit)
            payload = attr_len + 1
            cursor = payload + number(attr_len, 1, limit)
            if cursor > limit or cursor <= payload:
                raise ValueError("轨道信息无效")
            if index >= video + audio:
                start = payload + (2 if data[payload] == 0x92 else 1)
                lang = data[start:start + 3].decode("ascii", "ignore").lower() if start + 3 <= cursor else ""
                languages.add(lang if re.fullmatch("[a-z]{3}", lang) else "")
        if length > 0:
            clips.append((data[pos:pos + 5].decode("ascii"), length / 45000, languages))
    return clips


def main_playlist(path):
    try:
        directory = structure(path)
        if directory is None or directory.name.casefold() != "bdmv":
            return []
        playlist = next((p for p in directory.iterdir() if p.name.casefold() == "playlist" and p.is_dir()), None)
        if playlist is None or not playlist.resolve().is_relative_to(Path(path).resolve()):
            return []
        best, duration = [], 0
        for file in sorted(playlist.iterdir()):
            if file.suffix.lower() != ".mpls" or file.is_symlink():
                continue
            try:
                with file.open("rb") as stream:
                    contents = stream.read(4 * 1024 * 1024 + 1)
                if len(contents) > 4 * 1024 * 1024:
                    continue
                clips = read_playlist(contents)
            except (OSError, ValueError):
                continue
            length = sum(n for _, n, _ in clips)
            if length > duration:
                best, duration = clips, length
        return best if duration >= 600 else []
    except OSError:
        return []
