"""Starter parser patterns, inserted on first boot when `url_patterns` is empty.

These are educated guesses about each site's URL and page-title shapes, not ground
truth. Sites change their URLs, so treat this list as a starting point and fix
patterns in the database as real captures show where they miss.

Priority is ascending: ATS-specific confirmation pages run first so they are not
swallowed by the posting pattern for the same ATS; generic confirmation shapes
run last as a fallback.
"""

from app.parsing.engine import PatternSpec

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

SEED_PATTERNS: tuple[PatternSpec, ...] = (
    # ATS-specific confirmation pages.
    PatternSpec(
        ats="greenhouse",
        kind="confirmation",
        url_regex=r"greenhouse\.io/(?P<company>[^/?#]+)/jobs/(?P<external_id>\d+)/confirmation",
        priority=5,
    ),
    PatternSpec(
        ats="lever",
        kind="confirmation",
        url_regex=rf"jobs\.lever\.co/(?P<company>[^/?#]+)/(?P<external_id>{_UUID})/thanks",
        priority=5,
    ),
    # Applicant tracking systems.
    PatternSpec(
        ats="greenhouse",
        kind="ats",
        url_regex=r"greenhouse\.io/(?P<company>[^/?#]+)/jobs/(?P<external_id>\d+)",
        title_regex=r"^Job Application for (?P<role>.+?) at (?P<company>.+)$",
        priority=10,
    ),
    PatternSpec(
        ats="greenhouse",
        kind="ats",
        url_regex=r"[?&]gh_jid=(?P<external_id>\d+)",
        priority=11,
    ),
    PatternSpec(
        ats="lever",
        kind="ats",
        url_regex=rf"jobs\.lever\.co/(?P<company>[^/?#]+)/(?P<external_id>{_UUID})",
        title_regex=r"^(?P<company>.+?) - (?P<role>.+)$",
        priority=10,
    ),
    PatternSpec(
        ats="workday",
        kind="ats",
        url_regex=(
            r"(?P<company>[a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com/"
            r"(?:[^?#]*/)?job/(?:[^/?#]+/)*[^/?#]*_(?P<external_id>[A-Za-z0-9-]+)"
        ),
        priority=10,
    ),
    PatternSpec(
        ats="ashby",
        kind="ats",
        url_regex=rf"jobs\.ashbyhq\.com/(?P<company>[^/?#]+)/(?P<external_id>{_UUID})",
        title_regex=r"^(?P<role>.+?) @ (?P<company>.+)$",
        priority=10,
    ),
    PatternSpec(
        ats="smartrecruiters",
        kind="ats",
        url_regex=r"jobs\.smartrecruiters\.com/(?P<company>[^/?#]+)/(?P<external_id>\d+)(?:-(?P<role>[^/?#]+))?",
        priority=10,
    ),
    PatternSpec(
        ats="icims",
        kind="ats",
        url_regex=r"careers-(?P<company>[a-z0-9-]+)\.icims\.com/jobs/(?P<external_id>\d+)(?:/(?P<role>[^/?#]+))?",
        priority=10,
    ),
    PatternSpec(
        ats="eightfold",
        kind="ats",
        url_regex=r"(?P<company>[a-z0-9-]+)\.eightfold\.ai/careers(?:/job/|\?(?:[^#]*&)?pid=)(?P<external_id>\d{6,})",
        title_regex=r"Careers at (?P<company>[^|]+?)\s*(?:\||$)",
        priority=10,
    ),
    # Eightfold also runs on company domains, e.g. jobs.nvidia.com/careers?pid=...
    PatternSpec(
        ats="eightfold",
        kind="ats",
        url_regex=r"/careers(?:/job/|\?(?:[^#]*&)?pid=)(?P<external_id>\d{6,})",
        title_regex=r"Careers at (?P<company>[^|]+?)\s*(?:\||$)",
        priority=60,
    ),
    # Aggregators and job boards.
    PatternSpec(
        ats="linkedin",
        kind="aggregator",
        url_regex=r"linkedin\.com/jobs/view/(?:[^/?#]*-)?(?P<external_id>\d{6,})",
        title_regex=r"^(?:\(\d+\)\s*)?(?P<company>.+?) hiring (?P<role>.+?) in ",
        priority=50,
    ),
    PatternSpec(
        ats="linkedin",
        kind="aggregator",
        url_regex=r"linkedin\.com/jobs/[^?#]*\?(?:[^#]*&)?currentJobId=(?P<external_id>\d{6,})",
        priority=51,
    ),
    PatternSpec(
        ats="shine",
        kind="job_board",
        url_regex=r"shine\.com/jobs/(?P<role>[^/?#]+)/(?P<company>[^/?#]+)/(?P<external_id>\d+)",
        priority=50,
    ),
    PatternSpec(
        ats="naukri",
        kind="job_board",
        url_regex=r"naukri\.com/job-listings-[^?#]*?-(?P<external_id>\d{9,})",
        title_regex=r"^(?P<role>.+?) - (?P<company>.+?) - ",
        priority=50,
    ),
    PatternSpec(
        ats="indeed",
        kind="aggregator",
        url_regex=r"indeed\.[a-z.]+/(?:m/)?(?:viewjob|rc/clk|pagead/clk)[^#]*[?&]jk=(?P<external_id>[0-9a-f]+)",
        title_regex=r"^(?P<role>.+?) - (?P<company>.+?) - .*Indeed",
        priority=50,
    ),
    PatternSpec(
        ats="glassdoor",
        kind="aggregator",
        url_regex=r"glassdoor\.[a-z.]+/job-listing/[^#]*[?&]jl=(?P<external_id>\d+)",
        priority=50,
    ),
    PatternSpec(
        ats="wellfound",
        kind="aggregator",
        url_regex=r"wellfound\.com/jobs/(?P<external_id>\d+)(?:-(?P<role>[^/?#]+))?",
        priority=50,
    ),
    # Generic confirmation shapes, matched only when nothing more specific did.
    PatternSpec(
        ats="generic",
        kind="confirmation",
        url_regex=r"/(?:thank-?you|thanks|application-?(?:submitted|received|complete))(?:[/?#]|$)",
        priority=200,
    ),
    PatternSpec(
        ats="generic",
        kind="confirmation",
        url_regex=r"[?&](?:submitted|applied|application_submitted)=(?:true|1)\b",
        priority=200,
    ),
)
