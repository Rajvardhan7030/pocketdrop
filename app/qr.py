"""Terminal QR code generation for PocketDrop."""

import logging
from typing import Optional

logger = logging.getLogger("pocketdrop.qr")


def print_terminal_qr(url: str) -> bool:
    """
    Print a compact UTF-8 QR code directly to the terminal.
    Returns True if successfully printed, False if generation failed.
    Never crashes or stops startup if QR generation encounters an issue.
    """
    try:
        import segno
        qr = segno.make(url)
        print("\n  Scan with your phone camera:")
        qr.terminal(compact=True)
        print()
        return True
    except Exception as e:
        logger.debug("QR generation skipped or failed: %s", e)
        return False
