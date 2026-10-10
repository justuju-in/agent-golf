# Agent Golf

Solve the problem. Spend fewer tokens.

Students solve a [Hackattic](https://hackattic.com) problem with the [Pi](https://pi.dev) coding agent, type `/golf-submit`, and land on a leaderboard ranked by fewest total tokens (ties: fewer prompts, then fewer characters typed).

This is the one-day MVP of [Arnav's Agent Golf plan](https://sites.arnavg.in/plans/agent-golf/): Pi only, Hackattic for correctness, trusted students.

## Start here

- Rules, scoring and the plugin↔website contract: [`docs/spec.md`](docs/spec.md)
- Who is building what: [`.agents/plans/README.md`](.agents/plans/README.md)
- Working with an AI agent in this repo: open it in Claude Code, Codex or Pi; the agent reads [`AGENTS.md`](AGENTS.md) first. Point it at your own plan file.

## Layout

| Path | What |
|---|---|
| `server/` | Website, upload API, and `counter/` (scoring) |
| `plugin/` | Pi extension: `/golf-login`, `/golf-submit` |
| `samples/` | Redacted Pi session logs used as test fixtures |
| `tools/check.sh` | The gate: `bash tools/check.sh` |

Set up with the [agentic workflow playbook](https://github.com/justuju-in/agentic-workflow-playbook).
