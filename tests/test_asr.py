import json

from vocalize.asr import SpeechRecognizer


class FakeKaldi:
    def __init__(self, final=False, text="", confidence=None):
        self.final = final
        self.text = text
        self.confidence = confidence
        self.resets = 0

    def AcceptWaveform(self, chunk):
        return self.final

    def Reset(self):
        self.resets += 1

    def Result(self):
        payload = {"text": self.text}
        if self.confidence is not None:
            payload["result"] = [{"word": self.text, "conf": self.confidence}]
        return json.dumps(payload)

    def PartialResult(self):
        return json.dumps({"partial": self.text})


def test_final_result_is_marked_final():
    event = SpeechRecognizer(model_path=None, recognizer=FakeKaldi(final=True, text="дальше")).accept(b"audio")
    assert event["text"] == "дальше"
    assert event["final"] is True


def test_partial_result_is_not_final():
    event = SpeechRecognizer(model_path=None, recognizer=FakeKaldi(final=False, text="даль")).accept(b"audio")
    assert event["text"] == "даль"
    assert event["final"] is False


def test_empty_partial_returns_none():
    recognizer = SpeechRecognizer(model_path=None, recognizer=FakeKaldi(final=False, text=""))
    assert recognizer.accept(b"audio") is None


def test_reset_clears_recognizer():
    kaldi = FakeKaldi()
    SpeechRecognizer(model_path=None, recognizer=kaldi).reset()
    assert kaldi.resets == 1


def test_one_language_command_is_kept_when_the_other_is_silent():
    recognizer = SpeechRecognizer(
        recognizers=[FakeKaldi(final=False, text="дальше"), FakeKaldi(final=False, text="[unk]")]
    )
    assert recognizer.accept(b"audio")["text"] == "дальше"


def test_same_command_from_both_languages_is_accepted():
    event = SpeechRecognizer(
        recognizers=[FakeKaldi(final=False, text="дальше"), FakeKaldi(final=False, text="next")]
    ).accept(b"audio")
    assert event["text"] in {"дальше", "next"}


def test_two_languages_disagreeing_without_confidence_do_not_choose():
    recognizer = SpeechRecognizer(
        recognizers=[FakeKaldi(final=False, text="дальше"), FakeKaldi(final=False, text="pause")]
    )
    assert recognizer.accept(b"audio") is None


def test_higher_confidence_wins_a_language_conflict():
    recognizer = SpeechRecognizer(
        recognizers=[
            FakeKaldi(final=True, text="дальше", confidence=0.95),
            FakeKaldi(final=True, text="next", confidence=0.4),
        ]
    )
    assert recognizer.accept(b"audio")["text"] == "дальше"
