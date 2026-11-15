from datetime import datetime

from core.app import run
from vocalize.commands import Command

STAMP = "00:05:12.340"
NOW = lambda: datetime(2026, 11, 16, 0, 5, 12, 340000)


def heard(text):
    return f"{STAMP} [HEARD] {text}"


def action(name):
    return f"{STAMP} [ACTION] {name}"


class Recorder:
    def __init__(self, events):
        self.events = list(events)
        self.calls = 0
        self.resets = 0

    def accept(self, chunk):
        self.calls += 1
        return self.events.pop(0)

    def reset(self):
        self.resets += 1


class Keys:
    def __init__(self):
        self.pressed = []

    def press(self, command):
        self.pressed.append(command)

    def close(self):
        pass


def test_final_phrase_presses_next():
    lines = []
    keys = Keys()
    recognizer = Recorder([{"text": "дальше", "final": True}])
    run(
        audio_iter=[b"\x10\x00" * 20],
        recognizer=recognizer,
        keys=keys,
        rms_threshold=0,
        clock=lambda: 10,
        now=NOW,
        output=lines.append,
    )
    assert keys.pressed == [Command.NEXT]
    assert recognizer.resets == 1
    assert lines == [heard("дальше"), action("next")]


def test_partial_is_printed_and_does_not_press():
    lines = []
    keys = Keys()
    run(
        audio_iter=[b"\x10\x00" * 20],
        recognizer=Recorder([{"text": "даль", "final": False}]),
        keys=keys,
        rms_threshold=0,
        now=NOW,
        output=lines.append,
    )
    assert keys.pressed == []
    assert lines == [heard("даль")]


def test_partial_command_acts_immediately_and_repeats_are_quiet():
    lines = []
    keys = Keys()
    recognizer = Recorder(
        [
            {"text": "дальше", "final": False},
            {"text": "дальше", "final": False},
            {"text": "дальше", "final": True},
        ]
    )
    run(
        audio_iter=[b"\x10\x00" * 20] * 3,
        recognizer=recognizer,
        keys=keys,
        rms_threshold=0,
        debounce_s=1.2,
        clock=lambda: 10,
        now=NOW,
        output=lines.append,
    )
    assert keys.pressed == [Command.NEXT]
    assert recognizer.resets == 1
    assert lines == [heard("дальше"), action("next")]


def test_silence_is_still_sent_to_recognizer():
    recognizer = Recorder([None])
    keys = Keys()
    run(
        audio_iter=[b"\x00\x00" * 20],
        recognizer=recognizer,
        keys=keys,
        rms_threshold=300,
        output=lambda line: None,
    )
    assert recognizer.calls == 1
    assert keys.pressed == []


def test_debounce_skips_repeated_command():
    lines = []
    keys = Keys()
    times = iter([0.0, 0.5])
    run(
        audio_iter=[b"\x10\x00" * 20, b"\x00\x00" * 20, b"\x10\x00" * 20],
        recognizer=Recorder(
            [
                {"text": "дальше", "final": True},
                {"text": "", "final": True},
                {"text": "дальше", "final": True},
            ]
        ),
        keys=keys,
        rms_threshold=0,
        debounce_s=1.2,
        clock=lambda: next(times),
        output=lines.append,
    )
    assert keys.pressed == [Command.NEXT]
    assert any(line.endswith("[SKIP] next") for line in lines)


def test_dry_run_does_not_press():
    keys = Keys()
    run(
        audio_iter=[b"\x10\x00" * 20],
        recognizer=Recorder([{"text": "пауза", "final": True}]),
        keys=keys,
        rms_threshold=0,
        dry_run=True,
        clock=lambda: 0,
        output=lambda line: None,
    )
    assert keys.pressed == []


def test_conflicting_phrase_does_not_press():
    keys = Keys()
    run(
        audio_iter=[b"\x10\x00" * 20],
        recognizer=Recorder([{"text": "дальше назад", "final": True}]),
        keys=keys,
        rms_threshold=0,
        output=lambda line: None,
    )
    assert keys.pressed == []


def test_key_error_is_reported():
    lines = []

    class Broken(Keys):
        def press(self, command):
            raise OSError("device gone")

    run(
        audio_iter=[b"\x10\x00" * 20],
        recognizer=Recorder([{"text": "дальше", "final": True}]),
        keys=Broken(),
        rms_threshold=0,
        clock=lambda: 0,
        output=lines.append,
    )
    assert any("[ERROR]" in line for line in lines)


def test_stuck_hypothesis_does_not_fire_again():
    keys = Keys()
    run(
        audio_iter=[b"\x10\x00" * 20, b"\x10\x00" * 20],
        recognizer=Recorder(
            [
                {"text": "дальше", "final": False},
                {"text": "дальше", "final": False},
            ]
        ),
        keys=keys,
        rms_threshold=0,
        debounce_s=1.2,
        clock=lambda: 10,
        output=lambda line: None,
    )
    assert keys.pressed == [Command.NEXT]


def test_verbose_trace_shows_wait_and_vosk_time():
    lines = []
    run(
        audio_iter=[(b"\x10\x00" * 20, 4)],
        recognizer=Recorder([{"text": "дальше", "final": False}]),
        keys=Keys(),
        rms_threshold=0,
        verbose=True,
        clock=lambda: 1,
        now=NOW,
        output=lines.append,
    )
    trace = next(line for line in lines if "[TRACE]" in line)
    assert "wait=" in trace
    assert "queue=4" in trace
    assert "vosk=" in trace
    assert "-> action" in trace


def test_stop_flag_ends_the_loop():
    recognizer = Recorder([{"text": "дальше", "final": True}] * 5)
    run(
        audio_iter=[b"\x10\x00" * 20] * 5,
        recognizer=recognizer,
        keys=Keys(),
        rms_threshold=0,
        should_stop=lambda: recognizer.calls >= 1,
        output=lambda line: None,
    )
    assert recognizer.calls == 1
