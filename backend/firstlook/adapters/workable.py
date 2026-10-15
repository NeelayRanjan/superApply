from firstlook.adapters import Base, plain
from firstlook.models import RawPosting


class Adapter(Base):
    def parse(self, data) -> list[RawPosting]:
        return [
            RawPosting(
                external_id=str(j["shortcode"]),
                title=j["title"],
                apply_url=j["url"],
                locations=[
                    ", ".join(str(j.get(k, "")) for k in ("city", "state", "country") if j.get(k))
                ],
                remote=j.get("telecommuting", False),
                department=j.get("department", ""),
                employment_type=j.get("employment_type", ""),
                posted_at=j.get("published_on"),
                description_html=j.get("description", ""),
                description=plain(j.get("description", "")),
                compensation=j.get("salary", {}),
            )
            for j in data["jobs"]
        ]
