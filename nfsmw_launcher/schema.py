import re
from dataclasses import dataclass, field

from .ini_file import IniFile

TABS = ["Display", "Graphics", "Gameplay", "Menus", "Hotkeys", "Advanced"]

FILES = {
    "NFSMostWanted.WidescreenFix.ini": "Widescreen Fix",
    "NFSMW_XenonEffects.ini": "Xenon Effects",
    "NFSMWGraphicsSettings.ini": "Graphics Override",
    "NFSMWHDReflections.ini": "HD Reflections",
    "NFSMWFEShadows.ini": "Front-end Shadows",
    "NFSMWMotionBlurControllerSettings.ini": "Motion Blur",
    "NFSMWExtraOptionsSettings.ini": "Extra Options",
    "NFSMWRaceFixesSettings.ini": "Race Fixes",
    "NFSMWUnlimiterSettings.ini": "Unlimiter",
}

_FILE_TAB = {
    "NFSMostWanted.WidescreenFix.ini": "Graphics",
    "NFSMW_XenonEffects.ini": "Graphics",
    "NFSMWGraphicsSettings.ini": "Graphics",
    "NFSMWHDReflections.ini": "Graphics",
    "NFSMWFEShadows.ini": "Graphics",
    "NFSMWMotionBlurControllerSettings.ini": "Graphics",
    "NFSMWExtraOptionsSettings.ini": "Gameplay",
    "NFSMWRaceFixesSettings.ini": "Menus",
    "NFSMWUnlimiterSettings.ini": "Gameplay",
}

_SECTION_TAB = {
    ("NFSMostWanted.WidescreenFix.ini", "MAIN"): "Display",
    ("NFSMostWanted.WidescreenFix.ini", "MISC"): "Display",
    ("NFSMWExtraOptionsSettings.ini", "Weather"): "Graphics",
    ("NFSMWExtraOptionsSettings.ini", "Menu"): "Menus",
    ("NFSMWExtraOptionsSettings.ini", "Fixes"): "Advanced",
    ("NFSMWExtraOptionsSettings.ini", "Misc"): "Advanced",
    ("NFSMWUnlimiterSettings.ini", "Fixes"): "Advanced",
    ("NFSMWUnlimiterSettings.ini", "Misc"): "Advanced",
}

_ZERO_ONE_FILES = {
    "NFSMostWanted.WidescreenFix.ini",
    "NFSMW_XenonEffects.ini",
    "NFSMWGraphicsSettings.ini",
    "NFSMWHDReflections.ini",
    "NFSMWFEShadows.ini",
}

RESOLUTIONS = [
    (1280, 720, "720p"),
    (1600, 900, "900p"),
    (1920, 1080, "1080p"),
    (2560, 1080, "1080p ultrawide"),
    (2560, 1440, "1440p"),
    (3440, 1440, "1440p ultrawide"),
    (5120, 1440, "1440p super ultrawide"),
    (3840, 2160, "4K"),
    (3840, 1600, "4K ultrawide"),
    (5120, 2160, "5K2K ultrawide"),
    (5120, 2880, "5K"),
    (6880, 2880, "5K ultrawide"),
]

_LABELS = {
    "UseD3DDeviceTexture": "Use D3D device texture",
    "SBRechargeTime": "Speedbreaker recharge time",
    "SBRechargeSpeedLimit": "Speedbreaker recharge speed limit",
    "SBMassMultiplier": "Speedbreaker mass multiplier",
    "DDayFix": "DDay fix",
    "ShowOnlineOpts": "Show online options",
    "FEScale": "Front-end UI scale",
    "FMVScale": "FMV scale",
    "AutoFitFE": "Auto-fit front-end",
    "AutoFitFMV": "Auto-fit FMVs",
}

_FLOAT_KEYS = {"GeneralRainAmount", "RoadReflectionAmount"}
_INT_RANGES = {"SimRate": (-2, 1000)}

_ANTIALIAS = [("-1", "Not set")] + [(str(n), str(n)) for n in range(5)]
_CHOICES = {
    "Scaling": [("0", "Original"), ("1", "Xbox 360"), ("2", "Mathematically correct")],
    "ShadowsRes": [
        ("1024", "1024 (original)"),
        ("2048", "2048 (Xbox 360)"),
        ("4096", "4096 (4K PC Ultra)"),
        ("16384", "16384 (maximum)"),
    ],
    "FMVWidescreenMode": [("1", "Cropped"), ("2", "Stretched")],
    "WindowedMode": [
        ("0", "Fullscreen"),
        ("1", "Borderless"),
        ("2", "Border"),
        ("3", "Resizable border"),
        ("4", "Borderless fullscreen"),
        ("5", "Borderless fullscreen stretched"),
    ],
    "ImproveGamepadSupport": [
        ("0", "Disabled"),
        ("1", "Xbox icons"),
        ("2", "PlayStation icons"),
        ("3", "None"),
    ],
    "ShadowMapTextureFormat": [
        ("-1", "Disable patches"),
        ("0", "D24S8 (sharp)"),
        ("1", "INTZ (soft)"),
        ("2", "DF16 (Radeon)"),
        ("3", "DF24 (Radeon)"),
    ],
    "ForcedGPUVendor": [
        ("0", "Disabled"),
        ("0x10DE", "NVIDIA"),
        ("0x1002", "ATI/AMD"),
        ("0x8086", "Intel"),
    ],
    "BetterHandlingWithFlatTires": [
        ("0", "NFS Most Wanted"),
        ("1", "NFS Carbon"),
        ("2", "Carbon and Most Wanted mix"),
    ],
    "RestoreDetails": [("0", "Off"), ("1", "Lights and shadows"), ("2", "And particle effects")],
    "RemoveLastGenEffects": [("0", "Off"), ("1", "Sun flare"), ("2", "Sun flare and headlights")],
    "ForceMaximumFSAALevel": _ANTIALIAS,
    "ForceCarLOD": [("-1", "None")] + [(str(i), "ABCDE"[i]) for i in range(5)],
    "ForceTireLOD": [("-1", "None")] + [(str(i), "ABCD"[i]) for i in range(4)],
}

_DEFAULT_PATTERNS = [
    re.compile(r"Default\s*=\s*(-?[\w.]+)"),
    re.compile(r"(-?[\w.]+)\s*=\s*[^,()|]*\(Default\)"),
    re.compile(r"(-?[\w.]+)\s*=\s*Default"),
]
_RANGE = re.compile(r"\((-?\d+)/(-?\d+)\)")
_BOOLEAN_WORDING = re.compile(r"0 = False|1 = True")
_INT = re.compile(r"-?\d+")
_FLOAT = re.compile(r"-?\d*\.\d+")
_WORD_BREAK = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


@dataclass
class Option:
    file: str
    section: str
    key: str
    label: str
    description: str
    tab: str
    group: str
    kind: str
    advanced: bool = False
    default: str | None = None
    choices: list[tuple[str, str]] = field(default_factory=list)
    minimum: float = 0
    maximum: float = 0
    digits: int = 0


def resolution_label(width: int, height: int) -> str:
    names = {(w, h): name for w, h, name in RESOLUTIONS}
    return f"{width} x {height} ({names.get((width, height), 'current')})"


def label_for(key: str) -> str:
    if key in _LABELS:
        return _LABELS[key]
    words = _WORD_BREAK.sub(" ", key.replace("_", " "))
    return words[0].upper() + words[1:]


def _section_title(section: str) -> str:
    title = label_for(section)
    return title.capitalize() if title.isupper() else title


def _default_for(comment: str) -> str | None:
    for pattern in _DEFAULT_PATTERNS:
        match = pattern.search(comment)
        if match:
            return match.group(1)
    return None


def _decimals(text: str | None) -> int:
    return len(text.split(".")[1]) if text and "." in text else 0


def _tab_for(filename: str, section: str, advanced: bool) -> str:
    if section == "Hotkeys":
        return "Hotkeys"
    if advanced:
        return "Advanced"
    return _SECTION_TAB.get((filename, section), _FILE_TAB[filename])


def _is_switch(filename: str, entry, bounds) -> bool:
    if entry.value not in ("0", "1"):
        return False
    if bounds:
        return bounds == (0, 1)
    if _BOOLEAN_WORDING.search(entry.comment):
        return True
    return filename in _ZERO_ONE_FILES and entry.key not in _FLOAT_KEYS


def _build(filename: str, entry) -> Option:
    comment = entry.comment
    match = _RANGE.search(comment)
    bounds = (int(match.group(1)), int(match.group(2))) if match else None
    advanced = "ONLY FOR EXPERTS" in comment or "EXPERIMENTAL" in comment
    option = Option(
        file=filename,
        section=entry.section,
        key=entry.key,
        label=label_for(entry.key),
        description=comment,
        tab=_tab_for(filename, entry.section, advanced),
        group=f"{FILES[filename]} · {_section_title(entry.section)}",
        kind="text",
        advanced=advanced,
        default=_default_for(comment),
    )
    value = entry.value
    if entry.key == "ResX":
        option.kind, option.label = "resolution", "Resolution"
        option.description = "Game resolution. Sets ResX and ResY together."
    elif entry.key == "ResY":
        option.kind = "resolution_height"
    elif entry.section == "Hotkeys":
        option.kind = "hotkey"
    elif entry.key in _CHOICES:
        option.kind, option.choices = "choice", _CHOICES[entry.key]
    elif _is_switch(filename, entry, bounds):
        option.kind = "switch"
    elif entry.key in _FLOAT_KEYS or _FLOAT.fullmatch(value) or (
        _INT.fullmatch(value) and "." in (option.default or "")
    ):
        option.kind = "float"
        option.digits = max(_decimals(value), _decimals(option.default), 2)
        option.minimum, option.maximum = -1e9, 1e9
    elif _INT.fullmatch(value):
        option.kind = "int"
        low, high = bounds or _INT_RANGES.get(entry.key, (-2_000_000_000, 2_000_000_000))
        option.minimum, option.maximum = low, high
    return option


def build_options(ini: IniFile, filename: str) -> list[Option]:
    return [_build(filename, entry) for entry in ini.entries]
