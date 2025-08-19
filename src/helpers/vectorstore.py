from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
import uuid, os
from loguru import logger

from src.config.env import QDRANT_URL, COLL

client = AsyncQdrantClient(url=QDRANT_URL)
model = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1")

async def ensure_collection():
    logger.info(f"Ensuring collection '{COLL}' exists in Qdrant at {QDRANT_URL}")
    try:
        collections_resp = await client.get_collections()
        cols = [c.name for c in collections_resp.collections]
        logger.info(f"Existing collections: {cols}")
        
        if COLL not in cols:
            logger.info(f"Creating new collection '{COLL}'")
            await client.recreate_collection(
                collection_name=COLL,
                vectors_config=VectorParams(size=model.get_sentence_embedding_dimension(),
                                           distance=Distance.COSINE),
            )
            logger.info(f"Collection '{COLL}' created successfully")
        else:
            logger.info(f"Collection '{COLL}' already exists")
            
    except Exception as e:
        logger.error(f"Error ensuring collection: {e}")
        raise

async def index_chunks(chunks, query_id: str):
    """Indexa *chunks* vinculando-os ao *query_id* para permitir filtragem posterior."""
    logger.info(f"Indexing {len(chunks)} chunks for query_id: {query_id}")
    
    if not chunks:
        logger.warning("No chunks to index")
        return

    try:
        logger.debug("Encoding chunks with sentence transformer")
        vecs = model.encode([c["text"] for c in chunks])
        logger.debug(f"Generated {len(vecs)} embeddings")
        
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=v.tolist(),
                payload={
                    "url": c["url"],
                    "title": c["title"],
                    "text": c["text"],
                    "query_id": query_id,
                },
            )
            for c, v in zip(chunks, vecs)
        ]
        
        logger.debug(f"Created {len(points)} points for indexing")
        await client.upsert(collection_name=COLL, points=points)
        logger.info(f"Successfully indexed {len(points)} chunks")
        
    except Exception as e:
        logger.error(f"Error indexing chunks: {e}")
        raise

async def retrieve(query: str, query_id: str, top_k: int = 8):
    """Recupera *top_k* chunks filtrando pela mesma consulta."""
    logger.info(f"Retrieving top {top_k} chunks for query: '{query}', query_id: {query_id}")
    
    try:
        logger.debug("Encoding query for vector search")
        qv = model.encode([query])[0]
        
        flt = Filter(must=[FieldCondition(key="query_id", match=MatchValue(value=query_id))])
        logger.debug(f"Searching in collection '{COLL}' with filter")
        
        hits = await client.search(
            collection_name=COLL,
            query_vector=qv.tolist(),
            limit=top_k,
            query_filter=flt,
        )
        
        logger.info(f"Retrieved {len(hits)} chunks from vector search")
        for i, hit in enumerate(hits):
            logger.debug(f"Hit {i+1}: score={hit.score:.4f}, url={hit.payload.get('url', 'N/A')}")
            
        return hits
        
    except Exception as e:
        logger.error(f"Error retrieving chunks: {e}")
        raise
