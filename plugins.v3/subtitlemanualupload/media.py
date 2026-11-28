"""读取本地媒体的字幕与英文音轨。STRM 只处理旁挂字幕。"""
import json
import re
import subprocess
import tempfile
from pathlib import Path
from time import monotonic

from .subtitles import Cue, MAX_SUBTITLE, TEXT_EXTS, parse

VIDEO = {".mkv", ".mp4", ".m4v", ".avi", ".mov", ".ts", ".m2ts", ".mpg", ".mpeg", ".wmv", ".webm", ".iso", ".strm"}
ENGLISH = {"eng", "en", "english"}
TEXT_CODECS = {"subrip", "srt", "ass", "ssa", "mov_text", "webvtt", "text"}
CHINESE_LABEL = re.compile(r"(?<![a-z0-9])(?:zh|chi|zho|chs|cht|cmn|yue|chinese)(?![a-z0-9])|中文|汉语|漢語|简体|簡體|繁体|繁體|简中|簡中|繁中", re.I)
CHINESE_SCRIPTS = {
    "hans": re.compile(r"(?<![a-z0-9])(?:zh[-_]hans|chs|simplified)(?![a-z0-9])|简体|簡體|简中|簡中", re.I),
    "hant": re.compile(r"(?<![a-z0-9])(?:zh[-_]hant|cht|traditional)(?![a-z0-9])|繁体|繁體|繁中", re.I),
}
LIMITED = re.compile(r"forced|commentary|director.s comment|signs[\s&_-]*(?:and[\s_-]*)?songs|外语部分|导演评论|導演評論|强制|強制", re.I)
EPISODE = re.compile(r"(?i)(?<![a-z0-9])s(\d{1,3})[ ._-]*e(\d{1,4})")


def metadata(path, *, title="", year="", season="", episode="", series_id=""):
    match = EPISODE.search(path.stem)
    title = title or (path.stem[:match.start()].strip(" ._-") if match else path.stem)
    def number(value, group):
        digits = re.search(r"\d+", str(value or ""))
        return int(digits.group()) if digits else (int(match[group]) if match else None)
    return {"title": title or path.stem, "year": str(year or ""), "season": number(season, 1),
            "episode": number(episode, 2), "series_id": str(series_id or "")}


def english_text(cues):
    sample = " ".join(c.en for c in cues if c.en)[:6000]
    if re.search(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7ff]", sample):
        return False
    return bool(re.search(r"(?i)\b(the|i|you|i'm|we|yes|no|hello|this|that|of|and|to|is|are|it's|don't|what|please|thanks|hi|bye|okay)\b", sample))


def probe_streams(video, *, timeout=90):
    if video.suffix.lower() == ".strm":
        return []
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(video)],
                           capture_output=True, timeout=timeout, check=True)
    return json.loads(probe.stdout).get("streams", [])


def language(track):
    return re.split("[-_]", str((track.get("tags") or {}).get("language") or "und").lower(), maxsplit=1)[0]


def chinese_script(labels):
    matches = [key for key, pattern in CHINESE_SCRIPTS.items() if pattern.search(labels)]
    return matches[0] if len(matches) == 1 else ""


def text_tracks(streams):
    return [
        track for track in streams if track.get("codec_type") == "subtitle" and track.get("codec_name") in TEXT_CODECS
        and not any((track.get("disposition") or {}).get(k) for k in ("forced", "comment", "hearing_impaired_only"))
        and not LIMITED.search((track.get("tags") or {}).get("title", ""))
    ]


def extract_track(video, track, *, timeout=300):
    result = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-map", f"0:{track['index']}",
                             "-f", "srt", "-"], capture_output=True, timeout=timeout)
    if result.returncode or not result.stdout:
        return []
    try:
        return parse(result.stdout, ".srt")
    except ValueError:
        return []


def embedded_chinese(video, streams):
    candidates = []
    for track in text_tracks(streams):
        tags = track.get("tags") or {}
        title = tags.get("title") or ""
        lang = language(track)
        if CHINESE_LABEL.search(lang) or (lang in ("und", "unk", "mul") and CHINESE_LABEL.search(title)):
            script = chinese_script(f"{tags.get('language', '')} {title}")
            rank = {"hans": 0, "hant": 1, "": 2}[script]
            candidates.append((rank, bool(track.get("disposition", {}).get("hearing_impaired")), track["index"], script, track))
    for _, _, index, script, track in sorted(candidates):
        cues = extract_track(video, track)
        if any(re.search(r"[\u3400-\u9fff]", cue.raw) for cue in cues):
            label = {"hans": "简中", "hant": "繁中", "": "中文"}[script]
            return cues, script, f"内封{label}轨 #{index}"
    return None


def english_subtitles(video, streams, *, deadline=None):
    prefix = video.stem.casefold()
    candidates = []
    for file in video.parent.iterdir():
        name = file.stem.casefold()
        if not (name == prefix or name.startswith(prefix + ".")) or file.suffix.lower() not in TEXT_EXTS or file.is_symlink():
            continue
        tags = name[len(prefix):].strip(".")
        if any(t in tags for t in ("ai", "chi", "chs", "cht", "zh", "bilingual", "双语", "&")) or LIMITED.search(tags):
            continue
        parts = set(re.split(r"[._ -]", tags))
        if tags and not parts.intersection(ENGLISH | {"sdh", "cc"}):
            continue
        candidates.append((0 if parts & ENGLISH else 1, file.suffix.lower() != ".srt", name, file))
    for _, _, _, file in sorted(candidates):
        if file.stat().st_size > MAX_SUBTITLE:
            continue
        try:
            rows = parse(file.read_bytes(), file.suffix)
        except (UnicodeError, ValueError):
            continue
        if english_text(rows) or (set(re.split(r"[._ -]", file.stem[len(video.stem):].lower())) & ENGLISH and
                                  not re.search(r"[\u3400-\u9fff]", "".join(c.en for c in rows)[:6000])):
            return rows, "英文外挂 · " + file.name
    for track in sorted(text_tracks(streams), key=lambda s: (language(s) not in ENGLISH, not s.get("disposition", {}).get("default"))):
        lang = language(track)
        if lang not in ENGLISH | {"und", ""}:
            continue
        timeout = 300 if deadline is None else max(0.1, deadline - monotonic())
        rows = extract_track(video, track, timeout=timeout)
        if rows and (lang in ENGLISH or english_text(rows)):
            return rows, f"内封英文轨 #{track['index']}"
    return None


def source_cues(video, model_path, progress, *, streams=None):
    if streams is None:
        try:
            streams = probe_streams(video)
        except (OSError, ValueError, subprocess.SubprocessError):
            subtitles = english_subtitles(video, [])
            if subtitles:
                return subtitles
            raise
    subtitles = english_subtitles(video, streams)
    if subtitles:
        return subtitles
    if video.suffix.lower() == ".strm":
        raise ValueError("STRM 未找到英文外挂，请选中本集并上传英文原稿")
    audio = [s for s in streams if s.get("codec_type") == "audio" and not LIMITED.search((s.get("tags") or {}).get("title", ""))]
    audio.sort(key=lambda s: (language(s) not in ENGLISH, not s.get("disposition", {}).get("default")))
    if not audio or language(audio[0]) not in ENGLISH | {"und", ""}:
        raise ValueError("没有英文字幕或可识别的英文音轨")
    try:
        from faster_whisper import WhisperModel
        import numpy as np
    except ImportError as exc:
        raise ValueError("无英文字幕，请安装 faster-whisper 或手动上传英文原稿") from exc
    if not model_path or not (Path(model_path) / "model.bin").is_file():
        raise ValueError("缺少本地 Whisper 模型，请在插件设置填写模型目录或上传英文原稿")
    progress("Whisper 识别英文音轨")
    with tempfile.TemporaryDirectory() as directory:
        # 直接传 16 kHz 单声道样本；兼容 MoviePilot 内置的不同版本 PyAV。
        pcm = str(Path(directory) / "speech.f32")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-map", f"0:{audio[0]['index']}",
                        "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", pcm], check=True, capture_output=True, timeout=3600)
        engine = WhisperModel(str(model_path), device="cpu", compute_type="int8", local_files_only=True)
        samples = np.memmap(pcm, dtype="<f4", mode="r")
        segments, info = engine.transcribe(samples, language="en" if language(audio[0]) in ENGLISH else None,
                                           vad_filter=True, temperature=0, beam_size=5)
        if info.language != "en":
            raise ValueError("音轨检测为非英语，请上传对应的英文原稿")
        rows = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                rows.append(Cue(len(rows) + 1, round(segment.start * 1000), round(segment.end * 1000), text, text, False))
        del samples, segments
    if not rows:
        raise ValueError("音轨没有识别出英文对白")
    return rows, "Whisper 英文听写"
