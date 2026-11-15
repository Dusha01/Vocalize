import ctypes

from vocalize.commands import Command
from vocalize.keys import WINDOWS_VK

_KEYEVENTF_KEYUP = 0x0002
_INPUT_KEYBOARD = 1


class WindowsMediaKeys:
    def __init__(self, send=None):
        self._send = send or _send_input

    def press(self, command: Command) -> None:
        vk = WINDOWS_VK[command]
        self._send(vk, False)
        self._send(vk, True)

    def close(self) -> None:
        return None


def open_windows_keys():
    return WindowsMediaKeys()


def _send_input(vk: int, key_up: bool) -> None:
    extra = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

    class KeybdInput(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", extra),
        ]

    class InputUnion(ctypes.Union):
        _fields_ = [("ki", KeybdInput)]

    class Input(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_ulong), ("u", InputUnion)]

    flags = _KEYEVENTF_KEYUP if key_up else 0
    event = Input(type=_INPUT_KEYBOARD, ki=KeybdInput(wVk=vk, dwFlags=flags))
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(event))
    if sent != 1:
        raise OSError(f"SendInput не отправил клавишу {vk}")
