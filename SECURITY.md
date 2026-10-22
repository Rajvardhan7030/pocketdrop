# PocketDrop — Security Model & Verification Checklist

## 1. Threat Model & Operational Environment

PocketDrop is designed for **local-first peer-to-peer sharing over a private home Wi-Fi network**.

### Threat Matrix

| Threat | Risk Level | Mitigation in PocketDrop |
|---|---|---|
| **Rogue device on local Wi-Fi** attempting to access or delete files | High | **Mandatory Authentication:** All sensitive operations (uploads, listing, download, delete, text) require either a valid pairing session cookie + CSRF token or an `X-PocketDrop-Token` header. URL knowledge or IP reachability does not grant access. |
| **Path Traversal / Directory Escape** (`../../etc/passwd`) | Critical | **Opaque Internal IDs:** Client filenames are strictly treated as display metadata in SQLite. On disk, files are stored as `<uuid4>.dat`. Path resolution explicitly verifies that the resolved path is strictly a child of `settings.STORAGE_DIR`. |
| **Malicious File Execution** (e.g. uploaded `.html` or `.svg` script) | High | **Forced Attachment Headers:** All file downloads enforce `Content-Disposition: attachment; filename="..."` and `X-Content-Type-Options: nosniff`. Browsers are instructed to download, never execute inline. |
| **Cross-Site Request Forgery (CSRF)** | Medium | **CSRF Validation:** Cookie-based sessions require a matching `X-CSRF-Token` header on all state-changing HTTP methods (`POST`, `PUT`, `DELETE`, `PATCH`). |
| **Cross-Site Scripting (XSS)** | High | **Safe DOM Manipulation:** Vanilla JS frontend uses `textContent` and `document.createElement()` exclusively. No untrusted filenames, text snippets, or server responses are ever inserted via `innerHTML`. |
| **Disk Exhaustion / Resource Starvation** | High | **Hard Quotas & Streaming:** Server-side enforcement of per-file maximum size (default 500 MB) and aggregate storage quota (default 10 GB). Chunks are streamed in 64 KB increments; partial files are deleted immediately if a quota is violated. |
| **Credential / Token Exposure in Logs** | Medium | **Secret-Free Logging:** Access logging is disabled in Uvicorn; application loggers never record pairing PINs, session tokens, or uploaded content. |
| **Passive LAN Eavesdropping (Unencrypted HTTP)** | Medium | **Home LAN Scope Limitation:** PocketDrop operates over unencrypted HTTP for local convenience. It is documented and intended strictly for trusted private home networks. For hostile networks, an encrypted transport (e.g. WireGuard or TLS proxy) is required. |

---

## 2. Mandatory Security Checklist Verification

- [x] **Auth on all sensitive endpoints:** Upload, list, download, delete, and text endpoints reject unauthenticated requests with HTTP 401.
- [x] **No authentication by IP alone:** LAN IP reachability is not treated as authentication.
- [x] **No credentials in URLs:** Long-lived tokens and passwords are not placed in query parameters, error responses, or logs.
- [x] **Cookie attributes:** Session cookies use `HttpOnly; SameSite=Lax; Path=/`.
- [x] **CSRF protection:** Verified on all state-changing requests using cookie authentication.
- [x] **Quotas enforced server-side:** Real-time enforcement during streaming; client-side size headers are not trusted.
- [x] **Streaming I/O:** Uploads stream in 64 KB chunks to disk; large files do not load entirely into memory.
- [x] **Opaque internal storage IDs:** Internal files named `<UUID>.dat`.
- [x] **Path traversal prevention:** Tested against `../`, `%2F`, root paths, and symlink escapes.
- [x] **Storage path isolation:** Uploaded files stored outside web root; static files directory is mounted independently.
- [x] **Untrusted MIME types:** Client MIME types are treated as advisory display strings only.
- [x] **Safe download headers:** `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`.
- [x] **Atomic file operations:** Streaming writes use `.tmp_<uuid>` and atomic `replace()` upon checksum completion.
- [x] **Root privilege prevention:** Launcher `./run.sh` explicitly halts if executed with root privileges (`UID 0`).
- [x] **Manual firewall rules:** The server never modifies firewall zones or adds persistent rules. Reversible `firewall-cmd` instructions are documented for the user.
- [x] **No automatic background services:** Runs interactively and stops cleanly with `Ctrl+C`.
