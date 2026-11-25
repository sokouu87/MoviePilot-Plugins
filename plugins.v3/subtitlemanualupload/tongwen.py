"""沿用海拉姆字幕大师的同文堂繁简词表。"""
import json
from functools import lru_cache
from pathlib import Path

DICTIONARIES = Path(__file__).with_name("resources") / "tongwen"


@lru_cache(maxsize=1)
def dictionaries():
    phrases = json.loads((DICTIONARIES / "t2s-phrase.min.json").read_text(encoding="utf-8"))
    characters = json.loads((DICTIONARIES / "t2s-char.min.json").read_text(encoding="utf-8"))
    return sorted(phrases.items(), key=lambda item: len(item[0]), reverse=True), str.maketrans(characters)


def traditional_to_simplified(text):
    phrases, characters = dictionaries()
    for source, target in phrases:
        if source in text:
            text = text.replace(source, target)
    return text.translate(characters)
