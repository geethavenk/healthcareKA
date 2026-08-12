"""
Pydantic schemas - which defines the shape of API requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100, examples=["Cardiology"])
    description: Optional[str] = Field(None, max_length=500) 


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:int
    name: str
    description: Optional[str] = None
    create_at: datetime


class DoctorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100, examples=["Dr. Jane Smith"])
    specialty: str = Field(min_length=2, max_length=100, examples=["Cardiology"])
    department_id: int = Field(gt=0)
    email: Optional[str] = None
    phone: Optional[str] = None
    available: bool = True 

class DoctorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    specialty: str
    department_id: int
    email: Optional[str] = None
    phone: Optional[str] = None
    available: bool
    created_at: datetime


class PatientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = None
    contact: Optional[str] = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    create_at: datetime


class AppointmentCreate(BaseModel):
    patient_id: int = Field(gt=0)
    doctor_id: int = Field(ge=0)
    appointment_date: datetime
    reason: Optional[str] = Field(None, max_length=500, examples=["Follow-up consultation"]) 


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int
    appointment_date: datetime
    reason: Optional[str] = None
    status: str
    created_at: datetime

# for listing documents that have been uploaded
class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_type: str
    uploaded_by: Optional[str] = None
    create_at: datetime

# Response right after upload - tells how many chunks were extracted and embedded
class DocumentUploadResponse(BaseModel):
    id: int
    title: str
    chunks_created: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_digits=500, examples=["symptoms of diabetes"])
    top_k: int = Field(5, ge=1, le=20)


class SearchResultItem(BaseModel):
    document_id: int
    document_title: str
    chunk_text: str
    similarity_score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500, examples=["Which doctor specializes in skin related issues?"])
    top_k: int = Field(5, ge=1, le=20)


class RelatedEntity(BaseModel):
    """A graph node returned from Neo4j as relevant context for the answer."""
    type: str
    name: str
    relationship: Optional[str] = None
    related_to: Optional[str] = None

class AskResponse(BaseModel):
    question: str
    answer: str
    disclaimer: str = (
        "This assistant provides general health information only and does not provide" \
        "medical diagnosis. Please consult a qualified healthcare professional for medical advice."
    )
    sources: list[SearchResultItem]
    related_entities: list[RelatedEntity]


class HealthResponse(BaseModel):
    status: str
    postgres: str
    neo4j: str
    

