from firstlook.adapters import Base, plain
from firstlook.models import Company, RawPosting
from firstlook.registry import board_url


class Adapter(Base):
    def fetch(self, company: Company) -> list[RawPosting] | None:
        result = []
        offset = 0
        while True:
            response = self.client.get(board_url(company) + f"?limit=100&offset={offset}")
            if response.status_code == 304:
                if offset == 0:
                    return None
                response = self.client.cached_response(response.request.url)
            response.raise_for_status()
            data = response.json()
            for item in data["content"]:
                if "jobAd" not in item:
                    detail = self.client.get(board_url(company) + "/" + str(item["id"]))
                    if detail.status_code == 304:
                        detail = self.client.cached_response(detail.request.url)
                    detail.raise_for_status()
                    item.update(detail.json())
            result.extend(self.parse(data))
            offset += len(data["content"])
            if offset >= data.get("totalFound", offset) or not data["content"]:
                return result

    def parse(self, data) -> list[RawPosting]:
        result = []
        for j in data["content"]:
            loc = j.get("location", {})
            body = " ".join(
                s.get("text", "") for s in j.get("jobAd", {}).get("sections", {}).values()
            )
            result.append(
                RawPosting(
                    external_id=str(j["id"]),
                    title=j["name"],
                    apply_url=j.get("applyUrl")
                    or f"https://jobs.smartrecruiters.com/{j.get('company', {}).get('identifier', 'company')}/{j['id']}",
                    locations=[
                        ", ".join(str(loc[k]) for k in ("city", "region", "country") if loc.get(k))
                    ],
                    remote=loc.get("remote", False),
                    department=j.get("department", {}).get("label", ""),
                    employment_type=j.get("typeOfEmployment", {}).get("label", ""),
                    posted_at=j.get("releasedDate"),
                    description_html=body,
                    description=plain(body),
                    compensation=j.get("compensation", {}),
                )
            )
        return result
