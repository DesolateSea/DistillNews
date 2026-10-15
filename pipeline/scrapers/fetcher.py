"""Compatibility wrappers; untrusted public proxies are deliberately disabled."""
import urllib3
from .safe_fetch import fetch_public_html


def fetch_direct_and_via_proxy(target_url, working_urls):
    try:
        return fetch_public_html(target_url)
    except (ValueError, OSError, urllib3.exceptions.HTTPError):
        return None


def final_rotate_scrape(target_url, working_urls):
    return None
