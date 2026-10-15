from firstlook.adapters import Base, plain
from firstlook.models import RawPosting


class Adapter(Base):
    def parse(self, data) -> list[RawPosting]:
        return [
            RawPosting(
                external_id=str(j["id"]),
                title=j["title"],
                apply_url=j["applyUrl"],
                locations=[j.get("location", "")]
                + [x["location"] for x in j.get("secondaryLocations", [])],
                remote=j.get("isRemote", False),
                department=j.get("department", ""),
                employment_type=j.get("employmentType", ""),
                posted_at=j.get("publishedAt"),
                description_html=j.get("descriptionHtml", ""),
                description=j.get("descriptionPlain") or plain(j.get("descriptionHtml", "")),
                compensation=j.get("compensation", {}),
            )
            for j in data["jobs"]
        ]
