"""
POST /departments - create a department
GET /departments - list all departments
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from security import verify_api_key
import models, schemas, neo4j_client

router = APIRouter(prefix="/departments", tags=["Departments"], dependencies=[Depends(verify_api_key)])

@router.post("", response_model=schemas.DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(department: schemas.DepartmentCreate, db:Session=Depends(get_db)):
    new_department = models.Department(**department.model_dump())
    db.add(new_department)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A department named '{department.name}' already exists."
        ) 
    db.refresh(new_department)

    try:
        neo4j_client.create_department_node(
            department_id=new_department.id,
            name=new_department.name
        )   
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Department was saved but failed to sync to the graph database: {e}"
        )

    return new_department

@router.get("", response_model=list[schemas.DepartmentResponse])
def list_departments(db:Session = Depends(get_db)):
    return db.query(models.Department).order_by(models.Department.name).all()

