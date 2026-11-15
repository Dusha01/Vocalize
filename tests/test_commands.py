import json

import pytest

from vocalize.commands import Command, parse_command, recognition_grammar


@pytest.mark.parametrize(
    "phrase",
    ["пауза", "стоп", "останови", "плей", "играй", "продолжи", "включи", "play", "pause", "stop", "resume"],
)
def test_play_pause_words(phrase):
    assert parse_command(phrase) is Command.PLAY_PAUSE


@pytest.mark.parametrize(
    "phrase",
    ["дальше", "следующий", "следующая", "следующее", "некст", "next"],
)
def test_next_words(phrase):
    assert parse_command(phrase) is Command.NEXT


@pytest.mark.parametrize(
    "phrase",
    ["назад", "предыдущий", "предыдущая", "предыдущее", "previous", "back"],
)
def test_previous_words(phrase):
    assert parse_command(phrase) is Command.PREVIOUS


def test_punctuation_and_yo_are_normalized():
    assert parse_command("Дальше!") is Command.NEXT
    assert parse_command("Ёщё дальше") is Command.NEXT


def test_empty_and_unrelated_phrases_are_ignored():
    assert parse_command("") is None
    assert parse_command("какая погода") is None


def test_two_different_actions_in_one_phrase_are_ignored():
    assert parse_command("дальше назад") is None


def test_fuzzy_match_only_for_long_tokens():
    assert parse_command("дальшк") is Command.NEXT
    assert parse_command("nex") is None


@pytest.mark.parametrize("phrase", ["next", "skip", "forward"])
def test_english_next_words(phrase):
    assert parse_command(phrase) is Command.NEXT


@pytest.mark.parametrize("phrase", ["back"])
def test_english_previous_words(phrase):
    assert parse_command(phrase) is Command.PREVIOUS


def test_recognition_grammar_is_split_by_language():
    russian = json.loads(recognition_grammar("ru"))
    english = json.loads(recognition_grammar("en"))
    assert "дальше" in russian
    assert "next" not in russian
    assert "next" in english
    assert "дальше" not in english
    assert "[unk]" in russian
    assert "[unk]" in english
