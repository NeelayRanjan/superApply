from fastapi import APIRouter

from firstlook.apply import DRIVER, EXECUTOR
from firstlook.db import connect
from firstlook.track import applications, queue, transition

router = APIRouter()


@router.get("/api/applications")
def all_applications():
    with connect() as db:
        return applications(db)


@router.post("/api/applications")
def queue_application(data: dict):
    with connect() as db:
        return queue(db, int(data["job_id"]), data.get("variant_id"))


@router.put("/api/applications/{application_id}")
def update(application_id: int, data: dict):
    with connect() as db:
        return transition(
            db, application_id, data["state"], data.get("notes", ""), data.get("contacts", "")
        )


@router.get("/api/applications/{application_id}/receipt")
def receipt(application_id: int):
    with connect() as db:
        return {
            "fields": [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM application_field WHERE application_id=?", (application_id,)
                )
            ],
            "events": [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM application_event WHERE application_id=? ORDER BY id",
                    (application_id,),
                )
            ],
        }


@router.post("/api/applications/{application_id}/preview")
def preview(application_id: int, data: dict):
    def run():
        with connect() as db:
            return DRIVER.preview(db, application_id, data.get("answers", {}))

    return EXECUTOR.submit(run).result()


@router.post("/api/applications/confirm")
def confirm(data: dict):
    if data.get("confirmed") is not True:
        raise ValueError("Explicit confirmation is required")

    def run():
        with connect() as db:
            return (
                DRIVER.batch_confirm(db, data["tokens"], True)
                if "tokens" in data
                else DRIVER.confirm(db, data["token"], True)
            )

    return EXECUTOR.submit(run).result()
