"""
POST /appointments - book an appointment (writes to Postgres and mirrors to Neo4j)
GET /appointments - list appointments 
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from security import verify_api_key
import models, schemas, neo4j_client

router = APIRouter(prefix="/appointments", tags=["Appointments"], dependencies=[Depends(verify_api_key)])

@router.post("", response_model=schemas.AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(appointment:schemas.AppointmentCreate, db:Session=Depends(get_db)):
    # confirm both the patient and doctor actually exist before booking.
    patient = db.get(models.Patient, appointment.patient_id)
    if patient is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = f"Patient with id {appointment.patient_id} not found."
        )

    doctor = db.get(models.Doctor, appointment.doctor_id)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail = f"Doctor with id {appointment.doctor_id} not found."
        )

    # Write to Postgres
    new_appointment = models.Appointment(**appointment.model_dump())
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)

    # Mirror into Neo4j
    try:
        neo4j_client.create_appointment_node(
            appointment_id=new_appointment.id,
            patient_id=new_appointment.patient_id,
            doctor_id=new_appointment.doctor_id,
            appointment_date=new_appointment.appointment_date.isoformat()
        )
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Appointment was saved but failed to sync to the graph database: {e}"
        )
    return new_appointment

@router.get("", response_model=list[schemas.AppointmentResponse])
def list_appointments(
    doctor_id: int | None = None,
    patient_id: int | None = None,
    db:Session = Depends(get_db)
):
    """
    List appointments, supports optional filtering:
    GET /appointments?doctor_id=3
    GET /appointments?patient_id=7
    """
    query = db.query(models.Appointment)

    if doctor_id:
        query = query.filter(models.Appointment.doctor_id == doctor_id)
    if patient_id:
        query = query.filter(models.Appointment.patient_id == patient_id)

    return query.order_by(models.Appointment.appointment_date).all()
