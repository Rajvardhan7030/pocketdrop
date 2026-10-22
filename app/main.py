"""PocketDrop main FastAPI application and CLI entrypoint."""

import argparse
import logging
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import settings
from app.network import NetworkError, ensure_port_available, resolve_bind_ip
from app.routes.auth import router as auth_router
from app.routes.files import router as files_router
from app.routes.text import router as text_router
from app.security import get_or_create_auth_token

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("pocketdrop")

# Base paths
APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"

# Construct FastAPI app
app = FastAPI(
    title="PocketDrop",
    description="Local-first file and text sharing server for Fedora Linux",
    version=__version__,
    docs_url=None,  # Disabled on LAN to avoid leaking API schema unnecessarily
    redoc_url=None
)

# Ensure runtime directories exist
settings.ensure_directories()

# Mount static assets (CSS, JS) — explicitly isolated from data/storage
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Register API routers
app.include_router(auth_router)
app.include_router(files_router)
app.include_router(text_router)


@app.get("/", summary="Dashboard interface")
async def get_dashboard():
    """Serve the single-page dashboard."""
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard template not found")
    return FileResponse(index_file, media_type="text/html")


@app.get("/api/status", summary="Public health and status endpoint")
async def get_status():
    """
    Non-sensitive status endpoint.
    Crucial: Returns only application health and version.
    Never exposes internal file paths, credentials, tokens, or file listings.
    """
    return {
        "status": "ok",
        "app": "PocketDrop",
        "version": __version__
    }


def main():
    """CLI launcher for manual server start/stop."""
    parser = argparse.ArgumentParser(
        description="Start the PocketDrop local file-sharing server."
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Custom IP address to bind to (defaults to active Wi-Fi IPv4 address)."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Custom port to bind to (defaults to 8000 or POCKETDROP_PORT)."
    )
    parser.add_argument(
        "--iface",
        type=str,
        default=None,
        help="Preferred network interface name (e.g. wlan0, wlp0s26u1u3)."
    )
    args = parser.parse_args()

    # Determine port
    port = args.port or settings.PORT

    # Determine host IP
    try:
        bind_host, iface_name = resolve_bind_ip(
            preferred_ip=args.host or (None if settings.HOST == "127.0.0.1" and not args.host else settings.HOST),
            preferred_interface=args.iface
        )
    except NetworkError as err:
        logger.error("Network interface error:\n%s", err)
        sys.exit(1)

    # Check port availability
    try:
        ensure_port_available(bind_host, port)
    except NetworkError as err:
        logger.error("Port conflict error:\n%s", err)
        sys.exit(1)

    # Print startup banner
    pin = get_or_create_auth_token()
    url = f"http://{bind_host}:{port}"
    print("\n" + "=" * 55)
    print("  PocketDrop — Local File & Text Sharing")
    print("=" * 55)
    print(f"  Bound Interface: {iface_name} ({bind_host})")
    print(f"  Access URL:      {url}")
    print(f"  Pairing PIN:     {pin}")
    print("=" * 55)
    print("  Open the Access URL in your phone or PC browser.")
    print("  Enter the Pairing PIN to authorize your device.")
    print("  Both devices must be connected to the same home Wi-Fi.")
    print("  Press Ctrl+C to stop the server at any time.")
    print("=" * 55 + "\n")

    import uvicorn
    try:
        uvicorn.run(
            "app.main:app",
            host=bind_host,
            port=port,
            log_level="info",
            access_log=False  # Keep logs clean; avoid logging sensitive query params/headers
        )
    except KeyboardInterrupt:
        print("\nStopping PocketDrop server cleanly...")
        sys.exit(0)


if __name__ == "__main__":
    main()
