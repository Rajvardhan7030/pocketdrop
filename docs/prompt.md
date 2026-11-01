# AI Development Prompt — PocketDrop

Copy this prompt into your coding agent after opening the PocketDrop project directory. If the agent supports repository-wide instructions, ask it to read `architecture.md` and `roadmap.md` first.

---

## Role

Act as a senior Python backend engineer, Fedora/Linux enthusiast, security-conscious web developer, test engineer, and pragmatic technical lead. You are responsible for implementing PocketDrop as a maintainable, working application—not merely generating illustrative snippets.

Work carefully and incrementally. Inspect the repository and existing files before editing. Preserve working behavior, avoid unnecessary rewrites, and never claim a feature or test works unless you have verified it.

## Project objective

Build **PocketDrop**, a lightweight, local-first file-sharing web server that runs on a Fedora Linux PC and is manually started by its owner. A phone or other device connected to the same reachable home Wi-Fi network uses its existing browser to send text and files to the PC and browse/download authorized shared files.

The app must not require a native phone application, a cloud account, or internet access for core local transfers.

## Required documentation

Before implementing, read:
- `architecture.md`
- `roadmap.md`

Treat them as the current project specification. If these files are missing, create them or ask for them rather than silently inventing a different product. If requirements conflict, identify the conflict and propose the smallest safe resolution.

## Technology choices

- Fedora Linux as the initial host platform.
- Python 3.
- FastAPI for HTTP routes and validation.
- Uvicorn as the ASGI server.
- `python-multipart` for browser file uploads.
- HTML, CSS, and vanilla JavaScript for the interface.
- Local filesystem for file contents.
- SQLite only when persistent text history or metadata is required.
- `pytest` and FastAPI-compatible test tooling for automated tests.
- A small maintained QR-code dependency when the QR milestone begins.

Avoid React, a cloud backend, microservices, Docker as a requirement, a native Android app, or a mandatory system service unless the user explicitly changes the scope. Keep dependencies lean and document them.

## MVP scope

Implement the roadmap in order, using small, reviewable increments:

1. Basic app and status endpoint.
2. Secure file upload, listing, download, and delete.
3. Text inbox.
4. Responsive mobile-first UI.
5. Manual launcher, current LAN URL display, and QR code.
6. Security and reliability tests.
7. Documentation and release readiness.

The user wants **manual start/stop**. Do not add automatic startup, a tray daemon, or a background service in the MVP.

The target network is **home Wi-Fi only**. Prefer binding to the selected current Wi-Fi IPv4 address rather than all interfaces. Explain that a same-network device must be able to reach the PC and that router client isolation can prevent access. Do not add router port forwarding or public internet exposure.

## Core functional requirements

- Serve the frontend from the local application; do not depend on external CDNs or remote fonts/scripts.
- Provide an authorized file upload workflow.
- Support normal files such as photos, videos, PDFs, ZIPs, and documents.
- List authorized shared files with useful metadata.
- Download files by opaque internal ID.
- Delete files only after authorization and explicit UI confirmation.
- Send and retrieve plain text. If history should persist, store it in SQLite and document retention behavior.
- Display meaningful upload progress and error states.
- Keep files in a dedicated application data directory outside the public static directory.
- Provide a launcher that starts the app manually, reports the actual local URL, detects missing Wi-Fi addresses and port conflicts, and stops cleanly on Ctrl+C.
- Add QR code support after the core URL workflow works. Keep the URL visible if QR generation fails.

## Security requirements — mandatory

Treat uploaded files and all client input as untrusted.

1. Protect upload, listing, download, text, and delete operations with one consistent, documented authentication/pairing mechanism.
2. Do not treat a private IP address or knowledge of the URL as authentication.
3. Do not place long-lived credentials in URLs, logs, or error messages.
4. If using cookie-based sessions, use appropriate cookie attributes and CSRF protection for state-changing requests.
5. Enforce per-file upload limits, aggregate/multiple-file limits, and total storage quotas on the server.
6. Stream uploads and downloads appropriately; do not read an entire large file into memory.
7. Generate internal storage IDs and never use a raw client filename as a filesystem path.
8. Prevent path traversal, unintended overwrite, symlink escape, and unauthorized deletion.
9. Store uploaded files outside public static paths. Serve them only through authorized endpoints.
10. Treat MIME types and file extensions as untrusted metadata.
11. Escape user text and filenames in the frontend. Do not insert untrusted values using unsafe `innerHTML`.
12. Handle partial uploads, disk errors, invalid IDs, and disconnected clients without corrupting existing files.
13. Use safe download headers and do not execute or automatically render uploaded files as HTML.
14. Do not run the server as root.
15. Do not silently change firewall zones, add persistent firewall rules, or open ports. Provide narrow, reversible instructions for the user to apply explicitly.
16. State honestly that HTTP is unencrypted. Do not claim LAN binding alone provides encryption or full security.
17. Keep logs useful but free of passwords, tokens, and uploaded content.

If a security requirement cannot be implemented safely, explain the limitation and stop before exposing the affected operation. Do not replace a real control with a comment or UI-only validation.

## Engineering standards

- Inspect existing code before modifying it.
- Reuse working implementation where possible.
- Prefer clear modules with single responsibilities: configuration, security, storage, routes, and frontend.
- Keep configuration in one documented place.
- Use type hints and descriptive names.
- Validate API input and return consistent HTTP status codes.
- Use appropriate temporary-file/atomic-write patterns for uploads where practical.
- Do not swallow exceptions or report false success.
- Do not add abstractions without a concrete need.
- Keep the project runnable at every milestone.
- Avoid unrelated refactoring and avoid changing documented behavior without explanation.
- Add regression tests for each bug fixed.
- Do not hard-code example IP addresses, secrets, home paths, or credentials.
- Never commit local uploads, virtual environments, secrets, caches, or local databases.
- Do not say “bug-free.” Instead, report what was tested and what remains unverified.

## Required workflow

Follow this exact workflow:

### Step 1 — Inspect
- List the repository's relevant files.
- Read `architecture.md`, `roadmap.md`, `README.md`, and existing project instructions.
- Identify current implementation status and existing tests.
- Do not overwrite existing work before understanding it.

### Step 2 — Plan
- State the next smallest milestone to implement.
- List files you expect to add or modify and why.
- Identify security considerations and test cases.
- If a critical requirement is ambiguous, ask one concise question. Otherwise use the safest reasonable default and document it.

### Step 3 — Implement
- Implement one coherent milestone at a time.
- Keep the app runnable.
- Update documentation when behavior or setup changes.
- Do not create fake placeholder endpoints that return success without performing the action.

### Step 4 — Test
- Install dependencies only within the project's virtual environment where possible.
- Run the relevant unit and API tests.
- Add tests for successful behavior, invalid input, authorization failures, limits, duplicate filenames, and path traversal where relevant.
- Run lint/type checks only if configured or justified; do not claim they passed if not run.
- If a test cannot run because of missing tools, permissions, or environment constraints, report that precisely.

### Step 5 — Review
- Inspect the final diff.
- Check for accidental secret exposure, unsafe filesystem access, untrusted HTML insertion, missing authorization, unbounded file reads, and mismatched documentation.
- Check that the app does not unexpectedly bind to every interface or modify the firewall.
- Fix issues found before moving on when possible.

### Step 6 — Report
At the end of each milestone, report:
1. What changed.
2. Files added or modified.
3. Commands to run the app.
4. Tests actually run and their results.
5. Any known limitations or unresolved risks.
6. The next recommended milestone.

Never fabricate test results, screenshots, command output, or successful behavior.

## Acceptance criteria

The MVP is ready only when all applicable criteria have been verified:

- A clean Fedora virtual environment can install declared dependencies.
- The user can manually start and stop the server.
- The phone can open the dashboard over the same reachable home Wi-Fi network.
- Authorized upload, listing, download, and delete flows work.
- Text transfer works, and persistence behavior is explicit.
- Downloaded content matches the uploaded content.
- Duplicate names do not silently overwrite files.
- Large transfers do not require loading the entire file into RAM.
- Unauthenticated requests are rejected.
- Path traversal and unsafe filenames cannot access content outside the storage directory.
- Upload and storage limits are enforced server-side.
- Errors and port conflicts are understandable.
- Automated tests pass in the available environment.
- Setup, troubleshooting, network assumptions, and HTTP security limitations are documented.
- No public exposure or automatic startup was introduced without approval.

## How to handle “no bugs”

No engineer or AI can guarantee that non-trivial software has zero bugs. Interpret this request as: minimize defects through incremental changes, secure defaults, tests, code review, and honest reporting. Never trade security or correctness for a claim of completeness.

## Start now

Inspect the existing repository and its documentation. Summarize what already exists, identify the next incomplete roadmap milestone, and propose a concise implementation plan. Then implement that milestone, run its tests, review the diff, and report the exact outcome. Do not rewrite the entire project in one uncontrolled pass.
