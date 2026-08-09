"""
Turns raw uploaded text/PDF content into a list of text chunks
and turns text into embedding vectors via OpenAI
"""

import io
from openai import OpenAI
from pypdf import PdfReader
from config import settings

_client = OpenAI | None = None

def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


# Text extraction

def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extracts plain text from an uploaded file. Supports .txt and .pdf. 
    Raises ValueError for unsupported file types.
    """

    lower_name = filename.lower()

    if lower_name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        pages_txt = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages_txt).strip()

    if lower_name.endswith(".txt") or lower_name.endswith(".md"):
        return file_bytes.decode("utf-8", errors="ignore").strip()

    raise ValueError(f"Unsupported file type for: {filename}. Use .pdf, .txt or .md")

# chunking

def chunk_text(text:str, chunk_size:int = 200, overlap: int=40) -> list[str]:
    """
    Splits text into overlapping word-based chunks
    """

    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    step = max(chunk_size - overlap, 1)

    while start < len(words):
        chunk_words = words[start:start+chunk_size]
        chunks.append(" ".join(chunk_words))
        start += step
    return chunks

# Embeddings
def get_embedding(text:str) -> list[float]:
    client = get_openai_client()
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=text
    )  

    return response.data[0].embedding 

def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    client = get_openai_client() 
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )

    return [item.embedding for item in response.data]
