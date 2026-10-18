import re
from dataclasses import dataclass
from pathlib import Path

_SECTION = re.compile(r"\s*\[([^\]]+)\]")
_KEY_LINE = re.compile(
    r"(?P<head>\s*(?P<key>[^\s=;\[/][^=]*?)\s*=\s*)(?P<rest>[^\r\n]*)(?P<eol>\r?\n|\r)?"
)
_COMMENT_LINE = re.compile(r"\s*(?:;|//)\s?(.*?)\s*$")
_COMMENT_START = re.compile(r"\s*(//|;)")
_BACKUP_SUFFIX = ".redux-launcher.bak"


@dataclass
class Entry:
    section: str
    key: str
    value: str
    comment: str
    line_index: int


def _split_rest(rest: str) -> tuple[str, str]:
    marker = _COMMENT_START.search(rest)
    before = rest[: marker.start()] if marker else rest
    value = re.split(r"\s+\(", before, maxsplit=1)[0].strip()
    return value, rest[len(value):]


def _tail_to_comment(tail: str) -> str:
    text = tail.strip()
    for marker in ("//", ";"):
        if text.startswith(marker):
            return text[len(marker):].strip()
    return text


class IniFile:
    def __init__(self, text: str):
        self._lines = text.splitlines(keepends=True)
        self.entries: list[Entry] = []
        section = ""
        for index, line in enumerate(self._lines):
            header = _SECTION.match(line)
            if header:
                section = header.group(1)
                continue
            match = _KEY_LINE.fullmatch(line)
            if not match or not section:
                continue
            value, tail = _split_rest(match.group("rest"))
            comment = _tail_to_comment(tail) or self._preceding_comment(index)
            self.entries.append(Entry(section, match.group("key"), value, comment, index))

    def _preceding_comment(self, index: int) -> str:
        parts: list[str] = []
        for line in reversed(self._lines[:index]):
            match = _COMMENT_LINE.fullmatch(line.rstrip("\r\n"))
            if not match:
                break
            parts.append(match.group(1))
        return " ".join(reversed(parts))

    @classmethod
    def load(cls, path: Path) -> "IniFile":
        raw = Path(path).read_bytes().decode("utf-8", "surrogateescape")
        return cls(raw)

    def _find(self, section: str, key: str) -> Entry:
        for entry in self.entries:
            if entry.section == section and entry.key == key:
                return entry
        raise KeyError(f"{section}/{key}")

    def get(self, section: str, key: str) -> str:
        return self._find(section, key).value

    def set(self, section: str, key: str, value: str) -> None:
        entry = self._find(section, key)
        line = self._lines[entry.line_index]
        match = _KEY_LINE.fullmatch(line)
        rest = match.group("rest")
        old, tail = _split_rest(rest)
        if tail.strip():
            gap = len(tail) - len(tail.lstrip())
            tail = " " * max(1, len(old) + gap - len(value)) + tail.lstrip()
        else:
            tail = ""
        self._lines[entry.line_index] = (
            match.group("head") + value + tail + (match.group("eol") or "")
        )
        entry.value = value

    def dumps(self) -> str:
        return "".join(self._lines)

    def save(self, path: Path) -> None:
        path = Path(path)
        backup = path.with_name(path.name + _BACKUP_SUFFIX)
        if path.exists() and not backup.exists():
            backup.write_bytes(path.read_bytes())
        path.write_bytes(self.dumps().encode("utf-8", "surrogateescape"))
