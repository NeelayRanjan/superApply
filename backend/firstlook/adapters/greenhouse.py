from firstlook.adapters import Base, plain
from firstlook.models import RawPosting


class Adapter(Base):
    def parse(self, data) -> list[RawPosting]:
        result = []
        for j in data["jobs"]:
            body = j.get("content", "")
            location = j.get("location", {}).get("name", "")
            result.append(
                RawPosting(
                    external_id=str(j["id"]),
                    title=j["title"],
                    apply_url=j["absolute_url"],
                    locations=[location] if location else [],
                    remote="remote" in location.lower(),
                    department=", ".join(d["name"] for d in j.get("departments", [])),
                    employment_type=j.get("employment_type", ""),
                    posted_at=j.get("first_published"),
                    description_html=body,
                    description=plain(body),
                    compensation=j.get("pay_input_ranges", {})
                    if isinstance(j.get("pay_input_ranges", {}), dict)
                    else {"ranges": j["pay_input_ranges"]},
                )
            )
        return result
