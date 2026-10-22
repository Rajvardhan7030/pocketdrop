"""Network interface discovery and binding helpers for PocketDrop."""

import json
import logging
import os
import socket
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger("pocketdrop.network")


@dataclass
class NetworkInterface:
    name: str
    ip: str
    state: str
    is_wifi: bool


class NetworkError(Exception):
    """Raised when network binding or interface resolution fails."""
    pass


def get_available_interfaces() -> List[NetworkInterface]:
    """
    Discover all non-loopback network interfaces with an assigned IPv4 address.
    Uses 'ip -j addr' on Linux/Fedora.
    """
    interfaces: List[NetworkInterface] = []

    try:
        output = subprocess.check_output(
            ["ip", "-j", "addr"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2.0
        )
        data = json.loads(output)
        for iface in data:
            name = iface.get("ifname", "")
            state = iface.get("operstate", "").upper()
            
            # Check if wireless: names starting with 'wl' or listed under /sys/class/net/<name>/wireless
            is_wifi = name.startswith("wl") or os.path.exists(f"/sys/class/net/{name}/wireless")

            for addr in iface.get("addr_info", []):
                family = addr.get("family")
                ip = addr.get("local")
                if family == "inet" and ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                    interfaces.append(NetworkInterface(
                        name=name,
                        ip=ip,
                        state=state,
                        is_wifi=is_wifi
                    ))
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError, OSError) as e:
        logger.warning("Failed to query 'ip -j addr': %s", e)

    return interfaces


def resolve_bind_ip(
    preferred_ip: Optional[str] = None,
    preferred_interface: Optional[str] = None
) -> Tuple[str, str]:
    """
    Resolve the specific IPv4 address and interface name to bind the server to.
    
    Priority:
    1. preferred_ip if explicitly provided.
    2. preferred_interface if explicitly provided and has an IPv4 address.
    3. Active (UP) Wi-Fi interface with IPv4.
    4. Active (UP) Ethernet/wired interface with IPv4.
    5. Any other available non-loopback IPv4 interface.

    Raises NetworkError if no suitable address is found.
    """
    if preferred_ip and preferred_ip not in ("0.0.0.0", "127.0.0.1"):
        return preferred_ip, "manual"

    interfaces = get_available_interfaces()

    if preferred_interface:
        for iface in interfaces:
            if iface.name == preferred_interface:
                return iface.ip, iface.name
        raise NetworkError(
            f"Preferred network interface '{preferred_interface}' has no valid IPv4 address or is unavailable."
        )

    # 1. Look for active UP Wi-Fi
    wifi_up = [i for i in interfaces if i.is_wifi and i.state == "UP"]
    if wifi_up:
        return wifi_up[0].ip, wifi_up[0].name

    # 2. Look for any active UP interface
    any_up = [i for i in interfaces if i.state == "UP"]
    if any_up:
        return any_up[0].ip, any_up[0].name

    # 3. Look for any Wi-Fi interface (even if operstate unknown or non-UP)
    any_wifi = [i for i in interfaces if i.is_wifi]
    if any_wifi:
        return any_wifi[0].ip, any_wifi[0].name

    # 4. Any interface
    if interfaces:
        return interfaces[0].ip, interfaces[0].name

    # If preferred_ip is localhost, allow explicit fallback
    if preferred_ip == "127.0.0.1":
        return "127.0.0.1", "lo"

    raise NetworkError(
        "No active Wi-Fi or LAN IPv4 address found. PocketDrop requires an active network connection "
        "to allow devices on your home Wi-Fi to connect.\n"
        "Troubleshooting steps:\n"
        "  1. Ensure Wi-Fi is connected on this PC.\n"
        "  2. Check that your router does not have 'Client Isolation' enabled.\n"
        "  3. Use --host 127.0.0.1 for local PC testing only."
    )


def is_port_available(host: str, port: int) -> bool:
    """Check if the given host and port combination is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
    except OSError:
        return False


def ensure_port_available(host: str, port: int) -> None:
    """Validate that the port is free, raising NetworkError with troubleshooting advice if busy."""
    if not is_port_available(host, port):
        raise NetworkError(
            f"Port {port} on {host} is already in use by another application.\n"
            f"Troubleshooting steps:\n"
            f"  1. Stop any existing PocketDrop or web server instances.\n"
            f"  2. Set a different port with: export POCKETDROP_PORT=8080 (or pass --port 8080)."
        )
