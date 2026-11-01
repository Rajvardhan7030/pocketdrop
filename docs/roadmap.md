# PocketDrop — Development Roadmap

**Document:** `roadmap.md`  
**Goal:** Deliver a dependable, manually started local file-sharing server for Fedora, accessible from a phone browser over home Wi-Fi.

## Roadmap Principles

- Build a working, testable increment at each stage.
- Keep the first release small; do not add cloud, accounts, a native phone app, or a tray icon.
- Security and reliability are acceptance criteria, not a final polish phase.
- Do not claim a feature is complete until its tests pass on the intended workflow.
- Prefer clear code and explicit behavior over premature optimization.

## Phase 0 — Requirements and Environment

### Tasks
- [x] Confirm the project is named PocketDrop for now; check name availability before public distribution.
- [x] Create the Git repository and a Python virtual environment.
- [x] Choose one dependency-management source (`requirements.txt` or `pyproject.toml`).
- [x] Define the application data directory and default port.
- [x] Document the supported environment: Fedora host, modern phone browser, same reachable home LAN.
- [x] Establish baseline coding style and test command.

### Deliverables
- Repository skeleton.
- Initial README and architecture document.
- Reproducible development environment.

### Acceptance criteria
- A fresh virtual environment can install all declared dependencies.
- No dependency requires global Python installation.
- No secrets or personal files are committed.

## Phase 1 — Network Proof of Concept

### Tasks
- [x] Create a minimal FastAPI app.
- [x] Add `GET /` and `GET /api/status`.
- [x] Start Uvicorn on a selected Wi-Fi IPv4 address and a configurable port.
- [x] Verify the dashboard is reachable from the PC and phone.
- [x] Detect and explain missing Wi-Fi addresses and port conflicts.
- [x] Document the firewall and same-network requirements.

### Deliverables
- Server can be started manually.
- Phone can reach the local dashboard over home Wi-Fi.

### Acceptance criteria
- Server does not start automatically.
- It does not need public internet access to serve its own page.
- It does not silently bind to all network interfaces.
- The status route returns no secrets or private file listings.

## Phase 2 — File Storage and Transfers

### Tasks
- [x] Implement a dedicated storage service.
- [x] Implement authenticated single-file uploads.
- [x] Support multiple files if this can be done without compromising limits or error handling.
- [x] Generate opaque internal IDs for files.
- [x] Save original filenames as sanitized display metadata only.
- [x] Add an authorized file-list endpoint.
- [x] Add authorized download and delete endpoints.
- [x] Stream large uploads/downloads safely.
- [x] Prevent overwrites and path traversal.
- [x] Enforce per-file and total storage quotas.
- [x] Clean up incomplete files after failed uploads where practical.

### Deliverables
- End-to-end phone-to-PC file upload.
- PC/phone browser file listing and downloads.
- Safe deletion workflow.

### Acceptance criteria
- Upload and download checksums match.
- Duplicate filenames do not cause silent data loss.
- Files are stored outside the public frontend directory.
- Oversized requests are rejected cleanly.
- Unauthorized requests cannot list, fetch, upload, or delete content.
- A large test file does not cause memory usage to scale with the entire file size.

## Phase 3 — Text Inbox

### Tasks
- [x] Add a text submission endpoint.
- [x] Display recent text snippets in the dashboard.
- [x] Add a copy button with graceful browser clipboard fallback.
- [x] Decide whether text history must persist across server restarts.
- [x] If persistent, add SQLite metadata/history with schema initialization and parameterized queries.
- [x] Add clear limits for snippet length and history size.
- [x] Escape user content in the frontend.

### Deliverables
- Phone-to-PC text transfer.
- PC-to-phone text retrieval through the browser.

### Acceptance criteria
- Text containing quotes, Unicode, newlines, and code snippets is preserved.
- Text is rendered as text, not executable HTML.
- Persistence behavior is documented and tested.
- Clipboard API denial does not break the rest of the app.

## Phase 4 — Mobile-First Dashboard

### Tasks
- [x] Build responsive HTML/CSS/JavaScript interface.
- [x] Add file picker and drag-and-drop on compatible desktop browsers.
- [x] Add upload progress, errors, and retry guidance.
- [x] Show filename, size, date, and type.
- [x] Add image and plain-text previews where safe.
- [x] Add download links and confirmation before deletion.
- [x] Provide loading, empty, and failure states.
- [x] Keep all assets local; no CDN dependency.
- [x] Test common mobile viewport sizes and keyboard accessibility.

### Deliverables
- A coherent, usable browser UI on phone and PC.

### Acceptance criteria
- Primary actions are easy to use on a narrow screen.
- Network errors are visible and understandable.
- Untrusted filenames and text cannot inject HTML/script.
- All primary actions can be operated with a keyboard on desktop.

## Phase 5 — QR Code and Manual Launcher

### Tasks
- [x] Add a maintained QR-code library.
- [x] Generate a QR code for the current LAN URL.
- [x] Keep the URL visible as selectable text.
- [x] Create `run.sh` that activates the virtual environment.
- [x] Detect a usable Wi-Fi IPv4 address and report it.
- [x] Support a documented port override.
- [x] Detect port conflicts and exit with a helpful message.
- [x] Handle `Ctrl+C` and clean shutdown.
- [x] Do not silently open firewall ports or change network trust zones.

### Deliverables
- User starts one command and gets the address and QR code.

### Acceptance criteria
- QR points to the current address, not a hard-coded example.
- If no suitable address is found, the launcher explains how to troubleshoot.
- Server stops cleanly when the user interrupts it.
- Manual start/stop behavior remains intact.

## Phase 6 — Security and Reliability Hardening

### Tasks
- [x] Review authorization on every sensitive route.
- [x] Review session, cookie, CSRF, and credential handling for the selected authentication design.
- [x] Add request-size and storage limits, including aggregate limits.
- [x] Test traversal strings, weird Unicode names, duplicate names, symlink edge cases, and malicious text.
- [x] Verify uploads cannot escape the storage directory.
- [x] Ensure logs do not contain passwords, tokens, or uploaded content.
- [x] Test invalid, interrupted, and concurrent uploads.
- [x] Add useful, non-sensitive error responses.
- [x] Document that plain HTTP is unencrypted and limit usage to trusted home Wi-Fi until a secured transport is added.
- [x] Verify firewall instructions are narrow, reversible, and distribution-appropriate.

### Deliverables
- Security checklist, regression tests, and updated threat model.

### Acceptance criteria
- All critical security tests pass.
- No endpoint exposes files without authorization.
- The application does not claim LAN-only binding is a substitute for authentication.
- No router port-forwarding instructions are included.

## Phase 7 — Test, Package, and Release MVP

### Tasks
- [x] Add automated tests for status, uploads, listing, download, deletion, text, and authorization.
- [x] Add tests for oversized uploads, duplicate names, invalid IDs, and path traversal.
- [x] Run tests on Fedora in a clean virtual environment.
- [x] Test with at least one real phone browser.
- [x] Test image, PDF, ZIP, and a large video file.
- [x] Confirm restart and persistence behavior.
- [x] Complete README installation, usage, troubleshooting, and security sections.
- [x] Add screenshots and a concise demo flow.
- [x] Tag a first MVP release after all acceptance criteria pass.

### Deliverables
- Reproducible setup.
- Automated regression suite.
- Documented MVP release.

### Release acceptance criteria
- A new user can follow the README from a clean Fedora setup.
- Core transfer tasks work on the home LAN.
- Security limitations and configuration are documented honestly.
- Automated tests pass without relying on personal local files or network credentials.

## Future / Optional Phases — Only After MVP

- Resumable or chunked uploads for interrupted large transfers.
- Configurable cleanup and retention policy.
- Search, sorting, hashes, and deduplication.
- Multiple paired devices and device-specific permissions.
- Optional desktop tray utility and user-level `systemd` service.
- Optional PWA support.
- Optional secure HTTPS setup for more demanding network scenarios.
- Optional OS clipboard integration for Wayland/X11, with explicit user consent.
- Optional packaging for other Linux distributions.

These are not prerequisites for the first release. Reassess each feature based on actual usage and test results.

## Suggested Milestone Tracking

For each task, record:
- Status: `Not started`, `In progress`, `Blocked`, or `Done`.
- Implementation commit or pull request.
- Tests added and test result.
- Known limitations.
- Any architecture/documentation changes.

Do not mark a milestone complete because the UI looks finished; mark it complete only when the acceptance criteria have been demonstrated.
