"""
Graph RAG orchestration.

1. Embed the users question
2. Vector search: find the most relevant document chunks
3. Graph search: extract keywords from the user question and traverse Neo4j for realtd entities
4. Combine both as context
5. Ask the LLM to generate a grounded answer using the context
6. Return the anser + sources + related entities (never a diagnosis)
"""

import re 
from sqlalchemy.orm import Session
from sqlalchemy import select

from config import settings
from models import DocumentChunk, Document
from services.embeddings import get_embedding, get_openai_client
import neo4j_client

# A minimal stopword list, just enough to filter out noise words when
# pulling "meaningful" keywords out of a question for the graph search.
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "which", "what", "who",
    "does", "do", "did", "for", "of", "to", "in", "on", "and", "or", "with",
    "about", "general", "generally", "problems", "problem", "please", "can",
    "you", "tell", "me", "handles", "handle", "department", "doctor",
    "available", "consultation", "documents", "related",
}

def extract_keywords(question:str) -> list[str]:
    """
    Lightweight keyword extraction: lowercase, strip punctuation,
    split into words, drop stopwords and very short words.
    """

    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ",question.lower())
    words = cleaned.split()
    keywords = [w for w in words if w not in _STOPWORDS and len(w)>2 ]
    return keywords

def vector_search(db: Session, query_embedding: list[float], top_k:int=5) -> list[dict]:
    """
    Finds the top_k most similar document chunks to the given embedding, using
    pgvector's cosine distance operator.
    """

    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    stmt = (
        select(DocumentChunk, Document.title, distance.label("distance"))
        .join(Document, DocumentChunk.document_id == Document.id)
        .order_by(distance)
        .limit(top_k)
    )

    rows = db.execute(stmt).all()

    results = []
    for chunk, doc_title, dist in rows:
        results.append({
            "document_id": chunk.document_id,
            "document_title": doc_title,
            "chunk_text": chunk.chunk_text,
            "similarity_score": round(1-dist,4),
        })
    return results


def graph_search(question:str) -> list[dict]:
    """
    Extract keywords from the question and traverse Neo4j for relaed entities.
    """
    keywords = extract_keywords(question)
    return neo4j_client.get_related_entities(keywords)


def build_context_text(chunks: list[dict], related_entities: list[dict]) -> str:
    """Formats vector + graph results into a single text block for the LLM prompt."""
    parts = []

    if chunks:
        parts.append("Relevant document excerpts:")
        for i, c in enumerate(chunks, start=1):
            parts.append(f"[{i}] (from \"{c['document_title']}\"): {c['chunk_text']}")

    if related_entities:
        parts.append("\nRelevant graph relationships:")
        for e in related_entities:
            if e.get("relationship") and e.get("related_to"):
                parts.append(f"- {e['type']} \"{e['name']}\" --{e['relationship']}--> \"{e['related_to']}\"")
            else:
                parts.append(f"- {e['type']} \"{e['name']}\"")

    return "\n".join(parts) if parts else "No relevant information was found in the knowledge base."


def generate_answer(question:str, context_text:str) -> str:
    """
    Calls the LLM to produce a final answer, grounded ONLY in the provided context.
    """

    client = get_openai_client()

    system_prompt = (
        "You are a healthcare information assistant. You ONLY provide general, educational" \
        "health information based on the CONTEXT provided below. You must NEVER provide a medical" \
        "diagnosis, prescribe treatment or tell a user what condition they have. If the context" \
        "does not contain enough information to answer, say so clearly instead of guessing." \
        "Always keep your tone informative and cautious, and defer to healthcare professionals" \
        "for anything diagnostic or urgent."
    )

    user_prompt = f"CONTEXT:\n{context_text}\n\nQUESTION:\n{question}"

    response = client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},

        ],
        temperature = 0.2,
    )
    return response.choices[0].message.content.strip()

def answer_question(db:Session, question:str, top_k:int=5) -> dict:
    """
    Ties together vector search, graph search and LLM generation
    """
    query_embedding = get_embedding(question)

    chunks = vector_search(db, query_embedding, top_k=top_k)
    related_entities = graph_search(question)

    context_text = build_context_text(chunks, related_entities)
    answer = generate_answer(question, context_text)

    return {
        "question": question,
        "answer": answer,
        "sources": chunks,
        "related_entities": related_entities
    }