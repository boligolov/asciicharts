# Installing the skill

The skill is the folder [`skills/asciicharts/`](../skills/asciicharts/): `SKILL.md`, `references/` — the principles,
a hand-drawing guide and a glyph cheat sheet — and the one-file renderer in `scripts/asciicharts.py`. It is
self-contained — copy the folder and you are done. It teaches the agent to draw text charts itself and to
use an exact renderer (the MCP server, or the script) when one is available.

Agents find skills in known folders or in an uploaded package: they read each skill's `name` and
`description` from the `SKILL.md` frontmatter, and load the rest only when a task matches. For Claude Code
the repository is also a **plugin marketplace** (`.claude-plugin/marketplace.json`) with one plugin: this
skill.

## Claude Code

**As a plugin** (recommended — updates arrive with `/plugin marketplace update`):

```
/plugin marketplace add boligolov/asciicharts
/plugin install asciicharts@asciicharts
```

The same from a shell: `claude plugin marketplace add boligolov/asciicharts`, then
`claude plugin install asciicharts@asciicharts`. Remove it with `/plugin uninstall asciicharts@asciicharts`.

**As a folder**, if you prefer to manage the files yourself — pick one:

| scope | folder | when to use |
|---|---|---|
| personal — every project on this machine | `~/.claude/skills/asciicharts/` (Windows: `%USERPROFILE%\.claude\skills\asciicharts\`) | you want it everywhere |
| project — everyone who works on one repository | `<project>/.claude/skills/asciicharts/` | commit it so the team gets it too |

```sh
# personal, macOS / Linux
mkdir -p ~/.claude/skills && cp -r skills/asciicharts ~/.claude/skills/

# personal, Windows (PowerShell)
Copy-Item -Recurse skills\asciicharts $env:USERPROFILE\.claude\skills\asciicharts

# project
mkdir -p .claude/skills && cp -r /path/to/repo/skills/asciicharts .claude/skills/
```

Start a new session so the skill is discovered. To check, ask the agent which skills it has, or just ask for
a chart ("plot these numbers as a bar chart, plain text": 62, 21, 12, 5). The folder name must match the
`name` in the frontmatter (`asciicharts`).

**Requirements:** none to draw charts — without a tool the agent draws them by hand from
`references/drawing.md`. With the MCP server connected, the `asciicharts` command on the PATH (a single
binary from the [releases](https://github.com/boligolov/asciicharts/releases)), or `python` (or `python3`),
they are rendered exactly. Nothing is installed.

## Claude.ai and Claude Desktop

Download **[asciicharts.skill](https://asciicharts.online/asciicharts.skill)** and upload it under
*Settings → Capabilities → Skills* (it needs a plan that includes skills and code execution enabled; the
wording may differ between versions). A `.skill` file is a zip archive: the folder `asciicharts/` with
`SKILL.md` directly inside.

To build it from a checkout instead: `python scripts/package_skill.py` writes `dist/asciicharts.skill`. The
build is deterministic, and a test checks that the copy the site serves (`site/public/asciicharts.skill`) is
the current skill.

## Claude API and other agents

The same folder or zip can be uploaded through the API's skills endpoint (see Anthropic's documentation for
the current request format). Agents that follow the open skill convention only need the folder in the place
they scan; anything without skill support can use the [MCP server](../go/cmd/asciicharts-mcp/README.md) instead.

## Updating, removing

- **Update:** as a plugin, `/plugin marketplace update asciicharts`; as a folder, replace it with the new
  version (delete the old one first so no stale files remain); on Claude.ai, upload the new `.skill`.
- **Remove:** `/plugin uninstall asciicharts@asciicharts`, or delete the folder.
- **Working on the skill itself:** the script inside the skill is a copy of the repository's `asciicharts.py`;
  after editing the original run `python scripts/sync_skill.py` (a test fails if the copy is stale).

## Skill or MCP server?

| | skill | MCP server |
|---|---|---|
| needs | nothing (draws by hand); a shell and Python for exact rendering | an MCP client |
| input | JSON spec, or a CSV file straight from disk | JSON tool arguments |
| good for | Claude Code and other agents that run commands | any MCP client, or one shared always-on deployment |

They render identically and work best side by side: the skill knows how to choose and read a chart, and
uses the server as its renderer when it is connected.

## Listing it in Claude's plugin directories

Anthropic runs two public marketplaces: `claude-plugins-official` (curated by Anthropic, no application) and
`claude-community` (third-party plugins, after review). To submit this plugin to the community one, the
repository must be public on GitHub and pass `claude plugin validate .` (a test runs it); then submit the
repository link through the Console form, [platform.claude.com/plugins/submit](https://platform.claude.com/plugins/submit)
(or, for a Team or Enterprise organization, the claude.ai directory form). Once approved it is pinned to a
commit in [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community) and
follows new commits automatically; users then install it with
`/plugin install asciicharts@claude-community`.
