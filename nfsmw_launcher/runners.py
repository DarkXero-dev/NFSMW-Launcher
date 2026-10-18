import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import Config

GAME_EXE = "speed.exe"
FLATPAK_BOTTLES = ["flatpak", "run", "--command=bottles-cli", "com.usebottles.bottles"]
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_SAVED_PREFIX = "NFSMW_ORIG_"


@dataclass
class Launch:
    argv: list[str]
    env: dict[str, str]
    cwd: str


def parse_env(text: str) -> dict[str, str]:
    env = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def host_env(environ: dict[str, str]) -> dict[str, str]:
    env = dict(environ)
    for key in [k for k in env if k.startswith(_SAVED_PREFIX)]:
        original = env.pop(key)
        name = key[len(_SAVED_PREFIX):]
        if original:
            env[name] = original
        else:
            env.pop(name, None)
    return env


def find_game_dir(candidates: list[Path]) -> Path | None:
    return next((path for path in candidates if find_game_exe(path)), None)


def find_game_exe(game_dir: str | Path) -> Path | None:
    directory = Path(game_dir)
    if not directory.is_dir():
        return None
    for child in directory.iterdir():
        if child.name.lower() == GAME_EXE:
            return child
    return None


def parse_bottles_list(output: str) -> list[str]:
    names = []
    for line in output.splitlines():
        match = re.fullmatch(r"- (.+)", _ANSI.sub("", line).strip())
        if match:
            names.append(match.group(1))
    return names


def find_bottles_cli() -> list[str] | None:
    path = host_env(os.environ).get("PATH")
    if shutil.which("bottles-cli", path=path):
        return ["bottles-cli"]
    if shutil.which("flatpak", path=path):
        probe = subprocess.run(
            ["flatpak", "info", "com.usebottles.bottles"],
            capture_output=True,
            env=host_env(os.environ),
        )
        if probe.returncode == 0:
            return list(FLATPAK_BOTTLES)
    return None


def list_bottles(bottles_cli: list[str] | None = None) -> list[str]:
    bottles_cli = bottles_cli or find_bottles_cli()
    if not bottles_cli:
        return []
    result = subprocess.run(
        [*bottles_cli, "list", "bottles"],
        capture_output=True,
        text=True,
        env=host_env(os.environ),
    )
    return parse_bottles_list(result.stdout)


def validate(config: Config) -> list[str]:
    problems = []
    if not config.game_dir.strip():
        problems.append("Set the game folder.")
    elif find_game_exe(config.game_dir) is None:
        problems.append(f"{GAME_EXE} was not found in the game folder.")
    if config.runner == "bottles" and not config.bottles_bottle.strip():
        problems.append("Choose a bottle.")
    if config.runner == "custom" and not config.custom_command.strip():
        problems.append("Enter a custom command.")
    return problems


def build_launch(config: Config, bottles_cli: list[str] | None = None) -> Launch:
    exe = str(find_game_exe(config.game_dir) or Path(config.game_dir) / GAME_EXE)
    user_env = parse_env(config.env)
    runner_env: dict[str, str] = {}

    if config.runner == "bottles":
        cli = bottles_cli or find_bottles_cli() or ["bottles-cli"]
        run = ["run", "-b", config.bottles_bottle, "-e", exe]
        if cli[:2] == ["flatpak", "run"]:
            env_flags = [f"--env={k}={v}" for k, v in user_env.items()]
            argv = [*cli[:2], *env_flags, *cli[2:], *run]
        else:
            argv = [*cli, *run]
    elif config.runner == "wine":
        argv = [config.wine_binary or "wine", exe]
        if config.wine_prefix:
            runner_env["WINEPREFIX"] = config.wine_prefix
    elif config.runner == "umu":
        argv = ["umu-run", exe]
        runner_env["GAMEID"] = "0"
        if config.umu_proton:
            runner_env["PROTONPATH"] = config.umu_proton
        if config.umu_prefix:
            runner_env["WINEPREFIX"] = config.umu_prefix
    elif config.runner == "custom":
        argv = [
            token.replace("{exe}", exe).replace("{dir}", config.game_dir)
            for token in shlex.split(config.custom_command)
        ]
    else:
        raise ValueError(f"unknown runner: {config.runner}")

    return Launch(argv, {**runner_env, **user_env}, config.game_dir)


def start(launch: Launch) -> subprocess.Popen:
    return subprocess.Popen(
        launch.argv,
        env={**host_env(os.environ), **launch.env},
        cwd=launch.cwd,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
