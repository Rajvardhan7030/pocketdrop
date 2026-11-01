# PocketDrop 📱💻

**PocketDrop** is a lightweight, local-first file sharing and text transfer web application hosted on a Linux PC (optimized for Fedora). It allows mobile phones, tablets, or other computers on the same home Wi-Fi network to seamlessly transfer files and text snippets via a modern web browser—**with zero cloud accounts, no third-party internet dependencies, and no native phone apps required**.

---

## 📖 What is PocketDrop?

When you want to quickly move a photo, video, PDF, or link between your phone and your PC, you often have to rely on cloud services (Google Drive, Dropbox), messaging apps (Telegram, WhatsApp), or email. These methods route your private files across external third-party servers and require internet access.

PocketDrop runs an on-demand, local web server directly on your PC:
- **Private & Local-First:** All files and text stay strictly inside your local home Wi-Fi network. No cloud, no external tracking, no internet connection needed.
- **No Mobile Apps Needed:** Any smartphone (iOS Safari, Android Chrome, Firefox) opens the dashboard directly in its browser.
- **Manual Start & Stop:** You are in full control. The server only runs when you execute `./run.sh`, and shuts down cleanly on `Ctrl+C`. No background daemons or hidden system services.
- **Pairing-Based Security:** Protects your files with a secure 6-digit Pairing PIN displayed in your terminal. Strangers on the same Wi-Fi cannot browse or access files without the PIN.
- **Where Files Live on PC:** Uploaded files are stored in [`data/storage/`](data/storage/) on your PC, while text notes and metadata are recorded in [`data/pocketdrop.db`](data/pocketdrop.db).

---

## 🏗️ Architecture & How It Works

PocketDrop is built as a single, modular Python service with a vanilla HTML5/CSS/JavaScript frontend served locally without remote CDNs.

### High-Level Architecture Diagram

```text
 ┌────────────────────────┐                   ┌────────────────────────┐
 │      Phone Browser     │                   │       PC Browser       │
 │   (iOS / Android Web)  │                   │     (Firefox/Chrome)   │
 └───────────┬────────────┘                   └───────────┬────────────┘
             │                                            │
             │           HTTP over Home Wi-Fi LAN         │
             └─────────────────────┬──────────────────────┘
                                   │
                     ┌─────────────▼─────────────┐
                     │     FastAPI / Uvicorn     │
                     │  (Bound to active Wi-Fi)  │
                     └─────────────┬─────────────┘
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         │                                                   │
┌────────▼────────┐                                 ┌────────▼────────┐
│ Static Frontend │                                 │  Protected API  │
│  HTML / CSS / JS│                                 │ (Auth Required) │
│ (No Remote CDNs)│                                 └────────┬────────┘
└─────────────────┘                                          │
                   ┌───────────────────────┬─────────────────┴─────────────────┐
                   │                       │                                   │
         ┌─────────▼─────────┐   ┌─────────▼─────────┐               ┌─────────▼─────────┐
         │   Auth & Pairing  │   │  Streaming Upload │               │    Text Inbox     │
         │  6-Digit PIN/CSRF │   │ 64KB Chunks/Quota │               │ Persistent SQLite │
         └───────────────────┘   └─────────┬─────────┘               └─────────┬─────────┘
                                           │                                   │
                                 ┌─────────▼─────────┐               ┌─────────▼─────────┐
                                 │   Local Storage   │               │   SQLite Database │
                                 │  `data/storage/`  │◄──────────────┤ `pocketdrop.db`   │
                                 │  (<uuid4>.dat)    │   Metadata    │   (WAL Mode)      │
                                 └───────────────────┘               └───────────────────┘
```

### Core Architecture Components

1. **Network Interface Binding (`app/network.py`)**:
   - Rather than exposing all network interfaces (`0.0.0.0`), PocketDrop discovers your machine's active Wi-Fi IPv4 address (e.g. `172.29.181.175`) and binds exclusively to it.
   - Checks port availability and reports clear troubleshooting advice if another service is already using port 8000.

2. **Security & Session Management (`app/security.py` & `app/routes/auth.py`)**:
   - **Method B Pairing:** On startup, a random 6-digit numeric Pairing PIN is generated and displayed in your PC terminal.
   - Scanning the terminal QR code opens the clean Access URL. The user enters the PIN to establish an authorized session.
   - Issues a secure, `HttpOnly`, `SameSite=Lax` session cookie (`pocketdrop_session`).
   - Requires matching CSRF tokens on all state-changing requests (`POST`, `DELETE`).
   - Input normalization accepts entries with spaces or hyphens (e.g. `808 403` or `808-403`).

3. **Safe Storage Engine (`app/storage.py`)**:
   - **Opaque Storage Keys:** Files on disk are saved as `<uuid4>.dat` (e.g. `3e25fcef-6bc7-4c3d-b5a3-10d8c491db21.dat`). Client filenames are never used as raw filesystem paths, preventing directory traversal (`../../etc/passwd`).
   - **Streaming & Quota Enforcement:** Uploads stream in 64 KB chunks directly to temporary files (`.tmp_<uuid>`). Real-time per-file limits (500 MB) and aggregate storage quotas (10 GB) are enforced on the fly.
   - **Atomic Writes:** Completed uploads are atomically moved to their destination key via `Path.replace()`, ensuring partial or aborted uploads never corrupt existing data.
   - **Safe Download Headers:** Downloads enforce `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff` so browsers download files rather than executing untrusted scripts.

4. **Persistent Metadata & Text Inbox (`app/db.py` & `app/routes/text.py`)**:
   - Uses embedded SQLite with Write-Ahead Logging (WAL) and parameterized queries.
   - Maintains file metadata (original display filename, byte size, SHA-256 hash, upload timestamp).
   - Stores text messages with a 200-item retention window, preserving emojis, quotes, and multi-line code blocks.

5. **Self-Contained Frontend (`app/templates/` & `app/static/`)**:
   - Fully responsive, mobile-first design built with vanilla HTML5, CSS, and JavaScript.
   - **Zero external CDN dependencies** (works without internet access).
   - Strict XSS prevention: all dynamic text and filenames are rendered using DOM `textContent` (zero `innerHTML` usage).

---

## 🚀 How to Use PocketDrop

### 1. Prerequisites (Fedora Linux PC)

Ensure Python 3 is installed:
```bash
python3 --version
```

If running **Fedora Linux**, allow incoming LAN connections to port 8000 in `firewalld`:
```bash
# Allow port 8000 temporarily (resets on reboot)
sudo firewall-cmd --add-port=8000/tcp
```
*(PocketDrop never modifies firewall rules automatically to respect your system security).*

### 2. Starting the Server

Simply run the launcher script from the project folder:
```bash
./run.sh
```

The launcher will automatically set up the virtual environment (`.venv`), install dependencies, detect your active Wi-Fi IP, and display your connection details:

```text
=======================================================
  PocketDrop — Local File & Text Sharing
=======================================================
  Bound Interface: wlp0s26u1u3 (172.29.181.175)
  Access URL:      http://172.29.181.175:8000
  Pairing PIN:     808403
=======================================================

  Scan with your phone camera:
[ ASCII QR CODE ]

=======================================================
  Access URL:      http://172.29.181.175:8000
  Pairing PIN:     808403
=======================================================
  1. Scan the QR code with your phone (or open the Access URL).
  2. Enter the 6-digit Pairing PIN above to authorize your device.
  Both devices must be connected to the same home Wi-Fi.
  Press Ctrl+C to stop the server at any time.
=======================================================
```

---

### 3. Step-by-Step Walkthrough

```text
┌───────────────────────────────────────────────────────────────┐
│                      PocketDrop Dashboard            [Online] │
├───────────────────────────────────────────────────────────────┤
│ [1] Device Pairing                                            │
│     [ Enter 6-digit PIN ]  [ Connect Device ]                 │
├───────────────────────────────────────────────────────────────┤
│ [2] Send to PC                                                │
│     ┌───────────────────────────────────────────────────────┐ │
│     │  Tap here to select files or drag & drop              │ │
│     └───────────────────────────────────────────────────────┘ │
│     [████████████████████░░░░░░░] 75% photo.jpg               │
├───────────────────────────────────────────────────────────────┤
│ [3] Quick Text Transfer                                       │
│     [ Type or paste notes, links, code...                 ]   │
│     [ Send Text ]                                             │
│     - "Wi-Fi password: ..."  [ Copy ]  [ Delete ]             │
├───────────────────────────────────────────────────────────────┤
│ [4] Shared Files                                              │
│     • vacation.jpg (3.4 MB)  [ Download ]  [ Delete ]         │
│     • notes.pdf (512 KB)     [ Download ]  [ Delete ]         │
└───────────────────────────────────────────────────────────────┘
```

#### Step 1: Connect & Pair Phone
1. Connect your smartphone to the **same home Wi-Fi network** as your PC.
2. Open your phone camera and scan the QR code in the terminal (or open `http://<LAN-IP>:8000` in your phone's browser).
3. In the **Device Pairing** card, enter the 6-digit PIN shown in your PC terminal (e.g. `808403` or `808 403`) and tap **Connect Device**.

#### Step 2: Sending Files from Phone to PC
1. Tap the **Send to PC** drop zone.
2. Choose one or multiple photos, videos, PDFs, or documents.
3. A progress bar tracks the chunked upload. Once complete, the file appears immediately in the **Shared Files** list.

#### Step 3: Downloading Files on PC
1. Open `http://localhost:8000` (or the LAN IP) in your PC browser.
2. In the **Shared Files** list, click **Download** next to any file. The file downloads with its original name and extension.
3. Or view physical files directly on your PC at:
   ```bash
   ls -lh data/storage/
   ```

#### Step 4: Quick Text & Clipboard Sharing
1. Type or paste links, passwords, or code snippets into the **Quick Text Transfer** box and click **Send Text**.
2. On your other device, click **Copy** next to the snippet to copy it directly to your clipboard (includes automatic fallback if browser clipboard permissions are restricted over plain HTTP).

#### Step 5: Stopping the Server
When you are done, return to your PC terminal and press:
```bash
Ctrl + C
```
The server shuts down cleanly.

---

## ⚙️ CLI Options & Customization

The `./run.sh` script accepts optional command-line flags:

| Flag | Description | Example |
|---|---|---|
| `--port <port>` | Change the listening port (default: 8000) | `./run.sh --port 8080` |
| `--host <ip>` | Override binding address | `./run.sh --host 127.0.0.1` |
| `--pin <pin>` | Set a specific pairing PIN or token | `./run.sh --pin 123456` |
| `--new-pin` | Generate a fresh random PIN on launch | `./run.sh --new-pin` |
| `--no-qr` | Suppress terminal QR code output | `./run.sh --no-qr` |
| `--iface <name>`| Select a specific network interface | `./run.sh --iface wlan0` |

### Environment Variables

You can customize storage quotas and directories using environment variables:

```bash
# Store uploads in custom folder
export POCKETDROP_DATA_DIR="/home/raj/Downloads/pocketdrop_data"

# Set max single file size to 1 GB (in bytes)
export POCKETDROP_MAX_FILE_SIZE_BYTES=1073741824

# Set total storage quota to 20 GB (in bytes)
export POCKETDROP_MAX_TOTAL_STORAGE_BYTES=21474836480

./run.sh
```

---

## 🧪 Running Automated Tests

PocketDrop includes a comprehensive test suite (54 unit and integration tests) verifying network binding, streaming quotas, path traversal defense, and pairing authentication:

```bash
source .venv/bin/activate
pytest -v
```

---

## ❓ Troubleshooting & FAQs

- **Phone cannot open the page:**
  1. **Check Wi-Fi:** Ensure both your PC and phone are connected to the exact same Wi-Fi network.
  2. **Router Client Isolation:** Some routers enable "AP Isolation" or "Client Isolation", which blocks devices on Wi-Fi from talking to each other. Check your router settings to disable client isolation.
  3. **Fedora Firewall:** Make sure port 8000 is allowed: `sudo firewall-cmd --add-port=8000/tcp`.

- **"Invalid pairing PIN or token":**
  1. Check the 6-digit PIN displayed at the bottom of your PC terminal.
  2. Spaces and hyphens are accepted (e.g. `808 403` or `808-403`).
  3. If you want to reset the PIN, start the server with `./run.sh --new-pin`.

- **Where are files saved on my PC?**
  Files are located in [`data/storage/`](data/storage/) as `<uuid>.dat`. Original file names and timestamps are tracked in [`data/pocketdrop.db`](data/pocketdrop.db). To download them with original names, use the web interface.

- **Is traffic encrypted?**
  PocketDrop uses standard HTTP over your private home Wi-Fi. It is designed specifically for trusted home networks and should not be exposed to the public internet or untrusted public Wi-Fi without a VPN (e.g. WireGuard) or reverse proxy.

---

## 📚 Project Documentation

- [`SECURITY.md`](SECURITY.md): Threat model, threat matrix, and security control verification.
- [`docs/architecture.md`](docs/architecture.md): Architectural specifications and design rules.
- [`docs/roadmap.md`](docs/roadmap.md): Milestone progress and completion criteria.
- [`docs/prompt.md`](docs/prompt.md): Technical engineering standards and constraints.
