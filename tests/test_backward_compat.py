"""Backward compatibility: the three example fonts still build to the digests the baseline commit recorded.

WHAT IT'S FOR: every parameter added in 0.2 has a default under which the generator runs the original
expression, so a site that copies the new scripts over its old ones and rebuilds without touching its
concepts gets the same fonts. This is the first property to check after any edit of scripts/gen.js. It
compares three digests per example group (export JSON without branch records, the woff2 decompressed to
a TTF, the manifest without the source hashes, tool versions and brotli-dependent figures) with the ones
tests/fixtures/baseline.json recorded from the unmodified code of the baseline commit (BASELINE_REV below: 0.1.0's
0fc4314 from 0.2 to 0.4; since 0.5.0 the commit that redrew the R's leg root, the one deliberate departure, whose
`supersedes` entry in the fixture names the 0.1.0 record and the test that proves every other glyph stayed:
tests/test_r_leg_join.py::test_only_the_r_changed_since_0_4_0). How the
digests are computed, and what each one proves, is in tests/baseline_digest.py.

Exact guarantee: the OUTLINES and TABLES these three configurations build, on the platform AND node major version recorded in
the fixture (`darwin/26`, `linux/22`: floating-point output depends on both, as the first Linux CI run showed; the promise is per
platform and node). The three digests are not woff2 bytes: the export digest covers the generator's coordinates, advances, kerns and
title widths; the TTF digest covers the woff2 after fontTools decompresses and re-serialises it; the manifest digest covers the
manifest without its source hashes, tool versions, woff2 sha256 and sizes, and output paths. Brotli compression is outside all
three, so "the same woff2 bytes" is a separate claim, held by `test_the_0_1_woff2_bytes_are_unchanged_for_the_recorded_brotli`
below, and only when this machine's brotli is the one that compressed the baseline (it skips naming both versions otherwise).
It does not prove a concept this repo does not ship still builds identically, and it cannot see
a change that only the new parameters reach. Nor does it re-verify that the fixture's digests came from BASELINE_REV's scripts: the
script-identity guard runs in baseline_digest.py at --record time only, so this file checks the revision's shape and the digests'
agreement, and a fixture written by hand or from --print with a pasted revision would pass it; the recording path is what ties the
record to the commit (review of the 0.5.0 diff, F008). A platform/node with no recorded digests FAILS (it never
skips for that) and prints how to record it from the baseline commit's code (baseline_digest.py --record, or the record-baseline workflow on Linux).

Watched red 2026-11-16 under the weakest mutation: in scripts/export.js, `adv: Math.round(g.adv)`
became `adv: Math.round(g.adv) + 1`, which changes every digest (the export digest first, the TTF
digest because the advances ship in hmtx). Also to be watched under a `hzThin` default of 0.999
(mutation `compat-default`, by hand): the item-3 work records that run in references/testing.md.
"""
import json
import re

import baseline_digest as bd
import pytest

# the commit whose unmodified scripts produced the fixture; a full or abbreviated git sha, never a placeholder, so a
# fixture written before its commit existed cannot pass (docs/plan-r-leg.md section 6.1 records the two-commit order)
BASELINE_REV = "COMMIT_A"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """One build of the three examples, shared by the digest test and the woff2-bytes test (a build is about 20 seconds)."""
    return bd.compute(tmp_path_factory.mktemp("compat"))


def test_the_baseline_fixture_exists_and_covers_every_example_group():
    """A missing, malformed or partial fixture fails here instead of letting the comparison below pass
    on nothing. The five groups are the three examples' (neutral roman and italic, bract roman,
    driftwood roman and italic)."""
    data = bd.load_fixture()
    assert re.fullmatch(r"[0-9a-f]{7,40}", BASELINE_REV), f"BASELINE_REV is {BASELINE_REV!r}, not a git sha: the baseline commit has not been recorded yet"
    assert data["baseline_rev"] == BASELINE_REV, f"the baseline must come from {BASELINE_REV}, not {data['baseline_rev']}"
    assert data.get("baseline_version") and data.get("supersedes"), "the fixture must say which version it records and what it superseded"
    want = {"neutral/roman", "neutral/italic", "bract/roman", "driftwood/roman", "driftwood/italic"}
    for key, rec in data["by_platform_node"].items():
        assert re.fullmatch(r"[a-z0-9]+/\d+", key), f"{key!r} is not a platform/node-major key"
        assert set(rec["digests"]) == want, f"{key}: groups {sorted(rec['digests'])}, expected {sorted(want)}"
        for g, d in rec["digests"].items():
            assert set(d) == {"export_sha256", "ttf_sha256", "manifest_sha256"} and all(len(v) == 64 for v in d.values()), f"{g}: {d}"


def test_the_0_1_examples_export_and_build_to_the_recorded_digests(built):
    """Builds every group of the three examples into a temporary directory and compares the three digests
    with the baseline record for THIS platform and node major version. A mismatch names the example group and the digest, which says where to
    look: the export digest moves with any coordinate, advance, kern or title width (the generator or exporter); the
    TTF digest with anything fontTools writes (the builder or an interpolation change); the manifest digest
    with a per-master figure, a name or a budget (a key added to the manifest also moves it). A platform/node that is not recorded fails
    with the instructions to record it."""
    data = bd.load_fixture()
    key = bd.platform_key()
    status, message = bd.judge(data, key, built["digests"])
    assert status == "ok", (message if status == "unrecorded" else f"the examples no longer build to the baseline digests for {key}:\n  {message}")


def crafted(**keys):
    """A fixture dict with a record for each key given as {group: digest letter}, for the keying tests below."""
    def rec(letter):
        return {"digests": {"neutral/roman": {"export_sha256": letter * 64, "ttf_sha256": letter * 64, "manifest_sha256": letter * 64}}}
    return {"schema": bd.SCHEMA, "baseline_rev": BASELINE_REV, "by_platform_node": {k.replace("_", "/"): rec(v) for k, v in keys.items()}}


def digests(letter):
    return {"neutral/roman": {"export_sha256": letter * 64, "ttf_sha256": letter * 64, "manifest_sha256": letter * 64}}


def test_an_unrecorded_platform_fails_with_the_recording_instructions():
    """The keying is platform AND node major: a record for darwin/22 does not stand in for linux/22 (the first Linux CI run showed the digests
    differ between operating systems under one node major). `judge` on a fixture that has darwin/22 only, asked for linux/22, reports
    `unrecorded` and names the platform, the recorded keys and both ways to record it. Watched red under a lookup that ignores the platform
    (it would answer `ok` from the darwin record)."""
    status, message = bd.judge(crafted(darwin_22="a"), "linux/22", digests("a"))
    assert status == "unrecorded", f"a darwin record answered for linux: {status}"
    for needle in ("linux/22", "darwin/22", "record-baseline", f"--record --rev {BASELINE_REV}", "--merge"):
        assert needle in message, f"the instructions do not mention {needle!r}: {message}"


def test_a_recorded_platform_whose_digest_differs_fails_naming_it():
    """A record exists for the platform and node, and the fresh digest differs: `differs`, naming the group and the digest. And an equal
    digest is `ok`. Watched red under a comparison that skips the manifest digest."""
    data = crafted(linux_22="a")
    assert bd.judge(data, "linux/22", digests("a")) == ("ok", "")
    got = digests("a")
    got["neutral/roman"]["manifest_sha256"] = "b" * 64
    status, message = bd.judge(data, "linux/22", got)
    assert status == "differs" and "neutral/roman: manifest_sha256 is bbbbbbbbbbbb, recorded aaaaaaaaaaaa" in message, f"{status}: {message}"


def test_the_0_1_woff2_bytes_are_unchanged_for_the_recorded_brotli(built):
    """The raw woff2 bytes of the five groups equal the sha256 the baseline commit's code produced on this platform and node major version, when this machine's brotli
    is the one that compressed the baseline. Brotli output is not specified across versions, so with another brotli (or none recorded)
    the test SKIPS and names both versions: that is the one place this file skips, and it says why. The decoded-font digests above hold
    in every case. Watched red under `Math.round(g.adv) + 1` in export.js, like the digest test."""
    data = bd.load_fixture()
    key = bd.platform_key()
    rec = data["by_platform_node"].get(key)
    assert rec is not None, bd.record_instructions(data, key)
    if rec.get("brotli") != bd.brotli_version():
        pytest.skip(f"the baseline woff2 bytes were compressed by brotli {rec.get('brotli')!r}; this machine has {bd.brotli_version()!r}")
    bad = [f"{g}: {built['woff2'][g][:12]}, recorded {rec['woff2'][g][:12]}" for g in sorted(rec["woff2"]) if built["woff2"].get(g) != rec["woff2"][g]]
    assert not bad, "woff2 bytes differ from the baseline:\n  " + "\n  ".join(bad)


def test_merging_adds_one_platform_entry_and_refuses_a_head_entry(tmp_path, monkeypatch):
    """The Linux recording path: `record-baseline` uploads one entry per node major version, and `--merge` adds it under its `platform/node`
    key without touching the others. An entry written by `--print` (the CURRENT branch's digests, no baseline revision) must never be merged:
    it would make the baseline describe 0.2 itself. Watched red under a merge that accepts a null revision."""
    fixture = tmp_path / "baseline.json"
    monkeypatch.setattr(bd, "FIXTURE", fixture)
    base = crafted(darwin_22="a")
    fixture.write_text(json.dumps(base))
    record = crafted(x_y="b")["by_platform_node"]["x/y"]
    good = {"schema": bd.ENTRY_SCHEMA, "key": "linux/22", "baseline_rev": BASELINE_REV, "node": "v22.0.0", "record": record}
    (tmp_path / "good.json").write_text(json.dumps(good))
    bd.merge_entries([tmp_path / "good.json"])
    merged = json.loads(fixture.read_text())["by_platform_node"]
    assert sorted(merged) == ["darwin/22", "linux/22"] and merged["darwin/22"] == base["by_platform_node"]["darwin/22"], sorted(merged)
    head = dict(good, baseline_rev=None, key="linux/20")
    (tmp_path / "head.json").write_text(json.dumps(head))
    with pytest.raises(SystemExit):
        bd.merge_entries([tmp_path / "head.json"])
    assert "linux/20" not in json.loads(fixture.read_text())["by_platform_node"], "a head entry was merged into the baseline"
    # and with no fixture yet (so the revision check against an existing record cannot be what refuses it)
    monkeypatch.setattr(bd, "FIXTURE", tmp_path / "fresh.json")
    with pytest.raises(SystemExit):
        bd.merge_entries([tmp_path / "head.json"])
    assert not (tmp_path / "fresh.json").exists(), "a head entry created a baseline"
