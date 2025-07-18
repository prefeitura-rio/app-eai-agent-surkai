from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from time import perf_counter

from src.models.web_search_model import WebSearchRequest, WebSearchResponse, WebSearchContextResponse
from src.services.search_service import web_search, web_search_context

router = APIRouter(prefix="/api/v1", tags=["web_search"])

@router.post("/web_search", response_model=WebSearchResponse)
async def web_search_endpoint(req: WebSearchRequest):
    start_time = perf_counter()
    try:
        resp = await web_search(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    process_time = perf_counter() - start_time
    return JSONResponse(content=resp.model_dump(mode="json"),
                        headers={"X-Process-Time": f"{process_time:.4f}"})

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