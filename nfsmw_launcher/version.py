from pathlib import Path


def read_version(base: Path) -> str:
    try:
        return (Path(base) / "VERSION").read_text().strip() or "dev"
    except FileNotFoundError:
        return "dev"


def read_repo(base: Path) -> str | None:
    try:
        return (Path(base) / "REPO").read_text().strip() or None
    except FileNotFoundError:
        return None


_BASE = Path(__file__).resolve().parent.parent
VERSION = read_version(_BASE)
REPO = read_repo(_BASE)
