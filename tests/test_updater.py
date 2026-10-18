import hashlib
import os
import stat

import pytest

from nfsmw_launcher import updater
from nfsmw_launcher.updater import (
    Update,
    check_for_update,
    download,
    find_update,
    install,
    is_newer,
    looks_like_appimage,
    parse_version,
    relaunch_argv,
)

APPIMAGE_BYTES = b"\x7fELF\x02\x01\x01\x00AI\x02" + b"\0" * 100


def release(tag="v1.0.7", digest="sha256:" + "ab" * 32, name="NFSMW-Launcher.AppImage"):
    asset = {"name": name, "browser_download_url": "https://example.test/dl/" + name}
    if digest:
        asset["digest"] = digest
    return {"tag_name": tag, "assets": [{"name": "x.zsync", "browser_download_url": "u"}, asset]}


def test_parse_version_handles_v_prefix_and_rejects_text():
    assert parse_version("v1.0.7") == (1, 0, 7)
    assert parse_version("1.0.10") == (1, 0, 10)
    assert parse_version("dev") is None


@pytest.mark.parametrize(
    "candidate, current, expected",
    [
        ("1.0.7", "1.0.6", True),
        ("v1.0.10", "1.0.9", True),
        ("1.0.6", "1.0.6", False),
        ("1.0.5", "1.0.6", False),
        ("1.0.7", "dev", False),
        ("garbage", "1.0.1", False),
    ],
)
def test_is_newer(candidate, current, expected):
    assert is_newer(candidate, current) is expected


def test_find_update_returns_asset_url_and_checksum_for_a_newer_release():
    found = find_update(release(), "1.0.6")
    assert found == Update("1.0.7", "https://example.test/dl/NFSMW-Launcher.AppImage", "ab" * 32)


def test_find_update_without_digest_has_no_checksum():
    assert find_update(release(digest=None), "1.0.6").sha256 is None


def test_find_update_none_when_current_or_asset_missing():
    assert find_update(release(tag="v1.0.6"), "1.0.6") is None
    assert find_update(release(name="other.AppImage"), "1.0.1") is None


def test_check_for_update_uses_the_repo_and_swallows_network_errors():
    seen = []

    def fetch(repo):
        seen.append(repo)
        return release()

    assert check_for_update("me/app", "1.0.1", fetch=fetch).version == "1.0.7"
    assert seen == ["me/app"]

    def broken(repo):
        raise OSError("offline")

    assert check_for_update("me/app", "1.0.1", fetch=broken) is None

    def not_json(repo):
        raise ValueError("bad json")

    assert check_for_update("me/app", "1.0.1", fetch=not_json) is None


def test_looks_like_appimage(tmp_path):
    good = tmp_path / "good"
    good.write_bytes(APPIMAGE_BYTES)
    bad = tmp_path / "bad"
    bad.write_bytes(b"<html>not found</html>" + b"\0" * 20)
    assert looks_like_appimage(good)
    assert not looks_like_appimage(bad)


def test_download_writes_file_verifies_checksum_and_reports_progress(tmp_path):
    source = tmp_path / "src.AppImage"
    source.write_bytes(APPIMAGE_BYTES)
    dest = tmp_path / "out.tmp"
    progress = []
    download(source.as_uri(), dest, hashlib.sha256(APPIMAGE_BYTES).hexdigest(), lambda d, t: progress.append((d, t)))
    assert dest.read_bytes() == APPIMAGE_BYTES
    assert progress[-1] == (len(APPIMAGE_BYTES), len(APPIMAGE_BYTES))


def test_download_rejects_checksum_mismatch_and_removes_partial_file(tmp_path):
    source = tmp_path / "src.AppImage"
    source.write_bytes(APPIMAGE_BYTES)
    dest = tmp_path / "out.tmp"
    with pytest.raises(ValueError, match="checksum"):
        download(source.as_uri(), dest, "00" * 32, lambda d, t: None)
    assert not dest.exists()


def test_download_rejects_files_that_are_not_appimages(tmp_path):
    source = tmp_path / "src"
    source.write_bytes(b"<html>rate limited</html>" + b"\0" * 20)
    dest = tmp_path / "out.tmp"
    with pytest.raises(ValueError, match="AppImage"):
        download(source.as_uri(), dest, None, lambda d, t: None)
    assert not dest.exists()


def test_install_replaces_target_and_makes_it_executable(tmp_path):
    target = tmp_path / "NFSMW-Launcher.AppImage"
    target.write_bytes(b"old")
    new = tmp_path / "new.tmp"
    new.write_bytes(APPIMAGE_BYTES)
    install(new, target)
    assert target.read_bytes() == APPIMAGE_BYTES
    assert not new.exists()
    assert os.stat(target).st_mode & stat.S_IXUSR


def test_relaunch_waits_for_the_old_process_then_starts_the_new_file():
    argv = updater.relaunch_argv(4242, "/games/NFSMW-Launcher.AppImage")
    assert argv[0] == "sh" and argv[1] == "-c"
    assert 'kill -0 "$1"' in argv[2] and 'exec "$2"' in argv[2]
    assert argv[-2:] == ["4242", "/games/NFSMW-Launcher.AppImage"]


@pytest.mark.parametrize(
    "environ, version, repo, expected",
    [
        ({"APPIMAGE": "/g/NFSMW-Launcher.AppImage"}, "1.0.3", "me/app", True),
        ({}, "1.0.3", "me/app", False),
        ({"APPIMAGE": "/g/x"}, "dev", "me/app", False),
        ({"APPIMAGE": "/g/x"}, "1.0.3", None, False),
    ],
)
def test_update_check_only_runs_for_released_appimage_builds(environ, version, repo, expected):
    assert updater.update_check_enabled(environ, version, repo) is expected


def test_failed_update_check_is_logged_instead_of_silently_swallowed(caplog):
    def broken(repo):
        raise OSError("unknown url type: https")

    with caplog.at_level("WARNING"):
        assert check_for_update("me/app", "1.0.1", fetch=broken) is None
    assert "unknown url type: https" in caplog.text
