# Plans

Format and workflow: `.agents/skills/planning/SKILL.md`.

## Active

| Plan | Owner |
|---|---|
| [001 — Step 0, all three together](./001-step-0.md) | Anup, Amit, Prateek |
| [003 — Counter](./003-counter.md) | Amit |
| [004 — Pi plugin and going live](./004-plugin-and-deploy.md) | Prateek |

## Completed

| Plan | Owner |
|---|---|
| [002 — Website, Docker and website deployment](./archive/002-website.md) | Anup |

## Conventions

- Filename: `NNN-kebab-slug.md`, zero-padded, sequential. Find the next number with `ls .agents/plans | grep -E '^[0-9]{3}-' | sort | tail -1`. Never reuse a number.
- Frontmatter: `name, description, status (created|started|completed), created, updated`. Status lives only in the frontmatter, never in this file, so nobody edits this file on a branch.
- Progress checklist at the top; Validation section; Decisions table; Changelog at the bottom.
- Completed plans move to [`./archive`](./archive/README.md). Never delete a plan.

## Related plan guidance

- Rules, scoring and the plugin↔website contract live in [`docs/spec.md`](../../docs/spec.md); plans link to it rather than restating it.
- Website work (`server/` outside `server/counter/`: registration, upload and problem-list API, board, submission and rules pages, Docker, the live deployment): start from the decisions and results in [002 — Website](./archive/002-website.md), and `server/README.md` ("Live site") for deploy steps.
