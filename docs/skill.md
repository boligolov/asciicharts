# Installing the skill

The skill is the folder [`skills/asciicharts/`](../skills/asciicharts/): `SKILL.md`, `references/` — the principles,
a hand-drawing guide and a glyph cheat sheet — and the one-file renderer in `scripts/asciicharts.py`. It is
self-contained — copy the folder and you are done. It teaches the agent to draw text charts itself and to
use an exact renderer (the MCP server, or the script) when one is available.

**There is no registry to register it with.** Agents find skills by looking in known folders (or in an
uploaded package), read each skill's `name` and `description` from the `SKILL.md` frontmatter, and load the
rest only when a task matches. Installing a skill means putting the folder where the agent looks.

## Claude Code

Pick one:

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
`references/drawing.md`. With `python` (or `python3`) on the PATH, or the MCP server connected, they are
rendered exactly. Nothing is installed.

## Claude.ai and Claude Desktop

Build the upload package, then add it in the app's skills settings (the section is usually under
*Settings → Capabilities → Skills*; it needs a plan that includes skills and code execution enabled, and
the wording may differ between versions):

```sh
python scripts/package_skill.py          # writes dist/asciicharts.skill  (a zip: asciicharts/SKILL.md, ...)
```

Upload `dist/asciicharts.skill` (a `.skill` file is a zip archive, so renaming it to `.zip` also works).
The package must contain the folder `asciicharts/` with `SKILL.md` directly inside — the script guarantees that.

## Claude API and other agents

The same folder or zip can be uploaded through the API's skills endpoint (see Anthropic's documentation for
the current request format). Agents that follow the open skill convention only need the folder in the place
they scan; anything without skill support can use the [MCP server](../server/README.md) instead.

## Updating, removing

- **Update:** replace the folder with the new version (delete the old one first so no stale files remain).
- **Remove:** delete the folder.
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
