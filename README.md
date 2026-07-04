# Icon Designer Skills

[![CI](https://github.com/Paldom/icon-designer-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/Paldom/icon-designer-skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Agent Skills that design minimalist app and OSS package icons from a text brief or project context - symmetric logos on dark grey, Apple-style rounded-rectangle backgrounds.

Agent Skills for [Claude Code](https://code.claude.com/docs/en/skills) (and any
[Agent Skills](https://agentskills.io)-compatible tool). Each skill is a folder under
[`skills/`](skills/) with a single-purpose `SKILL.md`, trigger evals, and optional
scripts/references — validated on every write, commit, and PR.

## Quick start

Install everything as a plugin (recommended; needs read access while the repo is private):

```
/plugin marketplace add Paldom/icon-designer-skills
/plugin install icon-designer-skills@icon-designer-skills
```

Or copy a single skill into a project:

```bash
git clone https://github.com/Paldom/icon-designer-skills.git
cp -r icon-designer-skills/skills/<skill-name> your-project/.claude/skills/
```

Then just describe the task in Claude Code — the skill activates on its description —
or invoke it explicitly with `/<skill-name>`. To run the whole pipeline
(brief → draw → critique → export) against a repo in one supervised session, paste
the ready-made goal prompt from [docs/setup-prompt.md](docs/setup-prompt.md).

## Skills

| Skill | Description |
| --- | --- |
| [icon-brief](skills/icon-brief/) | Derives a minimalist icon design brief from a text prompt or the current repo — 3-5 symbol concepts (one Gestalt device each), symmetry axis, house palette, distinctiveness notes. |
| [icon-draw](skills/icon-draw/) | Draws the icon as a master 1024×1024 SVG — symmetric glyph on a dark grey rounded-rectangle (Apple-style radius) — as 2-4 lint-clean candidates ready for critique. |
| [icon-critique](skills/icon-critique/) | Renders candidates at 512/64/32/16 px and reviews the pixels against a fixed rubric, applying targeted SVG fixes with a hard iteration cap before the human picks a winner. |
| [icon-export](skills/icon-export/) | Exports the approved master SVG to platform assets — favicon set, PWA/maskable, App Store/Play PNGs, macOS icns, GitHub social preview — with overwrite guards and size validation. |

## Repository structure

```
skills/                  # distributed skills, one folder per skill (SKILL.md + evals/ + scripts/)
docs/                    # skill-authoring guide, eval methodology
scripts/                 # deterministic validator used by hooks and CI
.claude/                 # agentic dev setup: hooks + the bundled add-skill skill
.claude-plugin/          # plugin + marketplace manifests (makes this repo installable)
.local/                  # gitignored working area: sources, research, PROMPT.md (see below)
```

## Working on this repo with an agent

This repo is agent-native: canonical agent instructions live in
[AGENTS.md](AGENTS.md) (CLAUDE.md imports it), hooks validate every `SKILL.md` on
write, `make check` runs the full validator, and CI enforces the same gate on every
PR. The bundled `add-skill` skill walks the eval-first authoring workflow described
in [docs/skill-authoring.md](docs/skill-authoring.md). Maintainers drive sessions
with their own (gitignored, personal) `.local/PROMPT.md` goal prompt.

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the skill-proposal
process, the authoring workflow, and the PR checklist. Please note the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Support

Questions, ideas, or something not working? Start with [SUPPORT.md](SUPPORT.md) —
bugs and skill proposals have [issue templates](../../issues/new/choose), and
security concerns go through [SECURITY.md](SECURITY.md) (never a public issue).

## License

[MIT](LICENSE) © 2026 Paldom
