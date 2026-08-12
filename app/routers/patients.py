"""
POST /patients - create a patient
GET /patients - list patients (needed so the frontend can pick an existing patient when
booking an appointment)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from security import verify_api_key
import models, schemas, neo4j_client

router = APIRouter(prefix="/patients", tags=["Patients"], dependencies=[Depends(verify_api_key)])

@router.post("", response_model=schemas.PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(patient:schemas.PatientCreate, db:Session=Depends(get_db)):
    # Write to Postgres
    new_patient=models.Patient(**patient.model_dump())
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    # Mirror into Neo4j
    try:
        neo4j_client.create_patient_node(
            patient_id=new_patient.id,
            name=new_patient.name
        )
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Patient was saved but failed to sync to the graph database: {e}"
        )
    return new_patient

@router.get("", response_model=list[schemas.PatientResponse])
def list_patients(db:Session = Depends(get_db)):
    return db.query(models.Patient).order_by(models.Patient.name).all()