"""Tests for terminal QR code generation and launcher safety."""

import sys
from unittest.mock import patch
from app.qr import print_terminal_qr


def test_terminal_qr_generation_success(capsys):
    url = "http://192.168.1.50:8000"
    success = print_terminal_qr(url)
    assert success is True

    captured = capsys.readouterr()
    assert "Scan with your phone camera:" in captured.out
    # Check that block characters from QR are present
    assert "█" in captured.out or "▀" in captured.out


def test_terminal_qr_generation_failure_does_not_crash(capsys):
    # Simulate an error inside QR generation
    with patch("segno.make", side_effect=Exception("Simulated QR error")):
        success = print_terminal_qr("http://192.168.1.50:8000")
        assert success is False
