"""Polite conditional requests shared by all ATS adapters."""

import json
import os
import random
import sqlite3
import threading
import time
from collections import defaultdict
from urllib.parse import urlparse

import httpx

from firstlook.registry import allowed_url


class PoliteClient:
    MIN_DELAY = 0.5
    _global = threading.BoundedSemaphore(4)
    _hosts: dict = defaultdict(lambda: threading.BoundedSemaphore(1))
    _last: dict[str, float] = {}

    def __init__(
        self,
        db: sqlite3.Connection,
        transport=None,
        sleep=time.sleep,
        clock=time.monotonic,
        full=False,
    ):
        self.db, self.sleep, self.clock, self.full = db, sleep, clock, full
        self.client = httpx.Client(
            http2=True,
            timeout=30,
            transport=transport,
            follow_redirects=False,
            headers={
                "User-Agent": "firstlook/0.1 (+local job research; contact: "
                + os.environ.get("FIRSTLOOK_CONTACT", "configure-me")
                + ")"
            },
        )
        self.bytes = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.client.close()

    def cached_response(self, url):
        row = self.db.execute(
            "SELECT value FROM cache WHERE key=?", ("http:" + str(url),)
        ).fetchone()
        if not row:
            raise ValueError("304 without a cached response")
        value = json.loads(row[0])
        return httpx.Response(200, text=value["body"], request=httpx.Request("GET", str(url)))

    def get(self, url: str):
        allowed_url(url)
        host = urlparse(url).hostname
        headers = {}
        row = self.db.execute("SELECT value FROM cache WHERE key=?", ("http:" + url,)).fetchone()
        if row and not self.full:
            cached = json.loads(row[0])
            if cached.get("etag"):
                headers["If-None-Match"] = cached["etag"]
            if cached.get("modified"):
                headers["If-Modified-Since"] = cached["modified"]
        with self._global, self._hosts[host]:
            for attempt in range(4):
                self.sleep(max(0, self.MIN_DELAY - (self.clock() - self._last.get(str(host), 0))))
                response = self.client.get(url, headers=headers)
                self._last[str(host)] = self.clock()
                self.bytes += len(response.content)
                if response.status_code != 429 and response.status_code < 500:
                    break
                if attempt < 3:
                    retry = response.headers.get("Retry-After", "0")
                    self.sleep(
                        max(float(retry) if retry.isdigit() else 0, 2**attempt + random.random())
                    )
        if response.status_code == 200:
            value = dict(
                etag=response.headers.get("etag"),
                modified=response.headers.get("last-modified"),
                body=response.text,
            )
            self.db.execute(
                "INSERT INTO cache(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("http:" + url, json.dumps(value)),
            )
            self.db.commit()
        return response
