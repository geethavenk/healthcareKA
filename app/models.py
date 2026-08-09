"""
SQLAlchemy ORM models - defines every table in PostgreSQL.

Stores Users, Documents, Metadata, Questions, API request logs, and the domain entities
(Doctor, Patient, Department, Appointment) and the vector embeddings for document chunks.
"""

from datetime import datetime

from sqlalchemy import (
    Column, 
    Integer,
    String,
    Text,
    Boolean,
    DateTime, 
    ForeignKey,
)

from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from database import Base

# text-embedding-3-small produces 1536 dimensional vectors.
EMBEDDING_DIM = 1536

class User(Base):
    """
    Represents anyone using the system (a simple identity to attach questions/requests
    to - not a full auth system, since actual API acess control is handles by the API key, 
    not user login).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("Question", back_populates="user")


class Department(Base):
    """A hospital department, e.g. Cardiology, Dermatology."""

    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    doctors = relationship("Doctor", back_populates="department")


class Doctor(Base):
    """A doctor, linked to a department."""
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    available = Column(Boolean, default=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctors")


class Patient(Base):
    """A patient who can book appointments."""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="patient")


class Appointment(Base):
    """A booking linking a patient to a doctor at a given time""" 
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients_id"), nallable=False)
    doctor_id = Column(Integer, ForeignKey("doctors_id"), nallable=False)
    appointment_date = Column(DateTime, nullable=False)
    reason = Column(String, nullable=True)
    status = Column(String, default="scheduled") # scheduled | completed | cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")


class Document(Base):
    """
    A general health-information document uploaded to the system. The full text is 
    not stored here -  its split into chunks for embedding and retrieval.
    This just hold the document-level metadata.
    """    

    __table__name = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    source_type = Column(String, default="general_health_info")
    uploaded_by = Column(String, nullable=True)
    doc_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """
    A chunk of a document's text, along with its embedding vector.
    This is our vector store, implemented via pgvector inside Postgres rather than a 
    separate vector database service.
    """

    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")


class Question(Base):
    """
    Every question asked along with generated answer.
    Let us show history and audit what the assistant told users.
    """   
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="questions")

class RequestLog(Base):
    """
    Logs every API request for observability"""

    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    client_ip = Column(String, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

        




