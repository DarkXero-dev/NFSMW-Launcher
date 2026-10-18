_NAMED = {
    "BackSpace": (8, "Backspace"),
    "Tab": (9, "Tab"),
    "Return": (13, "Enter"),
    "Pause": (19, "Pause"),
    "Caps_Lock": (20, "Caps Lock"),
    "Escape": (27, "Escape"),
    "space": (32, "Space"),
    "Page_Up": (33, "Page Up"),
    "Page_Down": (34, "Page Down"),
    "End": (35, "End"),
    "Home": (36, "Home"),
    "Left": (37, "Left"),
    "Up": (38, "Up"),
    "Right": (39, "Right"),
    "Down": (40, "Down"),
    "Insert": (45, "Insert"),
    "Delete": (46, "Delete"),
    "KP_Multiply": (106, "Num *"),
    "KP_Add": (107, "Num +"),
    "KP_Subtract": (109, "Num -"),
    "KP_Decimal": (110, "Num ."),
    "KP_Divide": (111, "Num /"),
    "Num_Lock": (144, "Num Lock"),
    "Scroll_Lock": (145, "Scroll Lock"),
    "semicolon": (186, ";"),
    "equal": (187, "="),
    "comma": (188, ","),
    "minus": (189, "-"),
    "period": (190, "."),
    "slash": (191, "/"),
    "grave": (192, "`"),
    "bracketleft": (219, "["),
    "backslash": (220, "\\"),
    "bracketright": (221, "]"),
    "apostrophe": (222, "'"),
}

_KEY_NAME_TO_VK = {name: vk for name, (vk, _) in _NAMED.items()}
_VK_TO_NAME = {vk: label for vk, label in _NAMED.values()}

for _digit in range(10):
    _KEY_NAME_TO_VK[str(_digit)] = 48 + _digit
    _VK_TO_NAME[48 + _digit] = str(_digit)
    _KEY_NAME_TO_VK[f"KP_{_digit}"] = 96 + _digit
    _VK_TO_NAME[96 + _digit] = f"Num {_digit}"
for _index in range(26):
    _VK_TO_NAME[65 + _index] = chr(65 + _index)
    _KEY_NAME_TO_VK[chr(97 + _index)] = 65 + _index
    _KEY_NAME_TO_VK[chr(65 + _index)] = 65 + _index
for _number in range(1, 25):
    _KEY_NAME_TO_VK[f"F{_number}"] = 111 + _number
    _VK_TO_NAME[111 + _number] = f"F{_number}"


def vk_from_key_name(gdk_name: str) -> int | None:
    return _KEY_NAME_TO_VK.get(gdk_name)


def vk_name(code: int) -> str:
    return _VK_TO_NAME.get(code, f"Key {code}")
