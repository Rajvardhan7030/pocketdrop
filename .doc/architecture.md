# PocketDrop — Project Summary & Architecture

**Document:** `architecture.md`  
**Project status:** Planned / MVP  
**Target platform:** Fedora Linux PC + phone browser  
**Working name:** PocketDrop (verify name availability before public release)

## 1. Project Summary

PocketDrop is a lightweight, local-first file-sharing web application hosted by a Fedora Linux PC. The user manually starts the server when they want to transfer content. A phone or another browser-capable device on the same home Wi-Fi opens the PC's local address and can upload text, images, videos, documents, and other files, then browse and download items that the server is authorized to share.

The primary design goal is to make routine PC-to-phone and phone-to-PC transfers easy without requiring a dedicated phone app, cloud account, or internet connection for the core workflow.

### MVP goals

- Manual start and stop; no automatic startup in the MVP.
- Browser-based, responsive interface; no phone app required.
- Upload and download files over the home local network.
- Send and retrieve plain-text snippets.
- Display transfer status, file size, and useful errors.
- Store uploaded files in a dedicated application data directory.
- Use safe file identifiers, access controls, and configurable limits.
- Keep required frontend assets local so the interface does not depend on third-party CDNs.
- Provide clear setup, operation, troubleshooting, and security documentation.

### Explicit non-goals for the first MVP

- Public internet access, router port forwarding, or cloud relay.
- User accounts, multi-user tenancy, or remote synchronization.
- Native Android/iOS applications.
- Automatic OS startup, system tray, or desktop notifications.
- Full two-way OS clipboard synchronization.
- Resumable/chunked uploads unless the MVP's measured needs justify them.
- Complex frontend frameworks, microservices, or container requirements.

## 2. Technology Stack

| Area | Choice | Reason |
|---|---|---|
| Operating system | Fedora Linux | Primary host and development environment |
| Language | Python 3 | Readable, practical for a student-maintained utility |
| HTTP/API framework | FastAPI | API routing, validation, and file-upload support |
| ASGI server | Uvicorn | Runs the FastAPI application |
| Multipart upload support | `python-multipart` | Parses browser multipart file uploads |
| Frontend | HTML5, CSS, vanilla JavaScript | Lightweight and easy to maintain |
| File storage | Local filesystem | Large file contents stay out of the database |
| Metadata / text history | SQLite, if persistent history is needed | No separate database service required |
| Testing | `pytest` and FastAPI `TestClient` / HTTPX-compatible test setup | Unit and API regression tests |
| QR generation | Small maintained Python QR library, added when QR feature begins | Encodes the local URL for easy connection |
| Linux process management | Shell launcher initially | Explicit manual startup and shutdown |
| Later optional integration | User-level `systemd` service or tray icon | Out of MVP scope; only add if requested |

Keep direct dependencies explicit and reasonably pinned in the project's chosen dependency-management file. Do not rely on a developer's globally installed Python packages.

## 3. High-Level Architecture

```text
 Phone browser                          PC browser
      |                                     |
      +--------------- HTTP ----------------+
                        |
                 FastAPI / Uvicorn
                        |
             +----------+-----------+
             |                      |
      HTML/CSS/JS routes       Protected API
                                    |
                         +----------+----------+
                         |          |          |
                      Upload     Listing    Download/Delete
                         |          |          |
                         +------ Storage service
                                    |
                       Dedicated application directory
                                    |
                         SQLite metadata (when needed)
```

The application is a single local service. It does not need microservices or a separate database server.

### Suggested source tree

```text
pocketdrop/
├── app/
│   ├── __init__.py
│   ├── main.py                 # App construction and page/status routes
│   ├── config.py               # Settings and configurable limits
│   ├── security.py             # Authentication and request protections
│   ├── storage.py              # Safe filesystem operations
│   ├── schemas.py              # API response models, where useful
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── uploads.py
│   │   ├── files.py
│   │   └── text.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── style.css
│       └── app.js
├── tests/
│   ├── test_status.py
│   ├── test_uploads.py
│   ├── test_files.py
│   ├── test_text.py
│   └── test_security.py
├── data/                       # Development-only; never public static content
├── requirements.txt            # Or pyproject.toml; choose one source of truth
├── run.sh
├── .gitignore
├── README.md
├── architecture.md
├── roadmap.md
└── prompt.md
```

The structure can be simplified during the earliest prototype, but storage and security logic should be separated from HTTP handlers as the app grows.

## 4. Main Components and Responsibilities

### `main.py`
- Construct the FastAPI app.
- Mount local static assets and serve the dashboard.
- Register API routers.
- Expose a non-sensitive health/status endpoint.
- Avoid putting all storage and security logic in one file.

### `config.py`
- Define the default port and upload/storage limits.
- Resolve the dedicated data directory.
- Read documented environment variables or a configuration file.
- Validate configuration and fail with a clear error when invalid.

### `security.py`
- Implement the chosen access mechanism for every sensitive endpoint.
- Validate pairing/session credentials.
- Apply CSRF protections where cookie-based authentication is used.
- Do not log secrets or expose them in status responses.
- Keep authentication behavior consistent across upload, list, download, text, and delete routes.

### `storage.py`
- Generate opaque, unpredictable internal IDs for stored items.
- Sanitize display names and never trust client-provided paths.
- Store files only under the dedicated data directory.
- Avoid accidental overwrites.
- Stream file contents to disk and serve downloads without loading whole files into RAM.
- Enforce per-file and total-storage limits.
- Handle partial writes, failures, and cleanup safely.

### API routers
Suggested API shape (exact paths may be refined consistently):

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/` | Serve web dashboard |
| `GET` | `/api/status` | Health/status without secrets |
| `POST` | `/api/uploads` | Upload one or more files |
| `GET` | `/api/files` | List authorized shared items and metadata |
| `GET` | `/api/files/{file_id}` | Download by opaque internal ID |
| `DELETE` | `/api/files/{file_id}` | Delete an item after authorization |
| `POST` | `/api/text` | Save a text snippet |
| `GET` | `/api/text` | Retrieve authorized text history |

The text endpoints may be deferred until file transfer works. If text history must survive server restarts, use SQLite. Do not keep a supposedly persistent history only in process memory.

## 5. Data and Storage Design

- File content lives on disk, not as BLOBs in SQLite.
- Metadata may include internal ID, display filename, byte size, media type (treated as advisory), creation timestamp, content hash, and storage key.
- SQLite, when introduced, should use parameterized queries and transactions.
- A client-provided MIME type is untrusted. Do not use it as proof that a file is safe.
- Do not execute, render as HTML, or automatically open uploaded files.
- Store uploads outside the web root and never mount the upload directory as public static files.
- Use safe download headers and prevent path traversal.
- Decide and document what happens to files and text history after the server stops. Uploaded files should normally persist; in-memory-only text does not.

## 6. Network Model

- The server is started manually by the user.
- It should listen only on the selected current home-Wi-Fi IPv4 address when practical, rather than blindly binding to every interface.
- The local URL is similar to `http://<LAN-IP>:8000`; the actual IP must be detected, not hard-coded.
- The phone and PC must be able to reach each other on the same LAN. Router client isolation may prevent this.
- The launcher should report the chosen address and useful troubleshooting advice.
- A QR code can encode the local URL after the basic workflow is working.
- Do not automatically modify firewall rules in the MVP. Document a narrow, reversible rule and require explicit user action.
- Never configure router port forwarding or expose the service to the public internet as part of the MVP.
- HTTP is unencrypted. The first prototype should be limited to a trusted home network and should still use application-level authentication. For untrusted networks, add a properly secured transport before use.

## 7. Security Requirements

Treat this as a private-file service, not a trusted toy server.

1. Require authorization for uploads, listing, downloads, text operations, and deletion.
2. Use a documented pairing/session approach; never rely only on knowing the IP address.
3. Use secure random credentials, compare them safely, and do not place long-lived secrets in URLs or logs.
4. If cookie sessions are used, set appropriate `HttpOnly`, `SameSite`, and `Secure` attributes where the deployment supports them; protect state-changing requests against CSRF.
5. Validate request sizes on the server, including aggregate/multiple-file uploads.
6. Enforce per-file and total storage quotas.
7. Generate storage names and IDs server-side; treat original names only as display metadata.
8. Prevent path traversal, symlink escapes, overwrites, and unsafe file deletion.
9. Keep uploaded content outside public static paths.
10. Escape text and filenames in the frontend; never insert untrusted values using unsafe `innerHTML`.
11. Do not trust client MIME types or file extensions.
12. Return generic errors to clients and keep useful, secret-free server logs.
13. Bind to the intended network interface and document firewall scope.
14. Do not claim HTTP is encrypted. Explain the home-network limitation.
15. Add rate limits or bounded request concurrency where appropriate to avoid trivial resource exhaustion.

Security behavior must be tested, not merely described in documentation.

## 8. UI/UX Principles

- Mobile-first responsive layout.
- Clear Send to PC, Shared Files, and Text Inbox sections.
- Large touch targets and readable typography.
- Upload progress and clear success/failure states.
- Display filename, size, date, and file type.
- Confirm destructive deletion.
- No reliance on remote scripts, fonts, analytics, or CDNs.
- Accessible labels, keyboard navigation, focus states, and meaningful error messages.
- Keep the dashboard useful if QR generation is unavailable; show the local URL as text.

## 9. Operational Requirements

- `./run.sh` starts the server manually.
- `Ctrl+C` stops it cleanly.
- A virtual environment isolates dependencies.
- The launcher detects a usable Wi-Fi address and reports a clear error if none is found.
- It should detect port conflicts and explain how to choose another port.
- It should not silently run as root or alter firewall configuration.
- Uploaded files should persist in the configured application data directory.
- Include setup, usage, troubleshooting, test, and security sections in `README.md`.
- Do not commit secrets, virtual environments, user files, database files, or generated caches.

## 10. Definition of Done for the MVP

The MVP is complete only when:

- A clean setup on Fedora can install dependencies and start the app using documented commands.
- A phone on the same home Wi-Fi can open the dashboard.
- An authorized user can upload, list, download, and delete files.
- An authorized user can send and retrieve text if text support is included in the release.
- Uploads are stored safely and downloads match their original contents.
- Duplicate filenames do not silently overwrite data.
- Large-file handling does not read the entire file into memory.
- Unauthorized API calls fail safely.
- Malicious filenames and path traversal attempts cannot access files outside the storage directory.
- Limits, failures, disconnects, and port conflicts produce understandable behavior.
- Automated tests pass.
- The documentation accurately describes network and HTTP security limitations.
