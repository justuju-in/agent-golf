# Plans

Format and workflow: `.agents/skills/planning/SKILL.md`.

## Active

| Plan | Owner |
|---|---|
| [001 — Step 0, all three together](./001-step-0.md) | Anup, Amit, Prateek |
| [003 — Counter](./003-counter.md) | Amit |
| [005 — Plugin mvp-3 follow-up](./005-plugin-mvp3-follow-up.md) | Prateek |

## Completed

| Plan | Owner |
|---|---|
| [002 — Website, Docker and website deployment](./archive/002-website.md) | Anup |
| [004 — Pi plugin and going live](./archive/004-plugin-and-deploy.md) | Prateek |

## Conventions

- Filename: `NNN-kebab-slug.md`, zero-padded, sequential. Find the next number with `ls .agents/plans | grep -E '^[0-9]{3}-' | sort | tail -1`. Never reuse a number.
- Frontmatter: `name, description, status (created|started|completed), created, updated`. Status lives only in the frontmatter, never in this file, so nobody edits this file on a branch.
- Progress checklist at the top; Validation section; Decisions table; Changelog at the bottom.
- Completed plans move to [`./archive`](./archive/README.md). Never delete a plan.

## Related plan guidance

- Plugin origin, auth/upload privacy, public packaging, npm 0.1.1 and class E2E decisions: [004](./archive/004-plugin-and-deploy.md). New plugin release work resumes in [005](./005-plugin-mvp3-follow-up.md), not the archived plan.

- Rules, scoring and the plugin↔website contract live in [`docs/spec.md`](../../docs/spec.md); plans link to it rather than restating it.
- Website work (`server/` outside `server/counter/`: registration, upload and problem-list API, board, submission and rules pages, Docker, the live deployment): start from the decisions and results in [002 — Website](./archive/002-website.md), and `server/README.md` ("Live site") for deploy steps.
