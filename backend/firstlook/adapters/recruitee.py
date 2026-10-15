from firstlook.adapters import Base, plain
from firstlook.models import RawPosting


class Adapter(Base):
    def parse(self, data) -> list[RawPosting]:
        return [
            RawPosting(
                external_id=str(j["id"]),
                title=j["title"],
                apply_url=j["careers_url"],
                locations=[j.get("location", "")],
                remote=j.get("remote", False),
                department=j.get("department", ""),
                employment_type=j.get("employment_type_code", ""),
                posted_at=j.get("published_at"),
                description_html=j.get("description", "") + j.get("requirements", ""),
                description=plain(j.get("description", "") + j.get("requirements", "")),
                compensation=j.get("salary", {}),
            )
            for j in data["offers"]
        ]
