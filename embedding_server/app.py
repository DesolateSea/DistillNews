"""
Standalone Embedding Microservice.

Provides a lightweight REST API for generating text embeddings using
Sentence Transformers without burdening the main backend container with PyTorch.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(title="DistillNews Embedding Microservice", version="1.0.0")

# Lazy-load SentenceTransformer model on startup
MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
_model = None

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model

class EmbedRequest(BaseModel):
    text: str

class EmbedManyRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    embedding: List[float]

class EmbedManyResponse(BaseModel):
    embeddings: List[List[float]]

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "loaded": _model is not None
    }

@app.post("/embed", response_model=EmbedResponse)
def embed(request: EmbedRequest):
    if not request.text or not request.text.strip():
        return {"embedding": []}
    try:
        model = get_model()
        vector = model.encode(request.text.strip(), convert_to_numpy=True, normalize_embeddings=True)
        return {"embedding": [float(v) for v in vector]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed_many", response_model=EmbedManyResponse)
def embed_many(request: EmbedManyRequest):
    if not request.texts:
        return {"embeddings": []}
    try:
        model = get_model()
        cleaned = [t.strip() or " " for t in request.texts]
        vectors = model.encode(cleaned, convert_to_numpy=True, normalize_embeddings=True)
        return {"embeddings": [[float(v) for v in vector] for vector in vectors]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8001)
