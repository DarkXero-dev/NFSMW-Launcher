from pathlib import Path


def read_version(base: Path) -> str:
    try:
        return (Path(base) / "VERSION").read_text().strip() or "dev"
    except FileNotFoundError:
        return "dev"


VERSION = read_version(Path(__file__).resolve().parent.parent)
