from app.parsing.engine import ParsedJob
from app.parsing.resolver import (
    authority_for_ats,
    confidence_for_trigger,
    dedup_key,
    is_forward,
    resolve,
    should_replace_chain,
    status_for_confidence,
)


def test_dedup_key_prefers_ats_identity() -> None:
    parsed = ParsedJob(
        url="https://example.com/jobs/123?utm_source=linkedin",
        ats="greenhouse",
        external_id="123",
    )

    assert dedup_key(parsed) == "greenhouse:123"


def test_dedup_key_falls_back_to_url() -> None:
    parsed = ParsedJob(url="https://example.com/jobs/123")

    assert dedup_key(parsed) == parsed.url


def test_confirmation_confidence_promotes_application() -> None:
    parsed = ParsedJob(url="https://example.com/thank-you", kind="confirmation")

    assert confidence_for_trigger("ats_nav", parsed) == 70
    assert resolve(parsed, "ats_nav").status == "applied"
    assert status_for_confidence(30) == "viewed"


def test_status_does_not_move_backward() -> None:
    assert is_forward("viewed", "applied") is True
    assert is_forward("interview", "applied") is False
    assert is_forward("interview", "rejected") is True


def test_real_ats_beats_aggregator_in_navigation_chain() -> None:
    aggregator = ParsedJob(url="https://linkedin.com/jobs/1", ats="linkedin")
    ats = ParsedJob(url="https://jobs.example.com/1", ats="greenhouse")

    assert authority_for_ats("linkedin") == 1
    assert authority_for_ats("greenhouse") == 2
    assert should_replace_chain(aggregator, ats) is True
