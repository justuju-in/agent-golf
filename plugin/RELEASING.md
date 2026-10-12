# Releasing agent-golf

Maintainer instructions for the private source repository. This file and DEVELOPMENT.md are excluded from the public npm artifact. The student README is the published usage guide.

## Current release handoff (2026-10-12)

- User approved `0.1.1`, keeping read-only browser views, switching the default/homepage to `https://agent-golf.csbasics.in`, publishing to `latest` and moving `preview` to the same version. Rebase remains parked; prepare from original feature/plan-004.
- Production catalogue at the new hostname returns HTTP 200. Website 85718a5 activates the real counter; its unmodified local source passed 127 backend tests, published 0.1.0 passed 101 plugin integration tests and 11 scoring replays. Fresh solved production submission remains unverified: this URL/channel release is approved, not a claim of complete competition readiness.
- Backend deployment must also set `AGENT_GOLF_API_BASE_URL=https://agent-golf.csbasics.in`, since upload replies contain absolute submission URLs. Plugin overrides remain explicit and credentials never migrate between origins; users update/reload and log in again.
- Source release commit: `42013d6`, original feature/plan-004. After login/owner verification, assistant publish stopped at EOTP; operator published the exact reviewed tarball interactively. Registry metadata and downloaded sha512/shasum match the reviewed artifact. `latest` now points at 0.1.1; never republish it.
- Registry-installed exact 0.1.1 passed 101/101 local website integration tests. Fresh unversioned install resolved 0.1.1; its /golf-problems reached production with no origin override, login, model calls or session changes.
- `preview` and `latest` both verified at 0.1.1. Operator handled tag MFA privately; no credentials/auth URLs/codes used by assistant or stored in repo, no policy weakening. A genuine isolated preview install advanced from 0.1.0 to 0.1.1 with `pi update --extensions`, preserving source/settings and verifying csbasics.in default/homepage; user also confirmed their update worked. Do not touch the user's installed plugin/credentials. Exact-version pins still require explicit replacement.
- User authorized normal feature/plan-004 source push and current-main integration after the gate; parked rebase will not be adopted. Next release must change the browser's legacy "any model, one per session" wording to "any model" for mvp-3, including docs/tests; published 0.1.1 cannot be overwritten. Keep model_switched response handling for legacy rows. The live catalogue version is read dynamically, not pinned in the plugin.

## Previous release snapshot (2026-10-11)

- `agent-golf@0.1.0` is already published. Its downloaded integrity matches the reviewed artifact; do not publish that version again.
- Fresh Pi registry installs through both `npm:agent-golf@preview` and `npm:agent-golf@0.1.0` passed the local website integration gate (92/92). Install/update/removal also passed in isolated settings; no later-version upgrade was tested because no later release exists.
- Registry currently has **both preview and latest pointing to 0.1.0**. Removing latest returned E400; tags were left unchanged. This is still a preview in readiness terms: a tag is not scoring verification. Check current tags with `npm view agent-golf dist-tags --json --registry=https://registry.npmjs.org/` rather than assuming the initial snapshot is current.
- Production catalogue DNS resolution failed from the test machine; the tested website still uses the stand-in counter. Real counter alignment/wiring, deployment and a real solved/live E2E remain required before student distribution. Follow the owner-assigned checklist below.
- Backup npm invitations are pending confirmed usernames and acceptance. Existing maintainer instructions below explain permissions; do not assume source-repository access grants publishing access.
- For a stale ETARGET during preview installation, retry `npm_config_prefer_online=true pi install npm:agent-golf@preview`. If needed, use a fresh temporary npm cache rather than clearing the user's entire cache.
- Read [DEVELOPMENT.md](DEVELOPMENT.md) for local/registry verification commands, [README.md](README.md) for the public install guide, and the [owner plan](../.agents/plans/004-plugin-and-deploy.md) for dated evidence and pending work. This private guide is not shipped to npm.

## Prerequisites

- Agreed package: `agent-golf`, public npm, plugin-only MIT; first version `0.1.0`.
- Node 22.19+, npm, Pi, and permission to publish this package.
- Authenticate interactively with `npm login` when needed. Check `npm whoami --registry=https://registry.npmjs.org/` before release; login can expire and publishing may require additional 2FA/browser authorization.
- Never put npm tokens/passwords in source, shell scripts, repository `.npmrc`, chat or committed logs. No CI publishing is required for the MVP.
- Stable release requires live website catalogue/submission verification and a fresh-install E2E. Otherwise obtain explicit approval for a preview and label the README with its limitations. Preparing a package is not permission to upload it.

## Maintainer access

After the first publication, an existing owner can invite the other maintainers using their confirmed npm usernames:

```bash
npm owner add <anup-npm-username> agent-golf --registry=https://registry.npmjs.org/
npm owner add <amit-npm-username> agent-golf --registry=https://registry.npmjs.org/
npm owner ls agent-golf --registry=https://registry.npmjs.org/
```

Invite only trusted accounts approved by the team. Each invitee must accept the invitation, then use their own `npm login` and 2FA. Confirm their account appears in the owner list before relying on it for release coverage. Do not share another maintainer's credentials. Publishing access is not limited to previews; owners can publish versions and manage release tags, so treat this as privileged access.

Backend deployment is separate: the website owner must document its deployment procedure and arrange repository/infrastructure permissions for the backup deployer. npm access alone does not grant those permissions. Ensure the release commit and this guide are available in the team's private repository before the primary maintainer is unavailable.

## Finish the first release without Prateek

Initial artifact: `agent-golf@0.1.0`, approved for the `preview` channel. No `latest` promotion is authorized by the initial preview approval. Check registry state before publishing; if the version already exists, do not try to publish it again.

1. **Amit — counter:** merge current main into the counter branch, align `any`, `model_switched`, actual-answer-only setup, optional summary usage and solved evidence with the current spec; include reviewed redacted samples and a solved sample. Run the counter suite and merge through the agreed team workflow.
2. **Anup — website:** merge/integrate the real counter and replace the stand-in import. Run website tests, use the website deployment runbook, and verify production DNS/TLS and the catalogue/login/upload routes. Never use stand-in verdicts for the contest.
3. **Releasing maintainer — verification:** run the repo gate with both local website opt-ins from DEVELOPMENT.md against the integrated website. Then fresh-install the published preview and run a team-approved real solved attempt against production; verify expected metrics/verdict, repeat submission, board row and public-page privacy. A synthetic transport test is not proof of a correct score. Use your own disposable account/key, never a student's credentials.
4. **Releasing maintainer — stable:** obtain team approval after these checks. If plugin code and the initial-publication README remain accurate, promote the exact verified version using the tag command below. If plugin code or student-facing documentation must change, update README for stable usage, bump the version (for example to 0.1.1), gate/review/commit/pack and publish the new version with `--tag latest`. Backend-only fixes do not inherently need a plugin release.
5. **Team — distribution:** verify registry install/update again, communicate the exact supported version and stable install command to students, and record the release version/commit and live E2E evidence in the owner plan. Already-installed previews do not automatically switch channels.

## Prepare one reviewed release commit

1. Work on the plugin owner branch. First publication already has version `0.1.0`; do not bump unnecessarily. For subsequent releases, from `plugin/` run:

   ```bash
   npm version patch --no-git-tag-version
   # Use minor or major for the appropriate compatibility change.
   ```

   Published versions cannot be overwritten. The flag avoids automatic Git commits/tags so the repository's review workflow remains in control.

2. Update the student README/release notes and owner plan. Keep README's release notice and primary install command accurate for the chosen stable or preview channel. Keep maintainers' workflow and private development details out of that README.
3. From the repo root run `bash tools/check.sh`. It packs the package into a temporary directory, verifies the exact file allowlist/manifest and loads the extracted artifact in isolated Pi. For real website login and packed-plugin transport/UI coverage, also run the gate with `AGENT_GOLF_WEBSITE_DIR` and `AGENT_GOLF_E2E_WEBSITE_DIR` pointing at a current prepared website checkout (see DEVELOPMENT.md). Transport tests using stand-in scoring do not satisfy stable-release readiness.
4. From `plugin/` inspect `npm pack --dry-run --json`. The only files should be package.json, README.md, LICENSE and the seven runtime TypeScript modules (including problem-view.ts). Never include tests, logs, server code, planning material, development/release guides or credentials. Host-provided Pi packages stay peer dependencies and are not bundled.
5. Review and commit the release metadata/code/docs together. Do not update HANDOFF.md or the shared plans index on the feature branch. Do not publish an unreviewed or dirty working tree.

## Publish the reviewed artifact (separate external action)

From `plugin/`, with a clean, reviewed source tree:

```bash
npm whoami --registry=https://registry.npmjs.org/
ARTIFACT_DIR="$(mktemp -d)"
npm pack --json --pack-destination "$ARTIFACT_DIR"
TARBALL="$ARTIFACT_DIR/agent-golf-$(node -p "require('./package.json').version").tgz"
tar -tzf "$TARBALL"
```

Inspect the output, record the release commit and choose the explicitly approved channel. Publish the exact inspected tarball, not another working copy:

```bash
# Explicitly approved latest release; a tag alone is not scoring verification:
npm publish "$TARBALL" --access public --tag latest --registry=https://registry.npmjs.org/

# OR approved preview; do not run both commands:
npm publish "$TARBALL" --access public --tag preview --registry=https://registry.npmjs.org/
```

Complete npm's authentication prompt yourself. Do not paste its credentials into agent tools. If npm returns E401 (expired/invalid login) or E403 requiring two-factor authentication or an authorized bypass token, stop: confirm/enable publishing 2FA and refresh login in your own terminal before retrying. Do not automatically create tokens or weaken authentication settings. Check registry state first so an uncertain result cannot cause an accidental duplicate release. A preview is publicly downloadable; its tag is not access control. Testers explicitly install `npm:agent-golf@preview`. A preview can use version 0.1.0; if unchanged code later passes live verification, its tag can be promoted without republishing.

## Verify after publication

```bash
npm view agent-golf versions dist-tags --json --registry=https://registry.npmjs.org/
pi install npm:agent-golf@0.1.1   # Replace with the just-published version.
```

Use an isolated Pi home/config for verification, not a student's installation. Check all three commands, public browser requests, real login and an approved disposable submission; record the result in the owner plan. Separately verify the intended unpinned/tagged student install command and `pi update --extensions`. Restart Pi or `/reload` after updates. Exact-version installations remain pinned and do not advance to newer versions.

Remove temporary tarballs when finished. No generated `.tgz` belongs in git.

## Tags, previews and bad releases

Publishing does not update existing clients or remove old versions. By default, unversioned installs follow `latest`; preview users explicitly select their channel. Old versions remain available.

Promote a verified unchanged preview:

```bash
npm dist-tag add agent-golf@0.1.0 latest --registry=https://registry.npmjs.org/
```

For a bad release, publish a fixed version or point latest at a known-good version, then notify affected students to update/reinstall. Moving the tag does not replace already-installed code. Deprecation adds a warning but does not block installation; unpublishing is restricted and is not the normal rollback strategy.

Before a competition, communicate the supported plugin version. Publishing alone does not enforce a minimum client version; changes to backend compatibility/enforcement need team agreement.
