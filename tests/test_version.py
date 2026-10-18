import subprocess
from pathlib import Path

import pytest

from nfsmw_launcher.version import read_version

SCRIPT = Path(__file__).parent.parent / "packaging" / "next-version.sh"


def test_read_version_returns_trimmed_file_content(tmp_path):
    (tmp_path / "VERSION").write_text("1.0.7\n")
    assert read_version(tmp_path) == "1.0.7"


def test_read_version_falls_back_to_dev_without_file(tmp_path):
    assert read_version(tmp_path) == "dev"


def test_read_version_falls_back_to_dev_for_empty_file(tmp_path):
    (tmp_path / "VERSION").write_text("\n")
    assert read_version(tmp_path) == "dev"


def next_version(repo, *tags):
    run = lambda *args: subprocess.run(args, cwd=repo, check=True, capture_output=True, text=True)
    run("git", "init", "-q")
    run("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--allow-empty", "-q", "-m", "c")
    for tag in tags:
        run("git", "tag", tag)
    return run("bash", str(SCRIPT)).stdout.strip()


def test_next_version_starts_at_1_0_1_without_tags(tmp_path):
    assert next_version(tmp_path) == "1.0.1"


@pytest.mark.parametrize(
    "tags, expected",
    [
        (["v1.0.1"], "1.0.2"),
        (["v1.0.1", "v1.0.2", "v1.0.3"], "1.0.4"),
        (["v1.0.2", "v1.0.10", "v1.0.9"], "1.0.11"),
        (["v1.0.3", "unrelated", "v2.0.0", "nightly"], "1.0.4"),
    ],
)
def test_next_version_increments_the_highest_patch_number(tmp_path, tags, expected):
    assert next_version(tmp_path, *tags) == expected
