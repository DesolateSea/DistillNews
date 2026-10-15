"""Public-only HTTPS with DNS pinned to the validated address."""
import ipaddress
import socket
import ssl
import time
from urllib.parse import urlsplit, urljoin
import urllib3


def resolve_public(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Only public HTTPS URLs on port 443 are permitted")
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    ips = [address[4][0] for address in addresses]

    def public(ip):
        address = ipaddress.ip_address(ip)
        return address.is_global and not any((address.is_multicast, address.is_reserved,
            address.is_loopback, address.is_link_local, address.is_unspecified))

    if not ips or any(not public(ip) for ip in ips):
        raise ValueError("Non-public destination rejected")
    return parsed, ips[0]


def fetch_public_html(url):
    started = time.monotonic()
    for _ in range(4):
        if time.monotonic() - started > 20:
            raise ValueError("News fetch timed out")
        parsed, ip = resolve_public(url)
        pool = urllib3.HTTPSConnectionPool(ip, port=443, server_hostname=parsed.hostname,
            assert_hostname=parsed.hostname, ssl_context=ssl.create_default_context(),
            timeout=urllib3.Timeout(connect=5, read=5), retries=False)
        response = None
        try:
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            response = pool.urlopen("GET", path, headers={"Host": parsed.hostname,
                "Accept-Encoding": "identity", "User-Agent": "DistillNews/1.0"},
                redirect=False, preload_content=False)
            if response.status in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")
                if not location:
                    raise ValueError("Invalid redirect")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError("News source returned an error")
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise ValueError("Compressed responses are not permitted")
            content = bytearray()
            for chunk in response.stream(8192, decode_content=False):
                content.extend(chunk)
                if len(content) > 2_000_000 or time.monotonic() - started > 20:
                    raise ValueError("News response exceeds resource limits")
            return content.decode("utf-8", errors="replace")
        finally:
            if response:
                response.close()
            pool.close()
    raise ValueError("Too many redirects")
