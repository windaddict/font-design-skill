"""scripts/update-check.py tells an operator what installing the current skill would change in a shipped face.

WHAT IT'S FOR: a face folder records the skill version that built it. When the installed skill is newer, the operator needs to
see whether adopting it changes the font before running the build themselves. The script rebuilds the face with the installed
skill into a temporary folder, compares the shipped files with the rebuild by value and by render, and writes a report; it
never writes into the face folder. Before comparing it checks that what ships is what the manifest records, because an
edited font or input would otherwise be reported as the effect of the skill update. These tests run the real script as a
subprocess on a copy of a real build of the neutral face (built once per module; each test works on its own copy), edit the
copy on purpose, and read the report files and the exit code.
"""
import hashlib
import json
import shutil
import sys
import time

import pytest
from conftest import REPO, run

NEUTRAL = REPO / "examples" / "neutral"
SCRIPT = REPO / "scripts" / "update-check.py"
INSTALLED = (REPO / "VERSION").read_text(encoding="utf-8").strip()
WOFF2 = "Sampler-VF.woff2"
UNVERIFIED = "Attribution to the skill update is unverified"


@pytest.fixture(scope="module")
def built_face(tmp_path_factory):
    """A face folder with font.json, concepts.js, requirements.json and its build (both groups) in out/, built by the repo's build.py."""
    face = tmp_path_factory.mktemp("face")
    for n in ("font.json", "concepts.js", "requirements.json"):
        shutil.copyfile(NEUTRAL / n, face / n)
    r = run([sys.executable, str(REPO / "scripts" / "build.py"), "--font", str(face / "font.json")])
    assert r.returncode == 0, f"the neutral face did not build:\n{r.stderr[-1500:]}"
    return face


@pytest.fixture
def face(tmp_path, built_face):
    """This test's own copy of the built face, at tmp/face."""
    dest = tmp_path / "face"
    shutil.copytree(built_face, dest)
    return dest


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_of(face):
    return json.loads((face / "out" / "manifest.json").read_text(encoding="utf-8"))


def save_manifest(face, manifest):
    (face / "out" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def record(face, version):
    """Sets (or, with None, deletes) the skill_version the manifest records."""
    m = manifest_of(face)
    if version is None:
        m.pop("skill_version", None)
    else:
        m["skill_version"] = version
    save_manifest(face, m)


def move_o(path):
    """Shifts the default outline of `o` by +30 in x and keeps the left side bearing in step, as tests/test_diff.py does."""
    from fontTools.ttLib import TTFont
    font = TTFont(str(path))
    glyph = font["glyf"]["o"]
    glyph.coordinates.translate((30, 0))
    glyph.recalcBounds(font["glyf"])
    font["hmtx"].metrics["o"] = (font["hmtx"].metrics["o"][0], glyph.xMin)
    font.flavor = "woff2"
    font.save(str(path))


def check(face, out, *extra):
    r = run([sys.executable, str(SCRIPT), str(out), "--font", str(face / "font.json"), *extra])
    return r


def report(out):
    return (out / "update.md").read_text(encoding="utf-8"), json.loads((out / "update.json").read_text(encoding="utf-8"))


def adoption_line(md):
    """The one line of update.md that tells the operator how to adopt the installed version: it carries `scripts/build.py --font`."""
    lines = [ln for ln in md.splitlines() if "scripts/build.py --font" in ln]
    assert len(lines) == 1, lines
    return lines[0].strip()


def tree_state(folder):
    """{relative path: sha256} for every file under folder, to prove a run wrote nothing there."""
    return {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob("*")) if p.is_file()}


def test_matching_versions_report_up_to_date_and_build_nothing(tmp_path, face):
    """The manifest records the installed version: the script says so, names the version, exits 0 and creates no report folder
    (nothing was compared). The stdout assertion runs before the exit-code assertion so that a missing script and a placeholder
    that exits 0 and prints nothing both fail on it. Weakest mutation to watch red: the equal case falling through to the
    rebuild (the folder appears)."""
    record(face, INSTALLED)
    out = tmp_path / "out"
    r = check(face, out)
    assert "up to date" in r.stdout and INSTALLED in r.stdout, f"up-to-date: stdout {r.stdout!r} stderr {r.stderr!r}"
    assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
    assert not out.exists()


def test_a_version_mismatch_rebuilds_compares_by_value_and_overwrites_nothing(tmp_path, face):
    """A valid recorded build made at version 0.0.1 whose shipped roman has `o` moved +30 (the manifest's roman hash is rewritten
    to match, so the shipped file is what the manifest says it is and there is no drift). The rebuild with the installed skill
    differs from it: exit 3, update.md names both versions, lists the outline difference under roman and `no difference by value`
    for italic, says nothing in the folder was changed and gives the build command, which carries `--requirements` and the
    face's requirements file name; update.json lists no drift and no changed file; the sha256 of both woff2 files and the
    manifest are the same after the run. The report says attribution to the update is unverified, because the rewritten hash is
    exactly the case a clean drift check cannot see through. A copy whose manifest records `requirements: null` gets a build
    command ending in `--no-requirements`. Weakest mutation to watch red: the report written into the face folder (a hash
    changes); the adoption line hard-coded without a requirements flag."""
    record(face, "0.0.1")
    roman = face / "out" / WOFF2
    move_o(roman)
    m = manifest_of(face)
    m["groups"]["roman"]["woff2_sha256"] = sha(roman)
    save_manifest(face, m)
    paths = [roman, face / "out" / "Sampler-Italic-VF.woff2", face / "out" / "manifest.json"]
    before = [sha(p) for p in paths]
    out = tmp_path / "out"
    r = check(face, out, "--sizes", "16")
    assert r.returncode == 3, f"mismatch report: exit {r.returncode}: {r.stdout} {r.stderr}"
    md, data = report(out)
    assert "0.0.1" in md and INSTALLED in md
    by_value = md.index("## By value")
    i_roman = md.index("roman:", by_value)
    i_o = md.index("glyph o: default outline differs", by_value)
    i_italic = md.index("italic: no difference by value", by_value)
    assert i_roman < i_o < i_italic, (i_roman, i_o, i_italic)
    assert "Nothing in" in md and "scripts/build.py --font" in md
    assert "## Drift" not in md and data["drift"] == []
    assert UNVERIFIED in md and data["attribution"] == "unverified", data.get("attribution")
    assert data["changed_files"] == []
    assert (out / "diff" / "diff.md").is_file()
    assert "--requirements" in adoption_line(md) and "requirements.json" in adoption_line(md), adoption_line(md)
    assert [sha(p) for p in paths] == before, "update-check.py changed a file in the face folder"
    # A face with no requirements file (the manifest records null): the adoption line must say so, or the build refuses.
    other = tmp_path / "face-null"
    shutil.copytree(face, other)
    mm = manifest_of(other)
    mm["requirements"] = None
    save_manifest(other, mm)
    r2 = check(other, tmp_path / "out2", "--sizes", "16")
    assert r2.returncode == 3, f"null requirements: exit {r2.returncode}: {r2.stdout} {r2.stderr}"
    line = adoption_line(report(tmp_path / "out2")[0])
    assert line.endswith("--no-requirements") and "--requirements " not in line, line


def stale_report(out):
    """A complete report of an earlier run, written by the test: the `.update-check` marker a run leaves in OUT, update.md,
    update.json, diff/diff.json, diff/diff.md and a file only that run could have written."""
    (out / "diff").mkdir(parents=True)
    (out / ".update-check").write_text("written by update-check.py\n", encoding="utf-8")
    (out / "update.md").write_text("# earlier run\n", encoding="utf-8")
    (out / "update.json").write_text(json.dumps({"earlier": True}), encoding="utf-8")
    (out / "diff" / "diff.json").write_text(json.dumps({"changed": 0, "entries": []}), encoding="utf-8")
    (out / "diff" / "diff.md").write_text("0 of 0 renders changed\n", encoding="utf-8")
    (out / "diff" / "earlier-only.txt").write_text("from the earlier run\n", encoding="utf-8")


def test_a_failing_diff_is_an_error_and_leaves_no_stale_report(tmp_path, face, built_face):
    """A COMPLETE report of an earlier run sits in OUT. (1) font.json has its `review` block and `titles` removed and no --sizes is
    given, so build.py still builds but diff.py exits non-zero ("no `titles`"; the test confirms that exit itself by running
    diff.py on the pair, so the case cannot pass for another reason): the check exits 1, says `diff.py failed`, says it removed the
    report of an earlier run, and update.md, update.json and diff/ are gone, so the earlier report cannot be read as this run's
    result. (2) A failing BUILD (the manifest's requirements file does not exist) over the same earlier report ends the same
    way. (3) A successful run over an earlier report leaves the new update.md, update.json and diff/ only: no file of the old diff/
    remains. Weakest mutation to watch red: the removal of the earlier report deleted from the failure paths; `diff.py`'s exit
    status ignored and its output read anyway. Case 3 sees only the final state, so it cannot tell the order of the three moves
    that publish a report (update.md last); that order matters only if the process dies between moves, which no test here
    simulates."""
    record(face, "0.0.1")
    cfg = json.loads((face / "font.json").read_text(encoding="utf-8"))
    cfg.pop("review", None)
    cfg.pop("titles", None)
    (face / "font.json").write_text(json.dumps(cfg), encoding="utf-8")
    out = tmp_path / "out"
    stale_report(out)
    r = check(face, out)
    assert r.returncode == 1, f"failing diff: exit {r.returncode}: {r.stderr}"
    assert "diff.py failed" in r.stderr, r.stderr
    assert "removed the report of an earlier run" in r.stderr, r.stderr
    for gone in ("update.md", "update.json", "diff"):
        assert not (out / gone).exists(), f"a stale {gone} was left looking current"
    # The same inputs make diff.py itself exit non-zero on the shipped pair (the case is the one named, not an accident of the check).
    d = run([sys.executable, str(REPO / "scripts" / "diff.py"), str(tmp_path / "direct"), "--font", str(face / "font.json"),
             "--before", str(face / "out"), "--after", str(face / "out")])
    assert d.returncode != 0, "diff.py accepted a font.json with no titles and no review block"
    # Case 2: the build fails.
    broken = tmp_path / "face-broken"
    shutil.copytree(built_face, broken)
    record(broken, "0.0.1")
    mm = manifest_of(broken)
    mm["requirements"] = "no-such-requirements.json"
    save_manifest(broken, mm)
    out2 = tmp_path / "out2"
    stale_report(out2)
    r2 = check(broken, out2, "--sizes", "16")
    assert r2.returncode == 1, f"failing build: exit {r2.returncode}: {r2.stderr}"
    assert "removed the report of an earlier run" in r2.stderr, r2.stderr
    for gone in ("update.md", "update.json", "diff"):
        assert not (out2 / gone).exists(), f"a stale {gone} was left looking current after a failed build"
    # Case 3: a successful run over an earlier report replaces all of it.
    fine = tmp_path / "face-fine"
    shutil.copytree(built_face, fine)
    record(fine, "0.0.1")
    out3 = tmp_path / "out3"
    stale_report(out3)
    r3 = check(fine, out3, "--sizes", "16")
    assert r3.returncode == 0, f"success over an earlier report: exit {r3.returncode}: {r3.stdout} {r3.stderr}"
    md, data = report(out3)
    assert "earlier run" not in md and "earlier" not in data, (md[:200], data)
    assert (out3 / "diff" / "diff.md").is_file() and not (out3 / "diff" / "earlier-only.txt").exists(), "a file of the old diff/ remains"
    assert not list(out3.glob(".update-stage-*")), "the staging folder was left behind"


def test_an_out_folder_inside_the_face_folder_is_refused(tmp_path, face):
    """The update check never writes into the face folder, and refuses an OUT that would make it do so: exit 1, stderr names the OUT
    path and the face folder, the OUT folder is not created, and the face folder's file list and every file's sha256 are unchanged.
    OUT equal to the face folder itself is refused the same way. Weakest mutation to watch red: the refusal removed (the report
    lands in the face folder)."""
    record(face, "0.0.1")
    before = tree_state(face)
    inside = face / "update"
    r = check(face, inside)
    assert r.returncode == 1, f"out inside face: exit {r.returncode}: {r.stderr}"
    assert str(inside) in r.stderr and str(face) in r.stderr, r.stderr
    assert not inside.exists()
    assert tree_state(face) == before, "a run refused for its OUT still changed the face folder"
    same = check(face, face)
    assert same.returncode == 1, f"out equal to face: exit {same.returncode}: {same.stderr}"
    assert str(face) in same.stderr, same.stderr
    assert tree_state(face) == before


def test_a_shipped_file_that_differs_from_the_recorded_build_is_labelled_drift_not_update_effect(tmp_path, face, built_face):
    """The manifest records hashes of the shipped woff2 files and of font.json, concepts.js and the skeletons file. A file edited
    after the build is drift, not the effect of the skill update. (a) roman `o` moved with the manifest hash left alone: exit 3,
    a `## Drift` section that names the woff2 and says the differences cannot be attributed to the skill update, and a drift
    entry with different recorded and found hashes. (b) font.json with a trailing newline: drift names font.json. (c) the same for
    concepts.js. (d) the unedited copy: no drift, exit 0, no attribution sentence (nothing differs). Weakest mutation to watch
    red: the drift check removed, so (a) reads as a plain by-value difference with no `## Drift` section."""
    record(face, "0.0.1")
    move_o(face / "out" / WOFF2)
    out = tmp_path / "a"
    r = check(face, out, "--sizes", "16")
    assert r.returncode == 3, f"drift label: exit {r.returncode}: {r.stdout} {r.stderr}"
    md, data = report(out)
    assert "## Drift" in md and WOFF2 in md and "cannot be attributed to the skill update" in md, md
    entry = next(e for e in data["drift"] if str(e["file"]).endswith(WOFF2))
    assert entry["recorded"] != entry["found"]
    for label, name in (("b", "font.json"), ("c", "concepts.js")):
        copy = tmp_path / f"face-{label}"
        shutil.copytree(built_face, copy)
        record(copy, "0.0.1")
        with open(copy / name, "a", encoding="utf-8") as fh:
            fh.write("\n")
        o = tmp_path / label
        rr = check(copy, o, "--sizes", "16")
        assert rr.returncode == 3, f"drift label ({label}): exit {rr.returncode}: {rr.stdout} {rr.stderr}"
        _, d = report(o)
        assert [e for e in d["drift"] if str(e["file"]).endswith(name)], (name, d["drift"])
    clean = tmp_path / "face-d"
    shutil.copytree(built_face, clean)
    record(clean, "0.0.1")
    rd = check(clean, tmp_path / "d", "--sizes", "16")
    assert rd.returncode == 0, f"drift label (clean copy): exit {rd.returncode}: {rd.stdout} {rd.stderr}"
    md_d, data_d = report(tmp_path / "d")
    assert data_d["drift"] == [] and "## Drift" not in md_d
    assert "no difference in any group" in md_d and UNVERIFIED not in md_d, md_d


def test_a_face_recorded_at_0_6_0_gets_the_ambiguity_notice(tmp_path, face, built_face):
    """Version 0.6.0 names two font sources, so a face recorded at it gets a `## Notice` section in update.md, one entry in
    update.json `notices`, and the notice on stderr; the check still runs (exit 0 on an unedited face) because it fetches nothing.
    The version is given by `--recorded` after the manifest's key is deleted, as for a face built before the key existed. A face
    recorded at 0.0.1 has no notice. The stderr assertion comes first so that a missing script and a silent placeholder fail on
    it. Weakest mutation to watch red: `0.6.0` removed from the ambiguous versions."""
    record(face, None)
    out = tmp_path / "out"
    r = check(face, out, "--recorded", "0.6.0", "--sizes", "16")
    assert "0.6.0 is ambiguous" in r.stderr, f"0.6.0 notice: {r.stderr}"
    assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"
    md, data = report(out)
    assert "## Notice" in md and "0.6.0 is ambiguous" in md
    assert len(data["notices"]) == 1, data["notices"]
    other = tmp_path / "other"
    shutil.copytree(built_face, other)
    record(other, "0.0.1")
    r2 = check(other, tmp_path / "o2", "--sizes", "16")
    assert r2.returncode == 0, r2.stderr
    assert report(tmp_path / "o2")[1]["notices"] == [] and "ambiguous" not in r2.stderr


def test_a_face_without_a_recorded_version_is_refused_unless_recorded_is_given(tmp_path, face):
    """A face built before the manifest carried `skill_version` has no recorded version: exit 1, and stderr names `--recorded` and
    says a face built before 0.8.0 records none. With `--recorded` equal to the installed version the run says `up to date`, exits
    0, builds nothing (the report folder does not exist and the run takes under 10 seconds). Weakest mutation to watch red: a
    missing key read as the installed version (the first run exits 0)."""
    record(face, None)
    out = tmp_path / "out"
    r = check(face, out)
    assert r.returncode == 1, f"no recorded version: exit {r.returncode}: {r.stderr}"
    assert "--recorded" in r.stderr and "built before 0.8.0" in r.stderr, r.stderr
    assert not out.exists()
    start = time.monotonic()
    r2 = check(face, out, "--recorded", INSTALLED)
    elapsed = time.monotonic() - start
    assert r2.returncode == 0, r2.stderr
    assert "up to date" in r2.stdout and not out.exists()
    assert elapsed < 10, f"the up-to-date answer took {elapsed:.1f} s, so a build ran"


def load_update_check():
    """The real scripts/update-check.py imported as a module, so a test can make one of its own steps raise. The file name has a
    hyphen, so it is loaded by path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("update_check_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_an_unexpected_error_after_the_out_check_also_removes_the_earlier_report(tmp_path, face, monkeypatch, capsys):
    """Not every failure is one the script raises itself: a file it cannot read (a permission error while hashing for the drift
    check) or a copy that fails raises an ordinary exception. Any of them must still end with exit 1 and remove the earlier
    report in OUT, or that report reads as this run's result. The real script is imported and its drift check made to raise
    PermissionError. Weakest mutation to watch red: the cleanup handler catching only the script's own failure class."""
    record(face, "0.0.1")
    out = tmp_path / "out"
    stale_report(out)
    uc = load_update_check()

    def denied(cfg, manifest):
        raise PermissionError("permission denied (raised by the test)")

    monkeypatch.setattr(uc, "drift_of", denied)
    rc = uc.main([str(out), "--font", str(face / "font.json"), "--sizes", "16"])
    err = capsys.readouterr().err
    assert rc == 1, f"unexpected error: exit {rc}: {err}"
    assert "PermissionError" in err and "removed the report of an earlier run" in err, err
    for gone in ("update.md", "update.json", "diff"):
        assert not (out / gone).exists(), f"a stale {gone} was left looking current after an unexpected error"


def test_bytes_that_differ_with_no_compared_value_are_reported_not_called_identical(tmp_path, face):
    """The by-value section compares chosen tables, not every byte: the `post` table, for one, is not compared. A valid recorded
    build (manifest hash rewritten to match) whose shipped roman has its `post` underline position moved by one unit differs from
    the rebuild in bytes only. The report must not say adopting changes only manifest.json: exit 3, update.json `bytes_identical`
    false for roman and true for italic, and update.md says the woff2 files differ in bytes. Weakest mutation to watch red: the
    byte comparison removed (the run then exits 0 and says adopting changes only manifest.json)."""
    from fontTools.ttLib import TTFont
    record(face, "0.0.1")
    roman = face / "out" / WOFF2
    font = TTFont(str(roman))
    font["post"].underlinePosition += 1
    font.flavor = "woff2"
    font.save(str(roman))
    m = manifest_of(face)
    m["groups"]["roman"]["woff2_sha256"] = sha(roman)
    save_manifest(face, m)
    out = tmp_path / "out"
    r = check(face, out, "--sizes", "16")
    md, data = report(out)
    assert "changes only manifest.json" not in md, f"bytes only: the report calls the fonts identical: {md}"
    assert r.returncode == 3, f"bytes only: exit {r.returncode}: {r.stdout} {r.stderr}"
    assert data.get("bytes_identical") == {"roman": False, "italic": True}, data.get("bytes_identical")
    assert "differ in bytes" in md, md
    # A byte difference is a difference: the shipped font may not be the recorded version's output, so attribution is unverified.
    assert data["attribution"] == "unverified" and UNVERIFIED in md, (data.get("attribution"), md)


def test_the_printed_adoption_command_runs_from_another_directory_on_a_path_with_a_space(tmp_path, built_face):
    """The report says the adoption command runs from any directory, so it must survive a face folder whose path holds a space.
    The face is copied to `tmp/my faces/face`, the check is run, and the printed line is executed by a shell from an unrelated
    directory: it must exit 0 and rewrite the face's manifest with the installed version. Weakest mutation to watch red: the
    arguments joined without shell quoting (the shell splits the path at the space and build.py exits 2)."""
    face = tmp_path / "my faces" / "face"
    shutil.copytree(built_face, face)
    record(face, "0.0.1")
    out = tmp_path / "out"
    r = check(face, out, "--sizes", "16")
    assert r.returncode in (0, 3), f"adoption: exit {r.returncode}: {r.stderr}"
    md, _ = report(out)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    a = run(["/bin/sh", "-c", adoption_line(md)], cwd=elsewhere)
    assert a.returncode == 0, f"adoption command: exit {a.returncode}: {adoption_line(md)}\n{a.stderr[-800:]}"
    assert manifest_of(face)["skill_version"] == INSTALLED


def test_an_out_folder_holding_other_files_is_refused_and_left_alone(tmp_path, face):
    """OUT is replaced in part on every run (update.md, update.json, diff/), so it must be a new folder, an empty one, or the OUT of
    an earlier update check. A folder that holds anything else (here a site's own `diff/` and a notes file, the case of OUT given
    as a site root) is refused with exit 1 before anything is written or removed, and every file in it is unchanged. Weakest
    mutation to watch red: the contents check removed (the run then deletes the site's diff/ and writes its report there)."""
    record(face, "0.0.1")
    out = tmp_path / "site"
    (out / "diff").mkdir(parents=True)
    (out / "diff" / "keep.txt").write_text("the site's own file\n", encoding="utf-8")
    (out / "notes.txt").write_text("notes\n", encoding="utf-8")
    before = tree_state(out)
    r = check(face, out, "--sizes", "16")
    assert r.returncode == 1, f"other files in OUT: exit {r.returncode}: {r.stdout} {r.stderr}"
    assert "notes.txt" in r.stderr, r.stderr
    assert tree_state(out) == before, "update-check.py changed a folder it does not own"
    # A folder holding ONLY a diff/ (one of the names a run writes) is not therefore an earlier update check's OUT: without the
    # marker a run leaves, it is refused too, and its diff/ is left alone.
    only = tmp_path / "only-diff"
    (only / "diff").mkdir(parents=True)
    (only / "diff" / "keep.txt").write_text("someone else's diff\n", encoding="utf-8")
    before_only = tree_state(only)
    r2 = check(face, only, "--sizes", "16")
    assert r2.returncode == 1, f"a lone diff/ in OUT: exit {r2.returncode}: {r2.stdout} {r2.stderr}"
    assert tree_state(only) == before_only, "update-check.py deleted a diff/ it did not write"


def test_a_cleanup_that_cannot_remove_the_earlier_report_says_so_and_still_exits_1(tmp_path, face, monkeypatch, capsys):
    """When a run fails, the earlier report in OUT is removed so it cannot be read as this run's. If the filesystem refuses that
    removal, the run must still exit 1 (not raise out of its own error handler) and must say which file of the earlier report is
    still there, instead of claiming it was removed. The real script is imported, its drift check made to raise, and
    `Path.unlink` made to refuse update.md. Weakest mutation to watch red: the removal left unguarded (the PermissionError
    escapes the handler), or its failure swallowed (the message never names update.md)."""
    import pathlib
    record(face, "0.0.1")
    out = tmp_path / "out"
    stale_report(out)
    uc = load_update_check()

    def denied(cfg, manifest):
        raise OSError("the drift check failed (raised by the test)")

    real_unlink = pathlib.Path.unlink

    def refuse_update_md(self, *a, **kw):
        if self.name == "update.md":
            raise PermissionError("refused by the test")
        return real_unlink(self, *a, **kw)

    monkeypatch.setattr(uc, "drift_of", denied)
    monkeypatch.setattr(pathlib.Path, "unlink", refuse_update_md)
    rc = uc.main([str(out), "--font", str(face / "font.json"), "--sizes", "16"])
    err = capsys.readouterr().err
    assert rc == 1, f"cleanup refused: exit {rc}: {err}"
    assert "could not remove" in err and "update.md" in err, err
    assert "removed the report of an earlier run" not in err, err


def test_update_md_is_published_last(tmp_path, face, monkeypatch, capsys):
    """A report is complete if and only if update.md exists, because update.md is moved into OUT after diff/ and update.json. The
    real script is imported and `Path.replace` wrapped to record each move into OUT; the last one must be update.md, after both
    others. Weakest mutation to watch red: update.md moved first (the final state is the same, so only the order shows it)."""
    import pathlib
    record(face, "0.0.1")
    move_o(face / "out" / WOFF2)
    m = manifest_of(face)
    m["groups"]["roman"]["woff2_sha256"] = sha(face / "out" / WOFF2)
    save_manifest(face, m)
    out = tmp_path / "out"
    uc = load_update_check()
    moves = []
    real_replace = pathlib.Path.replace

    def recording(self, target):
        if pathlib.Path(target).parent == out.resolve():
            moves.append(pathlib.Path(target).name)
        return real_replace(self, target)

    monkeypatch.setattr(pathlib.Path, "replace", recording)
    rc = uc.main([str(out), "--font", str(face / "font.json"), "--sizes", "16"])
    capsys.readouterr()
    assert rc == 3, f"publication order: exit {rc}"
    assert moves and moves[-1] == "update.md" and {"diff", "update.json"} <= set(moves[:-1]), moves
