"""
GET /health

"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from schemas import HealthResponse
import neo4j_client

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
def health_check(db:Session = Depends(get_db)):
    # --- Postgres check ----
    try:
        db.execute(text("SELECT 1"))
        postgres_status = "ok"
    except Exception:
        postgres_status = "unreachable"

    # --- Neo4j check ----
    neo4j_status = "ok" if neo4j_client.verify_connectivity() else "unreachable"

    overall_status = "ok" if postgres_status=="ok" and neo4j_status=="ok" else "degraded"

    return HealthResponse(
        status=overall_status,
        postgres=postgres_status,
        neo4j=neo4j_status
    )
