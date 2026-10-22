#!/usr/bin/env bash
#
# PocketDrop Manual Launcher
# Starts the local-first file and text sharing server on Fedora Linux.
#

set -e

# Prevent running as root
if [ "$(id -u)" -eq 0 ]; then
    echo "ERROR: For security reasons, do not run PocketDrop as root." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"

# Check if Python 3 is installed
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3 is required but not installed." >&2
    exit 1
fi

# Check or create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Creating .venv at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        echo "Installing dependencies from requirements.txt..."
        "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    fi
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Launch application passing all arguments
exec python3 -m app.main "$@"
