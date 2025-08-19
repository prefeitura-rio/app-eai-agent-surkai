from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from time import perf_counter
from loguru import logger

from src.models.web_search_model import WebSearchRequest, WebSearchResponse, WebSearchContextResponse
from src.services.search_service import web_search, web_search_context
from src.helpers.vectorstore import cleanup_old_chunks, get_collection_stats

router = APIRouter(prefix="/api/v1", tags=["web_search"])

@router.post("/web_search", response_model=WebSearchResponse)
async def web_search_endpoint(req: WebSearchRequest):
    logger.info(f"API: Web search request received - query: '{req.query}', k: {req.k}, lang: {req.lang}")
    start_time = perf_counter()
    
    try:
        resp = await web_search(req)
        process_time = perf_counter() - start_time
        
        logger.info(f"API: Web search completed in {process_time:.4f}s - summary length: {len(resp.summary)}, sources: {len(resp.sources)}")
        
        return JSONResponse(
            content=resp.model_dump(mode="json"),
            headers={"X-Process-Time": f"{process_time:.4f}"}
        )
        
    except Exception as e:
        process_time = perf_counter() - start_time
        logger.error(f"API: Web search failed after {process_time:.4f}s - error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/web_search/context", response_model=WebSearchContextResponse)
async def web_search_context_endpoint(req: WebSearchRequest):
    start_time = perf_counter()
    try:
        resp = await web_search_context(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    process_time = perf_counter() - start_time
    return JSONResponse(
        content=resp.model_dump(mode="json"),
        headers={"X-Process-Time": f"{process_time:.4f}"},
    )


@router.get("/admin/collection-stats")
async def get_collection_statistics():
    """Get Qdrant collection statistics."""
    logger.info("API: Collection stats request received")
    try:
        stats = await get_collection_stats()
        if stats:
            return JSONResponse(content=stats)
        else:
            raise HTTPException(status_code=500, detail="Failed to get collection stats")
    except Exception as e:
        logger.error(f"API: Collection stats failed - error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/cleanup")
async def cleanup_collection(max_age_hours: int = 24):
    """Manually trigger cleanup of old chunks."""
    logger.info(f"API: Manual cleanup request received - max_age_hours: {max_age_hours}")
    try:
        await cleanup_old_chunks(max_age_hours=max_age_hours)
        stats = await get_collection_stats()
        return JSONResponse(content={
            "message": f"Cleanup completed for chunks older than {max_age_hours} hours",
            "collection_stats": stats
        })
    except Exception as e:
        logger.error(f"API: Manual cleanup failed - error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 