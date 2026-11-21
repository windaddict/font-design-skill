"""build.py records which skill version built a face, and refuses to build when it cannot know.

WHAT IT'S FOR: a face folder carries no scripts, so the only record of which skill produced its woff2 files is the
manifest. `update-check.py` and `fetch-version.py` trust that record, so a build that wrote a wrong or empty one would
mislead both. These tests run the real build.py on a copy of the neutral face: one holds that the manifest carries
`skill_version` equal to the installed VERSION file and validates against `templates/manifest.schema.json`; the other
holds that a copy of `scripts/` with no VERSION above it refuses to build and writes nothing.
"""
import json
import pathlib
import shutil
import sys

import jsonschema
from conftest import REPO, run

NEUTRAL = REPO / "examples" / "neutral"
BUILD = REPO / "scripts" / "build.py"
SCHEMA = REPO / "templates" / "manifest.schema.json"


def neutral_copy(tmp_path):
    """A copy of the neutral face's inputs (font.json, concepts.js, requirements.json); returns the font.json path."""
    face = tmp_path / "face"
    face.mkdir()
    for name in ("font.json", "concepts.js", "requirements.json"):
        shutil.copyfile(NEUTRAL / name, face / name)
    return face / "font.json"


def test_the_manifest_records_the_skill_version_and_validates_against_its_schema(tmp_path):
    """Builds the roman group of the neutral face and reads the manifest back: `skill_version` equals the VERSION file, the schema
    string is still `font-design/manifest/v1`, and the manifest validates against the manifest schema, which must exist and be a
    valid schema. The expected version is read from the VERSION file by the test, not from the build. Weakest mutation to watch
    red: `skill_version` taken from a constant string instead of the file; the schema making `skill_version` required (the
    0.7.1-era manifest then fails to validate)."""
    out = tmp_path / "out"
    r = run([sys.executable, str(BUILD), "--font", str(neutral_copy(tmp_path)), "--group", "roman", "--out-dir", str(out)])
    assert r.returncode == 0, r.stderr[-1500:]
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    assert manifest.get("skill_version") == version, f"manifest records no skill_version equal to {version}: {manifest.get('skill_version')!r}"
    assert manifest["schema"] == "font-design/manifest/v1"
    assert SCHEMA.is_file(), f"{SCHEMA} does not exist"
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(manifest, schema)
    # A manifest built before 0.8.0 has no skill_version and must still validate: the key is optional in the schema.
    older = dict(manifest)
    del older["skill_version"]
    jsonschema.validate(older, schema)
    malformed = dict(manifest, skill_version="not-a-version")
    assert not jsonschema.Draft202012Validator(schema).is_valid(malformed), "the schema accepts a skill_version that is not N.N.N"
    # The contract the plan states: a later skill may add top-level keys and v1 readers stay valid, and every group entry carries
    # its axes, instances and masters (build.py writes all three).
    later = dict(manifest, a_key_added_later={"any": 1})
    assert jsonschema.Draft202012Validator(schema).is_valid(later), "the schema refuses an added top-level key"
    for key in ("axes", "instances", "masters"):
        groups = {g: {k: v for k, v in e.items() if k != key} for g, e in manifest["groups"].items()}
        assert not jsonschema.Draft202012Validator(schema).is_valid(dict(manifest, groups=groups)), f"the schema accepts a group without {key}"


def test_build_refuses_to_run_when_the_skills_version_file_is_missing(tmp_path):
    """`scripts/` copied to tmp/copy/scripts with no VERSION above it, as a person who copies only the scripts folder would have.
    The copy's build.py exits 1 naming VERSION and the path it looked at, and writes neither a manifest nor a woff2. Weakest
    mutation to watch red: a missing VERSION read as the string 'unknown' (the copy builds and exits 0)."""
    copy = tmp_path / "copy"
    shutil.copytree(REPO / "scripts", copy / "scripts", ignore=shutil.ignore_patterns("__pycache__", "tests", "*.pyc"))
    assert not (copy / "VERSION").exists()
    out = tmp_path / "o"
    r = run([sys.executable, str(copy / "scripts" / "build.py"), "--font", str(neutral_copy(tmp_path)), "--group", "roman", "--out-dir", str(out)])
    assert r.returncode == 1, f"build without VERSION: exit {r.returncode}, stderr {r.stderr[-600:]}"
    assert "VERSION" in r.stderr and str(pathlib.Path(copy / "VERSION")) in r.stderr, r.stderr[-600:]
    assert not (out / "manifest.json").exists() and not list(out.glob("*.woff2")), "a refused build wrote files"
