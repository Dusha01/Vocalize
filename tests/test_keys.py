import pytest

from vocalize.commands import Command
from vocalize.keys import EV_KEY, KEY_NEXTSONG, KEY_PLAYPAUSE, KEY_PREVIOUSSONG, WINDOWS_VK
from vocalize.keys_linux import LinuxMediaKeys, open_linux_keys, pack_event, pack_setup
from vocalize.keys_windows import WindowsMediaKeys


class FakeDevice:
    def __init__(self):
        self.events = []
        self.closed = False

    def write(self, ev_type, code, value):
        self.events.append((ev_type, code, value))

    def syn(self):
        self.events.append(("syn",))

    def close(self):
        self.closed = True


def test_linux_next_presses_and_releases():
    device = FakeDevice()
    LinuxMediaKeys(device).press(Command.NEXT)
    assert device.events == [
        (EV_KEY, KEY_NEXTSONG, 1),
        ("syn",),
        (EV_KEY, KEY_NEXTSONG, 0),
        ("syn",),
    ]


@pytest.mark.parametrize(
    ("command", "code"),
    [
        (Command.PLAY_PAUSE, KEY_PLAYPAUSE),
        (Command.NEXT, KEY_NEXTSONG),
        (Command.PREVIOUS, KEY_PREVIOUSSONG),
    ],
)
def test_linux_command_codes(command, code):
    device = FakeDevice()
    LinuxMediaKeys(device).press(command)
    assert device.events[0] == (EV_KEY, code, 1)
    assert device.events[2] == (EV_KEY, code, 0)


def test_linux_close_closes_device():
    device = FakeDevice()
    LinuxMediaKeys(device).close()
    assert device.closed


def test_uinput_payloads_match_kernel_layout():
    assert len(pack_setup("vocalize-media-keys")) == 92
    assert len(pack_event(EV_KEY, KEY_NEXTSONG, 1)) == 24


def test_open_linux_keys_explains_missing_permission():
    class Denied:
        def __init__(self, *args, **kwargs):
            raise PermissionError("denied")

    with pytest.raises(RuntimeError, match="uinput"):
        open_linux_keys(uinput_cls=Denied, key_codes=(1, 2, 3))


def test_windows_next_sends_key_down_and_up():
    calls = []
    WindowsMediaKeys(send=lambda vk, key_up: calls.append((vk, key_up))).press(Command.NEXT)
    assert calls == [(WINDOWS_VK[Command.NEXT], False), (WINDOWS_VK[Command.NEXT], True)]


@pytest.mark.parametrize(
    ("command", "vk"),
    [
        (Command.PLAY_PAUSE, 0xB3),
        (Command.NEXT, 0xB0),
        (Command.PREVIOUS, 0xB1),
    ],
)
def test_windows_virtual_key_codes(command, vk):
    assert WINDOWS_VK[command] == vk
