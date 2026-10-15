from datetime import datetime, timezone

from firstlook.adapters import Base, plain
from firstlook.models import RawPosting


class Adapter(Base):
    def parse(self, data) -> list[RawPosting]:
        if not isinstance(data, list):
            raise ValueError("Lever expects an array")
        result = []
        for j in data:
            c = j.get("categories", {})
            body = (
                j.get("description", "")
                + "".join("<h3>" + x["text"] + "</h3>" + x["content"] for x in j.get("lists", []))
                + j.get("additional", "")
            )
            result.append(
                RawPosting(
                    external_id=str(j["id"]),
                    title=j["text"],
                    apply_url=j["applyUrl"],
                    locations=c.get("allLocations", [c.get("location", "")]),
                    remote=j.get("workplaceType") == "remote",
                    department=c.get("department", c.get("team", "")),
                    employment_type=c.get("commitment", ""),
                    posted_at=datetime.fromtimestamp(
                        j["createdAt"] / 1000, timezone.utc
                    ).isoformat()
                    if j.get("createdAt")
                    else None,
                    description_html=body,
                    description=plain(body),
                    compensation=j.get("salaryRange", {}),
                )
            )
        return result
