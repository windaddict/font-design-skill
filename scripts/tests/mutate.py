#!/usr/bin/env python3
"""Watches every guard in test_font.py fail under its named mutation, then restores and confirms green.

WHAT IT'S FOR: a green test proves nothing until it has been watched failing. This harness applies one
deliberate defect at a time to the real inputs (scripts/gen.js, scripts/export.js, scripts/build.py, the
project's font.json, concepts.js and requirements.json, the built woff2, the manifest, the statics),
rebuilds when the defect is a build input, runs the test the mutation is named for, prints RED, GREEN or
UNPROVEN, restores every file from a pristine copy and runs the test again to prove the restore. Anything
but RED is a finding about the TEST or the mutation, and the harness exits non-zero.

    .venv/bin/python3 scripts/tests/mutate.py --font examples/neutral/font.json --requirements examples/neutral/requirements.json --static-dir examples/neutral/out/static
    .venv/bin/python3 scripts/tests/mutate.py --font ... --requirements ... --static-dir none             # no statics ship: the static mutations are SKIPPED
    .venv/bin/python3 scripts/tests/mutate.py --font ... --requirements ... --only cmap --only F013     # a subset, by substring
    .venv/bin/python3 scripts/tests/mutate.py --font ... --requirements ... --list                       # names and targets only
    --static-dir DIR   where build.py --static wrote the instances; `none` when no statics ship (the same word
                       conftest.py takes), which skips the static mutations and says so; without the flag the
                       default is <out_dir>/static and the harness refuses to start when that folder is missing,
                       rather than building statics into the served font folder (second dry run, finding 1)

What RED means here (review finding C8; the first harness called any non-zero pytest exit RED, ran the
tests even when the rebuild had failed, and never looked at which assertion fired): a mutation is RED only
when ALL of these hold.
  (a) every replacement it names applied, exactly as many times as it said;
  (b) if it rebuilds, the rebuild exited 0, unless the mutation declares `build_refused="<text>"`, in which
      case the build must fail WITH that text and leave the artefacts untouched; the refusal is then the
      RED unless the mutation also sets `test_after_refusal=True`, in which case the tests still run on the
      pristine artefacts and must fail as in (d);
  (c) if it rebuilt, at least one artefact (a woff2, the manifest, a static) differs from its pristine copy,
      so the tests are looking at the mutated build and not at the old files;
  (d) pytest reported every named test FAILED (not ERROR, not a collection error: the short summary is
      parsed), no test ERRORed, and every `expect` text appears in the assertion lines (`E ...`) OF THE
      TEST IT BELONGS TO (the failure sections are split by their `____ test_name ____` headers; a text
      for one test found only in another test's section does not count), so each test failed on the
      assertion the mutation was written for and not somewhere else. `expect` is one text or a list
      (each must appear in every named test's lines) or a dict {test name: text or list} when a
      mutation names several tests with a text each (re-review, code-a F008: the first stricter harness
      searched one combined string, so two tests could satisfy each other's text).
Anything else is UNPROVEN, with the reason, and a mutation whose tests pass is GREEN. Both are problems.
A mutation the project cannot exercise (no statics; no digit, opsz axis, avar map or hand pair in its
requirements) is SKIPPED with the reason, counted apart from the problems, and never silently GREEN.

Project independence (second dry run, finding 2): every `expect` text is derived from the project's own
requirements.json or font.json, never typed from the neutral fixture, so `required-F002` on a site whose
titles need only the digits 2 and 4 expects "lacks ['2', '4']".

Each mutation is the WEAKEST change found that makes its assertion false and is the defect the test is
named for; the comment beside it says why. A project with no roman group takes its first group as the
primary one for the roman-specific mutations, and one with a single named instance gets the
`static-missing` mutation on that instance (re-review, code-a F006: the list crashed on both shapes). Three shapes recur and are worth knowing (references/testing.md):
a mutation blocked by an earlier self-check (the build refuses, nothing changes, the test stays green: the
check has to be switched off too, and the budget lifted, as the overlap mutation does; the harness now
reports this as UNPROVEN rather than GREEN); a mutation masked by a second mapping; a mutation of a
property no input exercises.

Mechanics: exact-string replacements asserted to match exactly once, JSON edits through json.load/dump,
file renames; pristine copies kept with shutil.copyfile in a temp dir and copied back (never rm);
__pycache__ cleared between runs so a same-size edit cannot reuse stale bytecode; tests run with
-p no:cacheprovider. Stray files a mutation creates in the output directories are deleted on restore.

Copyright 2026 John Knox. MIT licence. Generalised from the author's Bract mutation run (hopsafari.com).
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent
REPO = SCRIPTS.parent
PY = sys.executable
TEST = HERE / "test_font.py"
BUILD = SCRIPTS / "build.py"
GEN = SCRIPTS / "gen.js"
EXPORT = SCRIPTS / "export.js"
SUMMARY = re.compile(r"^(FAILED|ERROR) (\S+)")
# a pytest failure-section header: `____ test_name[param] ____`, padded with underscores to the terminal width, which
# leaves ONE underscore each side of a long name (the first pattern wanted three and read no section for the suite's
# longer test names)
SECTION = re.compile(r"^_+ (\S+?)(?:\[.*\])? _+$")


def assertion_lines_by_test(stdout):
    """{test name: "E ..." lines of every failure section headed by that test}. Only the `E ` lines count:
    the section also prints the test's source, where the TEXT of a later assertion appears as code, so a
    match there would be a mention, not the assertion that fired."""
    out, current = {}, None
    for ln in stdout.splitlines():
        m = SECTION.match(ln)
        if m:
            current = m.group(1)
            out.setdefault(current, [])
        elif current is not None and ln.startswith("E "):
            out[current].append(ln)
    return {t: "\n".join(v) for t, v in out.items()}


def judge_tests(m, rc, failed, errored, e_by_test):
    """The verdict on the pytest run of a mutation's named tests, rule (d) of the header: (verdict, detail).
    Pure, so tests/test_mutate_harness.py can feed it crafted outputs."""
    if rc == 0:
        return "GREEN", None
    if errored:
        return "UNPROVEN", f"pytest ERRORed rather than failing an assertion: {errored[:2]}"
    not_failed = [t for t in m.tests if t not in failed]
    if not_failed:
        return "UNPROVEN", f"named test(s) did not FAIL: {not_failed}; failed: {sorted(set(failed))}"
    missing = [(t, x) for t in m.tests for x in m.expect[t] if x not in e_by_test.get(t, "")]
    if missing:
        t, x = missing[0]
        first_e = next((ln for ln in e_by_test.get(t, "").splitlines() if ln.startswith("E ")), "(no E line)")
        return "UNPROVEN", f"the tests failed but not on the expected assertion: {x!r} not in {t}'s assertion lines; its first E line: {first_e[:160]}"
    first_e = next((ln for t in m.tests for ln in e_by_test.get(t, "").splitlines() if ln.startswith("E ")), "")
    return "RED", first_e[:140]


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


class Mutation:
    """One named defect. `tests` are test function names in test_font.py; `expect` is one text or a list of
    texts that must all appear in EVERY named test's failing assertion lines, or a dict {test: text or
    list} naming each test's own text; `rebuild` is None, "all", a group name or a dict {"group", "static",
    "extra", "no_requirements"}; `build_refused` is the text a REFUSING build must print (the refusal is
    then the RED unless `test_after_refusal`)."""

    def __init__(self, name, tests, apply, rebuild=None, expect=None, build_refused=None, test_after_refusal=False, skip=None):
        assert expect or build_refused, f"{name}: a mutation must say what text proves it (expect= or build_refused=)"
        self.name, self.tests, self.apply, self.rebuild = name, list(tests), apply, rebuild
        if isinstance(expect, dict):
            assert set(expect) == set(self.tests), f"{name}: expect names {sorted(expect)}, the tests are {sorted(self.tests)}"
            self.expect = {t: ([v] if isinstance(v, str) else list(v)) for t, v in expect.items()}
        else:
            texts = [expect] if isinstance(expect, str) else list(expect or [])
            self.expect = {t: list(texts) for t in self.tests}
        self.build_refused, self.test_after_refusal = build_refused, test_after_refusal
        self.skip = skip  # a reason the project cannot exercise this mutation; the harness reports SKIPPED and runs nothing

    def ids(self):
        return [f"{TEST}::{t}" for t in self.tests]


class Harness:
    def __init__(self, font, requirements, static_dir):
        self.font = pathlib.Path(font).resolve()
        self.requirements = pathlib.Path(requirements).resolve()
        self.cfg = json.loads(self.font.read_text())
        self.font_dir = self.font.parent
        self.concepts = (self.font_dir / self.cfg["concepts"]).resolve()
        self.out_dir = (self.font_dir / self.cfg["out_dir"]).resolve()
        self.manifest = (self.out_dir / self.cfg["manifest"]).resolve() if self.cfg.get("manifest") else self.out_dir / "manifest.json"
        # `none` is the conftest's word for "no statics ship": the static mutations are skipped. Without the flag the
        # default is <out_dir>/static, and a missing folder is a refusal, not a reason to build statics into the
        # served font folder during the static-overlap mutation (second dry run, finding 1).
        self.static_dir = None if static_dir == "none" else (pathlib.Path(static_dir).resolve() if static_dir else self.out_dir / "static")
        if self.static_dir is not None and not self.static_dir.is_dir():
            sys.exit(f"mutate.py: no static instances at {self.static_dir}; pass --static-dir DIR where build.py --static wrote them, "
                     f"or --static-dir none when no statics ship")
        fam = self.cfg["family"].replace(" ", "")
        self.woff2 = {}
        for g, spec in self.cfg["groups"].items():
            if spec.get("file"):
                self.woff2[g] = (self.out_dir / spec["file"]).resolve()
            else:
                self.woff2[g] = self.out_dir / (f"{fam}-Italic-VF.woff2" if spec.get("italic") else f"{fam}-VF.woff2")
        self.sources = [BUILD, GEN, EXPORT, self.font, self.concepts, self.requirements]
        self.artefacts = [self.manifest, *self.woff2.values()]
        if self.static_dir is not None:
            self.artefacts += sorted(p for p in self.static_dir.iterdir() if p.is_file())
        self.files = self.sources + self.artefacts
        for f in self.files:
            if not f.is_file():
                sys.exit(f"mutate.py: {f} does not exist; build first ({PY} {BUILD} --font {self.font}"
                         + (f" --static {self.static_dir})" if self.static_dir is not None else ")"))
        self.pristine = pathlib.Path(tempfile.mkdtemp(prefix="font-design-pristine-"))
        self.pristine_sha = {}
        for f in self.files:
            dst = self.pristine / f.name
            n = 1
            while dst.exists():  # two files with one name (unlikely): keep both
                dst = self.pristine / f"{f.name}.{n}"
                n += 1
            shutil.copyfile(f, dst)
            self.pristine_sha[f] = (dst, sha(f))
        self.baseline = {d: set(p.name for p in d.iterdir()) for d in (self.out_dir, self.static_dir) if d is not None and d.is_dir()}

    # --- file edits ------------------------------------------------------------------------------------
    def rep(self, path, old, new, count=1):
        """Exact-string replacement, asserted to match exactly `count` times, so a mutation that does not
        apply is a loud error rather than a verdict that means nothing."""
        p = pathlib.Path(path)
        s = p.read_text()
        assert s.count(old) == count, f"{p.name}: expected {count} match(es) of {old[:70]!r}, found {s.count(old)}"
        p.write_text(s.replace(old, new))

    def resub(self, path, pattern, fn, count=None):
        """A regular-expression edit, asserted to match at least once (exactly `count` times when given), for a
        mutation of a project file whose exact text the harness cannot know (a concept's `thin:` value)."""
        p = pathlib.Path(path)
        s = p.read_text()
        n = len(re.findall(pattern, s))
        assert n and (count is None or n == count), f"{p.name}: expected {count or 'at least one'} match(es) of /{pattern}/, found {n}"
        p.write_text(re.sub(pattern, fn, s))

    def jedit(self, path, fn):
        """A structural edit of a JSON file (font.json, requirements.json, the manifest); the formatting is restored with the file."""
        p = pathlib.Path(path)
        obj = json.loads(p.read_text())
        fn(obj)
        p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")

    def clear_pycache(self):
        for d in (HERE / "__pycache__", SCRIPTS / "__pycache__"):
            if d.is_dir():
                shutil.rmtree(d)

    def restore(self):
        for f, (src, _) in self.pristine_sha.items():
            shutil.copyfile(src, f)
        for d, names in self.baseline.items():
            for p in d.iterdir():
                if p.name not in names:
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        os.remove(p)
        self.clear_pycache()
        bad = [f.name for f, (_, digest) in self.pristine_sha.items() if sha(f) != digest]
        return not bad, bad

    def changed_artefacts(self):
        """Names of the artefacts (not sources) that differ from their pristine copy, plus any new file in the
        output directories: the proof that a rebuild produced something for the tests to look at."""
        changed = [f.name for f in self.artefacts if sha(f) != self.pristine_sha[f][1]]
        for d, names in self.baseline.items():
            changed += [f"+{p.name}" for p in d.iterdir() if p.name not in names]
        return changed

    # --- running ---------------------------------------------------------------------------------------
    def build(self, group=None, static=False, extra=(), no_requirements=False):
        cmd = [PY, str(BUILD), "--font", str(self.font), *extra]
        cmd += ["--no-requirements"] if no_requirements else ["--requirements", str(self.requirements)]
        if group:
            cmd += ["--group", group]
        if static:
            assert self.static_dir is not None, "a static mutation ran with --static-dir none"
            cmd += ["--static", str(self.static_dir)]
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        last = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else ""
        return r.returncode, last[:200], r.stderr

    def pytest(self, ids):
        """(returncode, last line, failed test names, errored node ids, {test name: its assertion lines}) for
        the named tests. The assertion lines (`E ...`) are collected per failure section, whose header
        `____ test_name[param] ____` names the test, so an expected text is held against the test it belongs
        to (re-review, code-a F008)."""
        self.clear_pycache()
        cmd = [PY, "-m", "pytest", "-q", "-rfE", "-p", "no:cacheprovider", "--font", str(self.font), "--requirements", str(self.requirements),
               "--static-dir", "none" if self.static_dir is None else str(self.static_dir), *ids]
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
        last = lines[-1] if lines else r.stderr.strip().splitlines()[-1][:200] if r.stderr.strip() else "(no output)"
        failed, errored = [], []
        for ln in r.stdout.splitlines():
            m = SUMMARY.match(ln)
            if m and m.group(1) == "FAILED":
                failed.append(m.group(2).split("::")[-1].split("[")[0])
            elif m:
                errored.append(m.group(2))
        if "error" in last.lower() and not failed and not errored:
            errored.append(last)  # a collection error or a usage error has no summary line
        return r.returncode, last, failed, errored, assertion_lines_by_test(r.stdout)


# --- the mutations ----------------------------------------------------------------------------------------
def mutations(h):
    """The mutation list for a project. Names begin with the plan's row or finding id."""
    F, C, B, M, Q = h.font, h.concepts, BUILD, h.manifest, h.requirements
    # the primary group for the roman-specific mutations: the first group that is not italic, else the
    # first group there is (an italic-only project is valid for build.py; re-review, code-a F006)
    roman = next((g for g, s in h.cfg["groups"].items() if not s.get("italic")), next(iter(h.cfg["groups"])))
    # the first italic group, even when it is the only group (then `roman` is that group too: an italic-only project is valid)
    italics = [g for g, s in h.cfg["groups"].items() if s.get("italic")]
    italic = italics[0] if italics else None
    roman_masters = list(h.cfg["groups"][roman]["masters"])
    first_master = roman_masters[0]
    instances = h.cfg["groups"][roman]["instances"]
    # the second named instance when there is one (the first is often the default location), else the only one
    some_instance = instances[min(1, len(instances) - 1)]["name"].replace(" ", "") if instances else None
    fam = h.cfg["family"].replace(" ", "")
    req = json.loads(Q.read_text())
    req_roman = req["groups"][roman]
    required = req.get("required_characters", "")
    M_ = []

    def cut(path, start, through="\n"):
        """Deletes from `start` (which must occur once) through the first `through` after it: switches off one
        self-check of build.py whose whole line the harness need not restate."""
        p = pathlib.Path(path)
        t = p.read_text()
        assert t.count(start) == 1, f"{p.name}: expected one match of {start[:60]!r}, found {t.count(start)}"
        i = t.index(start)
        j = t.index(through, i) + len(through)
        p.write_text(t[:i] + t[j:])

    def add(name, tests, apply, rebuild=None, **kw):
        M_.append(Mutation(name, tests, apply, rebuild, **kw))

    def unless(condition, reason):
        """None when the project exercises the mutation, else the SKIPPED reason (passed as skip=)."""
        return None if condition else reason

    # cmap (F002 c): build.py stops mapping U+2018. The self-check that every charset.required character
    # is mapped would refuse the build, so font.json drops the character too: a config that agrees with
    # itself and still goes red against the requirements is the F002 point.
    def cmap_mut():
        h.rep(B, '0x2018: "quoteleft", 0x22: "quotedbl",', '0x22: "quotedbl",')
        h.jedit(F, lambda c: c["charset"].__setitem__("required", c["charset"]["required"].replace("‘", "")))
    add("cmap-F002c: U+2018 unmapped in build.py and dropped from font.json required", ["test_the_cmap_is_exactly_the_required_set"], cmap_mut, "all",
        expect="missing: ['‘']", skip=unless("‘" in req["cmap"], "the requirements' cmap does not list U+2018"))
    # required (F002): the digits lose their cmap branch in build.py and font.json stops requiring them;
    # weakest because the digit glyphs still exist and still vary, only their characters are gone. The
    # expected text names the digits THIS project's titles require (second dry run, finding 2).
    def required_mut():
        h.rep(B, "        elif n in DIGITS:\n            cmap[ord(str(DIGITS.index(n)))] = n\n", "")
        h.jedit(F, lambda c: c["charset"].__setitem__("required", "".join(ch for ch in c["charset"]["required"] if not ch.isdigit())))
    digits = sorted({ch for ch in required if ch.isdigit()})
    add("required-F002: digits unmapped and dropped from font.json required", ["test_every_required_character_is_mapped"], required_mut, "all",
        expect=f"lacks {digits}", skip=unless(digits, "the requirements' required_characters hold no digit"))
    # nbsp: the flag goes off AND NBSP leaves charset.required AND requirements.required_characters; the
    # reviewed cmap still lists NBSP, so the test goes red. Two earlier shapes were blocked by a self-check
    # (survivor shape 1): the flag alone, by build.py's charset check; the flag plus font.json, by export.js's
    # required-character check once build.py passed it --requirements (C6), which the stricter harness
    # reported as UNPROVEN instead of GREEN on its first run.
    def nbsp_mut(c):
        c["charset"]["nbsp_to_space"] = False
        c["charset"]["required"] = c["charset"]["required"].replace(" ", "")
    add("nbsp: nbsp_to_space false, NBSP dropped from font.json required and requirements.required_characters", ["test_nbsp_is_the_space_glyph"],
        lambda: (h.jedit(F, nbsp_mut), h.jedit(Q, lambda r: r.__setitem__("required_characters", r["required_characters"].replace(" ", "")))),
        "all", expect="NBSP maps to None", skip=unless("\u00a0" in req["cmap"], "the requirements' cmap does not list NBSP"))
    # apostrophe: likewise one flag; U+0027 then draws the tick while the requirements expect the curly mark
    add("apos: font.json ascii_apostrophe_curly false", ["test_ascii_apostrophe_draws_the_right_mark"],
        lambda: h.jedit(F, lambda c: c["charset"].__setitem__("ascii_apostrophe_curly", False)), "all", expect="U+0027 draws quotesingle",
        skip=unless(req.get("ascii_apostrophe_curly", True), "the requirements set ascii_apostrophe_curly false"))

    # axes (F002 a): the opsz axis leaves the roman group; the masters and instances that only differed in
    # opsz go too, so the build passes and the font simply has one axis fewer than was reviewed
    def drop_opsz(c):
        g = c["groups"][roman]
        ax = next(a for a in g["axes"] if a["tag"] == "opsz")
        g["axes"] = [a for a in g["axes"] if a["tag"] != "opsz"]
        g["masters"] = {n: {**m, "location": {k: v for k, v in m["location"].items() if k != "opsz"}}
                        for n, m in g["masters"].items() if m["location"]["opsz"] == ax["min"]}
        g["hairline_floors"] = {n: v for n, v in g["hairline_floors"].items() if n in g["masters"]}
        g["instances"] = [{**i, "location": {k: v for k, v in i["location"].items() if k != "opsz"}}
                          for i in g["instances"] if i["location"]["opsz"] == ax["min"]]
    has_opsz = any(a["tag"] == "opsz" for a in h.cfg["groups"][roman]["axes"])
    add("axes-F002a: opsz axis dropped from the roman group in font.json", ["test_the_axes_and_instances_are_what_the_css_relies_on"],
        lambda: h.jedit(F, drop_opsz), roman, expect="fvar axes [('wght'", skip=unless(has_opsz, "the roman group has no opsz axis"))

    # axes: the opsz maximum moves (and the masters/instances on it), so fvar differs from the requirements
    def opsz_max(c):
        g = c["groups"][roman]
        ax = next(a for a in g["axes"] if a["tag"] == "opsz")
        old, ax["max"] = ax["max"], ax["max"] - 8
        for m in list(g["masters"].values()) + g["instances"]:
            if m["location"].get("opsz") == old:
                m["location"]["opsz"] = ax["max"]
    add("axes-max: opsz maximum lowered by 8 in font.json", ["test_the_axes_and_instances_are_what_the_css_relies_on"],
        lambda: h.jedit(F, opsz_max), roman, expect="fvar axes [('wght'", skip=unless(has_opsz, "the roman group has no opsz axis"))

    # gvar: one glyph's variations deleted after varLib, with the self-check that would refuse it switched off
    add("gvar: o's gvar deleted, self-check off", ["test_every_glyph_with_contours_varies"],
        lambda: (h.rep(B, '    vf["gasp"] = gasp\n', '    vf["gasp"] = gasp\n    del vf["gvar"].variations["o"]\n'),
                 h.rep(B, '    check(not missing, f"glyphs without gvar variations: {missing}")\n', '')), "all",
        expect="glyphs without variations: ['o']")

    # F013: the last master of the primary group is built with every outline shifted 3 units right; the
    # structure is identical, so every compatibility check passes and every glyph still varies, but
    # instancing at that corner returns outlines 3 units from the exported ones (the test's bound is 2).
    # The first version built the last master from the first master's outlines, which on a two-master
    # group makes every glyph identical across masters, and the builder's own gvar self-check refused the
    # build before the test could see it: UNPROVEN, not RED (re-review, code-a F007).
    last = roman_masters[-1]
    add(f"F013: {last}'s outlines shifted 3 units", ["test_each_master_location_reproduces_its_exported_outlines"],
        lambda: h.rep(B, 'master_outlines(masters[n], "polys", group["_angle"]), cmap, order, vmetrics,',
                      '{gn: (adv, [[(x + (3 if n == ' + repr(last) + ' else 0), y) for x, y in c] for c in cs]) '
                      'for gn, (adv, cs) in master_outlines(masters[n], "polys", group["_angle"]).items()}, cmap, order, vmetrics,'), "all",
        expect="units from the exported master")

    # quotes (#23): Driftwood's quotedblleft advance restored, the straight quotes' instead of the apostrophe's plus the gap
    # the 0.7.0 opening rule is bypassed too, so the italic's max() cannot hide the straight quotes' advance behind the ink's
    add("quotes-#23: quotedblleft given the straight quotes' advance", ["test_quote_glyphs_follow_the_apostrophe_in_every_master"],
        lambda: h.rep(B, '"quotedblleft": opening(round(ap_adv + dbl_gap), turned + shifted(turned)),',
                      '"quotedblleft": {"adv": round(tick_adv + aw * 0.8), "polys": turned + shifted(turned)},'), "all",
        expect="quotedblleft: advance")

    # avar: the roman wght map disappears from font.json, so weight 500 lands on the linear midpoint
    def drop_map(c):
        for a in c["groups"][roman]["axes"]:
            if a["tag"] == "wght":
                a.pop("map", None)
    wght_map = next((a.get("map") for a in h.cfg["groups"][roman]["axes"] if a["tag"] == "wght"), None)
    no_map = unless(wght_map, "the roman wght axis has no avar map in font.json")
    add("avar: wght map dropped from the roman group in font.json", ["test_avar_maps_the_reviewed_intermediate_weights"],
        lambda: h.jedit(F, drop_map), roman, expect="the requirements want", skip=no_map)

    # interpolated location (F010): the Medium's design value moves 30 units, so wght 500 no longer sits at t
    def move_medium(c):
        for a in c["groups"][roman]["axes"]:
            if a["tag"] == "wght" and "map" in a:
                mid = [p for p in a["map"] if p[0] != a["min"] and p[0] != a["max"]]
                assert mid, "the roman wght map has no intermediate point to move"
                mid[0][1] -= 30
    has_mid = bool(wght_map) and any(p[0] not in (wght_map[0][0], wght_map[-1][0]) for p in wght_map)
    add("interp-F010: the Medium's avar design value moved by 30", ["test_kerning_and_advances_at_the_interpolated_location"],
        lambda: h.jedit(F, move_medium), roman, expect="more than a unit from the interpolation",
        skip=unless(has_mid, "the roman wght map has no intermediate point to move"))

    # kerning (F005/F010): the non-default masters' pair values are zeroed in build.py, so the hand pairs
    # hold at the default master and nowhere else
    add("kern-zero: pair values zeroed in every master but the first", ["test_kerning_and_advances_at_every_master"],
        lambda: h.rep(B, 'masters[n]["kerns"], default_weight_class(group))',
                      f'[(a, b, 0 if n != {first_master!r} else v) for a, b, v in masters[n]["kerns"]], default_weight_class(group))'), "all",
        expect="hand pair", skip=unless(req.get("hand_kerns") or req_roman.get("hand_kerns"), "the requirements pin no hand kern pair"))
    # re-review code-a F005: build.py adds a pair the exporter never emitted (figures are never kerned
    # automatically, so zero|one is in no master's list); the first test compared the expected pairs only
    add("kern-extra: build.py adds a GPOS pair the exporter never emitted", ["test_kerning_and_advances_at_every_master"],
        lambda: h.rep(B, '    fea.append("} kern;")\n', '    fea.append("  pos zero one -40;\\n} kern;")\n'), "all",
        expect="GPOS pairs the exporter never emitted")
    # re-review code-a F004: the automatic pass returns 0 for every pair in export.js, so no automatic pair
    # reaches the threshold and the font ships with the hand and word-space pairs alone; a fresh export
    # agrees with itself, so only the "at least one live automatic pair" assertion can see it
    add("kern-auto-zero: export.js computes 0 for every automatic pair", ["test_kerning_and_advances_at_every_master"],
        lambda: h.rep(EXPORT, 'auto[n][a + "|" + b] = Math.round(m.kern(glyphs[a], glyphs[b], P, SPARSE_CAP));', 'auto[n][a + "|" + b] = 0;'), "all",
        expect="no automatic kern pair with a non-zero value")
    # F005: the word space ignores the display track in export.js (a fresh export is part of the rebuild). The
    # expectation is the word_space PINNED in requirements.json (C9), so the exporter cannot agree with itself.
    add("F005: word space ignores track in export.js", ["test_kerning_and_advances_at_every_master"],
        lambda: h.rep(EXPORT, "const space = Math.round(210 + 0.3 * P.W + 2 * P.track);", "const space = Math.round(210 + 0.3 * P.W);"), "all",
        expect="vs the reviewed")
    # C9 pin: the reviewed word space itself is edited by one unit; the font and the exporter now both disagree with it
    def move_word_space(r):
        r["groups"][roman]["word_space"][first_master] += 1
    add("C9-pin: requirements word_space moved by one unit", ["test_kerning_and_advances_at_every_master"],
        lambda: h.jedit(Q, move_word_space), expect=f"vs the reviewed {req['groups'][roman]['word_space'][first_master] + 1}")

    # hairlines (F002 b): every floor in font.json drops to 1 AND every concept's `thin` is cut to 0.8 of
    # itself (a regular-expression edit, because the harness cannot know a project's values); the build
    # passes its own (lowered) floors, and the font is thinner than was reviewed. The thinner design also
    # moved the neutral italic Bold@80 decimation diff to 51 levels (budget 48), so the raster budgets are
    # lifted too: the build must PASS, or the test only sees the fresh export. Whether 0.8 takes the
    # hairline under the reviewed floor depends on the design's margin above it: a face that keeps it
    # clear stays GREEN here, which is then a finding about the margin, not about the test.
    def lower_floors(c):
        for g in c["groups"].values():
            g["hairline_floors"] = {n: 1 for n in g["hairline_floors"]}
        c["raster"]["budget"] = {"decimation": 255, "union": 255, "seam": 255}
    add("floor-F002b: font.json floors to 1 and every concepts.js thin cut to 0.8 of itself", ["test_hairlines_clear_the_floor"],
        lambda: (h.jedit(F, lower_floors), h.resub(C, r"\bthin:\s*([0-9.]+)", lambda m: f"thin: {round(float(m.group(1)) * 0.8, 3)}")), "all",
        expect="manifest says")
    # hairlines: the manifest alone claims a stroke one unit under the reviewed floor (no rebuild)
    floor_req = req_roman["hairline_floors"][first_master]
    add(f"floor-manifest: manifest min stroke lowered to {floor_req - 1}", ["test_hairlines_clear_the_floor"],
        lambda: h.jedit(M, lambda m: m["groups"][roman]["min_stroke_width"].__setitem__(first_master, float(floor_req - 1))),
        expect=f"manifest says {float(floor_req - 1)} < {floor_req}")
    # hairlines (C7): the builder's own recomputed figure in the manifest is lowered; the exporter's stays
    add(f"floor-recomputed: manifest min_stroke_width_recomputed lowered to {floor_req - 1}", ["test_hairlines_clear_the_floor"],
        lambda: h.jedit(M, lambda m: m["groups"][roman]["min_stroke_width_recomputed"].__setitem__(first_master, float(floor_req - 1))),
        expect="from the polygons, below the floor")
    # gasp: the table is never added
    # (the build's own gasp self-check, in the font-table group of self_checks(), is cut too, or it refuses the build first)
    add("gasp: gasp table dropped, self-check off", ["test_hairlines_clear_the_floor"],
        lambda: (h.rep(B, '    vf["gasp"] = gasp\n', ''), cut(B, '    check("gasp" in rt and rt["gasp"].gaspRange')), "all", expect="no gasp table")
    # the build's own floor check (a build_refused mutation): a floor raised above the measured stroke must
    # refuse the build with the floor in the message, and leave the shipped files untouched
    floor_now = h.cfg["groups"][roman]["hairline_floors"][first_master]
    add(f"floor-selfcheck: font.json floor for {first_master} raised to {floor_now + 40}", ["test_hairlines_clear_the_floor"],
        lambda: h.jedit(F, lambda c: c["groups"][roman]["hairline_floors"].__setitem__(first_master, floor_now + 40)), roman,
        build_refused=f"below floor {floor_now + 40}")

    # fold fixture: the detector reads 0 on unequal runs instead of throwing (the survivor of Bract's first run)
    add("fold-unequal: detector returns 0 on unequal edge runs", ["test_the_fold_detector_sees_first_segment_decimated_and_unequal_folds"],
        lambda: h.rep(EXPORT, 'if (b1 - b0 + 1 !== n) throw new Error("edge runs of unequal length");',
                      'if (b1 - b0 + 1 !== n) return { raw: 0, decimated: 0 };'), expect="unequal edge runs did not throw")
    # fold fixture: the walk starts at the second segment, so a fold in the first is invisible (Bract R4)
    add("fold-first: the edge walk skips the first segment", ["test_the_fold_detector_sees_first_segment_decimated_and_unequal_folds"],
        lambda: h.rep(EXPORT, "for (let i = 0; i + 1 < points.length; i++) {", "for (let i = 1; i + 1 < points.length; i++) {"),
        expect="a fold in the first segment went unreported")
    # fold output (F002): font.json loosens the raw threshold tenfold; export.js obeys, the requirements do not
    add("fold-units-F002: font.json fold_units raw 4 -> 40", ["test_no_stroke_edge_folds_back"],
        lambda: h.jedit(F, lambda c: c["fold_units"].__setitem__("raw", 40)), "all", expect="export.js measures with")

    # budget: no decimation and the font.json budget lifted, so the build passes and ships every sample point
    add("budget: eps 0 with the font.json budget lifted", ["test_the_font_is_under_budget"],
        lambda: h.jedit(F, lambda c: (c.__setitem__("size_budget_bytes", 100 * 1024 * 1024), c.__setitem__("decimation_eps", 0))), "all",
        expect="the budget is")

    # F012: vertical metrics copied from a precedent instead of measured. The precedent's own figures
    # (940/300) would pass a face that happens to fit them, so the constants are the ascender's and
    # descender's HALVES: any face with a capital or a descender then has a glyph outside the box.
    add("F012: win metrics are constants", ["test_no_glyph_exceeds_the_win_metrics"],
        lambda: h.rep(B, "    return math.ceil(top), math.ceil(-bot)\n", "    return 350, 100\n"), "all", expect="outside win")

    # overlap: the flag is never set, the self-check is off, and the raster budgets are lifted in font.json
    # (the union check refused Bract's first try at this mutation, so it never reached the test)
    add("overlap: flag not set, self-check off, raster budgets lifted", ["test_glyphs_declare_their_overlaps"],
        lambda: (h.rep(B, "        g.flags[0] |= flagOverlapSimple", "        pass"),
                 h.rep(B, '    check(not bare, f"OVERLAP_SIMPLE flag lost on {bare[:8]}")\n', ''),
                 h.jedit(F, lambda c: c["raster"].__setitem__("budget", {"decimation": 255, "union": 255, "seam": 255}))), "all",
        expect="glyphs without OVERLAP_SIMPLE")

    # manifest: a comment in gen.js changes and nothing is rebuilt
    add("manifest-sources: a comment edited in gen.js", ["test_the_shipped_fonts_match_their_manifest"],
        lambda: h.rep(GEN, "/* ---------- Geometry helpers ---------- */", "/* ---------- Geometry helpers. ---------- */"),
        expect="gen.js changed since the font was built")
    # C6: the font rebuilt with --no-requirements; the manifest then records null and the suite must notice
    add("C6-norequirements: rebuilt with --no-requirements", ["test_the_shipped_fonts_match_their_manifest"],
        lambda: None, {"group": None, "no_requirements": True}, expect="built with --no-requirements")

    # names: the family is renamed in font.json (the output files are renamed with it, and cleaned up on restore)
    add("names: family renamed in font.json", ["test_the_font_names_the_project"],
        lambda: h.jedit(F, lambda c: c.__setitem__("family", c["family"] + "r")), "all", expect=f"family '{fam}r'")

    # designer (name ID 9): the record takes the manufacturer's string, the build's own check off; and the config edit alone
    add("designer-code: name ID 9 written from names.manufacturer, self-check off", ["test_the_font_names_the_project"],
        lambda: (h.rep(B, '"designer": names["designer"],', '"designer": names["manufacturer"],'),
                 cut(B, '    check(name.get(9) == cfg["names"]["designer"], f"name ID 9')),
        "all", expect="designer '", skip=unless((req.get("names") or {}).get("designer") and (req["names"]["designer"] != req["names"].get("manufacturer")),
                                                  "the requirements pin no designer, or it equals the manufacturer"))
    add("designer-config: font.json names.designer changed", ["test_the_font_names_the_project"],
        lambda: h.jedit(F, lambda c: c["names"].__setitem__("designer", c["names"]["designer"] + " II")), "all", expect="designer '",
        skip=unless((req.get("names") or {}).get("designer"), "the requirements pin no designer"))

    # reproducibility (trap 14): setdefault lets the caller's SOURCE_DATE_EPOCH into the bytes
    add("repro-setdefault: SOURCE_DATE_EPOCH via setdefault", ["test_the_build_is_reproducible"],
        lambda: h.rep(B, 'os.environ["SOURCE_DATE_EPOCH"] = str(int(cfg["source_date_epoch"]))',
                      'os.environ.setdefault("SOURCE_DATE_EPOCH", str(int(cfg["source_date_epoch"])))'), expect="DIFFERS")
    # reproducibility: random jitter in an advance
    add("repro-random: Math.random in an exported advance", ["test_the_build_is_reproducible"],
        lambda: h.rep(EXPORT, "G[k] = { adv: Math.round(g.adv),", "G[k] = { adv: Math.round(g.adv + Math.random()),"), expect="DIFFERS")

    # dropAmt (#24): the scale factor is pinned to 1, so the knob is dead again
    add("dropamt-noop: dk constant 1 in gen.js",
        ["test_dropamt_changes_the_teardrops_and_flareamt_with_tear_throws", "test_dropamt_scales_the_outer_inner_and_symmetric_teardrop"],
        lambda: h.rep(GEN, "var dk = P.dropAmt / DROP_AMT_DEFAULT;", "var dk = 1;"),
        expect={"test_dropamt_changes_the_teardrops_and_flareamt_with_tear_throws": "the knob is dead",
                "test_dropamt_scales_the_outer_inner_and_symmetric_teardrop": "must swell"})
    # F005: the knob must scale ALL THREE teardrop constants. These two leave the outer swell listening and
    # stop one of the others; the "changes outlines" test cannot see either (the first survived a review).
    # (the inner thinning then no longer differs between dropAmt 0 and 0.55, so the test sees an inner
    # displacement of exactly 0 where the outer still swells; the first run of the stricter harness showed
    # the assertion that fires is "must thin", not the linearity one this comment first expected)
    add("dropamt-inner: dk dropped from the inner thinning only", ["test_dropamt_scales_the_outer_inner_and_symmetric_teardrop"],
        lambda: h.rep(GEN, "inn = 1 - 0.28 * dk * dropK * e;", "inn = 1 - 0.28 * dropK * e;"), expect="inner 0.000 must thin")
    add("dropamt-s: dk dropped from the symmetric case only", ["test_dropamt_scales_the_outer_inner_and_symmetric_teardrop"],
        lambda: h.rep(GEN, "{ wl *= 1 + 0.3 * dk * e; wr *= 1 + 0.3 * dk * e; }", "{ wl *= 1 + 0.3 * e; wr *= 1 + 0.3 * e; }"),
        expect="both edges must swell, got 0.000 / 0.000")
    # #24: the throw on flareAmt beside tear is removed
    add("throw-removed: flareAmt beside tear no longer throws", ["test_dropamt_changes_the_teardrops_and_flareamt_with_tear_throws"],
        lambda: h.rep(GEN, '  if (concept.tear && concept.flareAmt !== undefined) {\n    throw new Error("params: concept " + concept.id'
                           + ' + " sets flareAmt with tear: true; flareAmt has no effect with teardrop terminals, set dropAmt instead");\n  }\n', ''),
        expect="did not throw naming dropAmt")

    # optical corrections (0.2 item 3). Each edit is the weakest change that makes one assertion of
    # test_optical_corrections_change_only_the_strokes_they_name false; the comment says which.
    OPT = "test_optical_corrections_change_only_the_strokes_they_name"
    CW = "closed ? 1 : cwOf ? cwOf[i] : 0"
    # a: hzThin loses its cos^2 weight, so a plumb stem thins as much as a level bar
    add("optical-hz-all: hzThin applied without the cos^2 weight", [OPT],
        lambda: h.rep(GEN, "(1 - (1 - P.hzThin) * c * c)", "(1 - (1 - P.hzThin))"), expect="stem is 90.000 wide")
    # a: every open stroke takes the full roundGain, so a straight stem swells
    add("optical-round-straight: curvature weight forced to 1 on open strokes", [OPT],
        lambda: h.rep(GEN, CW, "closed ? 1 : 1"), expect="stem is 105.000 wide")
    # d: only rings take the gain, so the open `c` never swells
    add("optical-round-open-off: curvature weight forced to 0 on open strokes", [OPT],
        lambda: h.rep(GEN, CW, "closed ? 1 : 0"), expect="off W x (1 + 0.05 x curvature weight)")
    # d: the cap at 1 is dropped, so the unfitted `c` swells past the full gain where it curves tightest
    add("optical-round-uncapped: curvature weight not capped at 1", [OPT],
        lambda: h.rep(GEN, "cwOf.push(Math.min(1, kappa * ROUND_GAIN_RADIUS * (P.W0 || P.W)));", "cwOf.push(kappa * ROUND_GAIN_RADIUS * (P.W0 || P.W));"),
        expect="off W x (1 + 0.05 x curvature weight)")
    # e: the diagonal weight is 0, so the `x` stroke keeps its full width
    add("optical-diag-flat: sin^2(2 theta) weight replaced by 0", [OPT],
        lambda: h.rep(GEN, "(1 - (1 - P.diagThin) * s2 * s2)", "(1 - (1 - P.diagThin) * 0)"), expect="the `x` stroke (theta")
    # f: hwFlat takes the pen law without the optical factor, so a flat bar's outer edge misses the line
    add("optical-fit: hwFlat ignores the optical factor", [OPT],
        lambda: h.rep(GEN, "  if (P.optical) return P.W * penWidth(0, P, 0) / 2;\n", ""), expect="the `z` bar's top edge is at 495")
    # g: the corner's partner width takes the pen law without the optical factor, so the stem runs past its bar
    add("optical-corner: the corner reach ignores the optical factor", [OPT],
        lambda: h.rep(GEN, "var pw = P.W * penWidth(pth, P, 0);",
                      "var pw = P.W * (P.thin + (1 - P.thin) * Math.pow(Math.abs(Math.sin(pth - P.nib)), P.pow));"),
        expect="the `E` stem tops out at")
    # g, with all three knobs: the corner treats its straight partner as a curve, so the stem runs 2.25 past the bar
    add("optical-corner-round: the corner reach takes the round gain", [OPT],
        lambda: h.rep(GEN, "var pw = P.W * penWidth(pth, P, 0);", "var pw = P.W * penWidth(pth, P, 1);"), expect="the `E` stem tops out at")
    # f, with all three knobs: the fit treats the level bar as a curve, so its outer edge sits 2.25 outside the line
    add("optical-fit-round: hwFlat takes the round gain", [OPT],
        lambda: h.rep(GEN, "return P.W * penWidth(0, P, 0) / 2;", "return P.W * penWidth(0, P, 1) / 2;"), expect="the `z` bar's top edge is at")
    # d: the documented radius constant changes, which moves every partly weighted sample of the fitted `c`
    add("optical-radius: ROUND_GAIN_RADIUS 2.5 becomes 2", [OPT],
        lambda: h.rep(GEN, "var ROUND_GAIN_RADIUS = 2.5;", "var ROUND_GAIN_RADIUS = 2;"), expect="off W x (1 + 0.05 x curvature weight)")
    # c: a ring is no longer round by definition, so the `o` keeps its full width at the right extreme
    add("optical-ring-off: curvature weight of a closed stroke is 0", [OPT],
        lambda: h.rep(GEN, "penWidth(th, P, closed ? 1 :", "penWidth(th, P, closed ? 0 :"), expect="the `o` is 100.000 thick at its right extreme")
    # c: the optical flag ignores roundGain, so roundGain alone is a dead knob (the dead-knob shape of issue #24)
    add("optical-flag-omits-round: roundGain alone does not switch the optical path on", [OPT],
        lambda: h.rep(GEN, "P.optical = !(P.hzThin === 1 && P.diagThin === 1 && P.roundGain === 1);", "P.optical = !(P.hzThin === 1 && P.diagThin === 1);"),
        expect="the `o` is 100.000 thick at its right extreme")
    # c2: the round fit takes the straight-bar half width again (the 0.2 first version), so under roundGain a round
    # top overshoots by the configured overshoot plus hw x (roundGain - 1)
    add("optical-overshoot-round: the round fit uses the level half width", [OPT],
        lambda: h.rep(GEN, "var hwRound = P.optical ? P.W * penWidth(0, P, 1) / 2 : hw;", "var hwRound = hw;"), expect="the `o` spans")
    # x-height (0.2 item 4). Each edit is the weakest change that makes one assertion of the named test false.
    XL = "test_xh_moves_the_lowercase_lines_and_leaves_the_capitals"
    # a: the round targets stay at the literal 500 (the ring and the open round extremes), so the `o` top does not follow xh
    def xh_round_literal():
        h.rep(GEN, "top = Y(ROUND[top][0]) + O - hwRound;", "top = ROUND[top][0] + O - hwRound;")
        h.rep(GEN, "bot = Y(ROUND[bot][0]) - O + hwRound;", "bot = ROUND[bot][0] - O + hwRound;")
        h.rep(GEN, "ny = Y(R[0]) + R[1] * (O - hwRound);", "ny = R[0] + R[1] * (O - hwRound);")
    add("xh-round-literal: ROUND targets stay at the literal lines", [XL], xh_round_literal, expect="the `o` spans")
    # c: flat strokes move inward from the literal 500, not from the new x-line
    add("xh-flat-literal: FLAT targets stay at the literal lines", [XL],
        lambda: h.rep(GEN, "p.ny = Y(p.y) + FLAT[fk] * hw;", "p.ny = p.y + FLAT[fk] * hw;"), expect="the `z` bar's top edge")
    # f: the map reaches capitals, figures and the apostrophe
    add("xh-caps-too: the map applied to UPPERISH keys and the apostrophe", [XL],
        lambda: h.rep(GEN, 'function xhMapped(key, P) { return P.xh !== 500 && !UPPERISH.test(key) && key !== "\'"; }',
                      "function xhMapped(key, P) { return P.xh !== 500; }"), expect="do not follow xh")
    # g: the band between the x-line and the ascender is left unmapped, so the i dot (680) stays where it was
    add("xh-band-unmapped: 500 < y < 740 left unmapped", [XL],
        lambda: h.rep(GEN, "  return xh + (y - 500) * (740 - xh) / 240;\n}\nfunction xhMapped", "  return y;\n}\nfunction xhMapped"), expect="the `i` dot is at")
    # g: the dot rule reads the MAPPED dot position (review F006): at xh 600 the colon's upper dot (420) reads 504 and misses it
    add("xh-dot-mapped: the dot rule reads the mapped position", [XL],
        lambda: h.rep(GEN, "else if (P.overshoot && dy > 380 && dy < 460) dy = (mapOn ? P.xh : 500) - r + 4;",
                      "else if (P.overshoot && (mapOn ? ymap(dy, P.xh) : dy) > 380 && (mapOn ? ymap(dy, P.xh) : dy) < 460) dy = (mapOn ? P.xh : 500) - r + 4;"),
        expect="the colon's dots are centred at")
    # the decisions read the drawn coordinates instead of the unmapped ones (review F004, F005)
    add("xh-branch-mapped: every decision reads the drawn skeleton", ["test_xh_does_not_change_any_branch_record"],
        lambda: h.rep(GEN, "var pu = U ? U.pts : pts, ju = U ? U.joins : joins;", "var pu = pts, ju = joins;"), expect="xh changed a branch record")
    # the curl test is decided on the drawn tail again (no shipped face curls, so only the test's all-curl variant can see it). The
    # outer call (with `info`) reads the drawn cross product; the inner call on the reference copy keeps its own, so when the two
    # disagree the copy is padded to the drawn length: since 0.7.0 the reference copy exists at every multiplier but 1, and the
    # one-line form left the two arrays different lengths and crashed node instead of failing the assertion (UNPROVEN, smoke step 5)
    def curl_mapped():
        h.rep(GEN, "if (Math.abs(crossD) < 0.06) return 0;", "if (Math.abs(info ? cross : crossD) < 0.06) return 0;")
        h.rep(GEN, "  if (dec) addCurl(dec, P);", "  if (dec) { addCurl(dec, P); while (dec.length < pts.length) dec.push(dec[dec.length - 1]); }")
    add("xh-curl-mapped: the curl decision reads the drawn skeleton", ["test_xh_does_not_change_any_branch_record"], curl_mapped, expect="xh changed a branch record")
    # weight (0.7.0, docs/plan-italic-bold.md): the decisions read the drawn geometry again at every multiplier but 1, so xf's weight
    # widening and the fit's half width move them; the italic w's serif kind flips between the masters
    add("weight-branch-drawn: every decision reads the drawn geometry away from mult 1", ["test_weight_does_not_change_any_branch_record"],
        lambda: h.rep(GEN, "var decideOn = mapOn || P.W !== P.W0;", "var decideOn = mapOn;"), expect="weight changed a structure or branch record")
    # the italic opening quotes keep the apostrophe-derived advance (0.5.0), so their slanted ink overhangs the next letter
    add("quote-opening-unslanted: the italic opening quotes keep the apostrophe-derived advance", ["test_opening_quotes_lie_inside_their_advance"],
        lambda: h.rep(B, "        if italic_angle:\n            xs = [x for p in polys", "        if False:\n            xs = [x for p in polys"),
        italic or roman, expect="overhangs its advance by", skip=unless(italic, "the project has no italic group"))
    # the apostrophe alone is mapped, so the six quote glyphs the builder derives from it move
    add("xh-apostrophe-mapped: the apostrophe follows the map", [XL],
        lambda: h.rep(GEN, 'function xhMapped(key, P) { return P.xh !== 500 && !UPPERISH.test(key) && key !== "\'"; }',
                      "function xhMapped(key, P) { return P.xh !== 500 && !UPPERISH.test(key); }"), expect="the apostrophe moved")
    # spacing: the glyph's sidebearing band stays 500
    add("xh-band-500: the sidebearing band of a lowercase glyph stays 500", ["test_xh_sets_the_spacing_band"],
        lambda: h.rep(GEN, "var top = UPPERISH.test(key) ? 700 : P.xh, b0 = binOf(0)", "var top = UPPERISH.test(key) ? 700 : 500, b0 = binOf(0)"),
        expect="the `o` left sidebearing")
    # spacing: the kern's band stays 500
    def kern_band_500():
        h.rep(GEN, "var top = (a.upper || b.upper) ? 700 : P.xh;", "var top = (a.upper || b.upper) ? 700 : 500;")
        h.rep(GEN, "pairGap(ref, ref, both ? 700 : P.xh).mean", "pairGap(ref, ref, both ? 700 : 500).mean")
    add("xh-kern-band-500: the kern's band stays 500", ["test_xh_sets_the_spacing_band"], kern_band_500, expect="the `a|v` kern is")
    add("xh-range-removed: params() accepts any xh", ["test_xh_outside_its_range_is_refused"],
        lambda: h.rep(GEN, 'if (concept.xh !== undefined && !(typeof concept.xh === "number" && concept.xh >= 400 && concept.xh <= 600)) {', "if (false) {"),
        expect="did not refuse it by name")
    # serifBracket
    BL = "test_an_unbracketed_serif_is_a_slab_with_the_bracketed_point_count"
    add("bracket-ignored: the blend factor is forced to 1", [BL],
        lambda: h.rep(GEN, "P.serifBracket = concept.serifBracket === undefined ? 1 : concept.serifBracket;", "P.serifBracket = 1;"),
        expect="at serifBracket 0 the serif spans")
    add("bracket-count: the slab is drawn as a six-point rectangle", [BL],
        lambda: h.rep(GEN, "function serifBlend(x, y, ed, L, h, sy, b) {\n",
                      "function serifBlend(x, y, ed, L, h, sy, b) {\n  if (b === 0) return [ed(-1, sy * h), [x - L, y + sy * h], [x - L, y], "
                      "[x + L, y], [x + L, y + sy * h], ed(1, sy * h)];\n"),
        expect="no 26-point serif")
    add("bracket-diag: the diagonal serif is not given the blend", [BL],
        lambda: h.rep(GEN, "  if (bk !== 1) { // blended with a slab", "  if (false) { // blended with a slab"), expect="v 26-point serif at y 500")
    add("bracket-range-removed: params() accepts any serifBracket", ["test_serifbracket_outside_zero_to_one_is_refused"],
        lambda: h.rep(GEN, 'if (concept.serifBracket !== undefined && !(typeof concept.serifBracket === "number" && concept.serifBracket >= 0 '
                           '&& concept.serifBracket <= 1)) {', "if (false) {"),
        expect="did not refuse it by name")
    # headSink (0.9.0)
    HS, HR = "test_headsink_sinks_the_stem_end_under_a_lowercase_head_serif", "test_headsink_outside_its_range_is_refused"
    SINK = "if (P.headSink > 0 && !UPPERISH.test(ch)) {"
    add("headsink-ignored: the sink never runs", [HS], lambda: h.rep(GEN, SINK, "if (false) {"), expect="pokes out above the wedge")
    add("headsink-capitals: the capital test is dropped", [HS],
        lambda: h.rep(GEN, SINK, "if (P.headSink > 0) {"), expect="which has no lowercase head serif")
    add("headsink-global: every point above the line is pinned", [HS],
        lambda: h.rep(GEN, "for (var j = k; j >= 0 && j < n && E[j][1] > line; j -= sg) E[j] = [E[j][0] + (line - E[j][1]) * leanK, line];",
                      "for (var j = 0; j < n; j++) if (E[j][1] > line) E[j] = [E[j][0] + (line - E[j][1]) * leanK, line];"),
        expect="away from its serifed end")
    add("headsink-spacing: the spacing profile reads the sunk body", [HS],
        lambda: h.rep(GEN, "profs.push(it.prof || f.pts);", "profs.push(f.pts);"), expect="headSink changed the advance of")
    add("headsink-no-serifgrow: the depth ignores serifGrow", [HS],
        lambda: h.rep(GEN, "line = pts[k][1] - P.headSink * SW * P.serifH;", "line = pts[k][1] - P.headSink * (P.W0 || P.W) * P.serifH;"),
        expect="of the serif height")
    add("headsink-range-removed: params() accepts any headSink", [HR],
        lambda: h.rep(GEN, 'if (concept.headSink !== undefined && !(typeof concept.headSink === "number" && concept.headSink >= 0 '
                           '&& concept.headSink <= 0.7)) {', "if (false) {"),
        expect="did not refuse it by name")
    # junctions and crotch (0.2 item 9)
    JL, CL = "test_joints_opt_in_cuts_a_sans_joint_level", "test_crotch_thins_only_the_inner_edge_of_an_acute_joint"
    add("joints-ignored: the joint pass reads ends.s only", [JL],
        lambda: h.rep(GEN, 'var jointsOn = P.ends.s === "serif" || P.joints === true;', 'var jointsOn = P.ends.s === "serif";'),
        expect="with joints the V's joint end is at y")
    add("joints-keep-disk: a joint whose end is a disk still draws the disk", [JL],
        lambda: h.rep(GEN, 'if (pd && vert) e[1] = "joint";', 'if (pd && vert) e[1] = mode === "disk" ? "disk" : "joint";'),
        expect="a terminal is still drawn at a joint")
    add("crotch-both-edges: wl and wr both thinned", [CL],
        lambda: h.rep(GEN, "if (c[1].left) wl *= fc; else wr *= fc;", "wl *= fc; wr *= fc;"), expect="the outer edge moved by")
    add("crotch-everywhere: every end of every stroke thins", [CL],
        lambda: h.rep(GEN, "var acute = isJoint && -(t[0] * sg * pdU[0] + t[1] * sg * pdU[1]) > 0.3;", "var acute = true;"), expect="differs between crotch 0 and 0.3")
    add("crotch-corners: the acute test is dropped, so a corner thins too", [CL],
        lambda: h.rep(GEN, "var acute = isJoint && -(t[0] * sg * pdU[0] + t[1] * sg * pdU[1]) > 0.3;", "var acute = !!pdU;"), expect="E differs between crotch 0 and 0.3")
    add("crotch-corner-as-joint: a corner counts as a joint", [CL],
        lambda: h.rep(GEN, "var isJoint = !!pdU && Math.abs(t[1]) > 0.5 && Math.abs(pdU[1]) > 0.5;", "var isJoint = !!pdU;"),
        expect="glyphs with an acute joint in their record")
    add("crotch-obtuse: every joint counts, not only the acute ones", [CL],
        lambda: h.rep(GEN, "t[1] * sg * pdU[1]) > 0.3;", "t[1] * sg * pdU[1]) > -0.9;"), expect="differs between crotch 0 and 0.3")
    add("crotch-floor: the reach grows to 2 W0, into the hairline interior", [CL],
        lambda: h.rep(GEN, "var crotchLen = tearL, cr = null;", "var crotchLen = 2 * (P.W0 || P.W), cr = null;"), expect="hairline minimum")
    add("apex-accepted: params() no longer refuses apex", ["test_apex_is_refused_until_built"],
        lambda: h.rep(GEN, "  if (concept.apex !== undefined) {\n    throw", "  if (false) {\n    throw"), expect="apex was not refused")
    add("optical-fit-overcorrect: round extremes are fitted with a curvature weight of 2", ["test_open_curve_extremes_stay_within_the_documented_bound_of_the_overshoot"],
        lambda: h.rep(GEN, "var hwRound = P.optical ? P.W * penWidth(0, P, 1) / 2 : hw;", "var hwRound = P.optical ? P.W * penWidth(0, P, 2) / 2 : hw;"),
        expect="beyond the bound")
    # G1, G2: a decision reads the drawn coordinates again
    XD = "test_no_decision_reads_a_mapped_coordinate"
    add("xh-beak-mapped: the beak gate reads the drawn points", [XD],
        lambda: h.rep(GEN, "pu.every(function (q) { return Math.abs(q[1] - pu[0][1]) < 0.5; })", "pts.every(function (q) { return Math.abs(q[1] - pts[0][1]) < 0.5; })"),
        expect="xh changed a branch record on a synthetic glyph")
    def partner_mapped():
        h.rep(GEN, 'ends.push({ p: qU[0], si: si, end: "a",', 'ends.push({ p: q[0], si: si, end: "a",')
        h.rep(GEN, 'ends.push({ p: qU[m], si: si, end: "b",', 'ends.push({ p: q[m], si: si, end: "b",')
        h.rep(GEN, "partner(ptsU[0], si), pB", "partner(pts[0], si), pB")
        h.rep(GEN, "partner(ptsU[ptsU.length - 1], si)", "partner(pts[pts.length - 1], si)")
    add("xh-partner-mapped: the pairing of two ends reads the drawn endpoints", [XD], partner_mapped, expect="xh changed a branch record on a synthetic glyph")
    add("optical-null-accepted: diagThin: null is accepted", ["test_the_optical_knobs_refuse_values_outside_their_ranges"],
        lambda: h.rep(GEN, "if (v !== undefined && !(typeof v === \"number\" && v > k[1] && v < k[2])) {",
                      "if (v !== undefined && !(k[0] === \"diagThin\" && v === null) && !(typeof v === \"number\" && v > k[1] && v < k[2])) {"),
        expect="diagThin=null: params() did not refuse it by name")
    add("crotch-token-always: the crotch token is written whether or not crotch is set", ["test_an_unset_crotch_leaves_the_0_1_branch_record"],
        lambda: h.rep(GEN, "if (P.crotch > 0) sig += ", "sig += "), expect="records are not in the 0.1 form with crotch unset")
    add("xh-curl-handedness: the spiral's handedness reads the drawn cross product", ["test_no_decision_reads_a_mapped_coordinate"],
        lambda: h.rep(GEN, "var sg = crossD > 0 ? 1 : -1, N", "var sg = cross > 0 ? 1 : -1, N"), expect="xh changed a branch record on a synthetic glyph")
    # the range refusals are removed, so a typo changes every stroke silently
    add("optical-range-removed: params() accepts any hzThin, diagThin, roundGain", ["test_the_optical_knobs_refuse_values_outside_their_ranges"],
        lambda: h.rep(GEN, "if (v !== undefined && !(typeof v === \"number\" && v > k[1] && v < k[2])) {", "if (false) {"), expect="params() did not refuse it by name")

    # F011: the missing-character scan reports nothing
    add("F011: missingCharacters returns []", ["test_export_refuses_a_required_character_without_a_skeleton"],
        lambda: h.rep(EXPORT, "    if (!have.has(ch)) out.push(ch);\n  }\n  return out;", "    if (!have.has(ch)) out.push(ch);\n  }\n  return [];"),
        expect="export.js exited 0")
    # C6: build.py stops passing --requirements to export.js, so a normal build skips the F011 check; the
    # build then SUCCEEDS on a requirements file naming "@", which is what the test must see
    add("C6-export: build.py no longer passes --requirements to export.js", ["test_build_refuses_a_required_character_without_a_skeleton"],
        lambda: h.rep(B, '    if requirements_path is not None:\n        cmd += ["--requirements", str(requirements_path)]\n', ''),
        expect="exited 0 on the export path")
    # C6: the --masters path's own required-character check finds nothing missing
    add("C6-masters: the --masters required-character check finds nothing", ["test_build_refuses_a_required_character_without_a_skeleton"],
        lambda: h.rep(B, '        missing = missing_required_characters(requirements.get("required_characters", ""), g_keys, cfg["charset"])\n',
                      '        missing = []\n'), expect="exited 0 on the --masters path")
    # re-review code-a F002: the recorded W/thin/track are no longer compared with gen.js params()
    add("C7-params: the recorded master parameters are never compared with gen.js", ["test_build_refuses_a_masters_json_whose_parameters_differ_from_the_generator"],
        lambda: h.rep(B, "            check(masters[n].get(key) == gp[n].get(key),\n", "            check(True,\n"), expect="exited 0 although")
    # re-review code-a F003: the per-polygon length check removed AND the zips no longer strict (three
    # edits: with the check alone removed a strict zip raises, the build exits 1 on a traceback, and the
    # test fails on its message assertion instead of the exit code: survivor shape 1 of testing.md)
    add("zip-lengths: the per-polygon length check removed and every zip over the lists lenient", ["test_build_refuses_a_masters_json_with_a_polygon_record_missing"],
        lambda: (h.rep(B, "        check(len(set(lengths.values())) == 1, ", "        check(True, "),
                 h.rep(B, ", strict=True)", ")", count=3)), expect="exited 0 although")
    # C7: the stroke-width recomputation no longer refuses a stated figure that disagrees with the polygons
    add("C7-trust: the recomputed stroke width is never compared with the stated one", ["test_build_refuses_a_masters_json_that_overstates_its_stroke_width"],
        lambda: h.rep(B, "        check(abs(stated - recomputed) <= STROKE_WIDTH_TOLERANCE,\n", "        check(True,\n"),
        expect="exited 0 although")

    # --- the font-table decisions (FontBakery findings, 2026-11-16) ------------------------------------------------
    # Each mutation edits the code AND switches off the build's own self-check for that property, because the
    # self-check would refuse the build first and the test would never see the defect (survivor shape 1); the
    # config-edit ones (font.json drifts from the reviewed requirements) need no such second edit.
    no_statics = unless(h.static_dir is not None, "no statics ship (--static-dir none)")
    WEIGHT_LINE = '    os2.usWeightClass = instance_weight_class(group, inst["location"])\n'  # make_static: where a static's OS/2 is edited
    vm = req_roman.get("vertical_metrics")
    no_vm = unless(vm, "the requirements pin no vertical_metrics for the primary group")
    tables = req.get("tables") or {}
    names_fs = (req.get("names") or {}).get("fs_type")
    # hhea gets a line gap of 200 (the old typo gap) while typo keeps 0: the Mac line height grows 20 %
    add("vm-hhea-gap: hhea line gap 200, the two self-checks off", ["test_the_line_height_is_the_reviewed_one_on_every_platform"],
        lambda: (h.rep(B, 'lineGap=vs["hhea"][2])', 'lineGap=200)'),
                 cut(B, '    check(got == vs, f"vertical'),
                 cut(B, '    check(got["hhea"] == got["typo"] and', "must be equal with a line gap of 0\")\n")),
        roman, expect="hhea (", skip=no_vm)
    # typo descender one unit short while hhea is right: the hhea assertion passes, so only the typo one can fail
    add("vm-typo: OS/2 typo descender one unit off, the two self-checks off", ["test_the_line_height_is_the_reviewed_one_on_every_platform"],
        lambda: (h.rep(B, 'sTypoDescender=vs["typo"][1],', 'sTypoDescender=vs["typo"][1] - 1,'),
                 cut(B, '    check(got == vs, f"vertical'),
                 cut(B, '    check(got["hhea"] == got["typo"] and', "must be equal with a line gap of 0\")\n")),
        roman, expect="OS/2 typo (", skip=no_vm)
    # font.json grows a typo_metrics override the operator never reviewed: the build agrees with its config, the requirements do not
    add("vm-override: font.json typo_metrics override 100 units under the reviewed ascender", ["test_the_line_height_is_the_reviewed_one_on_every_platform"],
        lambda: h.jedit(F, lambda c: c.__setitem__("typo_metrics", {"ascender": vm["ascender"] - 100, "descender": vm["descender"]})), roman,
        expect=f"hhea ({vm['ascender'] - 100}" if vm else "hhea (", skip=no_vm)
    # USE_TYPO_METRICS never set (the held test is the style one; the build's two checks are off)
    add("use-typo: USE_TYPO_METRICS not set, the two self-checks off", ["test_style_metadata_matches_the_group"],
        lambda: (h.rep(B, "fs = FS_USE_TYPO | (FS_ITALIC if group[\"italic\"] else FS_REGULAR)", "fs = (FS_ITALIC if group[\"italic\"] else FS_REGULAR)"),
                 h.rep(B, '    check(bool(fs & FS_USE_TYPO), "USE_TYPO_METRICS must stay set")\n', ''),
                 h.rep(B, '    check(bool(fs & FS_USE_TYPO), "USE_TYPO_METRICS must be set")\n', '')),
        "all", expect="USE_TYPO_METRICS cleared")
    bad_fs = 4 if names_fs != 4 else 0
    add(f"fstype-code: OS/2 fsType forced to {bad_fs} in build.py, self-check off", ["test_fs_type_is_the_operators_embedding_decision"],
        lambda: (h.rep(B, 'fsType=cfg["names"]["fs_type"],', f'fsType={bad_fs},'),
                 cut(B, '    check(os2.fsType == cfg["names"]["fs_type"]')),
        "all", expect=f"fsType {bad_fs} is not the reviewed {names_fs}", skip=unless(names_fs is not None, "the requirements pin no names.fs_type"))
    # the operator's decision edited in font.json only: the build agrees with its config, the requirements do not
    add(f"fstype-config: font.json names.fs_type {bad_fs}", ["test_fs_type_is_the_operators_embedding_decision"],
        lambda: h.jedit(F, lambda c: c["names"].__setitem__("fs_type", bad_fs)), "all",
        expect=f"fsType {bad_fs} is not the reviewed {names_fs}", skip=unless(names_fs is not None, "the requirements pin no names.fs_type"))
    stat_off = '    check(stat.AxisValueCount > 0 and not uncovered'
    STAT_NAMES_CHECK = '    check(not stat_bad, f"STAT value names'
    add("stat-none: buildStatTable never called (STAT keeps varLib's axis records and no values), self-check off", ["test_stat_names_every_named_instance"],
        lambda: (h.rep(B, '    buildStatTable(vf, stat_axes(group), elidedFallbackName=style_names(cfg, group)["style"], windowsNames=True, macNames=False)\n', ''),
                 cut(B, stat_off), cut(B, STAT_NAMES_CHECK)), "all", expect="STAT has no axis values")
    add("stat-missing: the last value of every axis left out of STAT, self-check off", ["test_stat_names_every_named_instance"],
        lambda: (h.rep(B, '        axes.append({"tag": a["tag"], "name": a["name"], "ordering": order, "values": [',
                      '        values = values[:-1]\n        axes.append({"tag": a["tag"], "name": a["name"], "ordering": order, "values": ['),
                 cut(B, stat_off), cut(B, STAT_NAMES_CHECK)), "all", expect="STAT")
    has_700 = unless(any(loc.get("wght") == 700 for g in req["groups"].values() for loc in g["instances"].values()), "no named instance of any group sits at weight 700")
    heavy = lambda: h.rep(B, '\nWEIGHT_NAMES = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"',
                              '\nWEIGHT_NAMES = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Heavy"')  # noqa: E731
    # the build's own STAT-name self-check is cut for the font-suite mutations below, and left ON for the *-refused ones, which prove it refuses
    add("stat-name: the weight 700 is named Heavy, not Bold, self-check off", ["test_stat_names_every_named_instance"],
        lambda: (heavy(), cut(B, STAT_NAMES_CHECK)), "all", expect="'Heavy'", skip=has_700)
    add("stat-name-refused: the weight 700 is named Heavy, not Bold; the build must refuse", ["test_stat_names_every_named_instance"], heavy, "all",
        build_refused="STAT value names", skip=has_700)
    add("stat-elide: the default value is not marked elidable, self-check off", ["test_stat_names_every_named_instance"],
        lambda: (h.rep(B, '**({"flags": STAT_ELIDABLE} if v == a["default"] else {})', '**{}'), cut(B, STAT_NAMES_CHECK)), "all", expect="STAT")
    add("stat-elide-refused: the default value is not marked elidable; the build must refuse", ["test_stat_names_every_named_instance"],
        lambda: h.rep(B, '**({"flags": STAT_ELIDABLE} if v == a["default"] else {})', '**{}'), "all", build_refused="STAT value names")
    add("stat-fallback: the elided fallback name is always Regular, self-check off", ["test_stat_names_every_named_instance"],
        lambda: (h.rep(B, 'elidedFallbackName=style_names(cfg, group)["style"]', 'elidedFallbackName="Regular"'), cut(B, STAT_NAMES_CHECK)), italic or roman,
        expect="elided fallback 'Regular' is not 'Italic'", skip=unless(italic, "the project has no italic group"))
    add("stat-fallback-refused: the elided fallback name is always Regular; the build must refuse", ["test_stat_names_every_named_instance"],
        lambda: h.rep(B, 'elidedFallbackName=style_names(cfg, group)["style"]', 'elidedFallbackName="Regular"'), italic or roman,
        build_refused="STAT value names", skip=unless(italic, "the project has no italic group"))
    add("prep-missing: no prep table, self-check off", ["test_the_smart_dropout_program_pairs_with_gasp"],
        lambda: (h.rep(B, '    vf["prep"] = prep\n', ''),
                 h.rep(B, '    check("prep" in rt and bytes(rt["prep"].program.getBytecode()) == PREP_SMART_DROPOUT, "prep must be the smart-dropout program")\n', '')),
        "all", expect="no prep table", skip=unless(tables.get("prep_hex"), "the requirements pin no tables.prep_hex"))
    # SCANTYPE's operand moves from 4 to 5: the build's check compares with its own constant and agrees, the requirements' bytes do not
    add("prep-bytes: the smart-dropout program's SCANTYPE operand 4 -> 5", ["test_the_smart_dropout_program_pairs_with_gasp"],
        lambda: h.rep(B, "0xB0, 0x04, 0x8D", "0xB0, 0x05, 0x8D"), "all", expect="is not the reviewed B801FF85B0048D",
        skip=unless(tables.get("prep_hex") == "B801FF85B0048D", "the requirements pin another prep program"))
    add("prep-maxp: maxp.maxStackElements left at 0 beside a prep program", ["test_the_smart_dropout_program_pairs_with_gasp"],
        lambda: h.rep(B, '    vf["maxp"].maxStackElements = max(vf["maxp"].maxStackElements, 1)', '    pass'), "all",
        expect="does not count the prep program's stack", skip=unless(tables.get("prep_hex"), "the requirements pin no tables.prep_hex"))
    add("codepage: ulCodePageRange1 bit 0 becomes bit 1", ["test_the_code_page_and_name_platforms_are_the_reviewed_ones"],
        lambda: h.rep(B, "CODE_PAGE_LATIN1 = 0x1  #", "CODE_PAGE_LATIN1 = 0x2  #"), "all",
        expect=f"is not {tables.get('code_page_range1', 1):#x}", skip=unless("code_page_range1" in tables, "the requirements pin no tables.code_page_range1"))
    add("mac-names: the master name table keeps Macintosh records (mac=False dropped), self-check off", ["test_the_code_page_and_name_platforms_are_the_reviewed_ones"],
        lambda: (h.rep(B, 'sn["file_stem"]), mac=False)', 'sn["file_stem"]))'), cut(B, '    check(not mac, f"the name table carries Macintosh')),
        "all", expect="Macintosh name records for IDs", skip=unless("mac_names" in tables and not tables["mac_names"], "the requirements allow Macintosh names"))
    # statics: three properties the static writer could break on its own (each also needs its check_static line off)
    add("static-mac: the static writer's name table keeps Macintosh records, check off", ["test_static_instances_exist_and_match_the_variable_font"],
        lambda: (h.rep(B, 'f"{cfg[\'family\']} {style}", stem, stem), mac=False)', 'f"{cfg[\'family\']} {style}", stem, stem))'),
                 h.rep(B, '    check(not any(r.platformID == 1 for r in st["name"].names), f"{label}: Macintosh name records in the static")\n', '')),
        {"group": None, "static": True}, expect="Macintosh name records in a static", skip=no_statics)
    add("static-metrics: the static writer sets a typo line gap of 200, check off", ["test_static_instances_exist_and_match_the_variable_font"],
        lambda: (h.rep(B, WEIGHT_LINE, WEIGHT_LINE + "    os2.sTypoLineGap = 200\n"),
                 cut(B, '    check((st["hhea"].ascent', 'the line gap is not 0")\n')),
        {"group": None, "static": True}, expect="static line metrics differ", skip=no_statics or no_vm)
    add("static-fstype: the static writer sets another fsType, check off", ["test_static_instances_exist_and_match_the_variable_font"],
        lambda: (h.rep(B, WEIGHT_LINE, WEIGHT_LINE + f"    os2.fsType = {bad_fs}\n"),
                 cut(B, '    check(st["OS/2"].fsType == cfg["names"]["fs_type"]')),
        {"group": None, "static": True}, expect=f"static fsType {bad_fs}", skip=no_statics or unless(names_fs is not None, "no names.fs_type"))
    add("static-stat: the static writer keeps STAT (dangling name IDs), check off", ["test_static_instances_exist_and_match_the_variable_font"],
        lambda: (h.rep(B, '    if "STAT" in static:\n        del static["STAT"]\n', ''),
                 h.rep(B, 'for t in ("fvar", "gvar", "avar", "STAT"):', 'for t in ("fvar", "gvar", "avar"):')),
        {"group": None, "static": True}, expect="STAT table present in a static", skip=no_statics)

    if italic:
        # italic (F004): the italic group is built with italicAngle 0; the self-check that would refuse it is off
        add("italic-angle: post.italicAngle 0 for the italic group, self-check off", ["test_style_metadata_matches_the_group"],
            lambda: (h.rep(B, 'fb.setupPost(italicAngle=-group["_angle"] if group["italic"] else 0.0)', 'fb.setupPost(italicAngle=0.0)'),
                     h.rep(B, '        check(abs(rt["post"].italicAngle + group["_angle"]) < 1e-6, f"italic group: post.italicAngle '
                              '{rt[\'post\'].italicAngle} is not {-group[\'_angle\']}")\n', '')), italic, expect="post.italicAngle 0")
        # italic (F004): roman fsSelection bits on the italic group, self-check off
        add("italic-bits: italic group gets REGULAR instead of ITALIC, self-check off", ["test_style_metadata_matches_the_group"],
            lambda: (h.rep(B, 'fs = FS_USE_TYPO | (FS_ITALIC if group["italic"] else FS_REGULAR)', 'fs = FS_USE_TYPO | FS_REGULAR'),
                     h.rep(B, '        check(fs & FS_ITALIC and not fs & FS_REGULAR, f"italic group: fsSelection {fs:#x} must set ITALIC and clear REGULAR")\n',
                           '')), italic, expect="fsSelection 0x")
        # italic tick: the slant is never applied
        add("italic-tick: straight tick not slanted", ["test_the_italic_straight_tick_is_slanted"],
            lambda: h.rep(B, "        if slant:\n            o = [(x + slant * (y - TICK_MIDDLE), y) for x, y in o]\n", ""), italic,
            expect="is not right of its bottom")

    # statics (F012 of the plan): the writer clears OVERLAP_SIMPLE after instancing and its own check is off
    # (two edits: the check refuses the build first, as the font-level overlap mutation showed). All three
    # static mutations are SKIPPED under --static-dir none: nothing ships for them to break.
    add("static-overlap: OVERLAP_SIMPLE cleared in the static writer, check off", ["test_static_instances_exist_and_match_the_variable_font"],
        lambda: (h.rep(B, "    style = inst[\"name\"]\n    stem = static_file_stem(cfg, style)\n",
                       "    for gn in static.getGlyphOrder():\n        if static[\"glyf\"][gn].numberOfContours > 0:\n"
                       "            static[\"glyf\"][gn].flags[0] &= ~flagOverlapSimple\n    style = inst[\"name\"]\n    stem = static_file_stem(cfg, style)\n"),
                 h.rep(B, '            check(a.flags[0] & flagOverlapSimple and c.flags[0] & flagOverlapSimple, '
                          'f"{label} {gn}: OVERLAP_SIMPLE flag missing")\n', '')),
        {"group": None, "static": True}, expect="OVERLAP_SIMPLE missing", skip=no_statics)
    # statics: the weight class is wrong for every instance, check off (instancer sets it right by itself;
    # the explicit assignment in make_static is what a wrong value overrides)
    # the forced class must be one NO static has (it was 400, a no-op when every shipped static is already 400)
    shipped_weights = {loc["wght"] for g in req["groups"].values() for loc in g["instances"].values() if "wght" in loc}
    forced_weight = next((w for w in range(100, 1000, 100) if w not in shipped_weights), 1000)
    add(f"static-weight: usWeightClass forced to {forced_weight}, check off", ["test_static_instances_exist_and_match_the_variable_font"],
        lambda: (h.rep(B, '    os2.usWeightClass = instance_weight_class(group, inst["location"])\n', f'    os2.usWeightClass = {forced_weight}\n'),
                 h.rep(B, '    check(st["OS/2"].usWeightClass == instance_weight_class(group, inst["location"]), '
                          'f"{label}: usWeightClass {st[\'OS/2\'].usWeightClass}")\n', '')),
        {"group": None, "static": True}, expect=f"usWeightClass {forced_weight}",
        skip=no_statics or unless(shipped_weights, "no named instance has a wght coordinate, so no static's usWeightClass is held"))
    # statics: one instance file is missing (renamed away; the pristine copy comes back on restore)
    add("static-missing: one static woff2 renamed away", ["test_static_instances_exist_and_match_the_variable_font"],
        lambda: os.rename(h.static_dir / f"{fam}-{some_instance}.woff2", h.static_dir / f"{fam}-{some_instance}.woff2.moved"),
        expect=f"and {fam}-{some_instance}.woff2 in", skip=no_statics or unless(some_instance, "the primary group names no instance"))
    dsg = (req.get("names") or {}).get("designer")
    old_line = 'fb.setupNameTable(name_records(cfg, group, style, f"{cfg[\'family\']} {style}", stem, stem), mac=False)'
    new_line = ('fb.setupNameTable({**name_records(cfg, group, style, f"{cfg[\'family\']} {style}", stem, stem), '
                '"designer": cfg["names"]["manufacturer"]}, mac=False)')
    add("static-designer: only the static writer sets name ID 9 from the manufacturer, check off", ["test_static_instances_exist_and_match_the_variable_font"],
        lambda: (h.rep(B, old_line, new_line), cut(B, '    check(name.get(9) == cfg["names"]["designer"], f"{label}: name ID 9')),
        {"group": None, "static": True}, expect="static designer",
        skip=no_statics or unless(dsg and dsg != req["names"].get("manufacturer"), "no distinct designer pinned"))
    return M_


def run_one(h, m):
    """Apply, rebuild if asked, test, judge. Returns (verdict, detail, build note) before any restore."""
    build_note = ""
    try:
        m.apply()
    except AssertionError as exc:  # a mutation that did not apply is a harness defect, reported as such
        return "UNPROVEN", f"mutation did not apply: {exc}", build_note
    if m.rebuild:
        spec = m.rebuild if isinstance(m.rebuild, dict) else {"group": None if m.rebuild == "all" else m.rebuild}
        rc, last, stderr = h.build(spec.get("group"), spec.get("static", False), spec.get("extra", ()), spec.get("no_requirements", False))
        build_note = f"build rc={rc} {last}"
        changed = h.changed_artefacts()
        if m.build_refused is None:
            if rc != 0:
                return "UNPROVEN", f"the rebuild failed, so the tests would see the pristine files: {last}", build_note
            if not changed:
                return "UNPROVEN", "the rebuild exited 0 but every artefact is byte-identical to its pristine copy", build_note
            build_note += f" changed={changed[:4]}"
        else:
            if rc == 0:
                return "UNPROVEN", f"the build was expected to refuse with {m.build_refused!r} but exited 0", build_note
            if m.build_refused not in stderr:
                return "UNPROVEN", f"the build refused for another reason than {m.build_refused!r}: {last}", build_note
            if changed:
                return "UNPROVEN", f"the refused build still changed {changed[:4]}", build_note
            if not m.test_after_refusal:
                return "RED", f"build refused as declared: {last}", build_note
    rc, last, failed, errored, e_by_test = h.pytest(m.ids())
    verdict, detail = judge_tests(m, rc, failed, errored, e_by_test)
    if verdict == "GREEN":
        return "GREEN", last, build_note
    if verdict == "UNPROVEN":
        return "UNPROVEN", f"{detail}; {last}", build_note
    return "RED", f"{last} | {detail}", build_note


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--font", required=True)
    ap.add_argument("--requirements", required=True)
    ap.add_argument("--static-dir")
    ap.add_argument("--only", action="append", default=[], help="run the mutations whose name contains this (repeatable)")
    ap.add_argument("--list", action="store_true", help="print the mutations and their target tests, run nothing")
    args = ap.parse_args(argv)
    h = Harness(args.font, args.requirements, args.static_dir)
    M = mutations(h)
    if args.only:
        M = [m for m in M if any(o in m.name for o in args.only)]
        if not M:
            sys.exit(f"mutate.py: no mutation name contains {args.only}")
    if args.list:
        for m in M:
            proof = f"build_refused={m.build_refused!r}" if m.build_refused else f"expect={m.expect}"  # per test
            print(f"{m.name}\n    -> {', '.join(m.tests)}  rebuild={m.rebuild}  {proof}" + (f"\n    SKIPPED: {m.skip}" if m.skip else ""))
        return 0
    results, skipped = [], []
    for m in M:
        t0 = time.time()
        if m.skip:
            skipped.append(m.name)
            print(f"{'SKIPPED':8} | {m.name} | {m.skip} | nothing applied, nothing run", flush=True)
            continue
        verdict, detail, build_note = run_one(h, m)
        ok_restore, bad = h.restore()
        grc, glast, _, _, _ = h.pytest(m.ids())
        green_again = grc == 0
        results.append((m.name, verdict, ok_restore, green_again))
        restored = f"restored={ok_restore}" + ("" if ok_restore else f" {bad}")
        print(f"{verdict:8} | {m.name} | {detail} | {build_note} | {restored} green again={green_again} | {round(time.time() - t0)}s", flush=True)
    problems = [r for r in results if not (r[1] == "RED" and r[2] and r[3])]
    print(f"\n{len(results)} mutations, {sum(1 for r in results if r[1] == 'RED')} RED, {len(skipped)} skipped, {len(problems)} problem(s)")
    for name in skipped:
        print(f"SKIPPED: {name}")
    for name, verdict, ok_restore, green_again in problems:
        why = [w for w, bad in ((f"verdict {verdict}", verdict != "RED"), ("restore failed", not ok_restore), ("not green after restore", not green_again)) if bad]
        print(f"PROBLEM: {name}: {', '.join(why)}")
    shutil.rmtree(h.pristine)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
