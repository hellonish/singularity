"""Network-target validation shared by URL-reading tools."""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse


async def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must use http or https and include a hostname")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing embedded credentials are not allowed")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("URL contains an invalid port") from exc
    if port is not None and port not in {80, 443}:
        raise ValueError("Only standard HTTP and HTTPS ports are allowed")
    default_port = 443 if parsed.scheme == "https" else 80
    addresses = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, port or default_port, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError("URL hostname did not resolve")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("Private, local, reserved, and link-local network targets are not allowed")
