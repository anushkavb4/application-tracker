import logging
import re
from dataclasses import dataclass, field
from typing import Protocol

from app.parsing.normalize import clean_title_fragment, deslugify

logger = logging.getLogger(__name__)


class PatternRow(Protocol):
    ats: str
    kind: str
    url_regex: str
    title_regex: str | None
    priority: int
    enabled: bool


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


def _first_group(match: re.Match[str], name: str) -> str | None:
    try:
        value = match.group(name)
    except (IndexError, KeyError):
        return None
    return clean_title_fragment(value)


def parse_job(url: str, page_title: str | None, patterns: list[PatternRow]) -> ParsedJob:
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

        company = _first_group(url_match, "company")
        role = _first_group(url_match, "role")
        external_id = _first_group(url_match, "external_id")
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

        if role is None:
            role = deslugify(_first_group(url_match, "role"))

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
