# Releasing agent-golf

Maintainer instructions for the private source repository. This file and DEVELOPMENT.md are excluded from the public npm artifact. The student README is the published usage guide.

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
4. From `plugin/` inspect `npm pack --dry-run --json`. The only files should be package.json, README.md, LICENSE and the six runtime TypeScript modules. Never include tests, logs, server code, planning material, development/release guides or credentials. Host-provided Pi packages stay peer dependencies and are not bundled.
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
# Stable, only after live readiness is verified:
npm publish "$TARBALL" --access public --tag latest --registry=https://registry.npmjs.org/

# OR approved preview; do not run both commands:
npm publish "$TARBALL" --access public --tag preview --registry=https://registry.npmjs.org/
```

Complete npm's authentication prompt yourself. Do not paste its credentials into agent tools. If npm returns E403 requiring two-factor authentication or an authorized bypass token, stop: confirm/enable publishing 2FA and refresh login in your own terminal before retrying. Do not automatically create tokens or weaken authentication settings. Check registry state first so an uncertain result cannot cause an accidental duplicate release. A preview is publicly downloadable; its tag is not access control. Testers explicitly install `npm:agent-golf@preview`. A preview can use version 0.1.0; if unchanged code later passes live verification, its tag can be promoted without republishing.

## Verify after publication

```bash
npm view agent-golf versions dist-tags --json --registry=https://registry.npmjs.org/
pi install npm:agent-golf@0.1.0   # Replace with the just-published version.
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
