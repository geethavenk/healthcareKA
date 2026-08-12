"""
POST /search - semantci search over uploaded document chunks using pgvector.

Rate limited to 10 requests per minute
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from security import verify_api_key, limiter
from config import settings
import schemas

from services.embeddings import get_embedding
from services.graph_rag import vector_search

router = APIRouter(prefix="/search", tags=["Search"], dependencies=[Depends(verify_api_key)])

@router.post("", response_model=schemas.SearchResponse)
@limiter.limit(settings.rate_limit_search)
def search_documents(
    request: Request,
    search_request: schemas.SearchRequest,
    db: Session=Depends(get_db)
):
    query_embedding = get_embedding(search_request.query)
    results = vector_search(db, query_embedding, top_k=search_request.top_k)

    return schemas.SearchResponse(
        query=search_request.query,
        results=results
    )