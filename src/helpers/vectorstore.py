from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, Range
from google import genai
import uuid, time
from loguru import logger

from src.config.env import QDRANT_URL, COLL, GEMINI_API_KEY

client = AsyncQdrantClient(url=QDRANT_URL)

# Initialize Gemini client for embeddings
logger.info("Initializing Gemini client for embeddings...")
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("Gemini client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Gemini client: {e}")
    raise

# Embedding model configuration
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 768  # text-embedding-004 dimension

async def encode_texts_async(texts: list[str]):
    """Generate embeddings using Gemini API"""
    logger.debug(f"Starting Gemini embedding generation for {len(texts)} texts")
    try:
        # Use Gemini embedding API
        response = await gemini_client.aio.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texts
        )
        
        # Extract embeddings from response
        logger.debug(f"Response structure: {type(response.embeddings[0])}")
        logger.debug(f"Available attributes: {dir(response.embeddings[0])}")
        
        # Try different attribute names
        if hasattr(response.embeddings[0], 'values'):
            embeddings = [item.values for item in response.embeddings]
        elif hasattr(response.embeddings[0], 'vector'):
            embeddings = [item.vector for item in response.embeddings]
        else:
            # Print first item for debugging
            logger.error(f"First embedding item: {response.embeddings[0]}")
            raise Exception("Cannot find embedding attribute")
            
        logger.debug(f"Successfully generated {len(embeddings)} embeddings via Gemini")
        return embeddings
        
    except Exception as e:
        logger.error(f"Error generating embeddings via Gemini: {e}")
        raise

async def encode_text_async(text: str):
    """Generate single text embedding using Gemini API"""
    logger.debug("Starting Gemini embedding generation for single text")
    try:
        # Use Gemini embedding API for single text
        response = await gemini_client.aio.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[text]
        )
        
        embedding = response.embeddings[0].values
        logger.debug("Successfully generated single embedding via Gemini")
        return embedding
        
    except Exception as e:
        logger.error(f"Error generating single embedding via Gemini: {e}")
        raise

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
                vectors_config=VectorParams(size=EMBEDDING_DIMENSION,
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
        logger.debug("Encoding chunks with Gemini embeddings")
        texts = [c["text"] for c in chunks]
        vecs = await encode_texts_async(texts)
        logger.debug(f"Generated {len(vecs)} embeddings")
        
        current_timestamp = int(time.time())
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=v,  # Gemini embeddings are already lists
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
        logger.debug("Encoding query for vector search with Gemini")
        qv = await encode_text_async(query)
        
        flt = Filter(must=[FieldCondition(key="query_id", match=MatchValue(value=query_id))])
        logger.debug(f"Searching in collection '{COLL}' with filter")
        
        hits = await client.search(
            collection_name=COLL,
            query_vector=qv,  # Gemini embeddings are already lists
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


async def delete_all_collections():
    """Delete all collections from Qdrant on application startup."""
    logger.info("Starting deletion of all Qdrant collections on startup")
    
    try:
        collections_resp = await client.get_collections()
        collection_names = [c.name for c in collections_resp.collections]
        
        if not collection_names:
            logger.info("No collections found to delete")
            return
            
        logger.info(f"Found {len(collection_names)} collections to delete: {collection_names}")
        
        for collection_name in collection_names:
            try:
                await client.delete_collection(collection_name=collection_name)
                logger.info(f"Successfully deleted collection '{collection_name}'")
            except Exception as e:
                logger.error(f"Error deleting collection '{collection_name}': {e}")
                
        logger.info("Finished deleting all collections")
        
    except Exception as e:
        logger.error(f"Error during collection deletion process: {e}")
        raise
