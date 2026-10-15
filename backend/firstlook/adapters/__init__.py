"""ATS source contract. None means an unchanged board (HTTP 304)."""

import html
from typing import Protocol

from selectolax.parser import HTMLParser

from firstlook.models import Company, RawPosting


class Source(Protocol):
    def fetch(self, company: Company) -> list[RawPosting] | None: ...
    def detect(self, careers_url: str) -> tuple[str, str] | None: ...


def plain(value: str) -> str:
    return html.unescape(HTMLParser(value).text(separator=" ", strip=True))


def source(platform: str, client):
    from importlib import import_module

    return import_module(f"firstlook.adapters.{platform}").Adapter(client)


class Base:
    def __init__(self, client):
        self.client = client

    def detect(self, careers_url: str) -> tuple[str, str] | None:
        from firstlook.registry import detect

        return detect(careers_url)

    def fetch(self, company: Company) -> list[RawPosting] | None:
        from firstlook.registry import board_url

        response = self.client.get(board_url(company))
        if response.status_code == 304:
            return None
        response.raise_for_status()
        return self.parse(response.json())

    def parse(self, data) -> list[RawPosting]:
        raise NotImplementedError
