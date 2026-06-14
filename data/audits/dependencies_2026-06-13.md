# Dependency Audit

- Date: 2026-06-13
- Branch: `demo-readiness`
- Scope: Python environment visible to `python -m pip_audit`; frontend workspace at `apps/web`.
- Action taken: audit only. No dependency upgrades were applied.

## Summary

| Ecosystem | Command | Result |
| --- | --- | --- |
| Python | `python -m pip_audit --format json` | 35 known vulnerabilities across 11 installed packages. |
| Node | `npm audit --json` in `apps/web` | 5 vulnerabilities: 1 moderate, 4 high. |
| Node outdated | `npm outdated --json` in `apps/web` | Several packages have newer major versions, including Next 16 / React 19 / Tailwind 4 / TypeScript 6. |

## Python Findings

`pip-audit` was installed into the user site for this audit. It is not listed in project `requirements.txt`.

Packages flagged by `pip-audit`:

- `cryptography 46.0.3`: multiple CVEs/GHSAs fixed in `46.0.5`, `46.0.6`, and `46.0.7`.
- `idna 3.11`: DoS issue fixed in `3.15`.
- `pillow 11.3.0`: multiple image/PDF/PSD parsing issues fixed in `12.1.1` or `12.2.0`.
- `pip 25.3`: installer/path handling issues fixed in `26.0`, `26.1`, and `26.1.2`.
- `pygments 2.19.2`: inefficient regex issue fixed in `2.20.0`.
- `PyJWT 2.10.1`: critical-header validation issue fixed in `2.12.0`.
- `python-dotenv`: symlink/cross-device rewrite vulnerability fixed in `1.2.2`.
- `python-multipart 0.0.21`: path traversal / multipart DoS issues fixed through `0.0.27`.
- `starlette 0.51.0`: malformed Host header URL reconstruction issue fixed in `1.0.1`.
- `transformers 4.57.6`: checkpoint/trainer deserialization issues, one fixed in `5.0.0rc3`, one without a stable fix version in the audit output.
- `torch`, `torchaudio`, and `torchvision` CPU wheels were skipped because their local `+cpu` versions were not found on PyPI by `pip-audit`.

Risk notes:

- Some flagged packages are transitive or installed in the wider user Python environment rather than direct project requirements. Before upgrading, separate project runtime dependencies from unrelated user-site packages.
- `python-multipart`, `starlette`, and `fastapi` adjacency matters for the API because request parsing and ASGI behavior are in the product path.
- `transformers` deserialization issues matter for Phase 2 model work. Treat all external checkpoints as untrusted unless pinned to approved sources and loaded through reviewed paths.
- `pillow` matters only if image/file upload handling is introduced or if local tooling processes untrusted images.

Recommended follow-up:

1. Create a project-local virtual environment or lockfile so future audits reflect the project rather than the entire user site.
2. Evaluate safe upgrades for direct project dependencies first: `python-multipart`, `starlette` via FastAPI compatibility, `transformers`, and `pip` in the environment.
3. Re-run `make test` after each dependency batch.
4. Avoid automatic major upgrades without compatibility review.

## Node Findings

`npm audit --json` in `apps/web` reported:

- `next 14.2.35`: high severity aggregate, with multiple advisories affecting versions below Next `15.5.16` / `16.x` ranges, including Server Components DoS, request smuggling/cache poisoning, SSRF through WebSocket upgrades, App Router/CSP nonce XSS, image optimizer DoS, and middleware/proxy issues.
- `postcss` bundled under `next`: moderate XSS advisory for versions below `8.5.10`.
- `eslint-config-next 14.2.35` and `@next/eslint-plugin-next`: high severity via vulnerable `glob`.
- `glob`: high severity command-injection advisory in `>=10.2.0 <10.5.0`.

`npm audit` suggested semver-major fixes:

- Upgrade `next` to `16.2.9`.
- Upgrade `eslint-config-next` to `16.2.9`.

`npm outdated --json` also showed newer major versions available:

- Next `14.2.35` -> `16.2.9`.
- React / React DOM `18.3.1` -> `19.2.7`.
- ESLint `8.57.1` -> `10.5.0`.
- Tailwind `3.4.19` -> `4.3.1`.
- TypeScript `5.9.3` -> `6.0.3`.

Risk notes:

- The frontend is currently local/demo-oriented, but the audit findings should block any public deployment until addressed.
- Next major upgrades can affect App Router behavior, build output, seqviz compatibility, Playwright tests, and styling.

Recommended follow-up:

1. Plan a dedicated frontend dependency-upgrade branch.
2. First test whether upgrading within the Next 14 line is possible; if not, plan a Next 16 migration explicitly.
3. Run `npm run build` and `npm run test:e2e` sequentially after any frontend upgrade.
4. Do not expose the current frontend publicly until the Next advisories are resolved or mitigated.
