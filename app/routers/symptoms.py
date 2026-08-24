"""
POST /symptoms - link a symptom to the department that generally handles it
GET /symptoms - list every seeded symptom -> department link

Symptoms live only in the graph - there is no Postgres table for them, because what
matters is the relationship to a department, not any attribute of the symptom itself.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from security import verify_api_key
import models, schemas, neo4j_client

router = APIRouter(prefix="/symptoms", tags=["Symptoms"], dependencies=[Depends(verify_api_key)])


@router.post("", response_model=schemas.SymptomLinkResponse, status_code=status.HTTP_201_CREATED)
def link_symptom(link: schemas.SymptomLink, db: Session = Depends(get_db)):
    # Check Postgres first: link_symptom_to_department MATCHes the department, so a
    # missing one would silently write nothing. This also gives us the canonical
    # casing, so "dermatology" from the client still matches the "Dermatology" node.
    department = (
        db.query(models.Department)
        .filter(models.Department.name.ilike(link.department_name))
        .first()
    )
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department '{link.department_name}' not found. Create the department first."
        )

    try:
        neo4j_client.link_symptom_to_department(
            symptom_name=link.symptom.strip().lower(),
            department_name=department.name
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write the symptom link to the graph database: {e}"
        )

    return schemas.SymptomLinkResponse(symptom=link.symptom.strip().lower(), department=department.name)


@router.get("", response_model=list[schemas.SymptomLinkResponse])
def list_symptoms():
    return neo4j_client.get_symptom_links()
