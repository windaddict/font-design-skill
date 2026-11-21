# Plan: the face-folder contract (skill 0.8.0)

Request: the operator request for the face-folder contract. Repository: the font-design skill,
worktree branch `feature/face-folder`, base `main` at 852fd96 (VERSION 0.7.1, no git tags exist, local or remote:
`git tag -l` and `git ls-remote --tags origin` both print nothing, checked 2026-11-20).

Every path in this document is relative to the repository root. Every command is typed from the repository root
with the repo venv, `.venv/bin/python3` (Python 3.12.16 there; the system `python3` is 3.9 and must not be used).

## 0. Reasoning: what the feature is, in this repository's terms

The sites today carry the skill as a submodule and a copy of `scripts/`; the skill's docs (SKILL.md Phase 7 step 1,
`references/process.md` section 7, `references/testing.md` sections 1 and 7, `scripts/tests/conftest.py`'s header,
`tests/test_copy_into_site.py`) all describe that copy. This run turns the design around: a **face folder** holds
only the face (`font.json`, `concepts.js`, `requirements.json`, optionally `skeletons.js`, and the build output the
manifest hashes), and every skill command runs from wherever the skill is installed, taking the path to `font.json`.
Three new mechanisms make the folder self-describing:

1. **The manifest records the skill version.** `scripts/build.py` writes one new top-level key,
   `skill_version`, read from `<skill folder>/VERSION` (the folder above `scripts/`, so the skill finds its own
   file relative to its own location). Existing keys stay as they are; the schema string stays
   `font-design/manifest/v1` because a reader of v1 is not broken by one added key. A `build.py` whose folder has
   no `VERSION` refuses to build, naming the path: nothing is built with an unknown version.
   Consequence for this repository: `tests/baseline_digest.py` drops the new key from the manifest digest the
   way it drops `tools`, because the 0.7.0 baseline (`tests/fixtures/baseline.json`, BASELINE_REV c5b4abb) was
   recorded without it and the key changes on every release by definition; the woff2 bytes and the other two
   digests are untouched, which is the proof that no font output changes.
2. **`scripts/fetch-version.py VERSION DIR`** materialises the skill's own code at a released version into
   `DIR`: from a git checkout by `git -C <skill folder> archive v<VERSION>`; otherwise, or when that fails, by
   downloading `https://github.com/windaddict/font-design-skill/archive/refs/tags/v<VERSION>.tar.gz`
   (`--archive-url URL` overrides the whole URL; `file://` URLs work, which is how the tests stay offline).
   Whatever the route, the code is extracted into a temporary folder beside `DIR` and moved to `DIR` only after
   its `VERSION` reads exactly `VERSION`; on any failure the temporary folder is removed, `DIR` is not created, and
   the script exits 1 saying what each route reported. Version `0.6.0` is refused before either route is tried
   (decision "The 0.6.0 refusal" below). The old code then runs with the installed venv:
   `.venv/bin/python3 DIR/scripts/build.py --font <face>/font.json --out-dir <tmp>`.
3. **`scripts/update-check.py OUT --font font.json`** compares the recorded `skill_version` (or `--recorded
   VERSION`, for a face built before 0.8.0) with the installed `VERSION`. Equal: it prints that and writes
   nothing. Different: it first runs the drift check (decision "The drift check" below), then rebuilds the face with the INSTALLED
   skill into a temporary folder
   (`build.py --out-dir`, the face's `requirements` setting from the manifest passed through), gathers the shipped
   group files into a temporary "before" folder by file name, runs `scripts/diff.py` on the pair and writes
   `OUT/update.md` and `OUT/update.json` (the versions, per group the by-value differences or "no difference by
   value", the render summary, and the build command that adopts the new version). Exit 0 when nothing differs,
   3 when something does, 1 on an error. It never writes into the face folder: the operator approves by running
   `build.py` themselves.

The by-value comparison is a site's own comparison tool for two builds of a variable font (read in this session,
430 lines), folded into `scripts/diff.py` as a second section beside the pixel renders: glyph order and cmap
(every subtable, format 14 included), per common glyph the default outline with its instructions, every gvar tuple
and the hmtx record, the instanced outline and advance at every named instance of the group (generalised from the
tool's fixed `wght,opsz` pair to the group's own axes, read from `font.json`), `fvar`/`avar`/`STAT`/`GSUB`/`gasp`/
`prep`/`fpgm`/`cvt ` as ttx text, `maxp` hinting limits, GPOS pair adjustments by resolved value and the
script/feature/lookup structure, GDEF classes, HVAR advance deltas by region, the platform-3 name records, `hhea`,
`OS/2` and `head` (without `checkSumAdjustment` and `modified`) field by field, and kerning as HarfBuzz
(`uharfbuzz`, already pinned in `requirements.txt`) applies it to every two-character string of the characters both
fonts map, at every named instance. The tool's two allowances (`--allow-extra-glyph`, `--allow-os2`) are NOT
carried over: they served one site migration, and the update check lists every difference for the operator to
judge; fewer flags is the request's item 9. The fold's docstring is written neutral: no site name, hostname or
path (`tests/test_hygiene.py`).

Issue #17 is fixed in the same file: `--before DIR` and `--after DIR` hold each group's file under its FILE NAME
(`build.py`'s own name, or the name part of the group's `file` key, which is exactly what `build.py --out-dir`
writes), so a `file` such as `../../static-pages/fonts/face/F-VF.woff2` no longer walks out of `DIR`. When
`--after` is omitted the after side is the shipped files where `font.json` puts them (`specimen.default_font_file`,
resolved), which is what the design-review loop and the update check both need. Two groups whose files share a
name are refused (exit 2, both groups named), the rule `build.py` already applies under `--out-dir`.

Decisions the plan makes where the request left room:

- The version is recorded in `manifest.json`, not in a new file: it is already the record of a build, already
  tracked, and already compared by `build.py --check`.
- A manifest schema IS added (`templates/manifest.schema.json`, `$id` `font-design/manifest/v1`), covering the
  top-level keys with `skill_version` optional (absent before 0.8.0; plan review F003) and `additionalProperties: true` for the per-group entries, so the
  face-folder contract has one machine-checkable document and the pattern of `templates/font.schema.json` is kept.
  Scripts do not validate against it (`jsonschema` is a dev dependency); the repo test does.
- The tag for a backfilled version goes on the FIRST commit on `main` whose `VERSION` reads that version, found
  with `git log --first-parent origin/main` and `git merge-base --is-ancestor` on 2026-11-20:

  | tag | commit | note |
  |---|---|---|
  | v0.1.0 | 0fc4314 | the first commit |
  | v0.2.0 | 183560f | merge of PR #2; the later 0.2.0 commit 3c4e8d9 (PR #4, lint) changed none of gen.js, export.js, build.py (`git diff --stat 183560f 3c4e8d9 -- scripts/gen.js scripts/export.js scripts/build.py` is empty) |
  | v0.3.0 | 7cbb3e4 | merge of PR #5 |
  | v0.3.1 | 4538c4c | merge of PR #6 (kerning `sparse_cap`) |
  | v0.4.0 | 598044b | merge of PR #8 |
  | v0.5.0 | 5d0b29f | merge of PR #11 |
  | v0.6.0 | 1c032ad | merge of PR #13. **Could not be placed uniquely:** c5b4abb (on the 0.7.0 branch) also set VERSION to 0.6.0 and its gen.js and export.js differ from 1c032ad's (192 and 28 lines); it reached main only inside 0.7.0 (aa4b9ae), so it gets no tag and the CHANGELOG note says so. This is the case the version-discipline rule forbids from now on; `fetch-version.py` refuses 0.6.0 and `update-check.py` prints the 0.6.0 notice (`scripts/versions.py`) |
  | v0.7.0 | aa4b9ae | merge of PR #14 |
  | v0.7.1 | b09faa9 | merge of PR #15; the later 0.7.1 commits 47ce908 and 852fd96 (CI, CLAUDE.md) changed none of the three font sources (`git diff --stat b09faa9 852fd96 -- scripts/gen.js scripts/export.js scripts/build.py` is empty) |
  | v0.8.0 | the merge commit of this branch | created by the operator after the merge (live-acceptance `tags-push`) |

  Local tags are created by the build agent (item `release-0-8-0`); pushing them needs the GitHub remote and is
  the operator's step.
- Item 8 of the request (the font suite is a skill operation): `scripts/tests/test_font.py` and `mutate.py` keep
  living in the skill and run from it against any face folder; `scripts/tests/test_site_wiring.py.tmpl` stays the
  site's file. No test code moves; the template header, SKILL.md, `references/testing.md` and the suite's
  `conftest.py` header say so, and `tests/test_copy_into_site.py` is rewritten as the suite running FROM THE SKILL
  on a face folder inside a sample site.
- The font suite's conftest keeps `--scripts=DIR` / `FD_SCRIPTS`: unchanged behaviour, reworded help.
- `scripts/check-env.py` is not changed; the installed version is `VERSION`.
- **The 0.6.0 refusal** (operator ruling, 2026-11-20, on the plan review's escalation of F001). Version 0.6.0 names
  two different font sources (the table above): the tag `v0.6.0` is 1c032ad, but the unreleased c5b4abb code also set
  `VERSION` to 0.6.0, and a face it built cannot be rebuilt from that tag. A new stdlib-only `scripts/versions.py`
  holds `AMBIGUOUS_VERSIONS = {"0.6.0": <text>}` and `ambiguity_notice(version) -> str | None`; the text says
  "0.6.0 is ambiguous: tag v0.6.0 is commit 1c032ad, and the unreleased code at c5b4abb records the same version".
  `fetch-version.py 0.6.0` REFUSES: before trying either route it prints the notice to stderr, adds "fetch-version.py
  will not choose between them; get the code that built your face by hand from a git checkout of the skill:
  `git -C <skill folder> archive 1c032ad` or `... archive c5b4abb`, extracted into DIR", exits 1 and writes nothing.
  There is NO flag to pick a commit: the ruling chose a refusal over a new mechanism (request item 9), and no face in
  use records 0.6.0 (both sites pin a 0.7.1 commit, and manifests record no `skill_version` before 0.8.0, so 0.6.0
  can only arrive through `--recorded 0.6.0` typed by hand). `update-check.py` does not fetch the recorded version
  (it compares the SHIPPED files with an installed rebuild), so it does not refuse: it prints the notice to stderr and
  writes it into `update.md` (a `## Notice` section) and `update.json["notices"]` whenever the recorded version is
  ambiguous. `references/face-folder.md` documents both in its version-record section.
- **The drift check** (verified finding F003). Before comparing, `update-check.py` checks that what ships is what the
  manifest records, because otherwise an edited font or input is reported as the effect of the skill update. Per
  group it hashes the shipped woff2 and compares with `manifest["groups"][g]["woff2_sha256"]`; it hashes `font.json`,
  `concepts.js` and the `skeletons` file (when `font.json` names one) and compares with the matching keys of
  `manifest["sources_sha256"]` (`font.json`, `concepts.js`, the skeletons file's name). The manifest holds no hash of
  the requirements file, so that input is not checked, and the report says so. A missing shipped woff2 exits 1 naming
  it. A mismatch is not an error: it is labelled drift. `update.md` gets a `## Drift` section above `## By value`
  that names each file and both hashes' first 12 characters and says "these differences cannot be attributed to the
  skill update"; `update.json["drift"]` lists `{"file", "recorded", "found"}`; the run still compares and the exit is 3.
  **The exact guarantee of a clean drift check** (verified finding F001): it proves manifest consistency only, that the
  shipped files hash to what `manifest.json` says. The manifest is an editable file, so a font changed together with
  its recorded `woff2_sha256` passes. It does NOT prove the shipped font is the output of the recorded skill version;
  only a rebuild at the recorded version (`fetch-version.py`, then `build.py --out-dir`, then a comparison) would, and
  that is not planned as a mechanism. So the report never says the differences are caused by the update: whenever
  any group differs, `update.md` carries, under `## By value`, the sentence "Attribution to the skill update is
  unverified: the drift check proves the shipped files match manifest.json, not that they are the output of the
  recorded version; only a rebuild at the recorded version (fetch-version.py) would." and `update.json["attribution"]`
  is `"unverified"`. The same sentence (the stated limit, as documented wording and not a new mechanism) is in
  `references/face-folder.md`'s update-check section; the test asserts it on the report.
- **Commands and working directory** (verified finding F004). A site has no `scripts/`. Every documented command
  names its working directory. `<skill>` stands for the skill folder (SKILL.md "Finding the skill folder"). For a
  face in a site, the commands are typed from the SITE ROOT as `<skill>/.venv/bin/python3 <skill>/scripts/<tool>.py
  ... --font tools/<face>/font.json`: the interpreter and the script are absolute (or `<skill>`-rooted) and every
  face path is relative to the site root, which is the working directory `build.py` already resolves paths against.
  The suite is `<skill>/.venv/bin/python3 -m pytest <skill>/scripts/tests/test_font.py -q --font tools/<face>/font.json
  --requirements tools/<face>/requirements.json --static-dir tools/<face>/out/static`, also from the site root. A
  command for the skill's own repository (examples, the repo tests) stays typed from the repository root as `.venv/bin/python3
  scripts/...`. `tests/test_docs_commands.py` learns the `<skill>/scripts/` prefix so these lines are still checked
  against the scripts' real flags, and `tests/test_face_folder_in_a_site.py` runs the exact documented forms from
  a separate site root.

Scope check against the request's out-of-scope list: no site repository and no `~/.claude` pointer is touched; no
glyph drawing changes (`gen.js`, `export.js` untouched; `build.py` changes only the manifest head and a refusal
path); the examples rebuild byte-identically, proved by `tests/test_backward_compat.py` and `smoke.sh` step 3.

## Code to be changed

- `scripts/build.py`
  - `compose_manifest()`: `head["skill_version"] = skill_version()` after `concepts`; new `skill_version()` reads
    `HERE.parent / "VERSION"` (strip; must match `^\d+\.\d+\.\d+$`) and raises `CheckFailed` naming the path when
    the file is missing or malformed ("run build.py from the skill install, not from a copy of scripts/;
    SKILL.md 'Finding the skill folder'"). `main()` already turns `CheckFailed` into exit 1 before anything is
    written; call `skill_version()` once in `load_config()` too, so the refusal comes before the export runs.
  - Module docstring: the `skill_version` key, the refusal, and `--check`'s consequence (a manifest built by another
    version DIFFERS on `skill_version` as it already does on `sources_sha256`).
- `scripts/diff.py`
  - `group_files()`: returns `{group: (name, before_path, after_path)}` where `name` is
    `PurePath(specimen.default_font_file(cfg, font_json, g)).name`; `before_path = before / name`;
    `after_path = after / name` when `--after` was given, else the resolved shipped path. Refuses two groups with
    one name: stderr `diff.py: groups roman and italic share the file name F-VF.woff2 under --before/--after; give
    each group's file a distinct name`, exit 2 (before anything is written). `main()` passes `after=None` when the
    flag is absent.
  - New by-value section (the fold): functions `ttx_text`, `outline`, `variations`, `hvar_advance`,
    `resolved_value`, `gpos_pairs`, `gpos_structure`, `gdef_classes`, `table_fields`, `ttf_bytes`, `shaped`,
    `value_diff(old_path, new_path, locations) -> (differences: list[str], strings_shaped: int)`; `locations` is
    the group's named-instance locations as `{axis: value}` dicts, each printed as `(wght 400, opsz 40)`; the
    instancer and HarfBuzz both take the dict. `run()` calls it per group before rendering and adds
    `result["values"] = {group: {"locations": [...], "differences": [...], "strings_shaped": n}}` and
    `result["files"] = {group: {"before": str, "after": str}}`. `markdown()` gains a `## By value` section before
    the renders table: per group `**<group>: N difference(s) by value**` with the lines, or
    `<group>: no difference by value`, then one sentence on what it compares and the shaping count. Exit status
    unchanged (0 whether or not anything differs; 2 on a missing file, a nameless group or shared names; 1 on a
    missing dependency, `uharfbuzz` now among them through `need()`).
  - Docstring: the two sections, the file-name rule, the default after side, the exact guarantee of each
    (renders: FreeType on this machine; values: the tables and HarfBuzz shaping of two-character strings, not
    contextual features or longer strings).
- `scripts/smoke.sh` step 2b: run `diff.py` for all three fixtures (neutral, bract, driftwood) against copies of
  their own `out/`, with `--sizes 16 40`, and grep both `^\*\*0 of [0-9]+ renders changed\*\*` and
  `no difference by value` per group (`grep -c 'no difference by value'` equals the fixture's group count: 2, 1, 2).
  `shellcheck scripts/smoke.sh` must stay clean.
- `tests/baseline_digest.py`: `MANIFEST_DROP = ("sources_sha256", "tools", "skill_version")` and the header's
  `manifest_sha256` paragraph says why the key is dropped (recorded before it existed; changes on every release).

## Code to be written

- `scripts/fetch-version.py` (argparse: `version`, `dir`, `--archive-url URL`; `--help` works without fontTools).
  Steps: validate `version` against `^\d+\.\d+\.\d+$`; refuse a `dir` that exists and is not empty; route 1:
  `git -C <skill folder> rev-parse --git-dir` (rc 0 means a checkout) then `git -C <skill folder> archive
  --format=tar v<version>` read into `tarfile` and extracted into `dir`; route 2: `urllib.request.urlopen(url)`
  with the default URL `https://github.com/windaddict/font-design-skill/archive/refs/tags/v<version>.tar.gz`,
  extracted with the single top-level folder stripped (refused when the archive has no single top folder);
  extraction uses `extractall(filter="data")`. Version `0.6.0` (any version with `versions.ambiguity_notice`) is
  refused first, before either route: the notice and the by-hand instruction on stderr, exit 1 (decision "The 0.6.0
  refusal"). Atomic write (plan review F004, high): each route extracts into `tempfile.mkdtemp(dir=<dir's parent>,
  prefix=".fetch-")`, never into `dir`; the temporary folder's `VERSION` must equal `version`, else exit 1
  `fetch-version.py: the archive at <url> reports version X, not Y`; only then is it moved to `dir` with
  `os.replace` (a missing or empty `dir` is removed first). Every failure path (a git error, a download error, a
  truncated or corrupt archive, a member the `data` filter rejects, a version mismatch) removes the temporary folder
  in a `finally`, so `dir` is never created and no `.fetch-*` folder is left beside it. Exit 1 when neither route
  works, naming both reasons (`not a git checkout: <stderr or 'git not on PATH'>`, then the URL and its error); exit 0
  printing `fetch-version.py: <version> from git tag v<version>` or `... downloaded from <url>`, `into <dir>`. Module docstring: WHAT IT'S FOR (decision 4 of the request), the two
  routes, the venv rule for running the fetched code, the guarantee (the tree at the tag, as the remote serves it;
  not a signature).
- `scripts/update-check.py` (argparse: `out`, `--font`, `--recorded VERSION`, `--sizes PX ...`): imports
  `build` from `HERE` for `load_config` and `group_file`; FIRST, before anything else is read or written, resolves
  `out` and the face folder (the folder holding `font.json`) and refuses an `out` that is the face folder or inside
  it: exit 1, `update-check.py: OUT <out> is inside the face folder <face dir>; the update check never writes there`
  (plan review F007), so the "Nothing in <face dir> was changed" line is true by construction; reads the manifest at `cfg["_manifest"]` (exit 1 when
  missing: "the face has no manifest; build it first"); recorded version from `manifest["skill_version"]` or
  `--recorded` (both present and different: exit 1; neither: exit 1 naming `--recorded` and saying a face built
  before 0.8.0 records none); installed version from `<skill folder>/VERSION`; equal: print
  `update-check.py: up to date: the face records <v> and the installed skill is <v>; nothing to compare` and exit
  0 without creating `out`; different: in a `TemporaryDirectory`, copy each group's shipped file
  (`build.group_file`) into `tmp/before/<name>`, run `[sys.executable, build.py, --font, <font.json>, --out-dir,
  tmp/after]` plus `--requirements <face dir>/<manifest.requirements>` or `--no-requirements` when the manifest
  records `null`; on a non-zero build exit, exit 1 with the build's last stderr lines; then run
  `[sys.executable, diff.py, tmp/report, --font, <font.json>, --before, tmp/before, --after, tmp/after]` (plus
  `--sizes`) into a FRESH folder inside the temporary directory (plan review F005, high); on a non-zero `diff.py`
  exit, exit 1 with `update-check.py: diff.py failed (exit N); no report was written` and the last stderr lines.
  **No stale report** (verified finding F002): once OUT has passed the face-folder check, EVERY exit-1 path after it
  (a failed build, a failed `diff.py`, a missing shipped file, a drift read error) first removes any `OUT/update.md`,
  `OUT/update.json` and `OUT/diff` left by an earlier run and prints
  `update-check.py: removed the report of an earlier run in <OUT>; it described a different state` (nothing is
  created when none exists), so an earlier complete report cannot be read as the failed run's result. On success the
  whole report is STAGED in a `.update-stage-*` folder inside OUT (same filesystem; removed in a `finally`): `diff/`
  (a copy of `tmp/report`, read from `tmp/report/diff.json`), `update.json` (`recorded`, `installed`, `face` (the
  face dir), `values`, `renders`, `changed`, `changed_files: []`, `drift`, `notices`, `attribution`) and `update.md`.
  It is then published in one step: the earlier three are removed, then `diff/`, `update.json` and, LAST, `update.md`
  are moved in with `os.replace`. `update.md` is the completion marker: an interruption leaves no `update.md`, never
  a new `update.md` beside an old `diff/`. The guarantee is "a report is complete if and only if `update.md`
  exists", not that the three moves are one atomic operation. `update.md` reads:

  ```
  # Update check: <family>
  recorded skill version: 0.0.1 (manifest.json)      installed: 0.8.0
  ## Notice          (only when the recorded version is ambiguous: 0.6.0)
  ## Drift           (only when a shipped file differs from the build the manifest records)
  roman: Sampler-VF.woff2 sha256 9f2c... recorded, 41ab... found. These differences cannot be attributed to the skill update.
  ## By value
  roman: 3 difference(s) by value
  - glyph o: default outline differs
  ...
  italic: no difference by value
  Attribution to the skill update is unverified: (the F001 sentence, present when any group differs)
  ## Renders
  <N> of <M> renders changed (out/diff/diff.md)
  ## Nothing was changed
  Nothing in <face dir> was changed. To adopt 0.8.0, run, from any directory,
  <python> <skill folder>/scripts/build.py --font <absolute path of font.json>
  and commit the woff2 files and manifest.json.
  ```

  `<python>` is `sys.executable` and `<skill folder>` is the folder above `scripts/`, both absolute, so the printed
  line runs from any directory. The printed line carries the same requirements flag as the check's own rebuild
  (plan review F006): `--requirements <absolute path of the face's requirements file>` when the manifest records one,
  `--no-requirements` when it records `null`, because `build.py` refuses a missing requirements file without that
  flag (a face like the Bract example has none). Exit 3 when any group has a difference by value, any render changed, or any drift
  was found; else 0 (then the report says `no difference in any group; adopting 0.8.0 changes only manifest.json`).
- `scripts/versions.py` (stdlib only, no fontTools): `AMBIGUOUS_VERSIONS`, `ambiguity_notice(version)`. WHAT IT'S FOR:
  the one place that records which released version numbers name more than one font source, so `fetch-version.py`
  (which refuses them) and `update-check.py` (which reports them) say the same thing.
- `templates/manifest.schema.json`: draft 2020-12, `$id` `font-design/manifest/v1`, `required`: `schema`,
  `family`, `version`, `font_json`, `concepts`, `requirements`, `sources_sha256`, `tools`,
  `source_date_epoch`, `size_budget_bytes`, `groups`; `skill_version` is NOT required (plan review F003): it is an
  optional property, absent from every manifest built before 0.8.0, so every existing v1 manifest still validates;
  its `description` says so; `schema` is `const "font-design/manifest/v1"`,
  `skill_version` (when present) matches `^\d+\.\d+\.\d+$`, `requirements` is string or null, `groups` is an object of objects
  each requiring `file`, `woff2_sha256` (64 hex), `woff2_bytes`, `axes`, `instances`, `masters`, with
  `additionalProperties: true`; the top level also allows additional properties (`skeletons`, future keys).

## New automated tests

Levels: **unit** = one function imported; **tool** = one script run as a subprocess on a fixture; **flow** = several
scripts in sequence through their files (the data flow a site would follow); **whole** = the shipped thing as a
site would run it. All red-green (none pins behaviour that already exists). Fixtures that need the neutral build:
`tests/test_diff.py`'s `built` fixture skips loudly when `examples/neutral/out` is unbuilt, so the build agent
builds it BEFORE the red run (Verification, step 0); the new test files below build their own copies into
`tmp_path` and never skip.

Red runs for scripts that do not exist yet (plan review F009; they follow Verification step A, which first removes the earlier drafts of those scripts and tests so the tree is the 0.7.1 one): the test-writing agent MAY create a placeholder
`scripts/fetch-version.py` or `scripts/update-check.py` that exits 0 and prints nothing, so the tests collect and
run. Every expected_failure marker in `tests/test_fetch_version.py` and `tests/test_update_check.py` sits on an
assertion that such a placeholder fails (a stdout or stderr text, a report file, or an exit code other than 0),
and the SAME assertion fails when the script is missing. No marker relies on Python's exit 2 for a missing file,
and no marker sits on an `exit == 0` assertion, which a placeholder passes. Each row below names the assertion.

`tests/test_diff.py` (item `diff-tests`):

| test | level | asserts | expected_failure (first assertion about the new behaviour) |
|---|---|---|---|
| `test_diff_finds_a_group_file_by_its_name_under_before_and_after` (issue #17) | tool | a neutral `font.json` copy at `tmp/site/tools/face/` with `out_dir: "."`, groups reduced to `roman`, `file: "../../static/F-VF.woff2"`; `Sampler-VF.woff2` copied to `tmp/site/static/F-VF.woff2`, `tmp/before/F-VF.woff2`, `tmp/after/F-VF.woff2`; `diff.py OUT --font ... --before tmp/before --after tmp/after --sizes 16` exits 0 with `len(entries) == instances x titles x 1`; a second run without `--after` exits 0 and `data["files"]["roman"]["after"]` ends with `static/F-VF.woff2` | `issue-17 basename lookup` (in `f"issue-17 basename lookup: diff.py exited {rc} on a group whose file is ../../static/F-VF.woff2: {stderr}"`); today the before path walks out of DIR and the run exits 2 |
| `test_diff_refuses_two_groups_whose_files_share_a_name` | tool | roman `file: "a/F-VF.woff2"`, italic `file: "b/F-VF.woff2"`, before and after each holding `F-VF.woff2`: exit 2, stderr names both groups and the name, no `diff.json` | `same-name groups` (in `f"same-name groups: exit {rc}: {stderr}"`, asserting rc 2 AND `"share the file name F-VF.woff2" in stderr`); today the message is the missing-files one |
| `test_diff_by_value_reports_no_difference_between_a_font_and_itself` | tool | the identity run: `data["values"]` has both groups, each `differences == []`, `strings_shaped > 0`, `locations` equal `font.json`'s instance locations; `diff.md` holds `roman: no difference by value` and `italic: no difference by value` | `by-value section missing from diff.json (identity)` |
| `test_diff_by_value_names_what_moved_in_the_roman_and_nothing_in_the_italic` | tool | after-roman doctored by the test with fontTools: `o` translated +30 x with lsb (as the existing moved-glyph test does), `four`'s advance +60, one `PairValueRecord` +80 (found as the existing kern test finds it), name ID 5 changed; `differences` contain a line starting `glyph o: default outline differs`, one matching `^glyph four: hmtx`, one starting `GPOS pair`, one starting `shaped '` (HarfBuzz saw the kern), one containing `glyph o @ (` (the instanced check), one starting `name 5:`; `values["italic"]["differences"] == []`; `diff.md` lists them under `## By value` | `by-value section missing from diff.json (moved)` |
| `test_diff_by_value_runs_on_the_bract_and_driftwood_examples_against_copies_of_themselves` (parametrised `bract`, `driftwood`) | flow | a module fixture builds each example into `tmp_path` with `build.py --out-dir` (`--no-requirements` for bract); `diff.py` with `--before <copy> --after <build> --sizes 16`: exit 0, every group `differences == []`, `0 of M renders changed`; this is the two-axis and the avar-mapped one-axis case the generalised locations must handle | `by-value section missing from diff.json (examples)` |

`tests/test_manifest_version.py` (item `manifest-version-tests`):

| test | level | asserts | expected_failure |
|---|---|---|---|
| `test_the_manifest_records_the_skill_version_and_validates_against_its_schema` | flow | `build.py --font examples/neutral/font.json --group roman --out-dir tmp`; `manifest["skill_version"] == VERSION file`; `templates/manifest.schema.json` exists, `check_schema` passes, the manifest validates; `MANIFEST_SCHEMA` string unchanged (`font-design/manifest/v1`) | `manifest records no skill_version` |
| `test_build_refuses_to_run_when_the_skills_version_file_is_missing` | tool | `scripts/` copied to `tmp/copy/scripts` (no `VERSION` above it); `tmp/copy/scripts/build.py --font <neutral copy> --group roman --out-dir tmp/o` exits 1, stderr names `VERSION` and the path `tmp/copy/VERSION`, `tmp/o` has no `manifest.json` and no woff2 | `build without VERSION` (in `f"build without VERSION: exit {rc}, stderr {stderr}"`); today the copy builds fine and exits 0 |

`tests/test_fetch_version.py` (item `fetch-version-tests`):

| test | level | asserts | expected_failure |
|---|---|---|---|
| `test_without_git_the_tag_archive_is_downloaded_and_the_fetched_code_rebuilds_the_recorded_version` | whole | `tmp/install/{scripts,VERSION}` copied from the repo (no `.git`); a tarball `tmp/archive/v<V>.tar.gz` built by the test with `tarfile`, top folder `font-design-skill-<V>/`, holding `scripts/` and `VERSION`; `tmp/install/scripts/fetch-version.py <V> tmp/at --archive-url file://.../v<V>.tar.gz` exits 0, stdout contains `downloaded from file://` and not `git tag`, `tmp/at/VERSION` reads `<V>`, `tmp/at/scripts/build.py` exists; then `tmp/at/scripts/build.py --font <neutral copy>/font.json --group roman --out-dir tmp/rebuilt` exits 0 and `tmp/rebuilt/Sampler-VF.woff2` equals `examples/neutral/out/Sampler-VF.woff2` byte for byte (loud skip ONLY for that last comparison when the neutral build is absent; the fetch assertions never skip) | `no-git fetch` (in `f"no-git fetch: stdout {stdout!r} stderr {stderr!r}"`), on the stdout assertion (`downloaded from file://`), which runs BEFORE the exit-code assertion; the exit-code assertion carries no marker. The stdout assertion fails first whether the script is missing (exit 2, empty stdout) or a placeholder that exits 0 and prints nothing |
| `test_from_a_git_checkout_the_tag_is_used_and_no_download_is_tried` | tool | `git init tmp/repo` (with `-c user.name -c user.email` on the commit), `scripts/` and a `VERSION` reading `9.9.9` committed, `git tag v9.9.9`; `tmp/repo/scripts/fetch-version.py 9.9.9 tmp/at2 --archive-url file:///nonexistent.tar.gz` exits 0, stdout contains `git tag v9.9.9`, `tmp/at2/VERSION` reads `9.9.9` | `git-tag fetch` (in `f"git-tag fetch: stdout {stdout!r} stderr {stderr!r}"`), on the stdout assertion (`git tag v9.9.9`), which runs BEFORE the exit-code assertion; the exit-code assertion carries no marker, so a missing script and a placeholder that exits 0 both fail on the marker |
| `test_neither_route_working_stops_naming_both_reasons_and_writes_nothing` | tool | the no-git install, `--archive-url file:///nonexistent-<random>.tar.gz`, version `0.0.9`: exit 1, stderr contains `not a git checkout` and the URL, `tmp/at3` does not exist | `neither route` (on the `rc == 1` assertion) |
| `test_fetching_0_6_0_is_refused_naming_both_commits_and_other_versions_are_not` | tool | a VALID tarball whose `VERSION` reads `0.6.0`, offered with `--archive-url file://...`, from the no-git install: exit 1, stderr contains `0.6.0 is ambiguous`, `1c032ad`, `c5b4abb` and `archive`, `tmp/at5` does not exist and no `.fetch-*` folder is beside it (the refusal comes before any route); the same script on a valid `9.9.9` tarball exits 0 and prints no `ambiguous` (the refusal is not unconditional) | `0.6.0 refusal` (in `f"0.6.0 refusal: exit {rc}: stderr {err!r}"`, on the `rc == 1` assertion, the first of the test; a placeholder exits 0 and fails it) |
| `test_an_archive_whose_version_differs_is_refused` | tool | a tarball whose `VERSION` reads `0.0.2`, requested `0.0.3`: exit 1, stderr contains `reports version 0.0.2, not 0.0.3`, `tmp/at4` does not exist, no `.fetch-*` folder beside it | `wrong-version archive` (on the `rc == 1` assertion) |
| `test_an_archive_that_breaks_partway_through_leaves_nothing_behind` (plan review F004) | tool | a tarball holding `VERSION` (`0.0.4`), `scripts/` and a 1 MB file of random bytes, then truncated by the test to half its length, offered with `--archive-url file://...` from the no-git install, version `0.0.4`: exit 1, stderr names the URL, `tmp/at6` does not exist, and `list(tmp.glob(".fetch-*")) == []` (the temporary folder was removed) | `partial archive` (in `f"partial archive: exit {rc}: {stderr}"`, on the `rc == 1` assertion, the first of the test) |

`tests/test_update_check.py` (item `update-check-tests`); a module fixture builds the neutral face once into
`tmp_path_factory.mktemp("face")` with `build.py --font <copy>/font.json` (both groups, about 20 s) and each test
copies it. The built face is a VALID recorded build: its manifest hashes match its woff2 files and inputs. A test that
makes the shipped font differ on purpose updates the manifest's `woff2_sha256` to match (so the face still claims
to be what it is), except the drift tests, which exist to break that match:

| test | level | asserts | expected_failure |
|---|---|---|---|
| `test_matching_versions_report_up_to_date_and_build_nothing` | tool | manifest `skill_version` set to the installed `VERSION`; `update-check.py tmp/out --font <face>/font.json` exits 0, stdout contains `up to date` and both version strings, `tmp/out` does not exist | `up-to-date` (in `f"up-to-date: stdout {stdout!r} stderr {stderr!r}"`), on the stdout assertion (`up to date`), which runs BEFORE the exit-code assertion; the exit-code assertion carries no marker, so a missing script and a placeholder that exits 0 both fail on the marker |
| `test_a_version_mismatch_rebuilds_compares_by_value_and_overwrites_nothing` | whole | manifest `skill_version` set to `0.0.1`; the shipped roman `o` translated +30 x (as in `test_diff.py`), re-saved, and roman's `woff2_sha256` in the manifest rewritten to the new file's hash (a valid recorded build, so no drift); sha256 of both woff2 files and the manifest taken; run with `--sizes 16`: exit 3; `update.md` contains `0.0.1`, the installed version, `glyph o: default outline differs` under `roman`, `italic: no difference by value`, `Nothing in` and `scripts/build.py --font`; `update.md` has no `## Drift` and `update.json["drift"] == []`; `update.md` contains `Attribution to the skill update is unverified` and `update.json["attribution"] == "unverified"` (F001: the rewritten hash is exactly the case a clean drift check cannot see through); the up-to-date and no-difference runs carry no such sentence; `update.json["changed_files"] == []`; `tmp/out/diff/diff.md` exists; every sha256 unchanged; the adoption line in `update.md` contains `--requirements` and the face's requirements file name (F006); a second copy whose manifest records `requirements: null`: its adoption line ends with `--no-requirements` | `mismatch report` (in `f"mismatch report: exit {rc}: {stdout} {stderr}"`, on the `rc == 3` assertion) |
| `test_a_failing_diff_is_an_error_and_leaves_no_stale_report` (plan review F005) | tool | a COMPLETE earlier report written by the test beforehand: `tmp/out/update.md` (reading "earlier run"), `tmp/out/update.json` and `tmp/out/diff/diff.json` (a report with no differences) and `tmp/out/diff/diff.md`; manifest `skill_version` `0.0.1`; `font.json` edited so `diff.py` exits non-zero while `build.py` still succeeds (its `review` block and any `titles` removed and no `--sizes` given, F011's case; the agent confirms this makes `diff.py` exit non-zero by running it by hand before writing the test, and if it does not, picks another such input and names it in the docstring): exit 1, stderr contains `diff.py failed`, stderr contains `removed the report of an earlier run`, and `tmp/out/update.md`, `tmp/out/update.json` and `tmp/out/diff` do not exist (a stale report is not left looking current); a second case with a failing BUILD (a `requirements` path that does not exist) and the same precreated report ends the same way; a third case, a successful run over a precreated report from an older run, leaves `update.md`, `update.json` and every file of `diff/` from the new run only (no file of the old `diff/` remains) | `failing diff` (in `f"failing diff: exit {rc}: {stderr}"`, on the `rc == 1` assertion, the first of the test) |
| `test_an_out_folder_inside_the_face_folder_is_refused` (plan review F007) | tool | manifest `skill_version` `0.0.1`; OUT is `<face dir>/update`: exit 1, stderr names both the OUT path and the face folder, `<face dir>/update` does not exist, and the face folder's file list and every file's sha256 are unchanged; OUT equal to the face folder itself is refused the same way | `out inside face` (in `f"out inside face: exit {rc}: {stderr}"`, on the `rc == 1` assertion, the first of the test) |
| `test_a_shipped_file_that_differs_from_the_recorded_build_is_labelled_drift_not_update_effect` | whole | (marker on the case (a) `rc == 3` assertion, the first of the test) manifest `skill_version` `0.0.1`; (a) roman woff2 `o` translated +30 x with the manifest hash NOT updated: exit 3, `update.md` has `## Drift`, names the roman woff2 file and `cannot be attributed to the skill update`, `update.json["drift"]` has an entry whose `file` ends with that woff2 name and whose `recorded` and `found` differ; (b) a fresh copy with `font.json` given a trailing newline: `drift` names `font.json`; (c) a fresh copy with `concepts.js` given a trailing newline: `drift` names `concepts.js`; (d) the clean copy (nothing edited): `drift == []`, exit 0 | `drift label` (in `f"drift label: exit {rc}: {stdout} {stderr}"`); today the script does not exist, and with no drift check the same edit would be reported as a plain by-value difference |
| `test_a_face_recorded_at_0_6_0_gets_the_ambiguity_notice` | tool | the clean copy with `--recorded 0.6.0` after deleting the manifest's `skill_version`: the check runs (it does not refuse: it fetches nothing), `update.md` has a `## Notice` section containing `0.6.0 is ambiguous`, `update.json["notices"]` has one entry, stderr repeats it; a copy recorded at `0.0.1` has `notices == []` | `0.6.0 notice` (in `f"0.6.0 notice: {stderr}"`, on the `'0.6.0 is ambiguous' in stderr` assertion, the first of the test) |
| `test_a_face_without_a_recorded_version_is_refused_unless_recorded_is_given` | tool | `skill_version` deleted from the manifest: exit 1, stderr names `--recorded` and `0.8.0`-era wording (`built before`); with `--recorded <installed VERSION>`: exit 0 and `up to date` (no build runs: the test checks the run takes under 10 s and `tmp/out` does not exist) | `no recorded version` (in `f"no recorded version: exit {rc}: {stderr}"`, on the `rc == 1` assertion) |

`tests/test_versions_and_skill.py` (item `changelog-font-output-test`):

| test | level | asserts | expected_failure |
|---|---|---|---|
| `test_the_current_versions_changelog_entry_states_whether_font_output_changes` | unit (text) | the block under `## [<VERSION>]` up to the next `## ` heading contains a line matching `^Font output: (unchanged|changes)\b`; the test names the version it looked at | `does not state whether font output changes` (in `f"the CHANGELOG entry for {version} does not state whether font output changes (a line starting 'Font output: unchanged' or 'Font output: changes')"`); today VERSION is 0.7.1 and its entry has no such line |

## Automated tests to be changed

- `tests/baseline_digest.py` (item `baseline-digest-drop`): `MANIFEST_DROP` gains `skill_version`; header
  paragraph updated. `tests/test_backward_compat.py`: one docstring sentence ("the manifest digest leaves
  `skill_version` out since 0.8.0"). No test logic changes; `test_the_0_1_examples_export_and_build_to_the_recorded_digests`
  must stay green on this machine (darwin/26 is recorded) and `test_the_0_1_woff2_bytes_are_unchanged_for_the_recorded_brotli`
  must pass, not skip, which is the byte-identity proof the request asks for.
- `tests/test_copy_into_site.py` → renamed `tests/test_face_folder_in_a_site.py` (item `site-tests-from-skill`,
  `git mv`): `make_site()` no longer copies `scripts/`; it builds the face at `site/tools/sampler/` with
  `scripts/build.py` from the repo and the suite runs as `pytest scripts/tests/test_font.py --font
  site/tools/sampler/font.json ...` from the site root; the two suite tests keep their names and assertions; the
  `--scripts` test (`test_tests_kept_elsewhere_find_the_scripts_through_the_scripts_option`) copies only
  `conftest.py` and `test_font.py` into `site/tests/font/` and points `--scripts=` and `FD_SCRIPTS` at the repo's
  `scripts/` (the option still proves the resolution); the mutate and `--out-dir` tests run the repo's scripts on the
  site's face. A new test, `test_the_documented_commands_run_from_the_site_root` (F004), builds the face in a sample
  site and, with `cwd` the SITE ROOT (a folder holding no `scripts/`), runs the exact documented forms:
  `<repo>/.venv/bin/python3 <repo>/scripts/build.py --font tools/sampler/font.json --check`,
  `.../diff.py out/diff --font tools/sampler/font.json --before <copy>`, `.../update-check.py out/update --font
  tools/sampler/font.json` and the suite `.../python3 -m pytest <repo>/scripts/tests/test_font.py -q --font
  tools/sampler/font.json --requirements tools/sampler/requirements.json --static-dir tools/sampler/out/static`,
  taking the command lines from `references/face-folder.md` and SKILL.md with `<skill>` replaced by the repo path
  (so a doc that drifts from the tested form fails the test); each exits as documented. Mutation to watch red:
  change a documented line to a site-relative `scripts/build.py` and the test fails on it. Module docstring rewritten
  for the face-folder contract (W1 kept as history).
  `scripts/tests/conftest.py`: header and the `--scripts` help and `UsageError` text no longer tell a site to copy
  the scripts folder; the default (the parent of the tests folder, inside the skill) is the documented layout.
  `tests/test_docs_commands.py` reads `conftest.py`'s registrations only, so no change there.
- `tests/test_docs_commands.py` (item `docs-commands-test`, F004): the `SCRIPT` pattern accepts an optional
  `<skill>/` prefix before `scripts/...` (today it matches `scripts/` only after whitespace, a backtick, a
  parenthesis or an interpreter, so `<skill>/scripts/build.py` would be silently unchecked). Mutation to watch red:
  put a nonexistent flag on a `<skill>/scripts/build.py` line in a doc and the flag test fails. The bare-python test
  already accepts any `.venv/bin/` interpreter path.
- Nothing in `tests/test_diff.py`'s existing tests changes: `test_diff_refuses_a_missing_group_file_naming_it`
  still names `before/Sampler-Italic-VF.woff2` under the file-name rule.

## Documentation to be updated

- `references/face-folder.md` (new; item `docs-face-folder`): WHAT IT'S FOR; the contract as a table (file,
  required?, who writes it, what reads it): `font.json` (required, the operator/agent; every tool),
  `concepts.js` (required, named by `font.json`), `requirements.json` (required for `build.py` unless
  `--no-requirements`, and for the suite), `skeletons.js` (optional), the build output where `font.json`'s `out_dir`
  and group `file` keys put it (the woff2 per group and `manifest.json`, which records `skill_version`), and what
  is NOT in the folder (no scripts, no tests of the font, no screenshots: decision 7); the path rule; the version
  record and what `build.py --check` proves against it; a "Working directory" paragraph (typed from the site root;
  `<skill>` is the skill folder; the interpreter and script are `<skill>`-rooted, the face paths are site-relative)
  and the three commands with their exact lines, each as typed from the site root
  (`<skill>/.venv/bin/python3 <skill>/scripts/update-check.py work/update --font tools/<face>/font.json`,
  `<skill>/.venv/bin/python3 <skill>/scripts/fetch-version.py 0.7.1 work/skill-0.7.1`,
  `<skill>/.venv/bin/python3 <skill>/scripts/diff.py work/diff --font tools/<face>/font.json --before work/round-3`);
  the version-record section carries the 0.6.0 refusal (fetch) and notice (update check), with the by-hand `git archive` route, and the drift check (what update-check verifies
  before comparing, and that the requirements file is not hashed); the refusal of an OUT inside the face folder, and that a failed build or `diff.py` writes no report and removes the one an earlier run left (`update.md` exists only when the report is complete); the limit of the drift check (F001), as the plan's sentence: it proves manifest consistency only, not that the shipped font is the output of the recorded version, so attribution to the update is unverified, and a rebuild at the recorded version is the only check that would verify it; the exit codes, what the update check proves and
  does not (by value and FreeType renders on this machine; no browser); "Comparing renderings across versions":
  fetch the recorded version, build it with `--out-dir`, shoot both with `shoot.py` (no PNG is stored);
  **Migration note** for a site moving off the submodule: delete the submodule (`git submodule deinit`, remove the
  `.gitmodules` entry and the `tools/font-design` path), delete `tools/<face>/scripts/`, keep `font.json`,
  `concepts.js`, `requirements.json`, `skeletons.js`, the woff2 files and `manifest.json`; keep the site's own
  tests (the filled wiring template, the page-character check, the font URL version check); add nothing but the
  skill's install path to the site's docs; first update check, from the site root: `<skill>/.venv/bin/python3 <skill>/scripts/update-check.py
  work/update --font tools/<face>/font.json --recorded <the VERSION file of the commit the submodule pinned>`, read `update.md`,
  then `build.py --font tools/<face>/font.json` to adopt, commit the woff2 files and manifest (now carrying
  `skill_version`); the version-discipline rule and the tags, in one paragraph. Neutral wording: no site names,
  hostnames or local paths.
- `SKILL.md` (items `docs-face-folder` and `release-0-8-0`; must stay at or under 500 lines, now 486):
  "Finding the skill folder": drop the "A project's copy of the scripts" sentence, add one line pointing to
  `references/face-folder.md`. Phase 7 step 1: replace the copy-and-diff instructions with "create the face folder
  (`references/face-folder.md`); the scripts stay in the skill". Step 4: the suite runs from the skill, typed from the SITE ROOT with `<skill>`-rooted interpreter and test file:
  `<skill>/.venv/bin/python3 -m pytest <skill>/scripts/tests/test_font.py -q --font tools/<face>/font.json --requirements
  tools/<face>/requirements.json --static-dir tools/<face>/out/static`; the wiring template stays the site's.
  Every other Phase 7 and Phase 9 command is given in the same form with its working directory stated.
  Phase 9 step 3: drop "the copied `scripts/`". New four-line subsection at the end of Phase 9, "Later: a new
  skill version under a shipped face" naming `update-check.py` and the approval rule. Section 5: `diff.py` row
  updated (renders AND values, the file-name rule); new rows for `fetch-version.py` and `update-check.py` with
  exact guarantees. Section 6: `references/face-folder.md` added. Version lines to 0.8.0 (frontmatter and body).
- `README.md`: the Install paragraph about the submodule replaced by the face-folder sentence and a link to
  `references/face-folder.md`; the Layout row for `references/` and `templates/` (the manifest schema); the badge
  to 0.8.0; a "Releases" sentence (tags `v<version>`, `fetch-version.py`).
- `references/process.md` section 7 (Phase 7) and section 9: the same replacements as SKILL.md, in its longer
  form, with each site command in the `<skill>`-rooted form from the site root; the sentence "every path given on the command line (`--static`, `--out-dir`" and "resolves relative to the
  working directory" must survive (`tests/test_docs_commands.py::test_the_docs_state_the_path_rule_build_py_implements`).
- `references/testing.md`: the header paragraph (the skill no longer copies `scripts/` into the site; the suite
  runs from the skill; the wiring template is the site's), section 6 first paragraph (what stays in the site:
  the page-character guard, the font URL guard), section 7's "Copy `scripts/` into a site" bullet replaced by
  "run the suite from the skill after `smoke.sh` has finished" (the mutation-in-progress hazard still holds for a
  skill run concurrently), section 8 gains a table block for the 0.8.0 guards (the tests above and the
  expected-failure each was watched red on).
- `references/variable-font-build.md`: section 7 (reproducibility) gains the `skill_version` key and the refusal;
  section 12's table gets no new `font.json` key (none is added); section 14 (Commands) gains the three new lines
  and the `diff.py` line's default after side; a sentence in section 11's neighbourhood pointing to
  `templates/manifest.schema.json`.
- `references/review-loop.md` section 2: the `diff.py` bullet mentions the by-value section and the file-name rule.
- `scripts/tests/test_site_wiring.py.tmpl` header: "the font itself is covered by the skill's suite, run from the
  skill when the font changes (SKILL.md Phase 7); this file needs no skill code and stays in the site".
- `CLAUDE.md` (item `claude-md-version-discipline`): new section "Version discipline": any change that alters
  font output (`scripts/gen.js`, `scripts/export.js`, `scripts/build.py`, the defaults they read) bumps `VERSION`
  in the same change; every CHANGELOG entry carries a `Font output: unchanged` or `Font output: changes — <what>`
  line, held by `tests/test_versions_and_skill.py`; every released version gets a tag `v<version>` on the first
  `main` commit carrying it, pushed after the merge; `manifest.json` records `skill_version`. The exact guarantee
  (plan review F002): two installs with one `VERSION` produce the same font output. Later commits under one `VERSION`
  may change CI, docs or tests, never font output; the 0.6.0 case in the CHANGELOG is the counter-example the rule
  now forbids. The CHANGELOG `## Releases` section says the same in one sentence. Also the
  test-scope table: a row for `scripts/fetch-version.py`, `scripts/update-check.py` (their test files plus
  `tests/test_hygiene.py`).
- `CHANGELOG.md` (item `release-0-8-0`): `## [0.8.0] — 2026-11-20` with `Font output: unchanged` as its first
  line after the heading (every example rebuilds byte-identically; `tests/test_backward_compat.py`), the
  `[Unreleased]` items (CI by hand, CLAUDE.md test scope) folded in, Added (the face-folder contract,
  `skill_version`, `fetch-version.py`, `update-check.py`, the by-value section, the manifest schema, the
  version-discipline rule, the tags) and Fixed (#17); a `## Releases` section listing the tags from the table in
  section 0, the 0.6.0 note, and the sentence that one `VERSION` guarantees the same font output, not identical files (F002); the file's intro sentence says each entry states whether font output changes.
- `VERSION` 0.8.0; `package.json` version 0.8.0; `docs/plan-face-folder.md`: a copy of this plan (relative paths
  only, the hygiene test scans `docs/`).

## Work items

| id | title | kind | files | verifiable_by |
|---|---|---|---|---|
| `diff-value-fold` | Fold the by-value comparison into diff.py, look up group files by name under --before and --after, default --after to the shipped files, refuse shared names | code-change | scripts/diff.py | agent |
| `diff-tests` | New diff.py tests for the file-name lookup (issue 17), the shared-name refusal and the by-value section on the neutral, Bract and Driftwood examples | test-new | tests/test_diff.py | agent |
| `manifest-skill-version` | build.py records skill_version in the manifest from the skill folder's VERSION file and refuses to build without it | code-change | scripts/build.py | agent |
| `manifest-schema` | A manifest schema with skill_version optional (absent before 0.8.0), in the pattern of font.schema.json | code-new | templates/manifest.schema.json | agent |
| `manifest-version-tests` | Tests that a build records the installed version and validates against the schema, and that a scripts copy without VERSION is refused | test-new | tests/test_manifest_version.py | agent |
| `baseline-digest-drop` | The manifest digest of the compatibility baseline leaves skill_version out | test-change | tests/baseline_digest.py, tests/test_backward_compat.py | agent |
| `version-notices` | A stdlib-only versions.py names the ambiguous released versions (0.6.0) and returns the notice text that fetch-version.py refuses with and update-check.py reports | code-new | scripts/versions.py | agent |
| `fetch-version` | fetch-version.py materialises the skill at a released version from the git tag or the GitHub tag archive through a temporary folder moved into place only after DIR/VERSION checks out, and refuses 0.6.0 | code-new | scripts/fetch-version.py | agent |
| `fetch-version-tests` | Tests for fetch-version.py: the no-git download route rebuilding a recorded version, the git-tag route, the neither-route refusal, the wrong-version archive, a truncated archive leaving nothing behind, and the 0.6.0 refusal | test-new | tests/test_fetch_version.py | agent |
| `fetch-version-live` | Operator check that fetch-version.py downloads a real tag archive from GitHub without git | live-acceptance | | operator |
| `update-check` | update-check.py compares the recorded and installed versions, checks the shipped files against the manifest and labels drift, rebuilds into a temporary folder on a mismatch, reports by value and by render with the 0.6.0 notice, stops on a failed build or diff and removes any earlier report, publishes the report with update.md last, words attribution to the update as unverified, and refuses an OUT inside the face folder | code-new | scripts/update-check.py | agent |
| `update-check-tests` | Tests for update-check.py: up to date, a mismatch on a valid recorded build reported without overwriting, drift labelled for an edited woff2 or input, the 0.6.0 notice, a face with no recorded version, a failing build or diff leaving no stale report, the unverified-attribution wording, and an OUT inside the face folder | test-new | tests/test_update_check.py | agent |
| `site-tests-from-skill` | The sample-site tests run the font suite from the skill against a face folder instead of a copied scripts folder, run the documented commands from a separate site root, and the suite's conftest header says so | test-change | tests/test_face_folder_in_a_site.py, scripts/tests/conftest.py | agent |
| `smoke-diff-three-fixtures` | smoke.sh step 2b runs diff.py on all three fixtures against copies of themselves and checks the by-value lines | code-change | scripts/smoke.sh | agent |
| `changelog-font-output-test` | A test that the current version's CHANGELOG entry states whether font output changes | test-new | tests/test_versions_and_skill.py | agent |
| `docs-commands-test` | test_docs_commands.py checks documented commands that carry the skill-root prefix before scripts/, so site-root command lines are verified against the scripts' real flags | test-change | tests/test_docs_commands.py | agent |
| `docs-face-folder` | Document the face-folder contract, the working directory of every site command, the 0.6.0 notice, the drift check, the three commands and the migration note; remove the copy-the-scripts design from SKILL.md, README, process, testing, build, review-loop and the wiring template header | doc-change | references/face-folder.md, SKILL.md, README.md, references/process.md, references/testing.md, references/variable-font-build.md, references/review-loop.md, scripts/tests/test_site_wiring.py.tmpl | agent |
| `claude-md-version-discipline` | CLAUDE.md gains the version-discipline rule and the test-scope rows for the new scripts | doc-change | CLAUDE.md | agent |
| `release-0-8-0` | Release 0.8.0: VERSION, CHANGELOG with the Font output line and the Releases section, SKILL.md and README version lines, package.json, the plan copy, and the nine backfilled local tags | doc-change | VERSION, CHANGELOG.md, SKILL.md, README.md, package.json, docs/plan-face-folder.md | agent |
| `ci-by-hand-live` | Operator runs the CI workflow by hand on the release branch and checks every job passes | live-acceptance | | operator |
| `tags-push` | Operator pushes the backfilled tags and, after the merge, tags v0.8.0 on the merge commit and pushes it | live-acceptance | | operator |

Order of execution: `diff-tests`, `manifest-version-tests`, `fetch-version-tests`, `update-check-tests` and
`changelog-font-output-test` are written and watched red first (the gate); then `manifest-skill-version`,
`manifest-schema`, `baseline-digest-drop`, `diff-value-fold`, `version-notices`, `fetch-version`, `update-check`,
`site-tests-from-skill`, `smoke-diff-three-fixtures`, `docs-commands-test`, `docs-face-folder`,
`claude-md-version-discipline`, `release-0-8-0` (last, so the CHANGELOG test turns green on the real entry; the
release verification then runs `smoke.sh --full`). The three live-acceptance items (`fetch-version-live`,
`ci-by-hand-live`, `tags-push`) are the operator's: `ci-by-hand-live` runs after the branch is pushed and before the
merge, the other two after the merge.

## Verification

Step A (F004), before any red run: the worktree already holds drafts from an earlier attempt, listed by
`git status --porcelain`: untracked `scripts/fetch-version.py`, `scripts/update-check.py`,
`tests/test_fetch_version.py`, `tests/test_manifest_version.py`, `tests/test_update_check.py`, and modified
`tests/test_diff.py` and `tests/test_versions_and_skill.py`. A red run against them is not a run against the 0.7.1
tree. The test-writing agent therefore (1) copies all seven files to a folder OUTSIDE the repository (a scratch
folder; the hygiene test scans the tree, so not under it), keeping them as reference only, (2) removes the five
untracked ones from the worktree with `mv` into that folder, one command per call, (3) restores the two modified
files with `git checkout HEAD -- tests/test_diff.py` and `git checkout HEAD -- tests/test_versions_and_skill.py`
(one git command per call), and (4) confirms `git status --porcelain` shows none of the seven (only `.claude/`),
before writing the tests from this plan. The drafts are not the starting point; if the agent reuses text from them,
the red run is still recorded on the clean tree. For each red run the agent captures the failing assertion text
(the expected_failure marker as printed by pytest) in its report, since a run proves only the first failing
assertion.

Step 0, before the red run and again before the green run (the neutral fixture the diff tests read):
`.venv/bin/python3 scripts/build.py --font examples/neutral/font.json --static examples/neutral/out/static`.
The hygiene test walks the whole tree including `.claude/`, so nothing written during the run under `.claude/plans/`
may hold an absolute home path, a session link or a temp-directory name (this file holds none).

Test layer (CLAUDE.md "Choosing how much to test"): the change touches `build.py`, which the table sends to layer
4 (`scripts/smoke.sh`), and it is a release (a `VERSION` bump, and a commit a site's pin will move to), which the
table sends to layer 4 with `--full`, then layer 5. So the layer is: `bash scripts/smoke.sh --full --out out/smoke`
(steps 1 to 11, Chrome steps included), then CI by hand: `gh workflow run ci.yml --ref feature/face-folder-contract` (the branch this run created from `feature/face-folder`). The
build agent runs the targeted files below after each item and `smoke.sh --full` once at the end, after
`release-0-8-0`; the commit names the layer. The CI run needs the pushed branch and GitHub credentials, so it is the
operator item `ci-by-hand-live`, not an agent step. `ruff check scripts tests` and `shellcheck scripts/smoke.sh` must
be clean (the CI lint job).

| id | verifier | how it is proved |
|---|---|---|
| `diff-tests` | agent | red-green. Red: `.venv/bin/python3 -m pytest tests/test_diff.py -q -k "by_its_name or share_a_name or by_value"` before `diff-value-fold` (plan review F008: the issue #17 test is named `..._by_its_name_...`); the run must report exactly 6 selected items (5 tests, the examples test parametrised twice), and any other count fails the step; each test fails on the expected_failure text in its row of "New automated tests" (`issue-17 basename lookup`, `same-name groups`, `by-value section missing from diff.json (identity)`, `... (moved)`, `... (examples)`). Green: the same command after `diff-value-fold`, then the whole file `.venv/bin/python3 -m pytest tests/test_diff.py -q` (the existing eleven tests must stay green). |
| `diff-value-fold` | agent | `diff-tests` green; `.venv/bin/python3 scripts/diff.py --help` lists `--font --before --after --sizes --scale` and no allowance flags; smoke step 2b by hand: `mkdir -p out/smoke-before && cp -R examples/neutral/out/. out/smoke-before/ && .venv/bin/python3 scripts/diff.py out/smoke-diff --font examples/neutral/font.json --before out/smoke-before --sizes 16 40` prints `0 of N renders changed` and `diff.md` holds two `no difference by value` lines; `ruff check scripts/diff.py`; `grep -n -i "bract\|hopsafari\|driftwood\|movingavg\|tools/" scripts/diff.py` prints nothing new (hygiene). |
| `manifest-version-tests` | agent | red-green. Red: `.venv/bin/python3 -m pytest tests/test_manifest_version.py -q` before `manifest-skill-version` and `manifest-schema`: `manifest records no skill_version` and `build without VERSION`. Green after both. |
| `manifest-skill-version` | agent | `manifest-version-tests` green; `.venv/bin/python3 scripts/build.py --font examples/neutral/font.json` then `SOURCE_DATE_EPOCH=1000000000 .venv/bin/python3 scripts/build.py --font examples/neutral/font.json --check` exits 0 (font and manifest identical); the same two commands for `examples/bract/font.json --no-requirements` and `examples/driftwood/font.json`; `.venv/bin/python3 -m pytest tests/test_backward_compat.py -q` passes with the woff2-bytes test PASSING (not skipping) on this machine, which is the byte-identity proof; `.venv/bin/python3 -m pytest tests/test_tools_and_templates.py -q -k "group_file or out_dir or two_groups"` stays green. |
| `manifest-schema` | agent | `manifest-version-tests` green; `.venv/bin/python3 -m pytest tests/test_schemas_and_concepts.py -q -k schemas` (add the manifest schema to `test_the_schemas_are_valid_schemas`); a manifest with `skill_version` deleted (a 0.7.1-era manifest) still validates (F003), checked by a line in `test_the_manifest_records_the_skill_version_and_validates_against_its_schema` after its presence assertion. |
| `baseline-digest-drop` | agent | `.venv/bin/python3 -m pytest tests/test_backward_compat.py -q`: all four digest tests pass, the woff2-bytes test passes. Then a by-hand check that the drop is what makes it pass: with the `skill_version` entry removed from `MANIFEST_DROP` the digest test must FAIL naming `manifest_sha256` on every group; restore the line (`git checkout -- tests/baseline_digest.py` is not available in a worktree-isolated session as a compound command; edit the line back and confirm with `git diff --stat`). |
| `fetch-version-tests` | agent | red-green. Red: `.venv/bin/python3 -m pytest tests/test_fetch_version.py -q` before `fetch-version` exists (after step A, so the script is missing or a placeholder, never the earlier draft): every test fails on its marker (`no-git fetch`, `git-tag fetch`, `neither route`, `0.6.0 refusal`, `wrong-version archive`, `partial archive`), whether the script is missing or a placeholder that exits 0 and prints nothing (see "Red runs for scripts that do not exist yet"). Green after `fetch-version`. The tests need `git` on PATH and no network (`file://` URLs only). |
| `fetch-version` | agent | `fetch-version-tests` green (the `0.6.0 refusal` test also needs `version-notices`); mutation to watch red for F004: extract straight into `dir` instead of the temporary folder and `test_an_archive_that_breaks_partway_through_leaves_nothing_behind` fails on `tmp/at6` existing; `.venv/bin/python3 scripts/fetch-version.py --help` exits 0 and lists `--archive-url`; `ruff check scripts/fetch-version.py`; `.venv/bin/python3 -m pytest tests/test_docs_commands.py -q` once the docs name the command. Not provable here: the real GitHub download (`fetch-version-live`). |
| `version-notices` | agent | `.venv/bin/python3 -c "import sys; sys.path.insert(0, 'scripts'); import versions; print(versions.ambiguity_notice('0.6.0')); print(versions.ambiguity_notice('0.7.1'))"` prints the notice, then `None`; `.venv/bin/python3 -m pytest tests/test_fetch_version.py tests/test_update_check.py -q -k 0_6_0` green (the `0.6.0 refusal` and `0.6.0 notice` tests are red before this item and `fetch-version`/`update-check` exist; deleting the `0.6.0` entry from `AMBIGUOUS_VERSIONS` turns both red, which is the mutation to watch); `ruff check scripts/versions.py`; `scripts/versions.py` imports nothing outside the standard library (`grep -n "^import\|^from" scripts/versions.py`). |
| `docs-commands-test` | agent | `.venv/bin/python3 -m pytest tests/test_docs_commands.py -q` green; mutation watched red: add `--nonexistent-flag` to one `<skill>/scripts/build.py` line in `references/face-folder.md` and the flag test fails naming that line; remove the change. `.venv/bin/python3 -m pytest tests/test_docs_commands.py -q --collect-only` lists at least one command per `<skill>/scripts/` form (the prefix is checked, not skipped). |
| `fetch-version-live` | operator | Requires: network access to github.com and the tags pushed (`tags-push`). From a copy of the skill WITHOUT `.git` (for example `cp -R` of the install minus `.git`, or a downloaded release zip), run `.venv/bin/python3 scripts/fetch-version.py 0.7.1 /tmp/skill-0.7.1`: exit 0, stdout says `downloaded from https://github.com/windaddict/font-design-skill/archive/refs/tags/v0.7.1.tar.gz`, `cat /tmp/skill-0.7.1/VERSION` prints `0.7.1`, and `.venv/bin/python3 /tmp/skill-0.7.1/scripts/build.py --font examples/neutral/font.json --out-dir /tmp/rebuilt-0.7.1` exits 0 (0.7.1's build.py has no `skill_version`; the woff2 equals the installed build's because font output is unchanged). Also from the git install: the same command prints `from git tag v0.7.1`. |
| `update-check-tests` | agent | red-green. Red: `.venv/bin/python3 -m pytest tests/test_update_check.py -q` before `update-check` exists (after step A): `up-to-date`, `mismatch report`, `drift label`, `0.6.0 notice`, `no recorded version`, `failing diff`, `out inside face`, whether the script is missing or a placeholder that exits 0 and prints nothing (see "Red runs for scripts that do not exist yet"; the fixture build of the neutral face must succeed first, which needs `manifest-skill-version` NOT to be required: the tests set or delete `skill_version` in the manifest themselves). Green after `update-check` and `manifest-skill-version`. |
| `update-check` | agent | `update-check-tests` green (including the drift test: with the drift check removed from the script, test (a) must go red, which is the mutation to watch; for F005, drop the `diff.py` exit-status check and read the report anyway, and `test_a_failing_diff_is_an_error_and_leaves_no_stale_report` must go red; for F002, delete the removal of the earlier report on the failure paths (the test's precreated `update.md` survives) and again publish `update.md` before `diff/` (the success-over-old-report case fails), each must go red; for F001, delete the attribution sentence from the report and the mismatch test must go red; for F007, delete the OUT-inside-face refusal and `test_an_out_folder_inside_the_face_folder_is_refused` must go red; for F006, hard-code the adoption line without a requirements flag and the `--no-requirements` assertion must go red); `--help` lists `--font --recorded --sizes`; `ruff check scripts/update-check.py`; by hand on a copy of the neutral face with `skill_version` edited to `0.0.1`: exit 0 and `no difference in any group` (same code, nothing moved), and `git status --porcelain examples/` shows nothing (the copy is outside the tree; the examples' `out/` is ignored anyway). |
| `site-tests-from-skill` | agent | `.venv/bin/python3 -m pytest tests/test_face_folder_in_a_site.py -q`: all seven tests pass (the six rewrites plus `test_the_documented_commands_run_from_the_site_root`, which runs from a site root holding no `scripts/` and reads its command lines from the docs; it needs `docs-face-folder` to have written them, so it runs green only after that item); `git status --porcelain tests/` shows the rename (`R tests/test_copy_into_site.py -> tests/test_face_folder_in_a_site.py`); `grep -rn "copy the whole scripts" scripts/tests/conftest.py` prints nothing. The six rewrites have no red phase and each keeps the mutation its docstring names; the new command test is watched red by changing one documented line to a site-relative `scripts/build.py`. |
| `smoke-diff-three-fixtures` | agent | `shellcheck scripts/smoke.sh` clean; `bash scripts/smoke.sh --full --out out/smoke` (steps 1 to 11; steps 1 to 7 take 60 to 81 minutes on CI, the Chrome steps come on top) exits 0 once at the end of the run, after `release-0-8-0`; its log shows step 2b's three `diff.py` runs and the four Chrome steps. If a Chrome step cannot run on the build machine, the agent stops and reports which, and does not call the release verified. `tests/test_ci_workflow.py` stays green (it reads `ci.yml`, not the step text). |
| `changelog-font-output-test` | agent | red-green. Red: `.venv/bin/python3 -m pytest tests/test_versions_and_skill.py -q -k font_output` on the 0.7.1 tree fails with `does not state whether font output changes`. Green after `release-0-8-0` writes the 0.8.0 entry with `Font output: unchanged`. |
| `docs-face-folder` | agent | `grep -n "<skill>/scripts" references/face-folder.md SKILL.md` finds each documented site command, and `grep -n "^ *\.venv/bin/python3 scripts/" references/face-folder.md` prints nothing (no site-relative form in the face-folder reference); `.venv/bin/python3 -m pytest tests/test_docs_commands.py tests/test_hygiene.py tests/test_versions_and_skill.py -q`: every documented command names a real script and real flags, SKILL.md is at or under 500 lines and names only files that exist (`references/face-folder.md` must exist), no bare `python3`, the path-rule sentence survives in SKILL.md and process.md; `grep -rn "tools/<face>/scripts" SKILL.md README.md references/process.md references/testing.md scripts/tests/conftest.py scripts/tests/test_site_wiring.py.tmpl` prints nothing (`references/generator.md:762` keeps its historical mention); `grep -n -i "hopsafari\|movingavg" references/face-folder.md` prints nothing. |
| `claude-md-version-discipline` | agent | `grep -n "Version discipline" CLAUDE.md` finds the section; `grep -n "Font output:" CLAUDE.md` finds the rule; `.venv/bin/python3 -m pytest tests/test_hygiene.py -q`. |
| `release-0-8-0` | agent | `bash scripts/smoke.sh --full --out out/smoke` exits 0 (the release layer, run last; see `smoke-diff-three-fixtures`); `.venv/bin/python3 -m pytest tests/test_versions_and_skill.py -q` (VERSION, SKILL.md twice, README badge, CHANGELOG top entry, package.json all 0.8.0; the Font output line); `.venv/bin/python3 -m pytest tests/test_hygiene.py -q` (the plan copy under `docs/` is scanned); the nine local tags, one git command per Bash call: `git tag v0.1.0 0fc4314`, `git tag v0.2.0 183560f`, `git tag v0.3.0 7cbb3e4`, `git tag v0.3.1 4538c4c`, `git tag v0.4.0 598044b`, `git tag v0.5.0 5d0b29f`, `git tag v0.6.0 1c032ad`, `git tag v0.7.0 aa4b9ae`, `git tag v0.7.1 b09faa9`; then for each `git show v0.7.1:VERSION` prints the version in its name (nine commands); `git tag -l` lists exactly nine. The CHANGELOG `## Releases` section lists the same nine with the 0.6.0 note. The tags live in the shared `.git` of the main checkout and are not pushed by the agent. |
| `ci-by-hand-live` | operator | Requires: push access to `github.com/windaddict/font-design-skill` and `gh` logged in; the branch pushed. Steps: `git push origin feature/face-folder-contract`; `gh workflow run ci.yml --ref feature/face-folder-contract`; `gh run list --workflow ci.yml --branch feature/face-folder-contract --limit 1` then `gh run watch <id>`: every job (lint, test on four machines) concludes success. CI does not run on push, so a branch never run by hand has no CI result. Accepts `release-0-8-0` (a release is layer 4 with `--full`, then layer 5). |
| `tags-push` | operator | Requires: push access to `github.com/windaddict/font-design-skill`; the merge of `feature/face-folder-contract` into `main`. Steps: `git push origin v0.1.0 v0.2.0 v0.3.0 v0.3.1 v0.4.0 v0.5.0 v0.6.0 v0.7.0 v0.7.1`; after the merge `git tag v0.8.0 <merge commit>` and `git push origin v0.8.0`; `git ls-remote --tags origin` lists ten tags; the GitHub archive URL for `v0.7.1` answers 200 (which `fetch-version-live` then exercises). |

Mutation-proof items: none. Every `test-new` item is red-green, because every one of its tests asserts behaviour
that does not exist on the 0.7.1 tree (a missing script, a missing key, a missing section, a wrong exit code).

Not done in this run, stated: the two site migrations and the `~/.claude` pointer (per-site runs);
`templates/platform-shots.yml` keeps its commit-SHA pin; `scripts/check-env.py` does not print the skill version
(`cat VERSION` does); `references/generator.md`'s historical note about a site patching its copy of `gen.js` stays
as history.
