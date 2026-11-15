import difflib
import json
import re
from enum import Enum

_TOKEN = re.compile(r"[0-9a-zа-я]+")
_FUZZY_CUTOFF = 0.8
_MIN_FUZZY_LENGTH = 4


class Command(Enum):
    PLAY_PAUSE = "play_pause"
    NEXT = "next"
    PREVIOUS = "previous"


_RU = {
    Command.PLAY_PAUSE: frozenset({"пауза", "стоп", "останови", "плей", "играй", "продолжи", "включи"}),
    Command.NEXT: frozenset({"дальше", "следующий", "следующая", "следующее", "некст"}),
    Command.PREVIOUS: frozenset({"назад", "предыдущий", "предыдущая", "предыдущее"}),
}
_EN = {
    Command.PLAY_PAUSE: frozenset({"play", "pause", "stop", "resume"}),
    Command.NEXT: frozenset({"next", "skip", "forward"}),
    Command.PREVIOUS: frozenset({"previous", "back"}),
}
_BY_LANG = {"ru": _RU, "en": _EN}
_GROUPS = {
    command: frozenset().union(*(groups[command] for groups in _BY_LANG.values()))
    for command in Command
}


def recognition_grammar(lang: str | None = None) -> str:
    groups = _BY_LANG[lang] if lang is not None else _GROUPS
    words = sorted(word for words in groups.values() for word in words)
    words.append("[unk]")
    return json.dumps(words, ensure_ascii=False)


def parse_command(text: str) -> Command | None:
    hits = {command for token in _tokens(text) if (command := _match_token(token)) is not None}
    if len(hits) != 1:
        return None
    return next(iter(hits))


def _tokens(text: str) -> list[str]:
    normalized = text.lower().replace("ё", "е")
    return _TOKEN.findall(normalized)


def _match_token(token: str) -> Command | None:
    for command, words in _GROUPS.items():
        if token in words:
            return command
    if len(token) < _MIN_FUZZY_LENGTH:
        return None
    vocabulary = [
        (word, command)
        for command, words in _GROUPS.items()
        for word in words
        if len(word) >= _MIN_FUZZY_LENGTH
    ]
    matches = difflib.get_close_matches(token, [word for word, _ in vocabulary], n=3, cutoff=_FUZZY_CUTOFF)
    commands = {
        command
        for word, command in vocabulary
        if word in matches and not word.startswith(token)
    }
    if len(commands) != 1:
        return None
    return next(iter(commands))
