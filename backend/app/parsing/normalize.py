import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_MEANINGFUL_QUERY_KEYS = {
    "currentJobId",
    "gh_jid",
    "job_id",
    "jobId",
    "jk",
    "jl",
    "pid",
    "requisitionId",
}
_LEGAL_SUFFIXES = ("inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation")
_SEPARATOR_RE = re.compile(r"\s*(?:[-|·•])\s*")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def deslugify(value: str | None) -> str | None:
    if not value:
        return None
    words = re.split(r"[-_]+", value.strip("-_/"))
    return " ".join(
        word if word != word.casefold() or word.isdigit() else word.capitalize()
        for word in words
        if word
    )


def clean_title_fragment(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _SEPARATOR_RE.sub(" ", value).strip(" -|·•\t")
    return re.sub(r"\s+", " ", cleaned) or None


def normalize_company_key(value: str | None) -> str | None:
    if not value:
        return None
    normalized = _NON_ALNUM_RE.sub(" ", value.casefold()).strip()
    words = normalized.split()
    while words and words[-1] in _LEGAL_SUFFIXES:
        words.pop()
    return "".join(words) or None


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").casefold()
    if host.startswith("www."):
        host = host[4:]
    netloc = host
    if parts.port:
        netloc = f"{host}:{parts.port}"
    path = parts.path or "/"
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key in _MEANINGFUL_QUERY_KEYS
        )
    )
    return urlunsplit(("https", netloc, path.rstrip("/") or "/", query, ""))
