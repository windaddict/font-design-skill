"""Backward compatibility: the three example fonts still build to the digests 0.1.0 recorded.

WHAT IT'S FOR: every parameter added in 0.2 has a default under which the generator runs the original
expression, so a site that copies the new scripts over its old ones and rebuilds without touching its
concepts gets the same fonts. This is the first property to check after any edit of scripts/gen.js. It
compares three digests per example group (export JSON without branch records, the woff2 decompressed to
a TTF, the manifest without the source hashes, tool versions and brotli-dependent figures) with the ones
tests/fixtures/baseline-0.1.0.json recorded from the unmodified 0.1.0 code (commit 0fc4314). How the
digests are computed, and what each one proves, is in tests/baseline_digest.py.

Exact guarantee: the OUTLINES and TABLES these three configurations build, on the node major version recorded in the
fixture. The three digests are not woff2 bytes: the export digest covers the generator's coordinates, advances, kerns and
title widths; the TTF digest covers the woff2 after fontTools decompresses and re-serialises it; the manifest digest covers the
manifest without its source hashes, tool versions, woff2 sha256 and sizes, and output paths. Brotli compression is outside all
three, so "the same woff2 bytes" is a separate claim, held by `test_the_0_1_woff2_bytes_are_unchanged_for_the_recorded_brotli`
below, and only when this machine's brotli is the one that compressed the baseline (it skips naming both versions otherwise).
It does not prove a concept this repo does not ship still builds identically, and it cannot see
a change that only the new parameters reach. A node major version with no recorded digests FAILS (it never
skips for that): record it with baseline_digest.py --record after a `build.py --check` on a 0.1.0 checkout.

Watched red 2026-11-16 under the weakest mutation: in scripts/export.js, `adv: Math.round(g.adv)`
became `adv: Math.round(g.adv) + 1`, which changes every digest (the export digest first, the TTF
digest because the advances ship in hmtx). Also to be watched under a `hzThin` default of 0.999
(mutation `compat-default`, by hand): the item-3 work records that run in references/testing.md.
"""
import json

import baseline_digest as bd
import pytest


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """One build of the three examples, shared by the digest test and the woff2-bytes test (a build is about 20 seconds)."""
    return bd.compute(tmp_path_factory.mktemp("compat"))


def test_the_baseline_fixture_exists_and_covers_every_example_group():
    """A missing, malformed or partial fixture fails here instead of letting the comparison below pass
    on nothing. The five groups are the three examples' (neutral roman and italic, bract roman,
    driftwood roman and italic)."""
    data = bd.load_fixture()
    assert data["baseline_rev"] == "0fc4314", f"the baseline must come from the 0.1.0 commit, not {data['baseline_rev']}"
    want = {"neutral/roman", "neutral/italic", "bract/roman", "driftwood/roman", "driftwood/italic"}
    for major, rec in data["by_node_major"].items():
        assert set(rec["digests"]) == want, f"node {major}: groups {sorted(rec['digests'])}, expected {sorted(want)}"
        for g, d in rec["digests"].items():
            assert set(d) == {"export_sha256", "ttf_sha256", "manifest_sha256"} and all(len(v) == 64 for v in d.values()), f"{g}: {d}"


def test_the_0_1_examples_export_and_build_to_the_recorded_digests(built):
    """Builds every group of the three examples into a temporary directory and compares the three digests
    with the 0.1.0 record. A mismatch names the example group and the digest, which says where to look: the
    export digest moves with any coordinate, advance, kern or title width (the generator or exporter); the
    TTF digest with anything fontTools writes (the builder or an interpolation change); the manifest digest
    with a per-master figure, a name or a budget (a key added to the manifest also moves it)."""
    data = bd.load_fixture()
    major = bd.node_major()
    assert major in data["by_node_major"], (
        f"no digests recorded for node {major} (recorded: {sorted(data['by_node_major'])}); if this is a V8 "
        f"difference and not a regression, run `build.py --check` on a 0.1.0 checkout under this node, then "
        f"`python tests/baseline_digest.py --record --rev {data['baseline_rev']}` there")
    want = data["by_node_major"][major]["digests"]
    got = built["digests"]
    assert set(got) == set(want), f"groups built {sorted(got)}, recorded {sorted(want)}"
    bad = [f"{g}: {k} is {got[g][k][:12]}, recorded {want[g][k][:12]}" for g in sorted(want) for k in sorted(want[g]) if got[g][k] != want[g][k]]
    assert not bad, "the 0.1.0 examples no longer build to the recorded digests:\n  " + "\n  ".join(bad) + "\n" + json.dumps({"node": major})


def test_the_0_1_woff2_bytes_are_unchanged_for_the_recorded_brotli(built):
    """The raw woff2 bytes of the five groups equal the sha256 the 0.1.0 code produced on this node major version, when this machine's brotli
    is the one that compressed the baseline. Brotli output is not specified across versions, so with another brotli (or none recorded)
    the test SKIPS and names both versions: that is the one place this file skips, and it says why. The decoded-font digests above hold
    in every case. Watched red under `Math.round(g.adv) + 1` in export.js, like the digest test."""
    data = bd.load_fixture()
    major = bd.node_major()
    rec = data["by_node_major"].get(major)
    assert rec is not None, f"no digests recorded for node {major}"
    if rec.get("brotli") != bd.brotli_version():
        pytest.skip(f"the baseline woff2 bytes were compressed by brotli {rec.get('brotli')!r}; this machine has {bd.brotli_version()!r}")
    bad = [f"{g}: {built['woff2'][g][:12]}, recorded {rec['woff2'][g][:12]}" for g in sorted(rec["woff2"]) if built["woff2"].get(g) != rec["woff2"][g]]
    assert not bad, "woff2 bytes differ from the 0.1.0 baseline:\n  " + "\n  ".join(bad)
