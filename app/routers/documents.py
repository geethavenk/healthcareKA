"""
POST /documents - upload a health information document (.pdf, .txt, .md):
                    extract text -> chunk -> embed -> store in Postgres/pgvector

GET /documents - list uploaded documents

Rate limited to 20 requests/minute 
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session

from database import get_db
from security import verify_api_key, limiter
from config import settings
import models, schemas
from services.embeddings import extract_text, chunk_text, get_embeddings_batch

router = APIRouter(prefix="/documents", tags=["Documents"], dependencies=[Depends(verify_api_key)])

@router.post("", response_model=schemas.DepartmentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_documents)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    db: Session = Depends(get_db)
):
    # Read and extract text from the uploaded file
    file_bytes = await file.read()

    try:
        extracted_text = extract_text(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail=str(e))  

    if not extracted_text.strip():
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No extractable text found in the uploaded file")

    # Crete the parent document row
    new_document = models.Document(
        title=title or file.filename,
        source_type="general_health_info"
    ) 

    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    # Split into chunks and embed them all in one batch call
    chunks = chunk_text(extracted_text)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text was empty after processing."

        ) 

    embeddings = get_embeddings_batch(chunks)

    # Store each chunk and its embeddings
    for index, (chunk_str, embedding) in enumerate(zip(chunks, embeddings)):
        db.add(models.DocumentChunk(
            document_id=new_document.id,
            chunk_index=index,
            chunk_text=chunk_str,
            embedding=embedding

        ))
    db.commit()

    return schemas.DocumentUploadResponse(
        id=new_document.id,
        title=new_document.title,
        chunks_created=len(chunks)
    )

@router.get("", response_model=list[schemas.DepartmentResponse])
def list_documents(db:Session = Depends(get_db)):
    return db.query(models.Document).order_by(models.Document.created_at.desc()).all()