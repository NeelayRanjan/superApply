"""Shared validated domain objects."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Platform = Literal[
    "greenhouse", "lever", "ashby", "smartrecruiters", "workable", "recruitee", "jsonld"
]


class Company(BaseModel):
    id: str
    name: str
    domain: str
    platform: Platform
    token: str
    tags: list[str] = Field(default_factory=list)
    size: str = "unknown"
    verified: bool = False
    notes: str = ""

    @field_validator("id", "name", "domain", "token")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Must not be empty")
        return value.strip()


class RawPosting(BaseModel):
    external_id: str
    title: str
    apply_url: str
    locations: list[str] = Field(default_factory=list)
    remote: bool = False
    department: str = ""
    employment_type: str = ""
    posted_at: str | None = None
    description_html: str = ""
    description: str = ""
    compensation: dict = Field(default_factory=dict)

    @field_validator("apply_url")
    @classmethod
    def absolute_url(cls, value: str) -> str:
        if not value.startswith(("https://", "http://")):
            raise ValueError("Apply URL must be absolute")
        return value
