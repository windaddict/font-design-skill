"""scripts/fetch-version.py puts the skill's own code at a released version into a folder, so an old build can be reproduced.

WHAT IT'S FOR: a face records the skill version that built it, and a face folder carries no scripts. To rebuild or compare
at that version the operator needs that version's code. The script gets it from the tag of a git checkout, or, with no git
checkout, from the tag archive on GitHub. These tests run the real script as a subprocess from an install that has no
`.git`, and from a real throwaway git repository, and give it `file://` archives so nothing touches the network. The
archive is built by the test with `tarfile`; the fetched code for the whole-flow test is this repository's own `scripts/`
under an invented version number, which is what a tag archive holds.
"""
import os
import random
import shutil
import sys
import tarfile
import uuid

import pytest
from conftest import REPO, run

NEUTRAL = REPO / "examples" / "neutral"
IGNORE = shutil.ignore_patterns("__pycache__", "tests", "*.pyc", ".pytest_cache", ".ruff_cache")


def env():
    """The environment without git's own variables: when this suite runs from a git hook, GIT_DIR and GIT_INDEX_FILE would point
    the throwaway repositories below at the real one."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def sh(cmd, **kw):
    kw.setdefault("env", env())
    return run(cmd, **kw)


def make_install(tmp_path):
    """An install with no .git: tmp/install/{scripts,VERSION} copied from the repository."""
    install = tmp_path / "install"
    shutil.copytree(REPO / "scripts", install / "scripts", ignore=IGNORE)
    shutil.copyfile(REPO / "VERSION", install / "VERSION")
    return install


def make_archive(tmp_path, version, full=False, name=None):
    """tmp/archive/v<name or version>.tar.gz with one top folder `font-design-skill-<version>/` holding VERSION (reading `version`)
    and `scripts/` (this repository's, when `full`; one small file otherwise). Returns the file:// URL."""
    stage = tmp_path / f"stage-{version}-{uuid.uuid4().hex[:6]}" / f"font-design-skill-{version}"
    if full:
        shutil.copytree(REPO / "scripts", stage / "scripts", ignore=IGNORE)
    else:
        (stage / "scripts").mkdir(parents=True)
        (stage / "scripts" / "note.txt").write_text("stand-in\n", encoding="utf-8")
    (stage / "VERSION").write_text(version + "\n", encoding="utf-8")
    archive = tmp_path / "archive" / f"v{name or version}.tar.gz"
    archive.parent.mkdir(exist_ok=True)
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(stage, arcname=stage.name)
    return archive.as_uri()


def fetch(install, version, dest, url):
    return sh([sys.executable, str(install / "scripts" / "fetch-version.py"), version, str(dest), "--archive-url", url])


def test_without_git_the_tag_archive_is_downloaded_and_the_fetched_code_rebuilds_the_recorded_version(tmp_path):
    """Whole flow with no git: the install has no .git, so the script downloads the archive (a file:// URL here), strips its top
    folder, and the fetched tree holds VERSION and scripts/build.py. The fetched build.py then builds the neutral face's roman group
    and the woff2 equals the example's own build byte for byte (the last comparison skips loudly when the example is unbuilt; the
    fetch assertions never skip). The stdout assertion runs before the exit-code assertion so that a missing script and a
    placeholder that exits 0 and prints nothing both fail on it. Weakest mutation to watch red: the top folder not stripped
    (VERSION lands one level too deep). What this proves is narrower than the name: the download route and a rebuild from the
    fetched tree. The archive holds THIS repository's scripts under an invented version, so it does not prove that an old
    release reproduces its recorded fonts; the operator check `fetch-version-live` does that with a real tag."""
    install = make_install(tmp_path)
    version = "9.8.7"
    url = make_archive(tmp_path, version, full=True)
    r = fetch(install, version, tmp_path / "at", url)
    assert "downloaded from file://" in r.stdout and "git tag" not in r.stdout, f"no-git fetch: stdout {r.stdout!r} stderr {r.stderr!r}"
    assert r.returncode == 0, f"fetch exit {r.returncode}: {r.stderr}"
    assert (tmp_path / "at" / "VERSION").read_text(encoding="utf-8").strip() == version
    assert (tmp_path / "at" / "scripts" / "build.py").is_file()
    face = tmp_path / "face"
    face.mkdir()
    for n in ("font.json", "concepts.js", "requirements.json"):
        shutil.copyfile(NEUTRAL / n, face / n)
    b = sh([sys.executable, str(tmp_path / "at" / "scripts" / "build.py"), "--font", str(face / "font.json"), "--group", "roman",
            "--out-dir", str(tmp_path / "rebuilt")])
    assert b.returncode == 0, b.stderr[-1500:]
    shipped = NEUTRAL / "out" / "Sampler-VF.woff2"
    if not shipped.is_file():
        pytest.skip("SKIPPED, NOT PASSED: examples/neutral/out is not built; the fetch assertions above passed")
    assert (tmp_path / "rebuilt" / "Sampler-VF.woff2").read_bytes() == shipped.read_bytes(), "the fetched code built a different roman woff2"


def test_from_a_git_checkout_the_tag_is_used_and_no_download_is_tried(tmp_path):
    """A throwaway git repository holding scripts/ and a VERSION reading 9.9.9, tagged v9.9.9. Run from that checkout the script
    takes the tag (stdout says `git tag v9.9.9`) even though the archive URL is a file that does not exist, so no download was
    needed or tried. The stdout assertion runs before the exit-code assertion (see the first test). Weakest mutation to watch red:
    the git route removed (the dead URL is then the only route and the run exits 1)."""
    repo = tmp_path / "repo"
    shutil.copytree(REPO / "scripts", repo / "scripts", ignore=IGNORE)
    (repo / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    cfg = ["-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
    for cmd in (["git", "init", "-q", str(repo)], ["git", "-C", str(repo), "add", "-A"], ["git", "-C", str(repo), *cfg, "commit", "-q", "-m", "release"],
                ["git", "-C", str(repo), *cfg, "tag", "v9.9.9"]):
        assert sh(cmd).returncode == 0, cmd
    r = fetch(repo, "9.9.9", tmp_path / "at2", "file:///nonexistent.tar.gz")
    assert "git tag v9.9.9" in r.stdout, f"git-tag fetch: stdout {r.stdout!r} stderr {r.stderr!r}"
    assert r.returncode == 0, f"fetch exit {r.returncode}: {r.stderr}"
    assert (tmp_path / "at2" / "VERSION").read_text(encoding="utf-8").strip() == "9.9.9"


def test_a_skill_copied_into_another_repository_does_not_take_that_repositorys_tag(tmp_path):
    """An install with no .git of its own, vendored (committed) into an unrelated git repository, a site, whose own release tag
    happens to be v9.9.9, the version asked for. `git -C <skill> rev-parse` succeeds there because git searches upward, and
    `git -C <skill> archive v9.9.9` then archives the SITE's tag: the vendored copy as the site committed it, which may be
    patched, not the skill's own release. So the git route must check that the repository's top folder IS the skill folder.
    With a dead archive URL the run exits 1 and names the other repository. Weakest mutation to watch red: the top-folder check
    removed (the site's v9.9.9 is archived, the vendored VERSION reads 9.9.9, and the run exits 0)."""
    outer = tmp_path / "site"
    install = outer / "vendor" / "skill"
    shutil.copytree(REPO / "scripts", install / "scripts", ignore=IGNORE)
    (install / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    (outer / "index.html").write_text("<p>a site</p>\n", encoding="utf-8")
    cfg = ["-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
    for cmd in (["git", "init", "-q", str(outer)], ["git", "-C", str(outer), "add", "-A"], ["git", "-C", str(outer), *cfg, "commit", "-q", "-m", "site"],
                ["git", "-C", str(outer), *cfg, "tag", "v9.9.9"]):
        assert sh(cmd).returncode == 0, cmd
    r = fetch(install, "9.9.9", tmp_path / "at7", f"file:///nonexistent-{uuid.uuid4().hex}.tar.gz")
    assert r.returncode == 1, f"enclosing repository: exit {r.returncode}: stdout {r.stdout!r} stderr {r.stderr!r}"
    assert "another git repository" in r.stderr, r.stderr
    assert not (tmp_path / "at7").exists()


def test_neither_route_working_stops_naming_both_reasons_and_writes_nothing(tmp_path):
    """No .git and a dead archive URL: exit 1, stderr names the git reason (`not a git checkout`) and the URL, and the target
    folder does not exist afterwards. Weakest mutation to watch red: the git reason dropped from the message."""
    install = make_install(tmp_path)
    url = f"file:///nonexistent-{uuid.uuid4().hex}.tar.gz"
    r = fetch(install, "0.0.9", tmp_path / "at3", url)
    assert r.returncode == 1, f"neither route: exit {r.returncode}: {r.stderr}"
    assert "not a git checkout" in r.stderr and url in r.stderr, r.stderr
    assert not (tmp_path / "at3").exists()
    assert list(tmp_path.glob(".fetch-*")) == []


def test_fetching_0_6_0_is_refused_naming_both_commits_and_other_versions_are_not(tmp_path):
    """Version 0.6.0 names two different font sources, so the script refuses it before trying either route, even when it is
    offered a VALID archive reading 0.6.0: exit 1, stderr says `0.6.0 is ambiguous`, names both commits (1c032ad, c5b4abb) and
    the `archive` command to run by hand, and nothing is created (no target, no `.fetch-*` folder). A valid 9.9.9 archive through
    the same script exits 0 and prints no `ambiguous`, so the refusal is not unconditional. Weakest mutation to watch red: the
    refusal removed (the archive is then accepted and the run exits 0)."""
    install = make_install(tmp_path)
    r = fetch(install, "0.6.0", tmp_path / "at5", make_archive(tmp_path, "0.6.0"))
    assert r.returncode == 1, f"0.6.0 refusal: exit {r.returncode}: stderr {r.stderr!r}"
    for needle in ("0.6.0 is ambiguous", "1c032ad", "c5b4abb", "archive"):
        assert needle in r.stderr, (needle, r.stderr)
    assert not (tmp_path / "at5").exists()
    assert list(tmp_path.glob(".fetch-*")) == []
    o = fetch(install, "9.9.9", tmp_path / "at7", make_archive(tmp_path, "9.9.9"))
    assert o.returncode == 0, o.stderr
    assert "ambiguous" not in o.stdout and "ambiguous" not in o.stderr


def test_an_archive_whose_version_differs_is_refused(tmp_path):
    """An archive that answers the request for 0.0.3 with a tree whose VERSION reads 0.0.2 is refused: exit 1, stderr says what it
    reports and what was asked, the target folder is not created and no `.fetch-*` folder is left beside it. Weakest mutation to
    watch red: the VERSION comparison removed."""
    install = make_install(tmp_path)
    url = make_archive(tmp_path, "0.0.2", name="0.0.3")
    r = fetch(install, "0.0.3", tmp_path / "at4", url)
    assert r.returncode == 1, f"wrong-version archive: exit {r.returncode}: {r.stderr}"
    assert "reports version 0.0.2, not 0.0.3" in r.stderr, r.stderr
    assert not (tmp_path / "at4").exists()
    assert list(tmp_path.glob(".fetch-*")) == []


def test_an_archive_that_breaks_partway_through_leaves_nothing_behind(tmp_path):
    """An archive holding VERSION (0.0.4), a scripts/ folder and a 1 MB file of random bytes, cut to half its length by the test, is
    a download that broke partway. Exit 1, stderr names the URL, the target folder does not exist and no `.fetch-*` temporary
    folder is left beside it. Weakest mutation to watch red: extracting straight into the target instead of a temporary folder (the
    half-extracted target remains), or the temporary folder not removed on failure."""
    install = make_install(tmp_path)
    stage = tmp_path / "stage-broken" / "font-design-skill-0.0.4"
    (stage / "scripts").mkdir(parents=True)
    (stage / "scripts" / "note.txt").write_text("stand-in\n", encoding="utf-8")
    (stage / "VERSION").write_text("0.0.4\n", encoding="utf-8")
    (stage / "scripts" / "blob.bin").write_bytes(random.Random(4).randbytes(1_000_000))
    archive = tmp_path / "archive" / "v0.0.4.tar.gz"
    archive.parent.mkdir()
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(stage, arcname=stage.name)
    data = archive.read_bytes()
    archive.write_bytes(data[: len(data) // 2])
    r = fetch(install, "0.0.4", tmp_path / "at6", archive.as_uri())
    assert r.returncode == 1, f"partial archive: exit {r.returncode}: {r.stderr}"
    assert archive.as_uri() in r.stderr, r.stderr
    assert not (tmp_path / "at6").exists()
    assert list(tmp_path.glob(".fetch-*")) == []


def test_a_failure_while_moving_the_fetched_tree_into_place_is_exit_1_and_leaves_nothing(tmp_path, monkeypatch, capsys):
    """Both routes can succeed and the last step, moving the checked tree from its temporary folder to DIR, still fail (a full
    disk, a permission). That must be exit 1 naming the failure, with DIR not created and no `.fetch-*` folder left, not a
    traceback. The real script is imported and its `os.replace` made to raise. Weakest mutation to watch red: the move left
    outside any error handler (the OSError escapes main)."""
    import importlib.util
    install = make_install(tmp_path)
    spec = importlib.util.spec_from_file_location("fetch_version_under_test", install / "scripts" / "fetch-version.py")
    fv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fv)

    def full(src, dst):
        raise OSError(28, "No space left on device (raised by the test)")

    monkeypatch.setattr(fv.os, "replace", full)
    url = make_archive(tmp_path, "0.0.5")
    rc = fv.main(["0.0.5", str(tmp_path / "at8"), "--archive-url", url])
    err = capsys.readouterr().err
    assert rc == 1, f"move into place: exit {rc}: {err}"
    assert "No space left on device" in err, err
    assert not (tmp_path / "at8").exists()
    assert list(tmp_path.glob(".fetch-*")) == []
