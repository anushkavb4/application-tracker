from app.parsing.engine import PatternSpec, parse_job


def test_parse_job_prefers_title_company_and_role() -> None:
    patterns = [
        PatternSpec(
            ats="greenhouse",
            kind="ats",
            url_regex=r"jobs\.example\.com/(?P<company>[^/]+)/jobs/(?P<external_id>\d+)",
            title_regex=r"^(?P<role>.+?)\s+at\s+(?P<company>.+?)$",
            priority=10,
        )
    ]

    parsed = parse_job(
        "https://jobs.example.com/acme-inc/jobs/123",
        "Senior Backend Engineer at Acme",
        patterns,
    )

    assert parsed.ats == "greenhouse"
    assert parsed.company == "Acme"
    assert parsed.role == "Senior Backend Engineer"
    assert parsed.external_id == "123"
    assert parsed.sources == {"company": "title", "role": "title", "external_id": "url"}


def test_parse_job_returns_unmatched_result() -> None:
    parsed = parse_job("https://example.com/jobs/1", "Unknown", [])

    assert parsed.kind == "unmatched"
    assert parsed.ats is None
    assert parsed.external_id is None


def test_lower_priority_patterns_are_used_as_fallback() -> None:
    patterns = [
        PatternSpec(ats="fallback", kind="ats", url_regex=r"example\.com/(?P<role>[^/]+)", priority=100),
        PatternSpec(ats="specific", kind="ats", url_regex=r"example\.com/jobs/(?P<external_id>\d+)", priority=10),
    ]

    parsed = parse_job("https://example.com/jobs/123", None, patterns)

    assert parsed.ats == "specific"
    assert parsed.external_id == "123"
