"""Explicitly synthetic demo data, never loaded into a user's database implicitly."""

from firstlook.embed import index
from firstlook.ingest import ingest
from firstlook.match import Profile, save_profile
from firstlook.models import Company, RawPosting
from firstlook.registry import upsert

NAMES = [
    "Northstar AI",
    "Orbital Labs",
    "Arc Health",
    "Fieldwork",
    "Meridian",
    "Gradient",
    "Canopy",
    "Vector Robotics",
    "Forma",
    "Atlas Systems",
    "Common Ground",
    "Relay Labs",
]
TITLES = [
    "Senior Software Engineer",
    "Senior Backend Engineer",
    "Software Engineer, Infrastructure",
    "Full Stack Engineer",
    "Staff Platform Engineer",
    "Machine Learning Engineer",
    "Senior Frontend Engineer",
    "Data Engineer",
]


def populate(db, count=48):
    save_profile(
        db,
        Profile(
            titles=["Software Engineer", "Backend Engineer"],
            locations=["United States", "San Francisco", "New York"],
            must_skills=["Python", "SQL", "AWS"],
            nice_skills=["Docker", "TypeScript"],
            remote="any",
        ),
    )
    for i in range(count):
        name = NAMES[i % len(NAMES)]
        company = Company(
            id=f"demo-{i % len(NAMES)}",
            name=name,
            domain="example.test",
            platform=["greenhouse", "lever", "ashby"][i % 3],  # type: ignore[arg-type]
            token="synthetic",
            tags=[["AI", "startup"], ["SaaS", "B2B"], ["health tech"], ["enterprise"]][i % 4],
            size=["11–50", "51–200", "201–1000"][i % 3],
            notes="Synthetic demonstration company",
        )
        upsert(db, company)
        descriptions = [
            "Build the infrastructure that helps small teams do their best work. Required Python, SQL and AWS. Docker is a plus. Remote within United States. 5+ years of experience. Salary $160,000 - $210,000 per year. Visa sponsorship available.",
            "Own reliable product experiences from idea to release. Required TypeScript, React and SQL. Python is a plus. Hybrid in San Francisco. 4+ years of experience. Salary $145,000 - $195,000 per year.",
            "Work with a thoughtful team on the next generation of data products. Required Python, AWS and Docker. 3+ years of experience. Remote within United States. Salary $150,000 - $220,000 per year.",
            "Develop reliable systems at meaningful scale. Required Rust and Kubernetes. SQL is a plus. Onsite in New York. 6+ years of experience. Salary $180,000 - $240,000 per year.",
        ]
        # Ingest all known roles for each company so demo creation is not a removal crawl.
        current = []
        for j in range(i % len(NAMES), i + 1, len(NAMES)):
            current.append(
                RawPosting(
                    external_id=f"fixture-{j}",
                    title=TITLES[j % len(TITLES)],
                    apply_url=f"https://example.test/apply/{j}",
                    locations=[
                        [
                            "Remote, United States",
                            "San Francisco",
                            "Remote, United States",
                            "New York",
                        ][j % 4]
                    ],
                    remote=j % 4 in (0, 2),
                    department="Engineering",
                    employment_type="Full-time",
                    description=descriptions[j % 4] + f" Product team {j}.",
                    posted_at="2026-10-12T09:00:00Z",
                )
            )
        ingest(db, company, current)
    return index(db)
