from dataclasses import dataclass

from app.parsing.engine import ParsedJob
from app.parsing.normalize import normalize_url

FUNNEL_ORDER = (
    "viewed",
    "applied",
    "screening",
    "interview",
    "offer",
)
CONFIDENCE_BY_TRIGGER = {
    "intent_click": 10,
    "ats_nav": 30,
    "confirmation": 70,
    "form_submit": 90,
}
AUTHORITY_BY_ATS_KIND = {
    "aggregator": 1,
    "job_board": 1,
    "ats": 2,
}


@dataclass(frozen=True)
class Resolution:
    dedup_key: str
    status: str
    confidence: int
    status_source: str = "automatic"


def dedup_key(parsed: ParsedJob) -> str:
    if parsed.ats and parsed.external_id:
        return f"{parsed.ats}:{parsed.external_id}"
    return normalize_url(parsed.url)


def confidence_for_trigger(trigger_type: str, parsed: ParsedJob) -> int:
    if parsed.kind == "confirmation":
        return CONFIDENCE_BY_TRIGGER["confirmation"]
    return CONFIDENCE_BY_TRIGGER.get(trigger_type, 0)


def status_for_confidence(confidence: int) -> str:
    return "applied" if confidence >= 70 else "viewed"


def resolve(parsed: ParsedJob, trigger_type: str) -> Resolution:
    confidence = confidence_for_trigger(trigger_type, parsed)
    return Resolution(
        dedup_key=dedup_key(parsed),
        status=status_for_confidence(confidence),
        confidence=confidence,
    )


def is_forward(current_status: str, proposed_status: str) -> bool:
    if proposed_status in {"rejected", "withdrawn"}:
        return True
    try:
        return FUNNEL_ORDER.index(proposed_status) >= FUNNEL_ORDER.index(current_status)
    except ValueError:
        return current_status == proposed_status


def authority_for_ats(ats: str | None, kind: str | None = None) -> int:
    if kind in AUTHORITY_BY_ATS_KIND:
        return AUTHORITY_BY_ATS_KIND[kind]
    if ats in {"linkedin", "indeed", "glassdoor", "ziprecruiter"}:
        return 1
    if ats:
        return 2
    return 0


def should_replace_chain(current: ParsedJob, incoming: ParsedJob) -> bool:
    return authority_for_ats(incoming.ats) > authority_for_ats(current.ats)
