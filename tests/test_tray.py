import pytest

from nfsmw_launcher.tray import argb_pixmap, close_decision, handle_menu_event, menu_items


def test_argb_pixmap_moves_alpha_first():
    rgba = bytes([255, 0, 0, 128, 0, 255, 0, 255])
    assert argb_pixmap(rgba) == bytes([128, 255, 0, 0, 255, 0, 255, 0])


def test_menu_offers_show_launch_settings_and_quit():
    items = menu_items()
    assert [(i, p.get("label"), p.get("type")) for i, p in items] == [
        (1, "Show Launcher", None),
        (2, "Launch Game", None),
        (3, "Redux Settings", None),
        (4, None, "separator"),
        (5, "Quit", None),
    ]


def test_clicking_menu_items_calls_the_right_callback():
    calls = []
    callbacks = {name: (lambda n=name: calls.append(n)) for name in ("show", "launch", "settings", "quit")}
    for item_id in (1, 2, 3, 4, 5):
        handle_menu_event(item_id, "clicked", callbacks)
    handle_menu_event(2, "hovered", callbacks)
    assert calls == ["show", "launch", "settings", "quit"]


@pytest.mark.parametrize(
    "action, tray_ok, expected",
    [
        ("ask", True, "ask"),
        ("quit", True, "quit"),
        ("tray", True, "tray"),
        ("ask", False, "ask"),
        ("tray", False, "ask"),
        ("quit", False, "quit"),
    ],
)
def test_close_decision_never_hides_the_app_without_a_tray_and_explains_instead(action, tray_ok, expected):
    assert close_decision(action, tray_ok) == expected
