"""
POST /doctors - create a doctor (writes to Postgres AND mirrors to Neo4j)
GET /doctros - list doctors, optionally filtered by specialty or department
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from security import verify_api_key
import models, schemas, neo4j_client

router = APIRouter(prefix="/doctors", tags=["Doctors"], dependencies=[Depends(verify_api_key)])

@router.post("", response_model=schemas.DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(doctor:schemas.DoctorCreate, db:Session=Depends(get_db)):
    department = db.get(models.Department, doctor.department_id)
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department with id {doctor.department_id} not found."
        )
    # Write to Postgres
    new_doctor = models.Doctor(**doctor.model_dump())
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)

    # Mirror into Neo4j
    try:
        neo4j_client.create_doctor_node(
            doctor_id=new_doctor.id,
            name=new_doctor.name,
            specialty=new_doctor.specialty,
            department_id=new_doctor.department_id
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dcotr was saved but failed to sync to the graph database: {e}"
        )
    return new_doctor

@router.get("", response_model=list[schemas.DoctorResponse])
def list_doctors(
    specialty: str | None = None,
    department_id: int | None = None,
    db: Session = Depends(get_db)
):
    """
    List all doctors and supports optional filtering:
    GET /doctors?specailty=dermatology
    GET /doctors?department_id=3
    """

    query=db.query(models.Doctor)

    if specialty:
        query = query.filter(models.Doctor.specialty.ilike(f"%{specialty}%"))
    if department_id:
        query = query.filter(models.Doctor.department_id == department_id)

    return query.order_by(models.Doctor.name).all()
