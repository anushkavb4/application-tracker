import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import unquote

from app.parsing.normalize import clean_title_fragment, deslugify

logger = logging.getLogger(__name__)


class PatternRow(Protocol):
    @property
    def ats(self) -> str: ...

    @property
    def kind(self) -> str: ...

    @property
    def url_regex(self) -> str: ...

    @property
    def title_regex(self) -> str | None: ...

    @property
    def priority(self) -> int: ...

    @property
    def enabled(self) -> bool: ...


@dataclass(frozen=True)
class ParsedJob:
    url: str
    ats: str | None = None
    kind: str = "unmatched"
    company: str | None = None
    role: str | None = None
    external_id: str | None = None
    sources: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PatternSpec:
    ats: str
    kind: str
    url_regex: str
    title_regex: str | None = None
    priority: int = 100
    enabled: bool = True


def _compile(pattern: str, label: str) -> re.Pattern[str] | None:
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        logger.warning("Skipping invalid %s regex: %s", label, pattern)
        return None


def _raw_group(match: re.Match[str], name: str) -> str | None:
    try:
        return match.group(name)
    except (IndexError, KeyError):
        return None


def _first_group(match: re.Match[str], name: str) -> str | None:
    return clean_title_fragment(_raw_group(match, name))


def _url_group(match: re.Match[str], name: str) -> str | None:
    value = _raw_group(match, name)
    return clean_title_fragment(deslugify(unquote(value))) if value else None


def parse_job(url: str, page_title: str | None, patterns: Sequence[PatternRow]) -> ParsedJob:
    ordered_patterns = sorted(
        (pattern for pattern in patterns if pattern.enabled),
        key=lambda pattern: pattern.priority,
    )

    for pattern in ordered_patterns:
        url_re = _compile(pattern.url_regex, "URL")
        if url_re is None:
            continue
        url_match = url_re.search(url)
        if url_match is None:
            continue

        company = _url_group(url_match, "company")
        role = _url_group(url_match, "role")
        external_id = (_raw_group(url_match, "external_id") or "").strip() or None
        sources: dict[str, str] = {}

        if company:
            sources["company"] = "url"
        if role:
            sources["role"] = "url"
        if external_id:
            sources["external_id"] = "url"

        if page_title and pattern.title_regex:
            title_re = _compile(pattern.title_regex, "title")
            title_match = title_re.search(page_title) if title_re else None
            if title_match:
                title_company = _first_group(title_match, "company")
                title_role = _first_group(title_match, "role")
                if title_company:
                    company = title_company
                    sources["company"] = "title"
                if title_role:
                    role = title_role
                    sources["role"] = "title"

        return ParsedJob(
            url=url,
            ats=pattern.ats,
            kind=pattern.kind,
            company=company,
            role=role,
            external_id=external_id,
            sources=sources,
        )

    return ParsedJob(url=url)
