import pytest

from nfsmw_launcher.hotkeys import vk_from_key_name, vk_name


@pytest.mark.parametrize(
    "gdk_name, vk",
    [
        ("F7", 118), ("F1", 112), ("F24", 135), ("o", 79), ("O", 79), ("1", 49),
        ("Page_Up", 33), ("Scroll_Lock", 145), ("Pause", 19), ("space", 32),
        ("KP_5", 101), ("Insert", 45), ("Left", 37), ("semicolon", 186),
    ],
)
def test_vk_from_key_name(gdk_name, vk):
    assert vk_from_key_name(gdk_name) == vk


def test_unknown_key_name_returns_none():
    assert vk_from_key_name("dead_acute") is None


@pytest.mark.parametrize(
    "vk, name",
    [(118, "F7"), (79, "O"), (33, "Page Up"), (145, "Scroll Lock"), (19, "Pause"), (49, "1"), (135, "F24")],
)
def test_vk_name(vk, name):
    assert vk_name(vk) == name


def test_vk_name_for_unmapped_code_is_numeric():
    assert vk_name(250) == "Key 250"
