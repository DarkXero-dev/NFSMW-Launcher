import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "packaging" / "changelog.sh"


def git(repo, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout


def commit(repo, message):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--allow-empty", "-q", "-F", "-"],
        cwd=repo, input=message, check=True, capture_output=True, text=True,
    )


def changelog(repo, rng="HEAD"):
    return subprocess.run(["bash", str(SCRIPT), rng], cwd=repo, check=True, capture_output=True, text=True).stdout


def test_subject_only_commit_is_one_bullet_with_short_hash(tmp_path):
    git(tmp_path, "init", "-q")
    commit(tmp_path, "Fix the thing")
    short = git(tmp_path, "rev-parse", "--short", "HEAD").strip()
    assert changelog(tmp_path) == f"- Fix the thing ({short})\n"


def test_bullet_lines_in_the_body_become_nested_bullets(tmp_path):
    git(tmp_path, "init", "-q")
    commit(tmp_path, "Add updater\n\nLonger explanation that is skipped.\n\n- Update button\n* Checksum check\n- Relaunch\n")
    short = git(tmp_path, "rev-parse", "--short", "HEAD").strip()
    assert changelog(tmp_path) == (
        f"- Add updater ({short})\n  - Update button\n  - Checksum check\n  - Relaunch\n"
    )


def test_range_limits_to_new_commits_and_lists_newest_first(tmp_path):
    git(tmp_path, "init", "-q")
    commit(tmp_path, "Old")
    git(tmp_path, "tag", "v1.0.1")
    commit(tmp_path, "First new")
    commit(tmp_path, "Second new\n\n- detail")
    lines = changelog(tmp_path, "v1.0.1..HEAD").splitlines()
    assert [l.split(" (")[0] for l in lines] == ["- Second new", "  - detail", "- First new"]
