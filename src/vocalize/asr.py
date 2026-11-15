import json

from core.settings import SAMPLE_RATE
from vocalize.commands import parse_command, recognition_grammar

_CONFIDENCE_GAP = 0.15
_MIN_CONFIDENCE = 0.75


def choose_transcript(events) -> dict | None:
    present = []
    for event in events:
        if not event:
            continue
        text = _without_unknown(event.get("text", ""))
        if not text:
            continue
        present.append({**event, "text": text})
    if not present:
        return None

    commanded = [(parse_command(event["text"]), event) for event in present]
    commanded = [(command, event) for command, event in commanded if command is not None]
    commands = {command for command, _ in commanded}
    if len(commands) == 1:
        return max((event for _, event in commanded), key=_rank)
    if len(commands) > 1:
        ranked = sorted(commanded, key=lambda item: _rank(item[1]), reverse=True)
        best = ranked[0][1]
        second = ranked[1][1]
        best_confidence = best.get("confidence") or 0
        second_confidence = second.get("confidence") or 0
        if best_confidence >= _MIN_CONFIDENCE and best_confidence - second_confidence >= _CONFIDENCE_GAP:
            return best
        return None
    return max(present, key=_rank)


class SpeechRecognizer:
    def __init__(self, model_path=None, sample_rate=SAMPLE_RATE, recognizer=None, recognizers=None, models=None):
        if recognizers is not None:
            self._engines = list(recognizers)
        elif recognizer is not None:
            self._engines = [recognizer]
        else:
            if models is None:
                models = {"ru": model_path}
            self._engines = [_load_model(path, lang, sample_rate) for lang, path in models.items()]

    def reset(self) -> None:
        for engine in self._engines:
            reset = getattr(engine, "Reset", None)
            if reset is not None:
                reset()

    def accept(self, chunk: bytes):
        return choose_transcript(_read_engine(engine, chunk) for engine in self._engines)


def _load_model(path, lang: str, sample_rate: int):
    import vosk
    from vosk import KaldiRecognizer, Model

    vosk.SetLogLevel(-1)
    return KaldiRecognizer(Model(str(path)), sample_rate, recognition_grammar(lang))


def _read_engine(engine, chunk: bytes):
    if engine.AcceptWaveform(chunk):
        payload = json.loads(engine.Result() or "{}")
        text = str(payload.get("text", "")).strip()
        final = True
        confidence = _confidence(payload)
    else:
        payload = json.loads(engine.PartialResult() or "{}")
        text = str(payload.get("partial", "")).strip()
        final = False
        confidence = None
    if not text:
        return None
    return {"text": text, "final": final, "confidence": confidence}


def _confidence(payload: dict) -> float | None:
    scores = [
        float(word["conf"])
        for word in payload.get("result") or []
        if isinstance(word, dict) and "conf" in word and word.get("word") != "[unk]"
    ]
    if not scores:
        return None
    return sum(scores) / len(scores)


def _without_unknown(text: str) -> str:
    return " ".join(token for token in text.split() if token != "[unk]").strip()


def _rank(event: dict):
    return (event.get("confidence") or 0, event.get("final", False), len(event.get("text", "")))
