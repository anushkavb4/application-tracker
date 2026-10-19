import re

import pytest

from app.parsing.engine import parse_job
from app.parsing.resolver import dedup_key
from app.seed_patterns import SEED_PATTERNS

NVIDIA_TITLE = "Careers at NVIDIA Corporation | NVIDIA Corporation"
NVIDIA_URLS = [
    "https://jobs.nvidia.com/careers?start=0&pid=893398225788&sort_by=timestamp",
    "https://jobs.nvidia.com/careers?start=0&pid=893398228603&sort_by=timestamp",
    "https://jobs.nvidia.com/careers?start=20&pid=893398196673&sort_by=timestamp",
    "https://jobs.nvidia.com/careers?start=20&pid=893396896658&sort_by=timestamp",
    "https://jobs.nvidia.com/careers?start=30&pid=893392890244&sort_by=timestamp",
]


def test_every_seed_pattern_compiles() -> None:
    for spec in SEED_PATTERNS:
        re.compile(spec.url_regex)
        if spec.title_regex:
            re.compile(spec.title_regex)


def test_nvidia_captures_become_separate_eightfold_jobs() -> None:
    parsed = [parse_job(url, NVIDIA_TITLE, SEED_PATTERNS) for url in NVIDIA_URLS]

    assert {job.ats for job in parsed} == {"eightfold"}
    assert {job.company for job in parsed} == {"NVIDIA Corporation"}
    assert len({dedup_key(job) for job in parsed}) == len(NVIDIA_URLS)
    assert dedup_key(parsed[0]) == "eightfold:893398225788"


@pytest.mark.parametrize(
    ("url", "title", "ats", "kind", "company", "role", "external_id"),
    [
        (
            "https://www.linkedin.com/jobs/view/4012345678/?trk=public_jobs",
            "(3) Acme hiring Backend Engineer in Bengaluru, Karnataka, India | LinkedIn",
            "linkedin", "aggregator", "Acme", "Backend Engineer", "4012345678",
        ),
        (
            "https://www.linkedin.com/jobs/search/?currentJobId=4012345678&keywords=python",
            "Python Jobs | LinkedIn",
            "linkedin", "aggregator", None, None, "4012345678",
        ),
        (
            "https://www.shine.com/jobs/software-engineer/acme-solutions/16543210",
            "Software Engineer Job | Shine.com",
            "shine", "job_board", "Acme Solutions", "Software Engineer", "16543210",
        ),
        (
            "https://boards.greenhouse.io/acme/jobs/4567890",
            "Job Application for Data Engineer at Acme",
            "greenhouse", "ats", "Acme", "Data Engineer", "4567890",
        ),
        (
            "https://acme.com/careers/open-roles?gh_jid=4567890",
            "Careers",
            "greenhouse", "ats", None, None, "4567890",
        ),
        (
            "https://jobs.lever.co/acme/0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0/apply",
            "Acme - Platform Engineer",
            "lever", "ats", "Acme", "Platform Engineer", "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0",
        ),
        (
            "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/Senior-Engineer_JR1987654",
            "Senior Engineer",
            "workday", "ats", "Nvidia", None, "JR1987654",
        ),
        (
            "https://jobs.ashbyhq.com/acme/0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0",
            "ML Engineer @ Acme",
            "ashby", "ats", "Acme", "ML Engineer", "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0",
        ),
        (
            "https://jobs.smartrecruiters.com/AcmeCorp/743999912345678-frontend-developer",
            "Frontend Developer",
            "smartrecruiters", "ats", "AcmeCorp", "Frontend Developer", "743999912345678",
        ),
        (
            "https://www.naukri.com/job-listings-java-developer-acme-bengaluru-3-to-5-years-120924501234",
            "Java Developer - Acme - 3 to 5 years of experience",
            "naukri", "job_board", "Acme", "Java Developer", "120924501234",
        ),
        (
            "https://in.indeed.com/viewjob?jk=a1b2c3d4e5f60789&from=serp",
            "Data Analyst - Acme - Pune, Maharashtra | Indeed.com",
            "indeed", "aggregator", "Acme", "Data Analyst", "a1b2c3d4e5f60789",
        ),
        (
            "https://boards.greenhouse.io/acme/jobs/4567890/confirmation",
            "Thank you for applying",
            "greenhouse", "confirmation", "Acme", None, "4567890",
        ),
        (
            "https://careers.example.com/application-submitted",
            "Thanks!",
            "generic", "confirmation", None, None, None,
        ),
    ],
)
def test_seed_pattern_extracts_fields(
    url: str,
    title: str,
    ats: str,
    kind: str,
    company: str | None,
    role: str | None,
    external_id: str | None,
) -> None:
    parsed = parse_job(url, title, SEED_PATTERNS)

    assert (parsed.ats, parsed.kind) == (ats, kind)
    assert parsed.company == company
    assert parsed.role == role
    assert parsed.external_id == external_id


def test_confirmation_page_shares_dedup_key_with_posting() -> None:
    posting = parse_job("https://boards.greenhouse.io/acme/jobs/4567890", None, SEED_PATTERNS)
    confirmation = parse_job(
        "https://boards.greenhouse.io/acme/jobs/4567890/confirmation", None, SEED_PATTERNS
    )

    assert dedup_key(posting) == dedup_key(confirmation)


def test_tracking_parameters_do_not_split_one_job() -> None:
    first = parse_job("https://www.linkedin.com/jobs/view/4012345678/?trk=a", None, SEED_PATTERNS)
    second = parse_job(
        "https://www.linkedin.com/jobs/view/4012345678/?refId=b&utm_source=x", None, SEED_PATTERNS
    )

    assert dedup_key(first) == dedup_key(second)


def test_unmatched_urls_with_pid_stay_separate() -> None:
    first = parse_job("https://careers.example.com/openings?pid=111", None, [])
    second = parse_job("https://careers.example.com/openings?pid=222", None, [])

    assert dedup_key(first) != dedup_key(second)
