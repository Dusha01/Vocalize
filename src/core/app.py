"""Vocalize entry point."""

import signal
import sys
import threading
import time
from datetime import datetime

from core.settings import DEBOUNCE_S, DEFAULT_RMS_THRESHOLD, Settings, load_settings, model_help
from vocalize.asr import SpeechRecognizer
from vocalize.audio import Microphone, rms_int16
from vocalize.commands import parse_command
from vocalize.keys import open_media_keys


class _DryRunKeys:
    def press(self, command) -> None:
        return None

    def close(self) -> None:
        return None


def format_log(message: str, now=None) -> str:
    current = datetime.now() if now is None else now()
    stamp = current.strftime("%H:%M:%S.") + f"{current.microsecond // 1000:03d}"
    return f"{stamp} {message}"


def run(
    audio_iter,
    recognizer,
    keys,
    *,
    dry_run=False,
    verbose=False,
    debounce_s=DEBOUNCE_S,
    rms_threshold=DEFAULT_RMS_THRESHOLD,
    clock=None,
    now=None,
    output=print,
    should_stop=None,
) -> None:
    if clock is None:
        clock = time.monotonic
    if should_stop is None:
        should_stop = lambda: False
    last_at = {}
    last_heard = None
    handled = None
    previous_tick = time.perf_counter()
    for item in audio_iter:
        if should_stop():
            break
        chunk, backlog = _unpack_chunk(item)
        arrived = time.perf_counter()
        wait_ms = (arrived - previous_tick) * 1000
        level = rms_int16(chunk)
        loud = level >= rms_threshold
        started = time.perf_counter()
        event = recognizer.accept(chunk)
        vosk_ms = (time.perf_counter() - started) * 1000
        previous_tick = time.perf_counter()
        text = (event or {}).get("text") or ""
        final = bool(event and event.get("final"))
        command = parse_command(text) if text else None
        decision, moment = _decide(text, command, handled, last_at, clock, debounce_s)
        slow = wait_ms >= 300 or vosk_ms >= 100 or (backlog or 0) >= 3
        if verbose or slow:
            output(format_log(_trace(wait_ms, backlog, level, loud, vosk_ms, text, final, decision), now))
        if not text:
            handled = None
            last_heard = None
            continue
        if text == handled:
            continue
        if text != last_heard:
            output(format_log(f"[HEARD] {text}", now))
            last_heard = text
        if command is None:
            continue
        if decision == "skip":
            output(format_log(f"[SKIP] {command.value}", now))
            _consume(recognizer)
            handled = text
            continue
        if not dry_run:
            try:
                keys.press(command)
            except Exception as exc:
                output(format_log(f"[ERROR] {exc}", now))
                continue
        last_at[command] = moment
        output(format_log(f"[ACTION] {command.value}", now))
        _consume(recognizer)
        handled = text
        last_heard = None


def _unpack_chunk(item):
    if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], (bytes, bytearray)):
        return item
    return item, None


def _decide(text, command, handled, last_at, clock, debounce_s):
    if not text:
        return "empty", None
    if text == handled:
        return "hold", None
    if command is None:
        return "no-command", None
    moment = clock()
    previous = last_at.get(command)
    if previous is not None and moment - previous < debounce_s:
        return "skip", moment
    return "action", moment


def _trace(wait_ms, backlog, level, loud, vosk_ms, text, final, decision) -> str:
    queue = "-" if backlog is None else str(backlog)
    kind = "final" if final else "partial"
    heard = text or "-"
    gate = "speech" if loud else "silence"
    return (
        f"[TRACE] wait={wait_ms:.0f}ms queue={queue} rms={level:.0f} {gate} "
        f"vosk={vosk_ms:.0f}ms {kind}='{heard}' -> {decision}"
    )


def _consume(recognizer) -> None:
    reset = getattr(recognizer, "reset", None)
    if reset is not None:
        reset()


def _with_backlog(microphone):
    for chunk in microphone:
        yield chunk, microphone._queue.qsize()


def main(argv=None) -> int:
    settings = load_settings(argv)
    if settings.list_devices:
        import sounddevice as sd

        print(sd.query_devices())
        return 0
    return listen(settings)


def listen(settings: Settings) -> int:
    missing = [(lang, path) for lang, path in settings.models.items() if not path.is_dir()]
    if missing:
        print("\n".join(model_help(lang, path) for lang, path in missing), file=sys.stderr)
        return 1

    try:
        keys = _DryRunKeys() if settings.dry_run else open_media_keys()
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    stop = threading.Event()
    microphone = Microphone(
        device=settings.device,
        samplerate=settings.sample_rate,
        blocksize=settings.block_size,
    )

    def handle_sigint(signum, frame):
        stop.set()
        microphone.interrupt()

    previous = signal.signal(signal.SIGINT, handle_sigint)
    langs = "+".join(settings.models)
    print(format_log(f"[READY] слушаю ({langs}). Ctrl+C — выход."), flush=True)
    try:
        run(
            _with_backlog(microphone),
            SpeechRecognizer(models=settings.models, sample_rate=settings.sample_rate),
            keys,
            dry_run=settings.dry_run,
            verbose=settings.verbose,
            debounce_s=settings.debounce_s,
            rms_threshold=settings.rms_threshold,
            should_stop=stop.is_set,
        )
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGINT, previous)
        keys.close()
        microphone.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
