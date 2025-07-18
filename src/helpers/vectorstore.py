from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid, os

from src.config.env import QDRANT_URL, COLL

client = AsyncQdrantClient(url=QDRANT_URL)
model = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1")

async def ensure_collection():
    collections_resp = await client.get_collections()
    cols = [c.name for c in collections_resp.collections]
    if COLL not in cols:
        await client.recreate_collection(
            collection_name=COLL,
            vectors_config=VectorParams(size=model.get_sentence_embedding_dimension(),
                                       distance=Distance.COSINE),
        )

async def index_chunks(chunks):
    vecs = model.encode([c["text"] for c in chunks])
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=v.tolist(),
            payload={"url": c["url"], "title": c["title"], "text": c["text"]}
        )
        for c, v in zip(chunks, vecs)
    ]
    await client.upsert(collection_name=COLL, points=points)

async def retrieve(query: str, top_k: int = 4):
    qv = model.encode([query])[0]
    hits = await client.search(collection_name=COLL, query_vector=qv.tolist(), limit=top_k)
    return hits
