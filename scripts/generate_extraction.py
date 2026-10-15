"""Labelled deterministic variations; expectations authored independently of extractor."""

import json
from pathlib import Path

rows = []
for title, seniority in [
    ("Intern Engineer", "intern"),
    ("Junior Developer", "junior"),
    ("Software Engineer", "mid"),
    ("Senior Engineer", "senior"),
    ("Staff Engineer", "lead"),
    ("Director of Engineering", "executive"),
]:
    for description, expected in [
        (
            "Required Python and SQL. 5+ years of experience. Salary $150,000 - $200,000 per year. Remote within United States. Visa sponsorship available.",
            {
                "skills": ["Python", "SQL"],
                "years": 5,
                "remote": "remote",
                "visa": "yes",
                "compensation": {
                    "min_cents": 15000000,
                    "max_cents": 20000000,
                    "currency": "USD",
                    "period": "year",
                },
            },
        ),
        (
            "K8s and AWS required. Rust is nice to have. Hybrid in Boston. No visa sponsorship.",
            {
                "skills": ["AWS", "Kubernetes"],
                "preferred_skills": ["Rust"],
                "remote": "hybrid",
                "visa": "no",
            },
        ),
        (
            "TypeScript and React. On-site in London. GBP 70k–90k per year. Bachelor degree required.",
            {
                "skills": ["React", "TypeScript"],
                "remote": "onsite",
                "compensation": {
                    "min_cents": 7000000,
                    "max_cents": 9000000,
                    "currency": "GBP",
                    "period": "year",
                },
            },
        ),
        (
            "C++ and Linux. Secret clearance required. $60 - $90 per hour.",
            {
                "skills": ["C++", "Linux"],
                "clearance": True,
                "compensation": {
                    "min_cents": 6000,
                    "max_cents": 9000,
                    "currency": "USD",
                    "period": "hour",
                },
            },
        ),
        (
            "Python is not required. Golang preferred. Fully remote. No security clearance required.",
            {
                "skills": [],
                "negated_skills": ["Python"],
                "preferred_skills": ["Go"],
                "clearance": False,
                "remote": "remote",
            },
        ),
        (
            "Machine learning and PyTorch. 3-5 years of experience. EUR 80k to 100k.",
            {
                "skills": ["Machine learning", "PyTorch"],
                "years": 3,
                "compensation": {
                    "min_cents": 8000000,
                    "max_cents": 10000000,
                    "currency": "EUR",
                    "period": "year",
                },
            },
        ),
        (
            "Figma and product design. Remote in Canada. CAD 100,000 - 140,000.",
            {
                "skills": ["Figma", "Product design"],
                "remote": "remote",
                "geography": "Canada",
                "compensation": {
                    "min_cents": 10000000,
                    "max_cents": 14000000,
                    "currency": "CAD",
                    "period": "year",
                },
            },
        ),
        (
            "SQL required. AWS optional. No remote work. Sponsorship unavailable.",
            {"skills": ["SQL"], "preferred_skills": ["AWS"], "remote": "onsite", "visa": "no"},
        ),
        (
            "Docker and Terraform. 10 years experience. Team of 500 employees.",
            {"skills": ["Docker", "Terraform"], "years": 10, "size_cue": "500 employees"},
        ),
        (
            "NLP, LLMs and statistics. PhD preferred. $8k - $12k per month.",
            {
                "skills": ["LLMs", "NLP", "Statistics"],
                "compensation": {
                    "min_cents": 800000,
                    "max_cents": 1200000,
                    "currency": "USD",
                    "period": "month",
                },
            },
        ),
    ]:
        rows.append(
            {
                "title": title,
                "description": description,
                "expected": dict(expected, seniority=seniority),
            }
        )
Path("fixtures/extraction.json").write_text(json.dumps(rows, indent=2))
