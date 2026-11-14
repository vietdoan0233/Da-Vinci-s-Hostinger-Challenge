"""One SQLite table as a cache, so repeat views do not spend LLM credits."""
import hashlib
import json
import logging
import os
import sqlite3
import time
from contextlib import closing

log = logging.getLogger("app.cache")


def _db():
    con = sqlite3.connect(os.environ.get("CACHE_PATH", "cache.db"))
    con.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, json TEXT, created REAL)")
    return con


def key(*parts):
    return hashlib.sha256("\x00".join(map(str, parts)).encode()).hexdigest()


def get(k, max_age=None):
    """A broken or unwritable cache file is a miss, never a failed request."""
    try:
        with closing(_db()) as con:
            row = con.execute("SELECT json, created FROM cache WHERE key = ?", (k,)).fetchone()
    except sqlite3.Error:
        log.warning("cache read failed", exc_info=True)
        return None
    if row and (max_age is None or time.time() - row[1] <= max_age):
        return json.loads(row[0])
    return None


def set(k, value):
    try:
        with closing(_db()) as con, con:  # closing() closes, `con` commits
            con.execute("INSERT OR REPLACE INTO cache VALUES (?, ?, ?)", (k, json.dumps(value), time.time()))
    except sqlite3.Error:
        log.warning("cache write failed", exc_info=True)
