from pathlib import Path

import pytest

from nfsmw_launcher.ini_file import IniFile
from nfsmw_launcher.schema import FILES, RESOLUTIONS, TABS, build_options, label_for, resolution_label

FIXTURES = Path(__file__).parent / "fixtures"


def options_for(filename):
    return {(o.section, o.key): o for o in build_options(IniFile.load(FIXTURES / filename), filename)}


def all_options():
    return [
        (name, o)
        for name in FILES
        for o in build_options(IniFile.load(FIXTURES / name), name)
    ]


def test_every_ini_entry_gets_an_option_in_a_known_tab():
    for name in FILES:
        ini = IniFile.load(FIXTURES / name)
        options = build_options(ini, name)
        assert len(options) == len(ini.entries), name
        assert {o.tab for o in options} <= set(TABS), name


def test_all_labels_and_groups_are_readable():
    for _, option in all_options():
        assert option.label and "_" not in option.label
        assert option.group


def test_resolution_width_becomes_one_resolution_picker_and_height_is_linked():
    opts = options_for("NFSMostWanted.WidescreenFix.ini")
    assert (opts[("MAIN", "ResX")].kind, opts[("MAIN", "ResX")].label) == ("resolution", "Resolution")
    assert opts[("MAIN", "ResX")].tab == "Display"
    assert opts[("MAIN", "ResY")].kind == "resolution_height"


def test_resolution_presets_cover_common_sizes_without_duplicates():
    sizes = [(w, h) for w, h, _ in RESOLUTIONS]
    assert len(sizes) == len(set(sizes))
    for wanted in [
        (1280, 720), (1920, 1080), (2560, 1080), (2560, 1440), (3440, 1440),
        (3840, 2160), (3840, 1600), (5120, 2160), (5120, 2880), (6880, 2880),
    ]:
        assert wanted in sizes
    assert all(label for _, _, label in RESOLUTIONS)


def test_resolution_label_marks_sizes_outside_the_presets():
    assert resolution_label(2560, 1440) == "2560 x 1440 (1440p)"
    assert resolution_label(1234, 567) == "1234 x 567 (current)"


def test_boolean_flags_become_switches():
    opts = options_for("NFSMostWanted.WidescreenFix.ini")
    assert opts[("MAIN", "FixHUD")].kind == "switch"
    assert opts[("MAIN", "HUDWidescreenMode")].kind == "switch"
    extra = options_for("NFSMWExtraOptionsSettings.ini")
    assert extra[("Menu", "ShowOnline")].kind == "switch"


def test_zero_one_numbers_are_not_mistaken_for_switches():
    extra = options_for("NFSMWExtraOptionsSettings.ini")
    assert extra[("Gameplay", "GameSpeed")].kind == "float"
    assert extra[("Weather", "GeneralRainAmount")].kind == "float"
    assert extra[("LapControllers", "Minimum")].kind == "int"
    unlimiter = options_for("NFSMWUnlimiterSettings.ini")
    assert unlimiter[("Main", "ReplacementModel")].kind == "int"


def test_enum_options_become_choices():
    option = options_for("NFSMostWanted.WidescreenFix.ini")[("MAIN", "Scaling")]
    assert option.kind == "choice"
    assert [v for v, _ in option.choices] == ["0", "1", "2"]
    vendor = options_for("NFSMostWanted.WidescreenFix.ini")[("GRAPHICS", "ForcedGPUVendor")]
    assert ("0x10DE", "NVIDIA") in vendor.choices


def test_range_comment_sets_bounds_and_zero_one_range_is_a_switch():
    gfx = options_for("NFSMWGraphicsSettings.ini")
    assert (gfx[("Graphics", "WorldLevelOfDetail")].minimum, gfx[("Graphics", "WorldLevelOfDetail")].maximum) == (0, 3)
    assert gfx[("Graphics", "VSync")].kind == "switch"
    assert gfx[("Graphics", "VisualTreatment")].kind == "switch"


def test_hotkeys_section_is_hotkey_kind_in_hotkeys_tab():
    extra = options_for("NFSMWExtraOptionsSettings.ini")
    option = extra[("Hotkeys", "Headlights")]
    assert (option.kind, option.tab) == ("hotkey", "Hotkeys")
    gfx = options_for("NFSMWGraphicsSettings.ini")
    assert gfx[("Hotkeys", "ReloadConfig")].tab == "Hotkeys"


def test_expert_and_experimental_options_go_to_advanced():
    extra = options_for("NFSMWExtraOptionsSettings.ini")
    assert extra[("Misc", "DoScreenPrintf")].advanced
    assert extra[("Misc", "DoScreenPrintf")].tab == "Advanced"
    assert extra[("Menu", "ShowOnline")].tab == "Menus"


def test_tab_assignment_by_section():
    extra = options_for("NFSMWExtraOptionsSettings.ini")
    assert extra[("Pursuit", "HeatLevelOverride")].tab == "Gameplay"
    assert extra[("Weather", "AlwaysRain")].tab == "Graphics"
    assert extra[("Fixes", "ZeroBountyFix")].tab == "Advanced"
    assert options_for("NFSMWRaceFixesSettings.ini")[("Sprint", "ShowInMenu")].tab == "Menus"


def test_text_option_for_paths():
    option = options_for("NFSMW_XenonEffects.ini")[("MAIN", "TexturePack")]
    assert option.kind == "text"


def test_defaults_are_extracted_from_comments():
    extra = options_for("NFSMWExtraOptionsSettings.ini")
    assert extra[("Hotkeys", "Headlights")].default == "72"
    assert extra[("Menu", "ShowOnline")].default == "1"
    assert extra[("Menu", "ShowSubs")].default == "0"
    assert extra[("Gameplay", "SBRechargeTime")].default == "25.0"
    assert options_for("NFSMWMotionBlurControllerSettings.ini")[("Main", "MotionBlurAmount")].default == "0.25"


def test_label_for_splits_camel_case_and_keeps_acronyms():
    assert label_for("FullScreenAntiAliasing") == "Full Screen Anti Aliasing"
    assert label_for("FNGFix") == "FNG Fix"
    assert label_for("UseD3DDeviceTexture") == "Use D3D device texture"
    assert label_for("emsprk_line1") == "Emsprk line1"
    assert label_for("SBRechargeTime") == "Speedbreaker recharge time"


@pytest.mark.parametrize("name", FILES)
def test_group_titles_name_the_source_mod(name):
    for option in build_options(IniFile.load(FIXTURES / name), name):
        assert option.group.startswith(FILES[name])


def test_shadows_res_is_a_dropdown_of_named_sizes():
    option = options_for("NFSMostWanted.WidescreenFix.ini")[("GRAPHICS", "ShadowsRes")]
    assert option.kind == "choice"
    assert [v for v, _ in option.choices] == ["1024", "2048", "4096", "16384"]
    assert dict(option.choices)["1024"] == "1024 (original)"
    assert dict(option.choices)["4096"] == "4096 (4K PC Ultra)"
