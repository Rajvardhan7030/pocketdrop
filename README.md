# PocketDrop

PocketDrop is a lightweight, local-first file-sharing and text transfer web application hosted on a Fedora Linux PC. It allows mobile phones and other devices on the same reachable home Wi-Fi network to transfer files and text snippets via a browser interface without requiring native mobile apps, cloud accounts, or an active internet connection.

## System Requirements

- **Host OS:** Fedora Linux (tested on Fedora Linux with Python 3.14).
- **Client Devices:** Any modern smartphone or tablet browser (Firefox, Chrome, Safari) connected to the same home Wi-Fi network.
- **Network:** Reachable home LAN (without client isolation on the router).

## Security & Architecture Principles

- **Local Network Only:** The server binds to the selected home Wi-Fi IPv4 address rather than exposing itself across all interfaces (`0.0.0.0`) or the public internet. No router port forwarding or automatic firewall modification is performed.
- **Explicit Manual Control:** The application is manually started and stopped by the user via `./run.sh` or `python -m app.main`. No background daemons or autostart services.
- **Opaque File Storage:** Uploaded files are stored in a dedicated local directory (`data/storage`) outside the web root using opaque internal IDs to prevent path traversal, overwriting, and arbitrary code execution.
- **No Remote Dependencies:** The web dashboard and static assets are served locally with zero CDN dependencies.
- **Plain HTTP Limitation:** Unencrypted HTTP is used over the local LAN. It is designed solely for trusted private home networks.

## Getting Started

### 1. Set Up the Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Running Automated Tests

```bash
source .venv/bin/activate
pytest -v
```

### 3. Running the Development Server

Start the server using Python (it automatically binds to your active Wi-Fi IP):

```bash
source .venv/bin/activate
python3 -m app.main
```

Or specify custom parameters if needed:
```bash
python3 -m app.main --port 8080
python3 -m app.main --host 127.0.0.1  # Localhost only (not accessible to phone)
```

### 4. Fedora Linux Firewall Instructions

On Fedora Linux, `firewalld` is active by default and blocks incoming connections to non-standard ports. To allow other devices on your home Wi-Fi to access PocketDrop on port 8000:

**Allow access temporarily (resets on reboot or firewall reload):**
```bash
sudo firewall-cmd --add-port=8000/tcp
```

**To remove the rule manually when finished:**
```bash
sudo firewall-cmd --remove-port=8000/tcp
```

> **Note:** PocketDrop does not modify firewall rules automatically to preserve system security. You retain complete manual control over open ports.

### 5. Troubleshooting Network Connectivity

- **Cannot open page on phone:**
  1. Confirm your phone is connected to the exact same Wi-Fi network as the PC.
  2. Verify your Wi-Fi router does not have **Client Isolation** (or AP Isolation) enabled. Client isolation prevents devices on Wi-Fi from communicating directly with each other.
  3. Ensure the firewall rule above was applied if running Fedora Linux.


## Documentation

Full project specifications and roadmaps are located in [`.doc/`](.doc/):
- [`architecture.md`](.doc/architecture.md): Architectural design, security rules, and data model.
- [`roadmap.md`](.doc/roadmap.md): Phased development milestones and acceptance criteria.
- [`prompt.md`](.doc/prompt.md): Engineering standards and constraints.
