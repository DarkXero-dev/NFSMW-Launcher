import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

DEFAULT_ENV = "WINEDLLOVERRIDES=dinput8=n,b;d3d9=n,b"


@dataclass
class Config:
    game_dir: str = ""
    runner: str = "bottles"
    bottles_bottle: str = ""
    wine_binary: str = ""
    wine_prefix: str = ""
    umu_proton: str = ""
    umu_prefix: str = ""
    custom_command: str = ""
    env: str = DEFAULT_ENV


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "nfsmw-redux-launcher" / "config.json"


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    try:
        data = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return Config()
    known = {f.name for f in fields(Config)}
    return Config(**{k: v for k, v in data.items() if k in known})


def save_config(config: Config, path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), indent=2) + "\n")
