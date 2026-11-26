# 标题

Introduce a local desktop application with Vue, Tauri, and a bundled Python backend

# 描述

The application previously relied on standalone browser pages and browser-local configuration. This change provides a unified Vue library and reader, persistent local settings, OS credential storage, and a Tauri desktop application with a bundled Python backend. Existing browser startup remains available, and legacy page URLs redirect to the new frontend.

The desktop host starts an authenticated loopback service on a dynamic port, manages its shutdown, reports startup/runtime failures, and asks before discarding unsaved edits. User data is stored outside the installation directory. An offline migration utility copies legacy libraries into a new destination without overwriting existing libraries or copying credential references.

## Scope

- Vue library, settings, import/export, statistics, recycle bin and PDF.js reader replacing the legacy frontend.
- Persistent preferences and reader state; API keys stored through OS credential adapters.
- Tauri/Python lifecycle, loopback session isolation and packaged runtime resources.
- macOS app, Windows NSIS and Ubuntu 24.04 deb test artifacts.
- Legacy data migration, compatibility redirects, automated tests and documentation.

The planned reader information-architecture redesign is excluded and preserved on `feat/reader-redesign`.

## Validation

For code commit `7d21b1f`:

- Frontend: 9 unit tests and 26 browser workflows passed.
- Backend: Windows, macOS and Linux with Python 3.10/3.12 passed.
- Desktop: all three platform package jobs passed, including lifecycle origin restriction tests and packaged backend verification.
- Local macOS: 81 backend tests, frontend production build, Rust lifecycle test and packaged integration acceptance passed.
- Packaged acceptance covers import/deduplication, metadata, settings, reader state, restart and same-version executable replacement. It does not establish cross-version upgrade safety.

CI: [frontend](https://github.com/xv1rcn/OpenPaper/actions/runs/45099701351), [backend](https://github.com/xv1rcn/OpenPaper/actions/runs/45099701177), [desktop](https://github.com/xv1rcn/OpenPaper/actions/runs/45099701271).

## Remaining acceptance and release limits

Keep this PR in draft pending native fault-injection and close/restart confirmation checks, plus Windows/Linux desktop and credential-vault acceptance. Browser tests emulate the host signal protocol and do not replace native WebView tests. The current automation environment cannot access the macOS UI; no native pass is claimed for the latest lifecycle changes.

Artifacts are unsigned test builds. macOS notarization, cross-version installer upgrades, uninstall data policies and older Linux distribution compatibility are not established. PDF export needs an installed Chrome/Edge/Chromium; PDF reading uses bundled PDF.js. macOS defaults to polling file observation after an isolated FSEvents startup/shutdown crash was reproduced.

See `docs/library-migration.md`, `docs/native-acceptance.md` and `docs/pr-readiness.md` for migration, acceptance criteria and remaining evidence.
