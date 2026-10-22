"""Tests for network interface discovery and binding helpers."""

import socket
import pytest
from unittest.mock import patch
from app.network import (
    NetworkError,
    NetworkInterface,
    ensure_port_available,
    is_port_available,
    resolve_bind_ip,
)


def test_resolve_bind_ip_explicit():
    ip, iface = resolve_bind_ip(preferred_ip="192.168.1.100")
    assert ip == "192.168.1.100"
    assert iface == "manual"


def test_resolve_bind_ip_prioritizes_wifi():
    mock_interfaces = [
        NetworkInterface(name="eth0", ip="192.168.1.10", state="UP", is_wifi=False),
        NetworkInterface(name="wlan0", ip="192.168.1.20", state="UP", is_wifi=True),
    ]
    with patch("app.network.get_available_interfaces", return_value=mock_interfaces):
        ip, iface = resolve_bind_ip()
        assert ip == "192.168.1.20"
        assert iface == "wlan0"


def test_resolve_bind_ip_falls_back_to_ethernet():
    mock_interfaces = [
        NetworkInterface(name="enp3s0", ip="192.168.1.50", state="UP", is_wifi=False),
    ]
    with patch("app.network.get_available_interfaces", return_value=mock_interfaces):
        ip, iface = resolve_bind_ip()
        assert ip == "192.168.1.50"
        assert iface == "enp3s0"


def test_resolve_bind_ip_explicit_interface():
    mock_interfaces = [
        NetworkInterface(name="eth0", ip="192.168.1.10", state="UP", is_wifi=False),
        NetworkInterface(name="wlan0", ip="192.168.1.20", state="UP", is_wifi=True),
    ]
    with patch("app.network.get_available_interfaces", return_value=mock_interfaces):
        ip, iface = resolve_bind_ip(preferred_interface="eth0")
        assert ip == "192.168.1.10"
        assert iface == "eth0"

        with pytest.raises(NetworkError, match="Preferred network interface 'wlan99' has no valid IPv4"):
            resolve_bind_ip(preferred_interface="wlan99")


def test_resolve_bind_ip_no_interfaces_error():
    with patch("app.network.get_available_interfaces", return_value=[]):
        with pytest.raises(NetworkError, match="No active Wi-Fi or LAN IPv4 address found"):
            resolve_bind_ip()


def test_resolve_bind_ip_localhost_fallback():
    with patch("app.network.get_available_interfaces", return_value=[]):
        ip, iface = resolve_bind_ip(preferred_ip="127.0.0.1")
        assert ip == "127.0.0.1"
        assert iface == "lo"


def test_port_availability():
    # Test with an unused ephemeral port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]

    # Free port should be available
    assert is_port_available("127.0.0.1", free_port) is True
    ensure_port_available("127.0.0.1", free_port)

    # Bind port to simulate in-use port
    occupied_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupied_socket.bind(("127.0.0.1", free_port))
    occupied_socket.listen(1)

    try:
        assert is_port_available("127.0.0.1", free_port) is False
        with pytest.raises(NetworkError, match=f"Port {free_port} on 127.0.0.1 is already in use"):
            ensure_port_available("127.0.0.1", free_port)
    finally:
        occupied_socket.close()
