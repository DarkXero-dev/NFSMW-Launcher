import re
from pathlib import Path

SCRIPT = (Path(__file__).parent.parent / "packaging" / "build-appimage.sh").read_text()


def removed_dynload_modules():
    line = next(l for l in SCRIPT.splitlines() if l.startswith("rm -f") and "lib-dynload" in l)
    group = re.search(r"\{([^}]*)\}", line).group(1)
    return set(group.split(","))


def test_bundle_keeps_the_modules_needed_for_https_downloads():
    removed = removed_dynload_modules()
    assert "_ssl" not in removed, "update check needs HTTPS, which needs _ssl"
    assert "_hashlib" not in removed


def test_build_verifies_its_own_bundle_can_do_https():
    assert "import ssl" in SCRIPT and "urllib.request" in SCRIPT
    check = SCRIPT.index("import ssl")
    assert check > SCRIPT.index("Bytecode") and check < SCRIPT.index("Packaging")
