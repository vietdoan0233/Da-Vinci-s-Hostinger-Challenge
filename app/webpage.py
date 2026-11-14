"""Feature 11: any web link -> the page's readable text, through the Oxylabs Web API.

/v1/scrape reads the page as Markdown (coverage.py uses the same call for its sources).
The text then goes through the same checks as a pasted post, so a technique is still
kept only if it quotes words that are on the page.
"""
import os
import re
from urllib.parse import urlsplit

import httpx

from app import cache, coverage

MAX_CHARS = 5000  # same cap as pasted text: one AI call per analysis
MIN_CHARS = 200   # less than this is a cookie wall or an empty shell, not something to analyse
MIN_WORDS = 8     # shorter blocks are menus, buttons and bylines
TTL = 600


class PageError(Exception):
    pass


def parse_url(url):
    """-> the link, if it is a public http(s) one. The page is fetched by Oxylabs, never by this server."""
    url = url.strip()
    try:
        u = urlsplit(url)
        host = u.hostname or ""
    except ValueError:
        raise PageError("Not a web link") from None
    if u.scheme not in ("http", "https") or len(url) > 2000 or re.search(r"\s", url):
        raise PageError("Not a web link")
    if "." not in host or ":" in host or re.fullmatch(r"[\d.]+", host):  # localhost, IP addresses
        raise PageError("Not a public web link")
    return url


def main_text(md):
    """A whole page as Markdown -> (title, readable text, truncated).

    Link and image markup is removed so a quote is compared against the words a reader sees.
    """
    # shortcut: the body is "blocks of MIN_WORDS words or more after the first top heading", which
    # keeps long cookie notices and drops short paragraphs; swap in Oxylabs AI Parsing
    # ("json" output with a schema) if demo pages come out wrong
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)
    md = re.sub(r"</?\s*post\s*>", " ", md, flags=re.I)
    m = re.search(r"^#\s+(.+)$", md, flags=re.M)
    title = " ".join(re.sub(r"[*`]+", "", m.group(1)).split())[:200] if m else ""
    if m:
        md = md[m.end():]  # menus and banners sit above the headline
    kept = []
    for block in re.split(r"\n\s*\n", md):
        # a list is one block of many lines: judge each item on its own, so a menu goes and a real list stays
        lines = block.split("\n") if re.match(r"\s*([-*+]|\d+\.)\s", block) else [block]
        for line in lines:
            line = re.sub(r"^\s*(#+|>+|[-*+]|\d+\.)\s+", "", line)
            line = " ".join(re.sub(r"[*`]+", "", line).split())
            if len(line.split()) >= MIN_WORDS and not line.startswith("|"):
                kept.append(line)
    text = "\n\n".join(kept)
    if len(text) <= MAX_CHARS:
        return title, text, False
    cut = text[:MAX_CHARS]
    end = max(cut.rfind(". "), cut.rfind(".\n"))
    return title, cut[:end + 1] if end > MAX_CHARS // 2 else cut, True


def get_page(url):
    """-> {text, author, url, ts, kind, title, truncated}: the shape of a Bluesky post, with the
    site's domain where the author's handle would be and kind "page". Cached for ten minutes."""
    url = parse_url(url)
    if not os.environ.get("OXYLABS_WEB_API_KEY"):
        raise coverage.NotConfigured("OXYLABS_WEB_API_KEY is not set")
    k = cache.key("page", url)
    hit = cache.get(k, TTL)
    if hit is not None:
        return hit
    title = text = ""
    truncated = False
    # A page that comes back empty is read once more in a real browser, as the Oxylabs docs advise
    # (run_js is slow: they ask for a client timeout of 150 s).
    for extra, timeout in (({}, 45), ({"run_js": True}, 150)):
        try:
            rows = coverage._oxy("scrape", {"url": url, "output": ["markdown"], **extra}, timeout).get("results") or [{}]
            title, text, truncated = main_text(str(rows[0].get("markdown") or ""))
        except (httpx.HTTPError, ValueError, AttributeError, IndexError):
            continue
        if len(text) >= MIN_CHARS:
            break
    else:
        raise PageError("Not enough data: the page could not be read, or has too little text to check")
    domain = coverage._domain(url)
    page = {"text": text, "author": domain, "url": url, "ts": None, "kind": "page",
            "title": title or domain, "truncated": truncated}
    cache.set(k, page)
    return page
