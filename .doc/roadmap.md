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
- [ ] Confirm the project is named PocketDrop for now; check name availability before public distribution.
- [ ] Create the Git repository and a Python virtual environment.
- [ ] Choose one dependency-management source (`requirements.txt` or `pyproject.toml`).
- [ ] Define the application data directory and default port.
- [ ] Document the supported environment: Fedora host, modern phone browser, same reachable home LAN.
- [ ] Establish baseline coding style and test command.

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
- [ ] Create a minimal FastAPI app.
- [ ] Add `GET /` and `GET /api/status`.
- [ ] Start Uvicorn on a selected Wi-Fi IPv4 address and a configurable port.
- [ ] Verify the dashboard is reachable from the PC and phone.
- [ ] Detect and explain missing Wi-Fi addresses and port conflicts.
- [ ] Document the firewall and same-network requirements.

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
- [ ] Implement a dedicated storage service.
- [ ] Implement authenticated single-file uploads.
- [ ] Support multiple files if this can be done without compromising limits or error handling.
- [ ] Generate opaque internal IDs for files.
- [ ] Save original filenames as sanitized display metadata only.
- [ ] Add an authorized file-list endpoint.
- [ ] Add authorized download and delete endpoints.
- [ ] Stream large uploads/downloads safely.
- [ ] Prevent overwrites and path traversal.
- [ ] Enforce per-file and total storage quotas.
- [ ] Clean up incomplete files after failed uploads where practical.

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
- [ ] Add a text submission endpoint.
- [ ] Display recent text snippets in the dashboard.
- [ ] Add a copy button with graceful browser clipboard fallback.
- [ ] Decide whether text history must persist across server restarts.
- [ ] If persistent, add SQLite metadata/history with schema initialization and parameterized queries.
- [ ] Add clear limits for snippet length and history size.
- [ ] Escape user content in the frontend.

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
- [ ] Build responsive HTML/CSS/JavaScript interface.
- [ ] Add file picker and drag-and-drop on compatible desktop browsers.
- [ ] Add upload progress, errors, and retry guidance.
- [ ] Show filename, size, date, and type.
- [ ] Add image and plain-text previews where safe.
- [ ] Add download links and confirmation before deletion.
- [ ] Provide loading, empty, and failure states.
- [ ] Keep all assets local; no CDN dependency.
- [ ] Test common mobile viewport sizes and keyboard accessibility.

### Deliverables
- A coherent, usable browser UI on phone and PC.

### Acceptance criteria
- Primary actions are easy to use on a narrow screen.
- Network errors are visible and understandable.
- Untrusted filenames and text cannot inject HTML/script.
- All primary actions can be operated with a keyboard on desktop.

## Phase 5 — QR Code and Manual Launcher

### Tasks
- [ ] Add a maintained QR-code library.
- [ ] Generate a QR code for the current LAN URL.
- [ ] Keep the URL visible as selectable text.
- [ ] Create `run.sh` that activates the virtual environment.
- [ ] Detect a usable Wi-Fi IPv4 address and report it.
- [ ] Support a documented port override.
- [ ] Detect port conflicts and exit with a helpful message.
- [ ] Handle `Ctrl+C` and clean shutdown.
- [ ] Do not silently open firewall ports or change network trust zones.

### Deliverables
- User starts one command and gets the address and QR code.

### Acceptance criteria
- QR points to the current address, not a hard-coded example.
- If no suitable address is found, the launcher explains how to troubleshoot.
- Server stops cleanly when the user interrupts it.
- Manual start/stop behavior remains intact.

## Phase 6 — Security and Reliability Hardening

### Tasks
- [ ] Review authorization on every sensitive route.
- [ ] Review session, cookie, CSRF, and credential handling for the selected authentication design.
- [ ] Add request-size and storage limits, including aggregate limits.
- [ ] Test traversal strings, weird Unicode names, duplicate names, symlink edge cases, and malicious text.
- [ ] Verify uploads cannot escape the storage directory.
- [ ] Ensure logs do not contain passwords, tokens, or uploaded content.
- [ ] Test invalid, interrupted, and concurrent uploads.
- [ ] Add useful, non-sensitive error responses.
- [ ] Document that plain HTTP is unencrypted and limit usage to trusted home Wi-Fi until a secured transport is added.
- [ ] Verify firewall instructions are narrow, reversible, and distribution-appropriate.

### Deliverables
- Security checklist, regression tests, and updated threat model.

### Acceptance criteria
- All critical security tests pass.
- No endpoint exposes files without authorization.
- The application does not claim LAN-only binding is a substitute for authentication.
- No router port-forwarding instructions are included.

## Phase 7 — Test, Package, and Release MVP

### Tasks
- [ ] Add automated tests for status, uploads, listing, download, deletion, text, and authorization.
- [ ] Add tests for oversized uploads, duplicate names, invalid IDs, and path traversal.
- [ ] Run tests on Fedora in a clean virtual environment.
- [ ] Test with at least one real phone browser.
- [ ] Test image, PDF, ZIP, and a large video file.
- [ ] Confirm restart and persistence behavior.
- [ ] Complete README installation, usage, troubleshooting, and security sections.
- [ ] Add screenshots and a concise demo flow.
- [ ] Tag a first MVP release after all acceptance criteria pass.

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
