from fastapi import APIRouter
from fastapi.responses import Response

from firstlook.analytics import export_csv, report
from firstlook.db import connect

router = APIRouter()


@router.get("/api/analytics")
def analytics():
    with connect() as db:
        return report(db)


@router.get("/api/analytics/export/{table}")
def export(table: str):
    with connect() as db:
        return Response(
            export_csv(report(db), table),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="firstlook-{table}.csv"'},
        )
