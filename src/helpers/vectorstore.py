from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, Range
from sentence_transformers import SentenceTransformer
import uuid, os, time, asyncio
from concurrent.futures import ThreadPoolExecutor
from loguru import logger

from src.config.env import QDRANT_URL, COLL

client = AsyncQdrantClient(url=QDRANT_URL)

# Initialize model with logging
logger.info("Initializing SentenceTransformer model...")
try:
    model = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1")
    logger.info(f"Model loaded successfully. Embedding dimension: {model.get_sentence_embedding_dimension()}")
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer model: {e}")
    raise

# Thread pool for CPU-intensive embedding operations
embedding_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="embedding")

def _encode_texts_sync(texts: list[str]):
    """Synchronous encoding function to run in thread pool"""
    logger.debug(f"Starting synchronous encoding of {len(texts)} texts")
    try:
        result = model.encode(texts)
        logger.debug(f"Successfully encoded {len(texts)} texts, output shape: {result.shape}")
        return result
    except Exception as e:
        logger.error(f"Error in synchronous encoding: {e}")
        raise

def _encode_text_sync(text: str):
    """Synchronous encoding function for single text"""
    return model.encode([text])[0]

async def encode_texts_async(texts: list[str]):
    """Async wrapper for text encoding using thread pool"""
    loop = asyncio.get_event_loop()
    try:
        # Add timeout to prevent hanging
        return await asyncio.wait_for(
            loop.run_in_executor(embedding_executor, _encode_texts_sync, texts),
            timeout=120.0  # 2 minutes timeout
        )
    except asyncio.TimeoutError:
        logger.error("Embedding encoding timed out after 120 seconds")
        raise Exception("Embedding operation timed out - model may need to download or system is overloaded")

async def encode_text_async(text: str):
    """Async wrapper for single text encoding using thread pool"""
    loop = asyncio.get_event_loop()
    try:
        # Add timeout to prevent hanging
        return await asyncio.wait_for(
            loop.run_in_executor(embedding_executor, _encode_text_sync, text),
            timeout=60.0  # 1 minute timeout for single text
        )
    except asyncio.TimeoutError:
        logger.error("Single text embedding encoding timed out after 60 seconds")
        raise Exception("Embedding operation timed out - model may need to download or system is overloaded")

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
        logger.debug("Encoding chunks with sentence transformer (async)")
        texts = [c["text"] for c in chunks]
        vecs = await encode_texts_async(texts)
        logger.debug(f"Generated {len(vecs)} embeddings")
        
        current_timestamp = int(time.time())
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=v.tolist(),
                payload={
                    "url": c["url"],
                    "title": c["title"],
                    "text": c["text"],
                    "query_id": query_id,
                    "timestamp": current_timestamp,
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
        logger.debug("Encoding query for vector search (async)")
        qv = await encode_text_async(query)
        
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


async def cleanup_old_chunks(max_age_hours: int = 24):
    """Remove chunks older than max_age_hours from the collection."""
    logger.info(f"Starting cleanup of chunks older than {max_age_hours} hours")
    
    try:
        current_time = int(time.time())
        cutoff_time = current_time - (max_age_hours * 3600)
        
        # Delete points with timestamp older than cutoff
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="timestamp",
                    range=Range(lt=cutoff_time)
                )
            ]
        )
        
        result = await client.delete(
            collection_name=COLL,
            points_selector=filter_condition
        )
        
        logger.info(f"Cleanup completed. Operation status: {result.status}")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise


async def cleanup_query_chunks(query_id: str):
    """Remove chunks associated with a specific query_id."""
    logger.info(f"Cleaning up chunks for query_id: {query_id}")
    
    try:
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="query_id",
                    match=MatchValue(value=query_id)
                )
            ]
        )
        
        result = await client.delete(
            collection_name=COLL,
            points_selector=filter_condition
        )
        
        logger.info(f"Query cleanup completed for {query_id}. Status: {result.status}")
        
    except Exception as e:
        logger.error(f"Error cleaning up query {query_id}: {e}")
        raise


async def get_collection_stats():
    """Get statistics about the collection."""
    try:
        info = await client.get_collection(collection_name=COLL)
        logger.info(f"Collection stats - Points: {info.points_count}, Vectors: {info.vectors_count}")
        return {
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "status": info.status
        }
    except Exception as e:
        if "doesn't exist" in str(e):
            logger.info(f"Collection '{COLL}' doesn't exist yet")
            return {
                "points_count": 0,
                "vectors_count": 0,
                "status": "collection_not_exists"
            }
        else:
            logger.error(f"Error getting collection stats: {e}")
            return None
