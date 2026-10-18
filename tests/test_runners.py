from nfsmw_launcher.config import Config, DEFAULT_ENV, load_config, save_config
from nfsmw_launcher.runners import (
    build_launch,
    find_game_dir,
    find_game_exe,
    host_env,
    parse_bottles_list,
    parse_env,
    validate,
)

FLATPAK_BOTTLES = ["flatpak", "run", "--command=bottles-cli", "com.usebottles.bottles"]


def make_game(tmp_path, name="speed.exe"):
    (tmp_path / name).write_bytes(b"MZ")
    return tmp_path


def test_parse_env_skips_blank_comment_and_malformed_lines():
    text = "A=1\n\n# note\nnoequals\nWINEDLLOVERRIDES=dinput8=n,b;d3d9=n,b\n"
    assert parse_env(text) == {"A": "1", "WINEDLLOVERRIDES": "dinput8=n,b;d3d9=n,b"}


def test_default_env_contains_mod_loader_overrides():
    assert parse_env(DEFAULT_ENV)["WINEDLLOVERRIDES"] == "dinput8=n,b;d3d9=n,b"


def test_find_game_exe_is_case_insensitive(tmp_path):
    game = make_game(tmp_path, "SPEED.EXE")
    assert find_game_exe(game).name == "SPEED.EXE"


def test_find_game_exe_missing_returns_none(tmp_path):
    assert find_game_exe(tmp_path) is None


def test_parse_bottles_list_extracts_names():
    output = "20:10:27 (INFO) Catalog loaded\nFound 2 bottles:\n- Gaming\n- Win Soft\n"
    assert parse_bottles_list(output) == ["Gaming", "Win Soft"]


def test_bottles_native_command(tmp_path):
    game = make_game(tmp_path)
    config = Config(game_dir=str(game), runner="bottles", bottles_bottle="Gaming", env="A=1")
    launch = build_launch(config, bottles_cli=["bottles-cli"])
    assert launch.argv == ["bottles-cli", "run", "-b", "Gaming", "-e", str(game / "speed.exe")]
    assert launch.env == {"A": "1"}
    assert launch.cwd == str(game)


def test_bottles_flatpak_passes_env_through_flatpak_flags(tmp_path):
    game = make_game(tmp_path)
    config = Config(game_dir=str(game), runner="bottles", bottles_bottle="Gaming", env="A=1")
    launch = build_launch(config, bottles_cli=FLATPAK_BOTTLES)
    assert launch.argv == [
        "flatpak", "run", "--env=A=1", "--command=bottles-cli", "com.usebottles.bottles",
        "run", "-b", "Gaming", "-e", str(game / "speed.exe"),
    ]


def test_wine_command_uses_prefix_and_binary(tmp_path):
    game = make_game(tmp_path)
    config = Config(
        game_dir=str(game), runner="wine", wine_binary="/opt/wine/bin/wine",
        wine_prefix="/home/u/pfx", env="A=1",
    )
    launch = build_launch(config)
    assert launch.argv == ["/opt/wine/bin/wine", str(game / "speed.exe")]
    assert launch.env == {"A": "1", "WINEPREFIX": "/home/u/pfx"}


def test_wine_defaults_to_system_wine_without_prefix(tmp_path):
    game = make_game(tmp_path)
    launch = build_launch(Config(game_dir=str(game), runner="wine", env=""))
    assert launch.argv == ["wine", str(game / "speed.exe")]
    assert launch.env == {}


def test_umu_command_sets_proton_and_prefix(tmp_path):
    game = make_game(tmp_path)
    config = Config(
        game_dir=str(game), runner="umu", umu_proton="GE-Proton",
        umu_prefix="/home/u/pfx", env="",
    )
    launch = build_launch(config)
    assert launch.argv == ["umu-run", str(game / "speed.exe")]
    assert launch.env == {"PROTONPATH": "GE-Proton", "WINEPREFIX": "/home/u/pfx", "GAMEID": "0"}


def test_umu_omits_unset_proton_and_prefix(tmp_path):
    game = make_game(tmp_path)
    launch = build_launch(Config(game_dir=str(game), runner="umu", env=""))
    assert launch.env == {"GAMEID": "0"}


def test_custom_command_substitutes_placeholders_per_token(tmp_path):
    spaced = tmp_path / "My Games"
    spaced.mkdir()
    make_game(spaced)
    config = Config(
        game_dir=str(spaced), runner="custom",
        custom_command="lutris-run --dir {dir} '{exe}' --flag", env="",
    )
    launch = build_launch(config)
    assert launch.argv == ["lutris-run", "--dir", str(spaced), str(spaced / "speed.exe"), "--flag"]


def test_user_env_overrides_runner_env(tmp_path):
    game = make_game(tmp_path)
    config = Config(game_dir=str(game), runner="wine", wine_prefix="/a", env="WINEPREFIX=/b")
    assert build_launch(config).env["WINEPREFIX"] == "/b"


def test_validate_reports_missing_game_folder():
    problems = validate(Config(game_dir="", runner="wine"))
    assert any("game folder" in p.lower() for p in problems)


def test_validate_reports_missing_exe(tmp_path):
    problems = validate(Config(game_dir=str(tmp_path), runner="wine"))
    assert any("speed.exe" in p for p in problems)


def test_validate_bottles_needs_bottle_name(tmp_path):
    game = make_game(tmp_path)
    problems = validate(Config(game_dir=str(game), runner="bottles"))
    assert any("bottle" in p.lower() for p in problems)


def test_validate_custom_needs_command(tmp_path):
    game = make_game(tmp_path)
    problems = validate(Config(game_dir=str(game), runner="custom", custom_command=" "))
    assert any("command" in p.lower() for p in problems)


def test_validate_ok(tmp_path):
    game = make_game(tmp_path)
    assert validate(Config(game_dir=str(game), runner="wine")) == []


def test_config_roundtrip(tmp_path):
    path = tmp_path / "sub" / "config.json"
    config = Config(game_dir="/g", runner="umu", umu_proton="GE-Proton", env="X=1")
    save_config(config, path)
    assert load_config(path) == config


def test_config_load_missing_file_gives_defaults(tmp_path):
    assert load_config(tmp_path / "none.json") == Config()


def test_config_load_ignores_unknown_keys(tmp_path):
    path = tmp_path / "c.json"
    path.write_text('{"game_dir": "/g", "future_option": 1}')
    assert load_config(path).game_dir == "/g"


def test_host_env_restores_variables_saved_by_apprun():
    env = {
        "LD_LIBRARY_PATH": "/app/lib",
        "NFSMW_ORIG_LD_LIBRARY_PATH": "/host/lib",
        "PATH": "/app/bin:/usr/bin",
        "NFSMW_ORIG_PATH": "/usr/bin",
        "HOME": "/home/u",
    }
    assert host_env(env) == {"LD_LIBRARY_PATH": "/host/lib", "PATH": "/usr/bin", "HOME": "/home/u"}


def test_host_env_unsets_variables_that_were_empty_before_apprun():
    env = {"GI_TYPELIB_PATH": "/app/gi", "NFSMW_ORIG_GI_TYPELIB_PATH": "", "HOME": "/h"}
    assert host_env(env) == {"HOME": "/h"}


def test_host_env_leaves_normal_environment_untouched():
    env = {"PATH": "/usr/bin", "HOME": "/h"}
    assert host_env(env) == env


def test_find_game_dir_returns_first_candidate_with_exe(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    (tmp_path / "game").mkdir()
    game = make_game(tmp_path / "game")
    other = tmp_path / "other"
    other.mkdir()
    make_game(other)
    assert find_game_dir([empty, game, other]) == game


def test_find_game_dir_none_when_no_candidate_matches(tmp_path):
    assert find_game_dir([tmp_path, tmp_path / "missing"]) is None


def test_close_action_defaults_to_ask_and_roundtrips(tmp_path):
    assert Config().close_action == "ask"
    path = tmp_path / "c.json"
    save_config(Config(close_action="tray"), path)
    assert load_config(path).close_action == "tray"


def test_invalid_close_action_in_config_falls_back_to_ask(tmp_path):
    path = tmp_path / "c.json"
    path.write_text('{"close_action": "explode"}')
    assert load_config(path).close_action == "ask"
