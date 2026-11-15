import fcntl
import os
import struct

from vocalize.commands import Command
from vocalize.keys import EV_KEY, KEY_NEXTSONG, KEY_PLAYPAUSE, KEY_PREVIOUSSONG, UINPUT_HELP

_CODES = {
    Command.PLAY_PAUSE: KEY_PLAYPAUSE,
    Command.NEXT: KEY_NEXTSONG,
    Command.PREVIOUS: KEY_PREVIOUSSONG,
}

# linux/uinput.h and linux/input.h on x86_64.
_UI_DEV_CREATE = 21761
_UI_DEV_DESTROY = 21762
_UI_DEV_SETUP = 1079792899
_UI_SET_EVBIT = 1074025828
_UI_SET_KEYBIT = 1074025829
_BUS_USB = 0x03
_EV_SYN = 0
_SYN_REPORT = 0
_UINPUT_PATH = "/dev/uinput"


class LinuxMediaKeys:
    def __init__(self, device):
        self._device = device

    def press(self, command: Command) -> None:
        code = _CODES[command]
        self._device.write(EV_KEY, code, 1)
        self._device.syn()
        self._device.write(EV_KEY, code, 0)
        self._device.syn()

    def close(self) -> None:
        self._device.close()


class UInputDevice:
    """Virtual keyboard. Same events a physical media-key keyboard sends."""

    def __init__(self, events, name="vocalize-media-keys"):
        self._fd = os.open(_UINPUT_PATH, os.O_WRONLY | os.O_NONBLOCK)
        try:
            for event_type, codes in events.items():
                fcntl.ioctl(self._fd, _UI_SET_EVBIT, int(event_type))
                if event_type == EV_KEY:
                    for code in codes:
                        fcntl.ioctl(self._fd, _UI_SET_KEYBIT, int(code))
            fcntl.ioctl(self._fd, _UI_DEV_SETUP, pack_setup(name))
            fcntl.ioctl(self._fd, _UI_DEV_CREATE, 0)
        except Exception:
            os.close(self._fd)
            self._fd = None
            raise

    def write(self, event_type, code, value) -> None:
        os.write(self._fd, pack_event(event_type, code, value))

    def syn(self) -> None:
        self.write(_EV_SYN, _SYN_REPORT, 0)

    def close(self) -> None:
        fd = self._fd
        self._fd = None
        if fd is None:
            return
        try:
            fcntl.ioctl(fd, _UI_DEV_DESTROY, 0)
        finally:
            os.close(fd)


def pack_setup(name: str) -> bytes:
    encoded = name.encode("utf-8")[:80]
    payload = struct.pack("HHHH80sI", _BUS_USB, 1, 1, 1, encoded, 0)
    if len(payload) != 92:
        raise RuntimeError(f"uinput setup size is {len(payload)}, expected 92")
    return payload


def pack_event(event_type: int, code: int, value: int) -> bytes:
    payload = struct.pack("llHHi", 0, 0, event_type, code, value)
    if len(payload) != 24:
        raise RuntimeError(f"input_event size is {len(payload)}, expected 24")
    return payload


def open_linux_keys(uinput_cls=None, key_codes=None):
    codes = key_codes if key_codes is not None else (KEY_PLAYPAUSE, KEY_NEXTSONG, KEY_PREVIOUSSONG)
    if uinput_cls is None:
        uinput_cls = UInputDevice
    try:
        device = uinput_cls({EV_KEY: list(codes)}, name="vocalize-media-keys")
    except (PermissionError, OSError) as exc:
        raise RuntimeError(UINPUT_HELP) from exc
    return LinuxMediaKeys(device)
