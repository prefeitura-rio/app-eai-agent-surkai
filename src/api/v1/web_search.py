from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.models.web_search_model import WebSearchRequest, WebSearchResponse
from src.services.search_service import web_search

router = APIRouter(prefix="/api/v1", tags=["web_search"])

@router.post("/web_search", response_model=WebSearchResponse)
async def web_search_endpoint(req: WebSearchRequest):
    try:
        resp = await web_search(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse(content=resp.model_dump(mode="json")) 