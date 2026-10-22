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

```bash
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
*(Launcher script `run.sh` with automatic Wi-Fi IP detection is provided in Phase 5).*

## Documentation

Full project specifications and roadmaps are located in [`.doc/`](.doc/):
- [`architecture.md`](.doc/architecture.md): Architectural design, security rules, and data model.
- [`roadmap.md`](.doc/roadmap.md): Phased development milestones and acceptance criteria.
- [`prompt.md`](.doc/prompt.md): Engineering standards and constraints.
