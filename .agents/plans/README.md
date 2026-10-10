# Plans

Format and workflow: `.agents/skills/planning/SKILL.md`.

## Active

| Plan | Owner | Status |
|---|---|---|
| [001 — Step 0, all three together](./001-step-0.md) | Anup, Amit, Prateek | created |
| [002 — Website, Docker and website deployment](./002-website.md) | Anup | created |
| [003 — Counter](./003-counter.md) | `<name>` | created |
| [004 — Pi plugin and going live](./004-plugin-and-deploy.md) | `<name>` | created |

## Conventions

- Filename: `NNN-kebab-slug.md`, zero-padded, sequential. Find the next number with `ls .agents/plans | grep -E '^[0-9]{3}-' | sort | tail -1`. Never reuse a number.
- Frontmatter: `name, description, status (created|started|completed), created, updated`.
- Progress checklist at the top; Validation section; Decisions table; Changelog at the bottom.
- Completed plans move to [`./archive`](./archive/README.md). Never delete a plan.

## Related plan guidance

- Rules, scoring and the plugin↔website contract live in [`docs/spec.md`](../../docs/spec.md); plans link to it rather than restating it.
