"""A face's own skeleton override reaches every master, follows into derived glyphs, is hashed, and changes nothing without the key.

WHAT IT'S FOR: since 0.6.0 a font.json may name one JavaScript file, `skeletons`, a bare file name beside font.json, whose
function edits the generator's skeleton tables before anything is drawn (scripts/gen.js applySkeletons; the contract is
references/generator.md, "Per-face skeletons"). The first use is Bract's n, m, h and r, whose shoulder showed a nick where the
head serif meets the arch (docs/plan-skeleton-overrides.md, sections 0 and 4). These tests hold the mechanism with the real
scripts: export.js and build.py on copies of the examples, the node probe tests/skeleton_probe.js on the generator, and
build-page.js on a concept page (executed in Chrome where one is found). The plan's section 5 names each test a to g and the
mutation that must turn it red; references/testing.md section 8 records the runs.

FONT_DESIGN_SK_GEN names another scripts/ folder to test (a scratch copy carrying a mutation, or the 0.5.0 scripts to watch a
test fail before the code existed); unset, the real one. Every override fixture is under tests/fixtures/skeletons/.
"""
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest
from conftest import REPO, node, run

SCRIPTS = pathlib.Path(os.environ.get("FONT_DESIGN_SK_GEN", REPO / "scripts"))
GEN = SCRIPTS / "gen.js"
PROBE = REPO / "tests" / "skeleton_probe.js"
FIX = REPO / "tests" / "fixtures" / "skeletons"
NEUTRAL = REPO / "examples" / "neutral"
BRACT = REPO / "examples" / "bract"
FIVE_SOURCES = {"gen.js", "export.js", "build.py", "font.json", "concepts.js"}
GLYPH_FIELDS = ("adv", "polys", "raw", "runs", "keptIdx", "minw")
ACCENTED_A = ["á", "à", "â", "ä", "ā"]


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def probe(mode, *args):
    """Runs the probe; returns (CompletedProcess, parsed stdout or None)."""
    r = run([node(), str(PROBE), mode, str(GEN), *map(str, args)])
    return r, (json.loads(r.stdout) if r.returncode == 0 else None)


def neutral_project(dest, override=None):
    """The neutral example copied to dest; with an override, font.json is the fixture's (the neutral one plus the
    `skeletons` key) and the override is copied in as skeletons.js."""
    dest.mkdir(parents=True)
    for name in ("font.json", "concepts.js", "requirements.json"):
        shutil.copyfile(NEUTRAL / name, dest / name)
    if override:
        shutil.copyfile(FIX / "font.json", dest / "font.json")
        shutil.copyfile(FIX / override, dest / "skeletons.js")
    return dest


def bract_project(dest, override=None, key="skeletons.js"):
    """The bract example copied to dest; with an override, font.json gains `skeletons` and the file is copied in."""
    dest.mkdir(parents=True)
    shutil.copyfile(BRACT / "concepts.js", dest / "concepts.js")
    cfg = json.loads((BRACT / "font.json").read_text(encoding="utf-8"))
    if override:
        cfg["skeletons"] = key
        shutil.copyfile(FIX / override, dest / key)
    (dest / "font.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    return dest


def build(project, out, *extra):
    return run([sys.executable, str(SCRIPTS / "build.py"), "--font", str(project / "font.json"), "--out-dir", str(out),
                "--keep-masters", str(out / "keep" / "export.json"), *extra])


def export(project, out, group=None):
    cmd = [node(), str(SCRIPTS / "export.js"), "--font", str(project / "font.json")]
    if group:
        cmd += ["--group", group]
    return run(cmd + [str(out)])


def changed_glyphs(a, b):
    return sorted(k for k in a["glyphs"] if any(a["glyphs"][k][f] != b["glyphs"][k][f] for f in GLYPH_FIELDS))


# --- a: without the key nothing changes; with an empty override only its own record does ----------------------------------

@pytest.fixture(scope="module")
def neutral_pair(tmp_path_factory):
    """The neutral example built as it is (A) and from the fixture font.json naming empty.js (B), both groups, exports kept."""
    tmp = tmp_path_factory.mktemp("pair")
    out = {}
    for name, override in (("A", None), ("B", "empty.js")):
        proj = neutral_project(tmp / name / "proj", override)
        r = build(proj, tmp / name / "out")
        assert r.returncode == 0, f"{name}: build.py exited {r.returncode}:\n{r.stderr[-2000:]}"
        o = tmp / name / "out"
        out[name] = {"proj": proj, "out": o, "log": r.stderr, "manifest": json.loads((o / "manifest.json").read_text(encoding="utf-8")),
                     "exports": {g: json.loads((o / "keep" / f"export-{g}.json").read_text(encoding="utf-8")) for g in ("roman", "italic")},
                     "woff2": {p.name: p.read_bytes() for p in sorted(o.glob("*.woff2"))}}
    return out


def test_the_fixture_font_json_is_the_neutral_one_plus_the_key():
    """The fixture is meant to differ from examples/neutral/font.json by the key alone (and its comment), or test a's
    'exactly three manifest values' would be measuring a drift in the fixture."""
    fixture = json.loads((FIX / "font.json").read_text(encoding="utf-8"))
    neutral = json.loads((NEUTRAL / "font.json").read_text(encoding="utf-8"))
    assert fixture.pop("skeletons") == "skeletons.js"
    fixture.pop("$comment")
    neutral.pop("$comment")
    assert fixture == neutral


def test_a_font_json_without_the_key_builds_as_today(neutral_pair):
    """(i) The byte-for-byte proof is tests/test_backward_compat.py on the unchanged baseline fixture. Its export digest drops
    fields it does not know, so this test holds the record itself: without the key the export carries neither `skeletons` nor
    `skeletonsSha256`, the manifest has no `skeletons` key and hashes exactly the five sources it hashed in 0.5.0, and the build
    log names no override. Red under M3 (build.py writing "skeletons": null when the key is absent) and M4 (export.js writing
    skeletons: null when absent)."""
    A = neutral_pair["A"]
    for g, e in A["exports"].items():
        assert "skeletons" not in e and "skeletonsSha256" not in e, f"{g}: an export without the key carries an override record"
    assert "skeletons" not in A["manifest"], "a manifest without the key carries a skeletons entry"
    assert set(A["manifest"]["sources_sha256"]) == FIVE_SOURCES, sorted(A["manifest"]["sources_sha256"])
    assert not re.search(r"^skeletons ", A["log"], re.M), "the build log names an override although font.json names none"


def test_an_empty_override_changes_only_its_own_record(neutral_pair):
    """(ii) The same project with the key naming empty.js (a function that changes nothing): the woff2 bytes are equal (asserted
    on their own, so a change of glyph order cannot hide behind equal exports); each export, once its two override fields are
    deleted, equals the bare one; the fields are the name and the file's sha256; and the manifests differ in exactly three values,
    named: `skeletons` (absent, then the name), sources_sha256["skeletons.js"] (absent, then the file's sha256) and
    sources_sha256["font.json"] (the key changed the file). Red on the 0.5.0 scripts (no fields; the manifest ignores the key),
    under M2 (the rerun deleting and re-adding keys: the woff2 bytes differ) and M4' (an advance moved when the key is set). The
    plan's M4'' (font.json's hash kept from the previous manifest) cannot reach this test, whose builds have no previous manifest;
    test_the_override_is_hashed_and_check_sees_an_edit holds it."""
    A, B = neutral_pair["A"], neutral_pair["B"]
    assert A["woff2"] == B["woff2"], "an empty override changed the woff2 bytes"
    for g in ("roman", "italic"):
        b = dict(B["exports"][g])
        assert b.pop("skeletons", None) == "skeletons.js", f"{g}: the export does not name the override"
        assert b.pop("skeletonsSha256", None) == sha(FIX / "empty.js"), f"{g}: the export's skeletonsSha256 is not the file's"
        assert b == A["exports"][g], f"{g}: the export differs beyond its two override fields"
    ma, mb = A["manifest"], B["manifest"]
    diffs = {k for k in set(ma) | set(mb) if k not in ("sources_sha256", "tools") and ma.get(k) != mb.get(k)}
    sa, sb = ma["sources_sha256"], mb["sources_sha256"]
    diffs |= {f"sources_sha256.{k}" for k in set(sa) | set(sb) if sa.get(k) != sb.get(k)}
    assert diffs == {"skeletons", "sources_sha256.skeletons.js", "sources_sha256.font.json"}, sorted(diffs)
    assert mb["skeletons"] == "skeletons.js" and sb["skeletons.js"] == sha(FIX / "empty.js")
    assert sb["font.json"] == sha(B["proj"] / "font.json") and sa["font.json"] == sha(A["proj"] / "font.json")


# --- b: an override reaches every master and nothing else ------------------------------------------------------------------

@pytest.fixture(scope="module")
def bract_pair(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("bract")
    bare, over = bract_project(tmp / "bare"), bract_project(tmp / "over", "bract-shoulder.js")
    ra, rb = export(bare, tmp / "bare.json"), export(over, tmp / "over.json")
    assert ra.returncode == 0, ra.stderr[-1500:]
    assert rb.returncode == 0, rb.stderr[-1500:]
    return {"bare": json.loads((tmp / "bare.json").read_text()), "over": json.loads((tmp / "over.json").read_text()), "log": rb.stderr,
            "file": over / "skeletons.js"}


def test_an_override_reaches_every_master_and_nothing_else(bract_pair):
    """bract-shoulder.js (candidate B7) on a copy of examples/bract/font.json: in every master the glyphs whose outline, record or
    minimum width differ from the bare export are exactly h, m, n, r and n-tilde (through the rerun); no advance, title width or
    word space differs; every kern pair that differs does so by at most 1 unit (plan section 4.2: the n|n reference moves by
    hundredths); the stderr line names the four overrides and the re-derivation; the export's skeletonsSha256 is the file's.
    Red on the 0.5.0 scripts (the key is ignored: nothing changes), M5 (the override applied to a copy of the tables), M6 (the rerun
    skipped: n-tilde unchanged), M7 (the report built from reference equality: G n, edited in place, leaves the line) and M7' (the
    hash taken of concepts.js)."""
    bare, over = bract_pair["bare"], bract_pair["over"]
    for n in bare["masters"]:
        a, b = bare["masters"][n], over["masters"][n]
        assert changed_glyphs(a, b) == sorted(["h", "m", "n", "r", "ñ"]), f"{n}: changed {changed_glyphs(a, b)}"
        assert [k for k in a["glyphs"] if a["glyphs"][k]["adv"] != b["glyphs"][k]["adv"]] == [], f"{n}: an advance moved"
        assert a["titles"] == b["titles"] and a["space"] == b["space"], f"{n}: titles or the word space moved"
        ka, kb = {(p[0], p[1]): p[2] for p in a["kerns"]}, {(p[0], p[1]): p[2] for p in b["kerns"]}
        assert set(ka) == set(kb), f"{n}: the kern pair list changed"
        worst = max((abs(ka[p] - kb[p]) for p in ka), default=0)
        assert worst <= 1, f"{n}: a kern pair moved by {worst}"
    assert "skeletons skeletons.js: overrides G h, G m, G n, G r; re-derives G ñ" in bract_pair["log"], bract_pair["log"][-800:]
    assert over["skeletons"] == "skeletons.js" and over["skeletonsSha256"] == sha(bract_pair["file"])


def test_the_shoulder_probe_sees_the_nick_and_its_removal():
    """The plan's section 0 and 4.2 figures, restated from the committed probe on examples/bract/concepts.js (the skill's copy of
    Bract's parameters): before, the nick on n is 28.3 / 19.6 / 28.0 / 19.2 units at text x1, text x1.5, display x1, display x1.5;
    under bract-shoulder.js it is 4.0 / 0.2 / 4.6 / 1.5, with m and r at or under 5 and the arch's peak between 510 and 512.5 on n
    and m. The probe measures the drawn outline, so a fixture edited into a no-op leaves the nick at 28 and fails here."""
    masters = "text:1,text:1.5,display:1,display:1.5"
    r0, before = probe("shoulder", "-", BRACT / "concepts.js", masters)
    r1, after = probe("shoulder", FIX / "bract-shoulder.js", BRACT / "concepts.js", masters)
    assert r0.returncode == 0, r0.stderr
    assert r1.returncode == 0, r1.stderr
    want_before = {"text:1": 28.3, "text:1.5": 19.6, "display:1": 28.0, "display:1.5": 19.2}
    want_after = {"text:1": 4.0, "text:1.5": 0.2, "display:1": 4.6, "display:1.5": 1.5}
    for spec in want_before:
        assert round(before[f"{spec} n"]["nick"], 1) == want_before[spec], (spec, before[f"{spec} n"])
        assert round(after[f"{spec} n"]["nick"], 1) == want_after[spec], (spec, after[f"{spec} n"])
        for k in "mr":
            assert after[f"{spec} {k}"]["nick"] <= 5, (spec, k, after[f"{spec} {k}"])
        for k in "nm":
            assert 510 <= after[f"{spec} {k}"]["peak"] <= 512.5, (spec, k, after[f"{spec} {k}"])


# --- c: derived glyphs follow an overridden base; an override's own composite is kept --------------------------------------

@pytest.fixture(scope="module")
def drift():
    """driftwood-a-t.js and the bare tables, drawn on the neutral concepts (roman and italic, mult 1 and 1.5)."""
    keys = "a,á,à,â,ä,ā,ñ,©,í,n,t,A,Á"
    r, over = probe("draw", FIX / "driftwood-a-t.js", NEUTRAL / "concepts.js", keys)
    assert r.returncode == 0, r.stderr[-1500:]
    r, bare = probe("draw", "-", NEUTRAL / "concepts.js", keys)
    assert r.returncode == 0, r.stderr[-1500:]
    return over, bare


def aligned(g, n):
    """The first n polygons of a drawing, shifted so the first polygon's first point is at x 0 (a composite's sidebearing differs
    from its base's because the mark moves the glyph's left edge)."""
    dx = g["polys"][0][0][0]
    return [[[round(x - dx, 6), round(y, 6)] for x, y in p] for p in g["polys"][:n]]


def test_derived_glyphs_follow_an_overridden_base(drift):
    """The Driftwood trap (plan sections 2.4 and 2.7): driftwood-a-t.js edits G.a[1] and GI.a[1] in place, assigns n-tilde whole and
    edits the copyright's inner stroke in place. In the tables the accented a's of both G and GI start with the overridden a;
    drawn, roman and italic at mult 1 and 1.5, their base polygons equal the overridden a's and differ from the bare a's; n-tilde is
    the override's (three strokes, the last a level bar), not n plus a tilde; the copyright keeps its edit (authored, never
    re-derived); i-acute is unchanged (built on a literal dotless stem, not on i); the report lists n-tilde and the copyright under
    overridden and the ten accented a's under rederived; and the key order of G and GI is unchanged. Red on the 0.5.0 gen.js (no
    applySkeletons), under M8 (no rerun), M9 (the rerun ignoring the snapshot: n-tilde overwritten), M10 (the copyright registered
    as a derivation: its edit overwritten) and M10' (the rerun deleting and re-adding keys: the order moves)."""
    over, bare = drift
    # the registered derivations are exactly the plan's table (section 2.4): the accented letters built from a base, and not the
    # authored copyright, trade mark and bullet or the dotless-i accents (M10: the copyright registered; M1: N-tilde dropped)
    derived = {tuple(d.split(" ", 1)) for d in over["derived"]}
    want = {("G", k) for k in "šāéáóúàèòùâêôûäëöüñçÁÀÂÄÉÈÊËÍÏÓÔÖÚÜÑÇ"} | {("GI", k) for k in "āéáàâäèêëúùûüñ"}
    assert derived == want, (sorted(derived - want), sorted(want - derived))
    rep = over["report"]
    assert {"G a", "GI a", "G t", "G ñ", "G ©"} <= set(rep["overridden"]), rep
    assert set(rep["rederived"]) == {f"{t} {k}" for t in ("G", "GI") for k in ACCENTED_A}, rep
    assert over["before"] == over["after"], "the override moved the key order of G or GI"
    for t in ("G", "GI"):
        base = over["tables"][t]["a"]
        assert base != bare["tables"][t]["a"], f"{t}.a is unchanged: the fixture does not exercise the rerun"
        for k in ACCENTED_A:
            assert over["tables"][t][k][:len(base)] == base, f"{t} {k} does not start with the overridden a"
    for name, rec in over["drawings"].items():
        a = rec["a"]
        for k in ACCENTED_A:
            assert aligned(rec[k], len(a["polys"])) == aligned(a, len(a["polys"])), f"{name} {k}: its base is not the drawn a"
        assert aligned(a, len(a["polys"])) != aligned(bare["drawings"][name]["a"], len(a["polys"])), f"{name}: a drew as before"
        assert rec["í"] == bare["drawings"][name]["í"], f"{name}: i-acute changed"
    n_tilde = over["tables"]["G"]["ñ"]
    assert len(n_tilde) == 3 and n_tilde[2]["d"] == "M 150 650 L 400 650", n_tilde
    assert over["tables"]["G"]["©"][1]["d"].startswith("M 425 425 C 400 465 370 490 "), over["tables"]["G"]["©"][1]


# --- d: the italic falls back to the roman entry where GI has none; the accented capitals' limit ----------------------------

def test_a_roman_override_reaches_the_italic_where_gi_has_no_entry(drift, tmp_path):
    """driftwood-a-t.js also types t's stem start "s". GI has no t, so the italic draws the roman entry slanted: its first stroke
    takes a head serif through diagSerifPoly (serifA=diag) where the bare italic t's stem leaves as an exit (A=exit), and the roman
    t takes a head serif (serifA=head). The italic a is the GI override (its first stroke still ends in the italic exit), not the
    roman one. And the limit of plan section 2.2 (F009): an override of the italic capital A leaves the italic A-acute equal to
    the bare one (it is G's, slanted), while an override that assigns GI A-acute itself is drawn. Red on the 0.5.0 gen.js, under M11
    (the italic fallback reading a load-time copy of G), M12 (fn handed a copy of GI) and M12' (a rerun that builds italic accented
    capitals from GI.A)."""
    over, bare = drift
    for name, rec in over["drawings"].items():
        sig0 = rec["t"]["sig"][0]
        if name.endswith("i"):
            assert "serifA=diag" in sig0 and "A=serif" in sig0, f"{name}: italic t {sig0}"
            assert "A=exit" in bare["drawings"][name]["t"]["sig"][0], f"{name}: the bare italic t did not start as an exit"
            assert "B=exit" in rec["a"]["sig"][0], f"{name}: the italic a is not GI's (no exit stroke)"
        else:
            assert "serifA=head" in sig0, f"{name}: roman t {sig0}"
    assert over["tables"]["GI"]["a"][1]["d"].startswith("M 440 360 "), over["tables"]["GI"]["a"][1]
    r, cap = probe("draw", FIX / "italic-cap-a.js", NEUTRAL / "concepts.js", "A,Á")
    assert r.returncode == 0, r.stderr[-1500:]
    r, cap2 = probe("draw", FIX / "italic-cap-a-acute.js", NEUTRAL / "concepts.js", "A,Á")
    assert r.returncode == 0, r.stderr[-1500:]
    italics = [n for n in cap["drawings"] if n.endswith("i")]
    assert italics, "no italic drawing: the neutral concepts no longer map the x end"
    for name in italics:
        assert cap["drawings"][name]["A"] != bare["drawings"][name]["A"], f"{name}: the GI.A override did not draw"
        assert cap["drawings"][name]["Á"] == bare["drawings"][name]["Á"], f"{name}: italic A-acute followed GI.A (the documented limit moved)"
        assert cap2["drawings"][name]["Á"] != bare["drawings"][name]["Á"], f"{name}: an assigned GI A-acute was not drawn"
    assert cap["tables"]["GI"]["Á"] is None and cap2["tables"]["GI"]["Á"] is not None


# --- e: each guardrail refuses its input -----------------------------------------------------------------------------------

REFUSALS = [
    ("bad-not-function.js", "skeletons bad-not-function.js does not export a function"),
    ("bad-delete.js", 'skeletons bad-delete.js: G "n" was deleted'),
    ("bad-q.js", 'skeletons bad-q.js: G "n" stroke 1 its d holds "Q" where L or C was expected'),
    ("bad-stray.js", 'skeletons bad-stray.js: G "n" stroke 1 its d holds "x" where L or C was expected'),
    ("bad-c-five.js", 'skeletons bad-c-five.js: G "n" stroke 1 C needs 6 numbers and "L" is not one'),
    ("bad-no-m.js", 'skeletons bad-no-m.js: G "n" stroke 1 its d must start with M'),
    ("bad-m-alone.js", 'skeletons bad-m-alone.js: G "n" stroke 1 its d is an M with no L or C segment'),
    ("bad-end-z.js", 'skeletons bad-end-z.js: G "n" stroke 1 has end b "z"'),
    ("bad-dot-string.js", 'skeletons bad-dot-string.js: G "i" stroke 1 is a dot whose dot is not [x, y]'),
    ("bad-ring-rx0.js", 'skeletons bad-ring-rx0.js: G "o" stroke 0 is a ring whose rx and ry must be positive'),
    ("bad-ring-d.js", 'skeletons bad-ring-d.js: G "o" stroke 0 is a ring whose d is not what ring(290, 250, 210, 260) draws'),
    ("bad-empty-entry.js", 'skeletons bad-empty-entry.js: G "n" is not an array of at least one stroke'),
    ("bad-key-ab.js", 'skeletons bad-key-ab.js: G "ab" is a new key the cmap cannot map'),
    ("bad-gi-only.js", 'skeletons bad-gi-only.js: GI "@" is a new italic key with no G counterpart'),
    ("bad-key-astral.js", 'skeletons bad-key-astral.js: G "\U0001d49c" is a new key the cmap cannot map'),
    ("bad-key-surrogate.js", 'skeletons bad-key-surrogate.js: G "\\ud800" is a new key the cmap cannot map'),
    ("bad-dot-and-path.js", 'skeletons bad-dot-and-path.js: G "i" stroke 1 is a dot that also carries d, a or b'),
]


@pytest.mark.parametrize("fixture, message", REFUSALS, ids=[f for f, _ in REFUSALS])
def test_each_guardrail_refuses_its_input(fixture, message):
    """Each malformed override exits 1 with the message naming the file, the table and the key (and the stroke). One mutation per
    refusal, the check deleted, turns its case red (the input is then applied); for the Q case the validator replaced by
    sampleCounts (the revision-1 design) is the mutation that proves the validator is needed, since sampleCounts skips a token it
    does not know."""
    r, _ = probe("apply", FIX / fixture)
    assert r.returncode == 1, f"{fixture} was accepted: {r.stdout[:300]}"
    assert message in r.stderr, r.stderr


def test_a_drawing_cached_before_the_override_is_not_served_after_it():
    """applySkeletons resets the glyph cache. Today's callers (export.js, build-page.js) apply the override before
    the first draw, so no build reaches a stale entry, and the diff review's mutation that deleted the reset left
    every other test green. This test draws n, applies the override and draws n again in one process: the second
    drawing must be the override's."""
    r, out = probe("stale", FIX / "bract-shoulder.js", BRACT / "concepts.js", "n")
    assert r.returncode == 0, r.stderr
    assert "G n" in out["report"]["overridden"], out["report"]
    assert out["second"] != out["first"], "the glyph cache served n as drawn before the override"


def test_a_second_application_in_one_process_is_refused():
    """Two overrides in sequence would apply the second to tables the first already edited, with the first's derivations rebuilt
    from both. Red under the once-only mark dropped."""
    r, _ = probe("twice", FIX / "empty.js", FIX / "bract-shoulder.js")
    assert r.returncode == 1 and "skeletons bract-shoulder.js: skeletons already applied in this process" in r.stderr, (r.stdout, r.stderr)


def test_a_glyph_added_to_both_tables_exports_in_both_groups(tmp_path):
    """The accepted counterpart of bad-gi-only.js: adds-at-both.js adds @ to G and GI. Both groups' exports carry it, the italic
    drawing the GI entry (its outline differs from the roman one slanted, which is what the italic would draw from G)."""
    proj = neutral_project(tmp_path / "p", "adds-at-both.js")
    outs = {}
    for g in ("roman", "italic"):
        r = export(proj, tmp_path / f"{g}.json", g)
        assert r.returncode == 0, r.stderr[-1500:]
        assert "skeletons skeletons.js: adds G @, GI @" in r.stderr, r.stderr[-600:]
        outs[g] = json.loads((tmp_path / f"{g}.json").read_text())
    assert all("@" in m["glyphs"] for o in outs.values() for m in o["masters"].values())
    cfg = json.loads((proj / "font.json").read_text())
    cfg["skeletons"] = "roman-only.js"
    (proj / "roman-only.js").write_text((FIX / "adds-at-both.js").read_text().replace("  GI[\"@\"]", "  // GI[\"@\"]"))
    (proj / "font.json").write_text(json.dumps(cfg))
    r = export(proj, tmp_path / "italic-from-g.json", "italic")
    assert r.returncode == 0, r.stderr[-1500:]
    from_g = json.loads((tmp_path / "italic-from-g.json").read_text())
    assert from_g["masters"]["Regular"]["glyphs"]["@"]["polys"] != outs["italic"]["masters"]["Regular"]["glyphs"]["@"]["polys"]


KEY_REFUSALS = [
    ("missing.js", None, "font.json skeletons names no file", "font.json skeletons names no file"),
    ("skeletons.json", "empty.js", "font.json skeletons must name a .js file beside font.json", "font.json skeletons must name a .js file beside font.json"),
    ("sub/skeletons.js", "empty.js", "font.json skeletons must name a .js file beside font.json", "font.json skeletons must name a .js file beside font.json"),
    ("gen.js", "empty.js", None, "font.json skeletons may not take the name of a hashed source"),
]


@pytest.mark.parametrize("key, fixture, export_msg, build_msg", KEY_REFUSALS, ids=[k for k, *_ in KEY_REFUSALS])
def test_a_font_json_key_that_names_no_usable_file_is_refused(tmp_path, key, fixture, export_msg, build_msg):
    """A missing file, a .json file and a path with a directory part (review F008: the manifest keys sources by bare name) are
    refused by export.js and by build.py, and gen.js by build.py (it would collide with the generator's own manifest entry); the
    schema refuses the second and third too (tests/test_schemas_and_concepts.py)."""
    proj = neutral_project(tmp_path / "p")
    cfg = json.loads((proj / "font.json").read_text())
    cfg["skeletons"] = key
    (proj / "font.json").write_text(json.dumps(cfg))
    if fixture:
        (proj / key).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIX / fixture, proj / key)
    if export_msg:
        r = export(proj, tmp_path / "e.json", "roman")
        assert r.returncode == 1 and export_msg in r.stderr, r.stderr[-800:]
    r = build(proj, tmp_path / "out", "--group", "roman")
    # build.py's own refusal, before any export: export.js words two of these the same way, so a match anywhere in the log
    # would pass with build.py's check deleted (it then runs export.js, which refuses; two guards on one fixture)
    assert r.returncode == 1 and f"build.py: {build_msg}" in r.stderr and "export.js:" not in r.stderr and "export.js exited" not in r.stderr, r.stderr[-800:]


# --- f: the override is hashed; --check sees an edit; --masters refuses a stale export --------------------------------------

@pytest.fixture(scope="module")
def hashed(tmp_path_factory):
    """The fixture project (neutral plus bract-shoulder.js as skeletons.js), roman group, built with its export kept."""
    tmp = tmp_path_factory.mktemp("hashed")
    proj = neutral_project(tmp / "proj", "bract-shoulder.js")
    r = build(proj, tmp / "out", "--group", "roman")
    assert r.returncode == 0, r.stderr[-2000:]
    # with two groups in font.json, --keep-masters adds -<group> to the name even under --group
    return {"tmp": tmp, "proj": proj, "out": tmp / "out", "export": tmp / "out" / "keep" / "export-roman.json"}


def check_run(h, *extra):
    return run([sys.executable, str(SCRIPTS / "build.py"), "--font", str(h["proj"] / "font.json"), "--out-dir", str(h["out"]),
                "--group", "roman", "--check", *extra])


def test_the_override_is_hashed_and_check_sees_an_edit(hashed, tmp_path):
    """After the build, --check passes; the manifest names the override and hashes it beside the five sources; after one comment
    character is appended to the override, --check exits 1 naming sources_sha256. Red on the 0.5.0 scripts (no manifest entry),
    under M13 (the sources entry omitted: --check passes after the edit) and M14 (the hash taken of concepts.js)."""
    h = hashed
    m = json.loads((h["out"] / "manifest.json").read_text())
    assert m["skeletons"] == "skeletons.js"
    assert set(m["sources_sha256"]) == FIVE_SOURCES | {"skeletons.js"}
    assert m["sources_sha256"]["skeletons.js"] == sha(h["proj"] / "skeletons.js")
    r = check_run(h)
    assert r.returncode == 0, r.stderr[-1500:]
    original = (h["proj"] / "skeletons.js").read_bytes()
    try:
        (h["proj"] / "skeletons.js").write_bytes(original + b"//\n")
        r = check_run(h)
        assert r.returncode == 1, "--check passed after the override was edited"
        assert "manifest.sources_sha256:" in r.stderr, r.stderr[-1500:]
    finally:
        (h["proj"] / "skeletons.js").write_bytes(original)
    # font.json is hashed afresh on every build, not carried over from the manifest on disk: adding the key changes the file, and
    # --check must see a font.json edit (M4'': the previous manifest's font.json hash kept). Test a cannot see that mutation,
    # because its two builds write fresh --out-dir folders with no previous manifest.
    original = (h["proj"] / "font.json").read_bytes()
    try:
        (h["proj"] / "font.json").write_bytes(original + b"\n")
        r = check_run(h)
        assert r.returncode == 1 and "manifest.sources_sha256:" in r.stderr, "--check passed after font.json was edited"
    finally:
        (h["proj"] / "font.json").write_bytes(original)


def masters_run(proj, out, export_json):
    return run([sys.executable, str(SCRIPTS / "build.py"), "--font", str(proj / "font.json"), "--out-dir", str(out), "--group", "roman",
                "--masters", str(export_json)])


def test_a_masters_json_drawn_with_another_override_is_refused(hashed, tmp_path):
    """Review F002: build.py --masters reads only params() back from gen.js, so an export drawn before an override edit, or with no
    override, would have been built and recorded under the current file's hash. Now: the matching export builds; after one
    coordinate of the override is edited the same export exits 1 naming the recorded and the current sha256; an export made with no
    key fed to a font.json that names one exits 1 naming the disagreement, and the reverse. Red on the 0.5.0 scripts, under M14'
    (the comparison dropped) and M14'' (presence compared, the hash not)."""
    h = hashed
    r = masters_run(h["proj"], tmp_path / "ok", h["export"])
    assert r.returncode == 0, r.stderr[-1500:]
    edited = neutral_project(tmp_path / "edited", "bract-shoulder.js")
    text = (edited / "skeletons.js").read_text()
    (edited / "skeletons.js").write_text(text.replace("M 90 480 C 170 510", "M 90 481 C 170 510", 1))
    r = masters_run(edited, tmp_path / "o1", h["export"])
    assert r.returncode == 1, "a stale export built after the override was edited"
    assert sha(h["proj"] / "skeletons.js") in r.stderr and sha(edited / "skeletons.js") in r.stderr, r.stderr[-1500:]
    bare = neutral_project(tmp_path / "bare")
    r = masters_run(bare, tmp_path / "o2", h["export"])
    assert r.returncode == 1 and "skeletons 'skeletons.js' but font.json names None" in r.stderr, r.stderr[-1500:]
    rb = build(bare, tmp_path / "bare-out", "--group", "roman")
    assert rb.returncode == 0, rb.stderr[-1500:]
    r = masters_run(h["proj"], tmp_path / "o3", tmp_path / "bare-out" / "keep" / "export-roman.json")
    assert r.returncode == 1 and "skeletons None but font.json names 'skeletons.js'" in r.stderr, r.stderr[-1500:]


# --- g: build-page.js splices the override and the call -------------------------------------------------------------------

BUILD_PAGE = SCRIPTS / "concepts" / "build-page.js"
CONTENT = REPO / "scripts" / "concepts" / "content.minimal.json"
TOP = re.compile(r"^(?:var|function|let|const|class)\s+([A-Za-z_$][\w$]*)", re.M)


def page_build(out, *extra, template="round1", content=CONTENT):
    return run([node(), str(BUILD_PAGE), "--template", template, "--concepts", str(NEUTRAL / "concepts.js"), "--content", str(content),
                *map(str, extra), str(out)])


def splice_of(page, name):
    start = page.index(f"var SKELETONS = (function () {{ /* ---- skeletons: {name} ---- */")
    end = page.index("\n", page.index("data-fd-skeletons", start))
    return page[start:end]


def test_build_page_splices_the_override_and_the_call(tmp_path):
    """--skeletons bract-shoulder.js: exit 0; the page holds the wrapped override, the call and the data-fd-skeletons line once
    each, after gen.js and before concepts.js and render.js (the templates splice GEN, then CONCEPTS, then RENDER); the only
    top-level name the splice declares is SKELETONS; a page built without the flag holds none of the three. A file whose export
    block is malformed fails with stripExports's message; a bad-*.js fixture fails at build time with the guardrail's message (the
    override is applied in a child node first); an override declaring a top-level const DEG builds (wrapped, it clashes with
    nothing), while a template edited to declare SKELETONS is refused. Red before the flag existed (0.5.0's build-page.js
    took any --name VALUE and ignored an unknown one, so the page built without the splice), under M15 (the call without the
    splice), M16 (the splice after concepts.js), M17 (the call
    appended without the flag) and M17' (the wrapper dropped: the const DEG page is refused or throws)."""
    out = tmp_path / "with.html"
    r = page_build(out, "--skeletons", FIX / "bract-shoulder.js")
    assert r.returncode == 0, r.stderr
    page = out.read_text(encoding="utf-8")
    assert page.count("/* ---- skeletons: bract-shoulder.js ---- */") == 1
    assert page.count('applySkeletons(SKELETONS, "bract-shoulder.js")') == 1
    assert page.count("data-fd-skeletons") == 1
    at = page.index("/* ---- skeletons: bract-shoulder.js ---- */")
    assert page.index("/* ---- gen.js ---- */") < at < page.index("/* ---- concepts.js ---- */") and at < page.index("/* ---- render.js ---- */")
    assert set(TOP.findall(splice_of(page, "bract-shoulder.js"))) == {"SKELETONS"}
    r = page_build(tmp_path / "without.html")
    assert r.returncode == 0, r.stderr
    plain = (tmp_path / "without.html").read_text(encoding="utf-8")
    assert "/* ---- skeletons:" not in plain and "applySkeletons(SKELETONS" not in plain and "data-fd-skeletons" not in plain
    r = page_build(tmp_path / "x.html", "--skeletons", FIX / "bad-export-block.js")
    assert r.returncode == 1 and "the export block is not the last thing in the file" in r.stderr, r.stderr
    assert page.count('data-fd-override-sha256", "' + sha(FIX / "bract-shoulder.js") + '"') == 1, "the page does not record the override's sha256"
    assert "data-fd-override-sha256" not in plain
    r = page_build(tmp_path / "e.html", "--skeletons", FIX / "export-only.js")
    assert r.returncode == 1 and "must declare SKELETONS and export it" in r.stderr, r.stderr
    r = page_build(tmp_path / "v.html", "--skeletons", FIX / "conditional-var.js")
    assert r.returncode == 1 and "must declare SKELETONS and export it" in r.stderr, r.stderr
    r = page_build(tmp_path / "y.html", "--skeletons", FIX / "bad-q.js")
    assert r.returncode == 1 and 'skeletons bad-q.js: G "n" stroke 1 its d holds "Q"' in r.stderr, r.stderr
    assert not (tmp_path / "y.html").exists(), "a page was written for a refused override"
    r = page_build(tmp_path / "deg.html", "--skeletons", FIX / "const-deg.js")
    assert r.returncode == 0, r.stderr
    tpl = (REPO / "scripts" / "concepts" / "round1-template.html").read_text(encoding="utf-8")
    bad_tpl = tmp_path / "round1-skel.html"
    bad_tpl.write_text(tpl.replace("<script>", "<script>\nvar SKELETONS = 1;", 1), encoding="utf-8")
    r = page_build(tmp_path / "z.html", "--skeletons", FIX / "empty.js", template=str(bad_tpl))
    assert r.returncode == 1 and "SKELETONS" in r.stderr and "declare" in r.stderr, r.stderr


def find_chrome_or_none():
    sys.path.insert(0, str(REPO / "scripts"))
    import shoot
    try:
        return shoot.find_chrome()
    except FileNotFoundError:
        return None


@pytest.fixture(scope="module")
def served_site(tmp_path_factory):
    """A folder to serve concept pages from, with the built Sampler roman at fonts/Sampler-VF.woff2: the neutral content's
    comparison face, as smoke.sh step 8 serves it (an installed Georgia, content.minimal.json's comparison face, was missing on
    the Linux CI runner, and the page's own font probe then fails the shot)."""
    site = tmp_path_factory.mktemp("served")
    r = run([sys.executable, str(SCRIPTS / "build.py"), "--font", str(NEUTRAL / "font.json"), "--group", "roman", "--out-dir", str(site / "fonts")])
    assert r.returncode == 0, r.stderr[-1500:]
    return site


@pytest.mark.parametrize("fixture", ["bract-shoulder.js", "const-deg.js"])
def test_the_spliced_page_runs_the_override_in_chrome(tmp_path, fixture, request):
    """Review F006: parsing proves only syntax. Where Chrome is found, shoot.py --dump-dom executes the whole assembled page and the
    dumped <html> must carry data-fd-rendered > 0 (the page drew) and data-fd-skeletons equal to the override's keys (set only after
    applySkeletons returned in the browser). Without Chrome it skips naming the reason; scripts/smoke.sh step 8 (the CI chrome job)
    builds and shoots the same page, so the skip is never the only run. Red under M17' (the wrapper dropped: const DEG is declared
    twice and the script throws)."""
    chrome = find_chrome_or_none()
    if not chrome:
        pytest.skip("SKIPPED, NOT PASSED: no Chrome found (set $CHROME); scripts/smoke.sh --full step 8 shoots this page in CI")
    site = request.getfixturevalue("served_site")
    page = f"round1-{fixture.replace('.js', '')}.html"
    r = page_build(site / page, "--skeletons", FIX / fixture, content=NEUTRAL / "content.json")
    assert r.returncode == 0, r.stderr
    out = tmp_path / "shots"
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "shoot.py"), str(out), "--serve", str(site), "--pages", page,
                        "--widths", "500", "--scales", "1", "--bands", "none", "--dump-dom", "--family", "Sampler",
                        "--font-url", "/fonts/Sampler-VF.woff2"],
                       capture_output=True, text=True, timeout=240, env={**os.environ, "CHROME": chrome})
    assert r.returncode == 0, r.stderr[-2000:]
    sys.path.insert(0, str(REPO / "scripts"))
    import shoot
    doms = list(out.glob("*.dom.html"))
    assert len(doms) == 1, doms
    attrs = shoot.html_attrs(doms[0].read_text(encoding="utf-8"))
    assert int(attrs.get("data-fd-rendered", "0")) > 0, attrs
    want = "G h,G m,G n,G r" if fixture == "bract-shoulder.js" else "G n"
    assert attrs.get("data-fd-skeletons") == want, attrs
