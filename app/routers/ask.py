"""
POST /ask - the Graph RAG endpoint. Combines vector search (pgvector) with 
graph traversal (Neo4j) to anser general health information questions.

NEVER provides a medical diagnosis.
Rate limited to 5 requests per minute
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from security import verify_api_key, limiter
from config import settings

import models, schemas
from services.graph_rag import answer_question

router = APIRouter(prefix="/ask", tags=["Ask"], dependencies=[Depends(verify_api_key)])


@router.post("", response_model=schemas.AskResponse)
@limiter.limit(settings.rate_limit_ask)
def ask(
    request: Request,
    ask_request: schemas.AskRequest, 
    db: Session = Depends(get_db)
):
    # Run the full Graph RAG pipelin
    try:
        result = answer_question(db, ask_request.question, top_k=ask_request.top_k)
    except Exception as e:
        raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Unable to generate an answer right now: {e}",
        )

    #  Log the question and answer to Postgres
    question_record = models.Question(
        question_text=result["question"],
        answer_text=result["answer"]
    )

    db.add(question_record)
    db.commit()

    # Return the full response
    return schemas.AskResponse(
        question=result["question"],
        answer=result["answer"],
        sources=result["sources"],
        related_entities=result["related_entities"]
    )
