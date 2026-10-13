from app.parsing.normalize import (
    clean_title_fragment,
    deslugify,
    normalize_company_key,
    normalize_url,
)


def test_deslugify_preserves_acronyms_and_numbers() -> None:
    assert deslugify("software-engineer-II") == "Software Engineer II"
    assert deslugify("ios-platform") == "Ios Platform"


def test_clean_title_fragment_removes_separators() -> None:
    assert clean_title_fragment("  Senior Engineer  |  Acme  ") == "Senior Engineer Acme"


def test_normalize_company_key_strips_legal_suffix() -> None:
    assert normalize_company_key("Discord, Inc.") == "discord"
    assert normalize_company_key("Acme LLC") == "acme"


def test_normalize_url_removes_tracking_parameters() -> None:
    assert normalize_url("http://www.example.com/jobs/42?utm_source=linkedin") == (
        "https://example.com/jobs/42"
    )


def test_normalize_url_keeps_meaningful_identifier() -> None:
    assert normalize_url("https://jobs.example.com/apply?gh_jid=123&utm_medium=email") == (
        "https://jobs.example.com/apply?gh_jid=123"
    )
