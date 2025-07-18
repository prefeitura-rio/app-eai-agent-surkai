from fastapi import FastAPI

from src.api.v1.web_search import router as web_search_router

app = FastAPI(title="Web Search Tool API", version="0.1.0")

app.include_router(web_search_router) 

@app.get("/")
async def root():
    return {"message": "Hello World"}