import sys
from typing import Protocol

from vocalize.commands import Command

EV_KEY = 1
KEY_NEXTSONG = 163
KEY_PLAYPAUSE = 164
KEY_PREVIOUSSONG = 165

WINDOWS_VK = {
    Command.PLAY_PAUSE: 0xB3,
    Command.NEXT: 0xB0,
    Command.PREVIOUS: 0xB1,
}

UINPUT_HELP = (
    "нет доступа к /dev/uinput. Один раз настройте права:\n"
    "  sudo tee /etc/udev/rules.d/99-vocalize-uinput.rules >/dev/null <<'EOF'\n"
    'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"\n'
    "EOF\n"
    "  sudo udevadm control --reload-rules && sudo udevadm trigger\n"
    '  sudo usermod -aG input "$USER"\n'
    "Затем выйдите из сессии и зайдите снова."
)


class MediaKeys(Protocol):
    def press(self, command: Command) -> None: ...

    def close(self) -> None: ...


def open_media_keys() -> MediaKeys:
    if sys.platform == "linux":
        from vocalize.keys_linux import open_linux_keys

        return open_linux_keys()
    if sys.platform == "win32":
        from vocalize.keys_windows import open_windows_keys

        return open_windows_keys()
    raise RuntimeError(f"медиа-клавиши не поддерживаются на {sys.platform}")
