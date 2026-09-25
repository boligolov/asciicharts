# Roadmap

What is still to do. Done work is in the git history; how the project is laid out and tested is in
[docs/development.md](docs/development.md). Remove an item in the same commit that finishes it.

The skill (`skills/asciicharts/`) is the main product; the principles (`docs/spec/`), the conformance suite
(`test/conformance/`) and the two renderers (`go/`, `python/`) serve it.

## Release

- [ ] **Merge `knowledge-first` into `master`.** The plugin marketplace
      (`/plugin marketplace add boligolov/asciicharts`) reads the default branch, so installing the skill
      as a Claude Code plugin works only after the merge.
- [ ] **Deploy the site** so that asciicharts.online serves the current page and
      `asciicharts.online/asciicharts.skill`, the download the README and the site link to.
- [ ] **First Go release**: push a tag `go/v1.0.0` (it must equal `asciicharts.Version`). It is the first
      real run of `.github/workflows/release-go.yml` — check that the six archives and `checksums.txt`
      appear on the release page, then the install instructions in `go/README.md` are true.
- [ ] **Submit the plugin to the community directory** (`claude-community`): after the merge, with the
      repository public, submit its link at [platform.claude.com/plugins/submit](https://platform.claude.com/plugins/submit)
      (see [docs/development.md](docs/development.md#listing-it-in-claudes-plugin-directories)). The owner's step.

## Open work

- [ ] **ExCSV in Go** — `#!excsv` files: `#column` roles, `#chart` suggestions, `--chart-name`,
      `--list-charts`, checked against the Python reader on `python/tests/golden/excsv_fixtures/` and with
      `test/parity/cli_parity.py`. Until then the Go CLI refuses an ExCSV file with a message that points to
      the Python CLI, and the skill says ExCSV needs the script.
- [ ] **The link-preview image** (`site/public/og.png`, from `site/src/pages/og.astro` via
      `scripts/og_image.py`) still carries the old tagline, "Charts for the places images can't go";
      regenerate it with the skill-first wording.
- [ ] **`docker build -f deploy/Dockerfile`** has never been run (the Docker daemon was down); build the
      image once and try `docker run --rm -e PORT=8080 -p 8080:8080 asciicharts` against `/healthz` and `/mcp`.

## Ideas, not decided

- **Column counting for weaker models.** The 1.6 evals ([test/evals/README.md](test/evals/README.md)): with
  the skill, Haiku's remaining mistakes are almost all one column off — a zero axis moved in one row, a
  frame broken by a long or CJK label. The self-check now asks for both; a re-run showed no regression, but
  one run per prompt cannot show an improvement either.
- **Evals with `claude plugin eval`.** Claude Code can run a plugin against a set of prompts with and
  without it; the hand-drawn evals and their grader could move onto it and run before each skill release.

## Working rules

- One logical change per commit. Commit messages end with the `Co-Authored-By` line.
- Work on a branch, not on `master`; the owner merges.
- Run the full test suite before every commit (`pytest` from the root, `cd go && go test ./...`) and read
  its last line: **a pipe (`| tail`) hides the exit code** — this already let a broken test into a commit once.
- A change to the skill bumps its version (`SKILL.md` `metadata.version` and its `plugin.json`), then
  `python scripts/package_skill.py --site`.
- A deliberate change in rendering is a new version of the principles: regenerate the suite
  (`scripts/conformance_refresh.py`), check that every changed case is one the change is about (count them
  by chart type) before writing them, and record it in `docs/spec/CHANGELOG.md`; change both implementations.
- Examples in docs are generated from specs, never hand-edited (`scripts/gallery_refresh.py`,
  `scripts/site_examples.py`, `scripts/sync_skill.py`, each with `--check`).
- On Windows, Python writes CRLF by default: write files with `newline="\n"`. Heredocs mangle `\n` inside
  Python strings — put non-trivial edit scripts in a file.
