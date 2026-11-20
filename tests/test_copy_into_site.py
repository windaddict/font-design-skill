"""The font suite runs from where a site is told to put it.

WHAT IT'S FOR: dry-run finding W1. A cold run of the skill copied test_font.py and conftest.py alone
into a site's tests directory, and the suite broke at once: conftest resolved the scripts folder as the
parent of its own directory, which in the site was the repository root. The rule is now: copy the WHOLE
scripts/ folder (tests included) to tools/<face>/scripts/ and run pytest on tools/<face>/scripts/tests;
a site that keeps the tests elsewhere points --scripts (or FD_SCRIPTS) at the scripts folder. This test
builds that layout from the repo's fixtures in a temp dir, builds the neutral face there with the copied
build.py, and runs the copied suite from the SITE's root. Nothing here reads examples/neutral/out, so it
holds in CI before the neutral build step.
"""
import json
import os
import pathlib
import shutil
import sys

from conftest import REPO, run

NEUTRAL = REPO / "examples" / "neutral"
SAMPLE = REPO / "tests" / "fixtures" / "site-sample"
SKELETONS = REPO / "tests" / "fixtures" / "skeletons"
IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache", "*.pyc")


def make_site(tmp_path, skeletons=None):
    """A site at tmp_path/site with tools/sampler/{scripts,font.json,requirements.json,concepts.js} and the
    face built into tools/sampler/out (font.json's out_dir) with statics in out/static. With `skeletons` (a file
    under tests/fixtures/skeletons/), font.json is that folder's fixture (the neutral one naming skeletons.js) and
    the override is copied in beside it as skeletons.js, as a site keeps tools/<face>/skeletons.js."""
    site = tmp_path / "site"
    shutil.copytree(SAMPLE, site)
    face = site / "tools" / "sampler"
    shutil.copytree(REPO / "scripts", face / "scripts", ignore=IGNORE)
    for name in ("font.json", "requirements.json", "concepts.js"):
        shutil.copyfile(NEUTRAL / name, face / name)
    if skeletons:
        shutil.copyfile(SKELETONS / "font.json", face / "font.json")
        shutil.copyfile(SKELETONS / skeletons, face / "skeletons.js")
    # --static is a command-line path, so it resolves from the working directory (the site root here), while the
    # woff2s go to font.json's own out_dir (re-review, docs F007: the two forms must name the same folder)
    r = run([sys.executable, str(face / "scripts" / "build.py"), "--font", str(face / "font.json"), "--static", "tools/sampler/out/static"], cwd=site)
    assert r.returncode == 0, f"the copied build.py did not build the face in the site:\n{r.stderr[-1500:]}"
    assert (face / "out" / "Sampler-VF.woff2").is_file(), "the build wrote the woff2 somewhere other than font.json's out_dir"
    assert (face / "out" / "static").is_dir() and not (site / "out").exists(), "--static did not resolve from the working directory"
    return site, face


def test_the_whole_scripts_folder_copied_into_a_site_runs_the_suite_green(tmp_path):
    """Layout 1, the documented one: tools/sampler/scripts/tests beside gen.js, export.js and build.py.
    The suite must pass from the site's root with only --font, --requirements and --static-dir."""
    site, face = make_site(tmp_path)
    r = run([sys.executable, "-m", "pytest", "tools/sampler/scripts/tests", "-q", "-p", "no:cacheprovider",
             "--font", "tools/sampler/font.json", "--requirements", "tools/sampler/requirements.json", "--static-dir", "tools/sampler/out/static"], cwd=site)
    assert r.returncode == 0, f"the copied suite failed in the site:\n{r.stdout[-3000:]}\n{r.stderr[-800:]}"
    summary = r.stdout.strip().splitlines()[-1]
    assert "passed" in summary and "failed" not in summary and "error" not in summary, summary


def test_a_site_whose_face_names_a_skeleton_override_runs_the_suite_green(tmp_path):
    """0.6.0: a face that names its own skeleton override in font.json (tools/sampler/skeletons.js here, Bract's shoulder fixture)
    builds with the copied scripts and passes the copied suite, whose manifest test now hashes the override beside the five
    sources. Then one comment character appended to the override makes that manifest test fail naming the file, so the suite
    sees an edit to the override as it sees an edit to gen.js. Mutation watched red (references/testing.md section 8, M13):
    build.py leaving the override out of sources_sha256 (the manifest test then fails on set equality)."""
    site, face = make_site(tmp_path, "bract-shoulder.js")
    common = ["-q", "-p", "no:cacheprovider", "--font", "tools/sampler/font.json", "--requirements", "tools/sampler/requirements.json",
              "--static-dir", "tools/sampler/out/static"]
    r = run([sys.executable, "-m", "pytest", "tools/sampler/scripts/tests", *common], cwd=site)
    assert r.returncode == 0, f"the copied suite failed on a face with a skeleton override:\n{r.stdout[-3000:]}\n{r.stderr[-800:]}"
    manifest = json.loads((face / "out" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["skeletons"] == "skeletons.js" and "skeletons.js" in manifest["sources_sha256"]
    with open(face / "skeletons.js", "a", encoding="utf-8") as f:
        f.write("//\n")
    r = run([sys.executable, "-m", "pytest", "tools/sampler/scripts/tests", *common, "-k", "shipped_fonts_match_their_manifest"], cwd=site)
    assert r.returncode != 0 and "skeletons.js changed since the font was built" in r.stdout, r.stdout[-1500:]


def test_tests_kept_elsewhere_find_the_scripts_through_the_scripts_option(tmp_path):
    """Layout 2: only conftest.py and test_font.py live in the site's own tests folder, and --scripts names
    the folder holding the scripts. Without the option the fixtures must refuse to start, naming the
    scripts the wrong folder lacks; with it, the manifest test (which hashes gen.js, export.js and
    build.py under the scripts folder) passes, proving the resolution."""
    site, face = make_site(tmp_path)
    tests = site / "tests" / "font"
    tests.mkdir(parents=True)
    for name in ("conftest.py", "test_font.py"):
        shutil.copyfile(REPO / "scripts" / "tests" / name, tests / name)
    common = ["-q", "-p", "no:cacheprovider", "--font", "tools/sampler/font.json", "--requirements", "tools/sampler/requirements.json",
              "--static-dir", "tools/sampler/out/static", "-k", "manifest or cmap"]
    r = run([sys.executable, "-m", "pytest", "tests/font", *common], cwd=site)
    assert r.returncode != 0, "the suite ran although the scripts folder it assumed (tests/) holds no gen.js"
    assert "lacks" in r.stderr + r.stdout and "gen.js" in r.stderr + r.stdout, f"the refusal does not name the missing scripts:\n{(r.stderr + r.stdout)[-800:]}"
    # --scripts=DIR with the equals sign: a space-separated value is read by pytest as a test path before the
    # option exists, and tools/sampler/scripts has a tests/ child whose conftest would then load a second time
    r = run([sys.executable, "-m", "pytest", "tests/font", *common, "--scripts=tools/sampler/scripts"], cwd=site)
    assert r.returncode == 0, f"--scripts did not make the suite find the scripts:\n{r.stdout[-2000:]}\n{r.stderr[-800:]}"
    assert "passed" in r.stdout.strip().splitlines()[-1]
    assert pathlib.Path(face / "scripts" / "gen.js").is_file()  # what --scripts pointed at
    r = run([sys.executable, "-m", "pytest", "tests/font", *common], cwd=site, env={**os.environ, "FD_SCRIPTS": "tools/sampler/scripts"})
    assert r.returncode == 0, f"FD_SCRIPTS did not make the suite find the scripts:\n{r.stdout[-2000:]}\n{r.stderr[-800:]}"


def test_mutate_skips_the_static_mutations_under_static_dir_none_and_refuses_a_missing_default(tmp_path):
    """Second dry run, finding 1: on a site with no statics, `mutate.py --static-dir none` was read as a
    path named "none", the static mutations built statics into the served font folder and the run
    died in a FileNotFoundError. Now `none` is the conftest's word: the static mutations are SKIPPED with
    the reason and the run exits 0; and with no flag and no <out_dir>/static the harness refuses to start,
    naming both ways out, instead of building statics anywhere. Mutation watched red: `none` resolved as
    a path again (the refusal then names .../none)."""
    site, face = make_site(tmp_path)
    mutate = str(face / "scripts" / "tests" / "mutate.py")
    common = ["--font", "tools/sampler/font.json", "--requirements", "tools/sampler/requirements.json"]
    r = run([sys.executable, mutate, *common, "--static-dir", "none", "--only", "static"], cwd=site)
    assert r.returncode == 0, f"mutate.py --static-dir none exited {r.returncode}:\n{r.stdout[-2000:]}\n{r.stderr[-800:]}"
    skipped = [ln for ln in r.stdout.splitlines() if ln.startswith("SKIPPED ") and "no statics ship (--static-dir none)" in ln]
    names = sorted(ln.split("|")[1].strip().split(":")[0] for ln in skipped)
    assert names == ["static-designer", "static-fstype", "static-mac", "static-metrics", "static-missing", "static-overlap", "static-stat",
                     "static-weight"], r.stdout[-2000:]
    assert "0 mutations, 0 RED, 8 skipped, 0 problem(s)" in r.stdout, r.stdout[-600:]
    assert not (face / "out" / "none").exists() and not (face / "none").exists(), "a folder named none was created"
    os.rename(face / "out" / "static", face / "out" / "static-moved")
    r = run([sys.executable, mutate, *common, "--list"], cwd=site)
    assert r.returncode != 0, "mutate.py started although <out_dir>/static is missing and no --static-dir was given"
    assert "no static instances at" in r.stderr and "--static-dir none" in r.stderr, r.stderr[-600:]
    assert not (face / "out" / "static").exists(), "the refused start created the static folder"


def test_build_out_dir_holds_the_manifest_even_when_the_manifest_key_points_elsewhere(tmp_path):
    """Second dry run, finding 15: with font.json's `manifest` key pointing back beside the tool (relative
    to out_dir), a build with --out-dir TMP wrote its manifest outside TMP. Under --out-dir the manifest
    goes into that directory. Mutation watched red: the `manifest` key honoured under --out-dir again."""
    site, face = make_site(tmp_path)
    cfg = json.loads((face / "font.json").read_text(encoding="utf-8"))
    cfg["manifest"] = "../stray/manifest.json"
    (face / "font.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    out = tmp_path / "build" / "o"
    r = run([sys.executable, str(face / "scripts" / "build.py"), "--font", str(face / "font.json"), "--group", "roman", "--out-dir", str(out)], cwd=site)
    assert r.returncode == 0, r.stderr[-1500:]
    assert (out / "manifest.json").is_file() and (out / "Sampler-VF.woff2").is_file(), sorted(p.name for p in out.iterdir())
    assert not (tmp_path / "build" / "stray").exists(), "the manifest was written outside --out-dir"
    assert f"wrote {out / 'manifest.json'}" in r.stderr, r.stderr[-800:]
    # the manifest names the woff2 where it was WRITTEN, not under the configured out_dir (re-review, code-a F009):
    # resolved against font.json's directory it must be the file in --out-dir, not the earlier build's file in
    # tools/sampler/out, which exists too (the trap for a weaker assertion). Mutation watched red: the entry
    # written as f"{cfg['out_dir']}/{rel_file}" again.
    entry = json.loads((out / "manifest.json").read_text(encoding="utf-8"))["groups"]["roman"]["file"]
    assert (face / entry).resolve() == (out / "Sampler-VF.woff2").resolve(), f"the manifest's file entry {entry!r} does not name the woff2 in --out-dir"
    assert (face / "out" / "Sampler-VF.woff2").is_file(), "the earlier build's file must still exist, or the assertion above proves nothing"


def test_mutate_lists_its_mutations_on_a_project_with_one_instance_and_on_an_italic_only_project(tmp_path):
    """Re-review code-a F006: mutations() took the second named instance and the first non-italic group
    unconditionally, so `mutate.py --list` died with an IndexError on a group with one named instance and a
    StopIteration on a project whose groups are all italic, both valid for build.py. Now the only instance
    serves the static-missing mutation and the first group stands in for the roman one. Mutations watched
    red: `instances[1]` restored (IndexError); `next(...)` without the default restored (StopIteration)."""
    site, face = make_site(tmp_path)
    mutate = str(face / "scripts" / "tests" / "mutate.py")
    cfg = json.loads((face / "font.json").read_text(encoding="utf-8"))
    one = json.loads(json.dumps(cfg))
    one["groups"]["roman"]["instances"] = one["groups"]["roman"]["instances"][:1]
    (face / "font-one-instance.json").write_text(json.dumps(one), encoding="utf-8")
    r = run([sys.executable, mutate, "--font", str(face / "font-one-instance.json"), "--requirements", str(face / "requirements.json"),
             "--static-dir", str(face / "out" / "static"), "--list"], cwd=site)
    assert r.returncode == 0, f"mutate.py --list failed on a one-instance group:\n{r.stderr[-800:]}"
    assert "static-missing: one static woff2 renamed away" in r.stdout and "Sampler-Regular.woff2 in" in r.stdout, r.stdout[-1500:]
    italic_only = json.loads(json.dumps(cfg))
    italic_only["groups"] = {"italic": italic_only["groups"]["italic"]}
    (face / "font-italic-only.json").write_text(json.dumps(italic_only), encoding="utf-8")
    r = run([sys.executable, mutate, "--font", str(face / "font-italic-only.json"), "--requirements", str(face / "requirements.json"),
             "--static-dir", "none", "--list"], cwd=site)
    assert r.returncode == 0, f"mutate.py --list failed on an italic-only project:\n{r.stderr[-800:]}"
    assert "F013: Bold's outlines shifted 3 units" in r.stdout, r.stdout[-1500:]
