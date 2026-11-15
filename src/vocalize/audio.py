import queue

import numpy as np

from core.settings import BLOCK_SIZE, SAMPLE_RATE


def rms_int16(chunk: bytes) -> float:
    usable = len(chunk) - (len(chunk) % 2)
    if usable < 2:
        return 0.0
    samples = np.frombuffer(chunk[:usable], dtype="<i2")
    return float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))


def is_loud_enough(chunk: bytes, threshold: float) -> bool:
    return rms_int16(chunk) >= threshold


class Microphone:
    def __init__(self, device=None, samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE):
        self.device = device
        self.samplerate = samplerate
        self.blocksize = blocksize
        self._queue = queue.Queue()
        self._stream = None
        self._stop = object()

    def interrupt(self) -> None:
        self._queue.put(self._stop)

    def __iter__(self):
        import sounddevice as sd

        self._stream = sd.RawInputStream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            device=self.device,
            dtype="int16",
            channels=1,
            callback=self._on_audio,
        )
        self._stream.start()
        try:
            while True:
                item = self._queue.get()
                if item is self._stop:
                    return
                yield item
        finally:
            self.close()

    def _on_audio(self, indata, frames, time_info, status) -> None:
        self._queue.put(bytes(indata))

    def close(self) -> None:
        stream = self._stream
        self._stream = None
        if stream is None:
            return
        stream.stop()
        stream.close()
