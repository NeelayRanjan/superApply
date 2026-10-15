import json
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

from selectolax.parser import HTMLParser

from firstlook.adapters import Base, plain
from firstlook.models import Company, RawPosting
from firstlook.registry import allowed_url


class Adapter(Base):
    def fetch(self, company: Company) -> list[RawPosting] | None:
        url = allowed_url(company.token)
        robots_url = urljoin(url, "/robots.txt")
        response = self.client.get(robots_url)
        if response.status_code == 304:
            response = self.client.cached_response(response.request.url)
        if response.status_code not in (200, 404):
            raise ValueError("Cannot establish robots permission")
        robots = RobotFileParser()
        robots.parse(response.text.splitlines() if response.status_code == 200 else [])
        if response.status_code == 200 and not robots.can_fetch("firstlook", url):
            raise ValueError("robots.txt disallows this page")
        response = self.client.get(url)
        if response.status_code == 304:
            return None
        response.raise_for_status()
        return self.parse(response.text)

    def parse(self, data) -> list[RawPosting]:
        result = []
        scripts = HTMLParser(data).css('script[type="application/ld+json"]')
        if not scripts:
            raise ValueError("No JSON-LD markup; board cannot be treated as empty")
        for script in scripts:
            payload = json.loads(script.text())
            nodes = payload if isinstance(payload, list) else payload.get("@graph", [payload])
            for j in nodes:
                if j.get("@type") != "JobPosting":
                    continue
                locations = j.get("jobLocation", [])
                if isinstance(locations, dict):
                    locations = [locations]
                identifier = j.get("identifier", j["url"])
                result.append(
                    RawPosting(
                        external_id=str(
                            identifier.get("value", j["url"])
                            if isinstance(identifier, dict)
                            else identifier
                        ),
                        title=j["title"],
                        apply_url=j["url"],
                        locations=[
                            ", ".join(
                                str(v)
                                for v in x.get("address", {}).values()
                                if isinstance(v, str) and v != "PostalAddress"
                            )
                            for x in locations
                        ],
                        remote=j.get("jobLocationType") == "TELECOMMUTE",
                        department=j.get("occupationalCategory", ""),
                        employment_type=j.get("employmentType", ""),
                        posted_at=j.get("datePosted"),
                        description_html=j.get("description", ""),
                        description=plain(j.get("description", "")),
                        compensation=j.get("baseSalary", {}),
                    )
                )
        return result
