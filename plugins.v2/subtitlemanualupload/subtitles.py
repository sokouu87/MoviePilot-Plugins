"""字幕行与时间码由本地处理，翻译模型只返回按编号对齐的中文。"""
import codecs
import ctypes
import errno
import html
import io
import json
import os
import re
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

MAX_SUBTITLE = 12 * 1024 * 1024
TEXT_EXTS = {".srt", ".ass", ".ssa"}
TIME = re.compile(r"(\d{1,3}):([0-5]\d):([0-5]\d)[,.](\d{1,3})")
SDH_PAREN = re.compile(r"\((?:[^()]{0,35}\b(?:sighs?|laughs?|laughing|chuckles?|grunts?|gasps?|whispers?|coughs?|sobbing|screams?|shouting|music|playing|door|knock|applause|gunshots?|breathes?|breathing|inaudible|speaking|whispering|ringing|singing|crying)\b[^()]{0,40})\)", re.I)
PREFIX = re.compile(r"^(\s*[-–—]?\s*)(?:[A-Z][A-Z0-9 .’'\-]{0,28}):\s+")
TAG = re.compile(r"</?(?:i|b|u|font|span|br)(?:\s[^<>]*)?\s*/?>", re.I)
EFFECT = re.compile(r"\{[^{}]*\\[^{}]*\}")
HEADER = Path(__file__).with_name("styles.ass").read_text(encoding="utf-8-sig").rstrip()


@dataclass(frozen=True)
class Cue:
    id: int
    start: int
    end: int
    raw: str
    en: str
    italic: bool

    @property
    def duration(self):
        return round(max(self.end - self.start, 0) / 1000, 1)

    def prompt_line(self):
        return {"id": self.id, "duration_sec": self.duration, "raw_en": self.raw, "sdh_only": not self.en}


def decode(data):
    if len(data) > MAX_SUBTITLE:
        raise ValueError("字幕文件超过 12 MiB")
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16")
    for encoding in ("utf-8-sig", "gb18030", "cp1252"):
        try:
            result = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\0" in result:
            break
        return result
    raise ValueError("字幕文本编码无法识别")


def milliseconds(value):
    match = TIME.fullmatch(value.strip())
    if not match:
        raise ValueError("字幕时间码无效")
    h, m, s, frac = match.groups()
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(frac.ljust(3, "0"))


def parse(data, extension):
    text = decode(data).replace("\r\n", "\n").replace("\r", "\n").strip()
    rows = []

    def add(start, end, raw, italic=False):
        start, end = milliseconds(start), milliseconds(end)
        if end < start:
            raise ValueError(f"第 {len(rows) + 1} 轴结束时间早于开始时间")
        raw = raw.strip()
        italic = italic or bool(re.fullmatch(r"<i\b[^>]*>(?:(?!</?i\b).)*</i>", raw, re.I | re.S))
        clean = html.unescape(TAG.sub("", raw))
        clean = re.sub(r"\[[^]\n]{1,90}\]", "", clean)
        clean = SDH_PAREN.sub("", clean)
        clean = " ".join(PREFIX.sub(r"\1", line).strip() for line in clean.splitlines())
        clean = " ".join(clean.split())
        if not clean.strip("-–— ♪♫"):
            clean = ""
        rows.append(Cue(len(rows) + 1, start, end, raw, clean, italic))

    if extension.lower() == ".srt":
        for block in re.split(r"\n[ \t]*\n+", text):
            lines = block.splitlines()
            if lines and lines[0].strip().isdigit():
                lines = lines[1:]
            if len(lines) < 2 or "-->" not in lines[0]:
                raise ValueError(f"第 {len(rows) + 1} 段缺少有效的 SRT 时间轴或正文")
            start, end = lines[0].split("-->", 1)
            add(start, end.strip().split(" ", 1)[0], "\n".join(lines[1:]))
    elif extension.lower() in (".ass", ".ssa"):
        fields = ["layer", "start", "end", "style", "name", "marginl", "marginr", "marginv", "effect", "text"]
        events = False
        for line in text.splitlines():
            label = line.strip().lower()
            if label.startswith("["):
                events = label == "[events]"
            elif events and label.startswith("format:"):
                fields = [key.strip().lower() for key in line.split(":", 1)[1].split(",")]
            elif events and label.startswith("dialogue:"):
                row = dict(zip(fields, line.split(":", 1)[1].split(",", len(fields) - 1)))
                if not {"start", "end", "text"} <= row.keys():
                    raise ValueError("ASS 事件缺少时间码或文本")
                raw = row["text"].strip()
                italic = bool(re.fullmatch(r"\{\\i1\}(?:(?!\{\\i0\}).)*(?:\{\\i0\})?", raw, re.S))
                raw = re.sub(r"\{[^{}]*\}", "", raw).replace(r"\N", " ").replace(r"\n", " ").replace(r"\h", " ")
                add(row["start"], row["end"], raw, italic)
    else:
        raise ValueError("请选择 SRT、ASS 或 SSA 字幕")
    if not rows:
        raise ValueError("字幕里没有可读的时间轴")
    return rows


def ass_time(cs):
    h, rest = divmod(cs, 360000)
    m, rest = divmod(rest, 6000)
    s, c = divmod(rest, 100)
    return f"{h}:{m:02}:{s:02}.{c:02}"


def srt_time(ms):
    s, milli = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02},{milli:03}"


def ass_text(value):
    return " ".join(value.splitlines()).translate(str.maketrans({"{": "｛", "}": "｝", "\\": "＼"}))


def render(cues, items):
    ass, srt = [HEADER], []
    for cue in cues:
        item = items[cue.id]
        if item["type"] == "sdh_drop":
            continue
        start = (cue.start + 5) // 10
        end = max((cue.end + 5) // 10, start + 1)
        interval = f"{ass_time(start)},{ass_time(end)}"
        zh = item["zh"]
        if item["type"] == "dialogue":
            style = "Default"
            italic = r"{\i1}" if cue.italic else ""
            body = r"{\b500}" + ass_text(zh) + r"\N{\rEng}" + italic + ass_text(cue.en)
            plain = html.escape(zh, quote=False) + "\n" + html.escape(cue.en, quote=False)
        else:
            style = "Sign" if item["type"] == "sign" else "Default"
            plain = f"【{zh}】"
            body = (r"{\b500}" if style == "Default" else "") + ass_text(plain)
            plain = html.escape(plain, quote=False)
        ass.append(f"Dialogue: 0,{interval},{style},,0,0,0,,{body}")
        if item["note"]:
            ass.append(f"Dialogue: 1,{interval},Note,,0,0,0,,注：{ass_text(item['note'])}")
        srt.append(f"{len(srt)+1}\n{srt_time(cue.start)} --> {srt_time(max(cue.end, cue.start+1))}\n{plain}")
    if not srt:
        raise ValueError("全部时间轴都被归为可丢弃音效，请核对源字幕")
    return (("\n".join(ass) + "\n").encode("utf-8-sig"),
            ("\n\n".join(srt) + "\n").encode("utf-8-sig"))


def write_file(path, data, *, replace=False, mode=None):
    """同目录暂存。手动字幕和译稿永远使用原子的不覆盖发布。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".subtitle-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            if mode is not None and os.name != "nt":
                os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        if replace:
            os.replace(name, path)
        elif os.name == "nt":
            os.rename(name, path)
        else:
            try:
                os.link(name, path)
            except OSError as exc:
                if exc.errno not in (errno.ENOTSUP, errno.EPERM, errno.EACCES, errno.EXDEV) or not sys.platform.startswith("linux"):
                    raise
                # 部分云盘挂载不支持硬链接，但实现了不覆盖的 renameat2。
                rename = getattr(ctypes.CDLL(None, use_errno=True), "renameat2", None)
                if rename is None:
                    raise
                if rename(-100, os.fsencode(name), -100, os.fsencode(path), 1):
                    number = ctypes.get_errno()
                    raise OSError(number, os.strerror(number), str(path))
    finally:
        Path(name).unlink(missing_ok=True)


def save_json(path, value):
    write_file(path, json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"), replace=True)


def upload_member(filename, data, member=""):
    ext = Path(filename).suffix.lower()
    if ext != ".zip":
        return ext, data
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        options = [x for x in archive.infolist() if not x.is_dir() and Path(x.filename).suffix.lower() in TEXT_EXTS
                   and not any(p.startswith((".", "__MACOSX")) for p in x.filename.split("/"))]
        if len(options) > 500 or not options:
            raise ValueError("压缩包中没有可选的文本字幕，或成员过多")
        names = [x.filename for x in options]
        if len(set(names)) != len(names):
            raise ValueError("压缩包内有重名字幕，请先在本地解压")
        if not member and len(options) > 1:
            return "", names
        info = next((x for x in options if x.filename == member), None) if member else options[0]
        if not info or info.flag_bits & 1 or info.file_size > MAX_SUBTITLE:
            raise ValueError("成员不存在、已加密或超过 12 MiB")
        with archive.open(info) as stream:
            return Path(info.filename).suffix.lower(), stream.read(MAX_SUBTITLE + 1)
