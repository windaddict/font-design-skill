# The face folder

WHAT IT'S FOR: the contract between a site and the skill. A site keeps only the face it ships, in one
folder; every skill command runs from where the skill is installed and takes the path to that folder's
`font.json`. Nothing of the skill's code is copied into the site, so a skill update reaches a site
without a diff of two script folders, and the folder says by itself which skill version built it.

Contents: 1 What is in the folder; 2 Working directory; 3 The version record; 4 The three commands;
5 Comparing renderings across versions; 6 Migration from a copied scripts folder; 7 Version discipline.

Terms used here. **Face folder**: the folder holding `font.json` for one typeface, conventionally
`tools/<face>/` in the site repository. **Skill folder** (`<skill>` in commands): the folder that holds
`SKILL.md` (SKILL.md, "Finding the skill folder"). **Recorded version**: the `skill_version` that
`build.py` wrote into `manifest.json`. **Installed version**: the text of `<skill>/VERSION`.

## 1. What is in the folder

| File | Required | Written by | Read by |
|---|---|---|---|
| `font.json` | yes | the operator and the agent, from `templates/font.example.json` | every tool |
| `concepts.js` | yes; `font.json` names it | the concept rounds (phase 3) | `build.py`, `export.js`, the suite |
| `requirements.json` | yes for `build.py`, unless `--no-requirements`; yes for the suite | phase 2 | `build.py`, the suite, `mutate.py`, `specimen.py` |
| `skeletons.js` | no; `font.json` names it as `"skeletons"` | the design-review rounds | `export.js`, `build.py` |
| the build output | yes once built | `build.py` | the site, `build.py --check`, the suite |

The build output sits where `font.json`'s `out_dir` and each group's `file` key put it: one woff2 per group,
and `manifest.json` (by default in `out_dir`). `manifest.json` records the hashes of the woff2 files and of
the sources, and `skill_version`. Its schema is `templates/manifest.schema.json`; `skill_version` is optional
there because a manifest built before 0.8.0 has none.

Not in the folder: no `scripts/`, no copy of the font suite, no screenshots. The font suite
(`scripts/tests/test_font.py`) and the mutation harness (`scripts/tests/mutate.py`) stay in the skill and
run against any face folder. The site keeps its own tests: the filled
`scripts/tests/test_site_wiring.py.tmpl`, the page-character check and the font URL check.

**Path rule.** A path written inside `font.json` (`out_dir`, `concepts`, a group's `file`) resolves relative
to the directory of `font.json`. A path given on the command line resolves relative to the working
directory, as the shell expects.

## 2. Working directory

Every command in the docs names where it is typed. A site has no `scripts/`, so a command for a face in a
site is typed from the SITE ROOT. The interpreter and the script are rooted at `<skill>`, the skill's own venv
and its own script. Every face path is relative to the site root:

`<skill>/.venv/bin/python3 <skill>/scripts/build.py --font tools/<face>/font.json`

Use the skill's interpreter, `<skill>/.venv/bin/python3`, never a bare `python3`: only the skill's venv has
the pinned fontTools. A command for the skill's own repository (the examples, the repository tests) is typed
from the repository root in the short form, and says so.

The suite, typed from the site root:

`<skill>/.venv/bin/python3 -m pytest <skill>/scripts/tests/test_font.py -q --font tools/<face>/font.json --requirements tools/<face>/requirements.json --static-dir tools/<face>/out/static`

Pass `--static-dir none` when no statics ship. The check that the build is byte-identical:

`<skill>/.venv/bin/python3 <skill>/scripts/build.py --font tools/<face>/font.json --check`

## 3. The version record

`build.py` writes the text of `<skill>/VERSION` into `manifest.json` as `skill_version`. The skill finds its
own `VERSION` relative to its own location (the folder above `scripts/`), so the value is the version of the
code that ran. A `build.py` whose folder has no `VERSION` refuses to build and names the path it looked at.
The manifest schema string stays `font-design/manifest/v1`, because a reader of v1 is not broken by one
added key.

`build.py --check` compares a rebuild with the shipped files and the manifest. A manifest built by another
skill version differs on `skill_version`, so `--check` fails after a skill update until the face is rebuilt.
That is intended: the manifest says what built the woff2.

**One VERSION, one font output.** Two installs with the same `VERSION` produce the same font output (the same
woff2 bytes for the same face folder). That is a guarantee about font output, not about every file in the
repository: a later commit under one `VERSION` may change CI, docs or tests, never font output.

**The 0.6.0 case.** Version 0.6.0 names two different font sources: the tag `v0.6.0` is commit 1c032ad, and
unreleased code at c5b4abb also set `VERSION` to 0.6.0 with different `gen.js` and `export.js`. A face built
by the second cannot be rebuilt from the tag. So:

- `fetch-version.py 0.6.0` refuses before it tries any route. It prints "0.6.0 is ambiguous" with both commits
  and exits 1. It writes nothing and has no flag to pick a commit. Get the code that built your face by hand
  from a git checkout of the skill: `git -C <skill> archive 1c032ad` or `git -C <skill> archive c5b4abb`,
  extracted into the folder you want.
- `update-check.py` does not fetch the recorded version, so it does not refuse. When the recorded version is
  0.6.0 (reachable only through `--recorded 0.6.0`, because manifests record nothing before 0.8.0), it prints
  the notice on stderr and writes it into `update.md` (a `## Notice` section) and `update.json` (`notices`).

No face in use records 0.6.0 today. The rule that forbids a new case is in section 7.

## 4. The three commands

All three are typed from the site root.

**`diff.py`**: which renders and which values changed between two builds of the face, for the design-review
loop and for any before and after pair.

`<skill>/.venv/bin/python3 <skill>/scripts/diff.py work/diff --font tools/<face>/font.json --before work/round-3`

`--before` and `--after` hold each group's file under its FILE NAME (the name part of the group's `file` key),
so a `file` such as `../../static/F-VF.woff2` is found as `F-VF.woff2` in the folder. Without `--after`, the
after side is the shipped files where `font.json` puts them. Two groups with one file name are refused (exit 2).
The report has two sections. `## By value` compares the tables: glyph order and cmap, each glyph's default
outline, variation tuples and metrics, the outline and advance at every named instance, the layout tables,
GPOS pair adjustments, the platform-3 name records (for other platforms, only whether each platform is present) and the
`head`, `hhea` and `OS/2` fields, and the kerning HarfBuzz applies to every two-character string of the characters both
fonts map (N characters make N*N strings per named instance, so the time grows with the square of the character set). `## Renders` is the FreeType pixel diff of the titles.
Exact guarantee: by value covers those tables and two-character shaping, not contextual features or longer
strings; renders are FreeType on this machine, not a browser. The exit status is 0 whether or not anything
differs.

**`fetch-version.py`**: put the skill's own code at a released version into a folder, so an old build can be
reproduced.

`<skill>/.venv/bin/python3 <skill>/scripts/fetch-version.py 0.7.1 work/skill-0.7.1`

Route one: from a git checkout of the skill, `git archive` of the tag `v<version>`. The skill folder must be the
checkout's top folder: a copy of the skill inside another repository (a site that commits it) does not count,
because that repository's tags are its own releases. Route two, when the skill is not a checkout or route one fails: the GitHub tag archive for that version (`--archive-url URL` replaces the
whole URL; `file://` works). The code is extracted into a temporary folder beside the target and moved into
place only after its `VERSION` reads exactly the requested version; on any failure the target is not created
and the temporary folder is removed. Exit 0 on success, 1 on any failure, naming what each route reported.
Run the fetched code with the installed venv:
`<skill>/.venv/bin/python3 work/skill-0.7.1/scripts/build.py --font tools/<face>/font.json --out-dir work/rebuilt-0.7.1`.
Guarantee: the tree at the tag as the remote or the checkout serves it. It is not a signature check.

**`update-check.py`**: what would the installed skill change in this shipped face.

`<skill>/.venv/bin/python3 <skill>/scripts/update-check.py work/update --font tools/<face>/font.json`

Steps, in order:

1. OUT must not be the face folder or inside it (exit 1), so the report is never written next to the face. OUT must
   also be a new folder, an empty one, or the OUT of an earlier update check: a folder holding any other file is
   refused (exit 1, the files named) before anything is written or removed, because each run replaces `update.md`,
   `update.json` and `diff/` there. A run leaves a `.update-check` file in OUT; that file, not the names of the other
   entries, is what marks a folder as an earlier update check's OUT. Give a folder of its own, such as `work/update`,
   never a site root.
2. The recorded version is the manifest's `skill_version`, or `--recorded VERSION` for a face built before
   0.8.0. A manifest with none and no `--recorded` is an error naming the flag. Both given and different is an
   error.
3. Equal to the installed version: it prints `up to date`, writes nothing and exits 0.
4. Different: it runs the drift check, rebuilds the face with the INSTALLED skill into a temporary folder
   (with the manifest's `requirements` setting), runs `diff.py` on the shipped files against that build, and
   writes `update.md`, `update.json` and `diff/` into OUT. It also hashes each shipped woff2 against the rebuild:
   `update.json` `bytes_identical` and the report's `## Bytes` section say, per group, whether the bytes match. The
   by-value section does not compare every table (`post`, for one), so bytes can differ when no listed value does;
   the report then says so instead of calling the fonts identical.

The drift check hashes each shipped woff2 and compares it with the manifest's `woff2_sha256`, and hashes
`font.json`, `concepts.js` and the skeletons file and compares them with `sources_sha256`. A mismatch is not an
error: the report labels it `## Drift` and says the differences cannot be attributed to the skill update.
The requirements file is not hashed by the manifest, so that input is not checked. A missing shipped woff2 is
an error naming it.

**The limit of the drift check.** A clean drift check proves manifest consistency only: the shipped files hash
to what `manifest.json` says. The manifest is an editable file, so a font changed together with its recorded
hash passes. It does not prove the shipped font is the output of the recorded skill version. So whenever any
group differs, the report says: "Attribution to the skill update is unverified: the drift check proves the
shipped files match manifest.json, not that they are the output of the recorded version; only a rebuild at
the recorded version (fetch-version.py) would." `update.json` carries `"attribution": "unverified"`. A rebuild
at the recorded version, from `fetch-version.py`, is the check that would verify it; no command does that
comparison for you.

A failed build, a failed `diff.py`, or any other error after the OUT checks (a file it cannot read, a copy that
fails) is exit 1 and writes no report. It also tries to remove the `update.md`,
`update.json` and `diff/` an earlier run left in OUT, because that report described a different state, and says
whether it did; when the filesystem refuses a removal it names each file still there. A report is complete if and only if `update.md` exists: it is moved into place last.

Exit codes: 0 up to date, or no difference in any group and identical bytes; 3 a difference by value, a changed
render, drift, or woff2 bytes that differ from the rebuild;
1 an error. The update check never writes into the face folder. The operator approves an update by running the
`build.py` line printed at the end of `update.md` (it carries the requirements flag the check itself used),
then commits the woff2 files and `manifest.json`.

What the update check proves: the installed skill's build differs from the shipped files by value and by
FreeType render on this machine, or it does not. It does not run a browser.

## 5. Comparing renderings across versions

To see how a skill update changes pixels in a browser: fetch the recorded version
(`fetch-version.py`, section 4), build it with `--out-dir` into one folder, build the installed version into
another, and shoot both with `shoot.py` (`references/review-loop.md`). No PNG is stored in the repository.

## 6. Migration from a copied scripts folder

For a site that carries the skill as a submodule and a copy of `scripts/` under `tools/<face>/`:

1. Delete the submodule: `git submodule deinit`, remove its `.gitmodules` entry and its path. Install the
   skill where the host loads skills from.
2. Delete `tools/<face>/scripts/`.
3. Keep `font.json`, `concepts.js`, `requirements.json`, `skeletons.js`, the woff2 files and `manifest.json`,
   and the site's own tests (the filled wiring template, the page-character check, the font URL version
   check). Add nothing to the site's docs except the skill's install path.
4. First update check, from the site root, naming the version the submodule pinned (the `VERSION` file of the
   pinned commit), because the old manifest records none:
   `<skill>/.venv/bin/python3 <skill>/scripts/update-check.py work/update --font tools/<face>/font.json --recorded <pinned version>`
5. Read `update.md`. When it reports no difference, adopt the new version with
   `<skill>/.venv/bin/python3 <skill>/scripts/build.py --font tools/<face>/font.json`, and commit the woff2
   files and the manifest, which now carries `skill_version`.

## 7. Version discipline

Any change that alters font output (`scripts/gen.js`, `scripts/export.js`, `scripts/build.py`, the defaults
they read) bumps `VERSION` in the same change. Every CHANGELOG entry has a line `Font output: unchanged` or
`Font output: changes: <what>`. Every released version gets a tag `v<version>` on the first `main` commit that
carries it, pushed after the merge. The CHANGELOG's `## Releases` section lists the tags.
