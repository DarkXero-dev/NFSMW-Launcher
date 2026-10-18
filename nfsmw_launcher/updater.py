import hashlib
import json
import logging
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path

API_ROOT = "https://api.github.com"
ASSET_NAME = "NFSMW-Launcher.AppImage"
_HEADERS = {"User-Agent": "NFSMW-Launcher"}
_CHUNK = 1 << 16


@dataclass
class Update:
    version: str
    url: str
    sha256: str | None


def update_check_enabled(environ, version: str, repo: str | None) -> bool:
    return bool(environ.get("APPIMAGE")) and bool(repo) and parse_version(version) is not None


def parse_version(text: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(part) for part in text.lstrip("v").split("."))
    except ValueError:
        return None


def is_newer(candidate: str, current: str) -> bool:
    new, old = parse_version(candidate), parse_version(current)
    return new is not None and old is not None and new > old


def find_update(release: dict, current: str) -> Update | None:
    version = release.get("tag_name", "").lstrip("v")
    if not is_newer(version, current):
        return None
    for asset in release.get("assets", []):
        if asset.get("name") == ASSET_NAME:
            digest = asset.get("digest") or ""
            sha256 = digest.removeprefix("sha256:") if digest.startswith("sha256:") else None
            return Update(version, asset["browser_download_url"], sha256)
    return None


def fetch_latest_release(repo: str) -> dict:
    request = urllib.request.Request(
        f"{API_ROOT}/repos/{repo}/releases/latest",
        headers={**_HEADERS, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)


def check_for_update(repo: str, current: str, fetch=fetch_latest_release) -> Update | None:
    try:
        return find_update(fetch(repo), current)
    except (OSError, ValueError) as error:
        logging.getLogger(__name__).warning("update check failed: %s", error)
        return None


def looks_like_appimage(path: Path) -> bool:
    with open(path, "rb") as handle:
        header = handle.read(11)
    return header[:4] == b"\x7fELF" and header[8:11] == b"AI\x02"


def download(url: str, dest: Path, sha256: str | None, progress) -> None:
    hasher = hashlib.sha256()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=_HEADERS), timeout=30) as response:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            with open(dest, "wb") as out:
                while chunk := response.read(_CHUNK):
                    out.write(chunk)
                    hasher.update(chunk)
                    done += len(chunk)
                    progress(done, total)
        if sha256 and hasher.hexdigest() != sha256.lower():
            raise ValueError("checksum mismatch")
        if not looks_like_appimage(dest):
            raise ValueError("downloaded file is not an AppImage")
    except BaseException:
        Path(dest).unlink(missing_ok=True)
        raise


def install(downloaded: Path, target: Path) -> None:
    os.chmod(downloaded, 0o755)
    os.replace(downloaded, target)


def relaunch_argv(pid: int, target: str) -> list[str]:
    return [
        "sh",
        "-c",
        'while kill -0 "$1" 2>/dev/null; do sleep 0.2; done; exec "$2"',
        "sh",
        str(pid),
        str(target),
    ]
