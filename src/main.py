from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from contextlib import asynccontextmanager

from src.api.v1.web_search import router as web_search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: No vector database initialization needed
    yield
    # Shutdown: Add any cleanup logic here if needed


app = FastAPI(
    title="Web Search Tool API", 
    version="0.1.0",
    description="API para ferramentas de busca web e agentes inteligentes",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.include_router(web_search_router) 

# Serve arquivos estáticos da documentação
if os.path.exists("docs"):
    app.mount("/docs-static", StaticFiles(directory="docs"), name="docs-static")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/swagger.json")
async def get_swagger_json():
    """Endpoint para acessar diretamente o JSON do Swagger"""
    swagger_path = "docs/swagger/swagger.json"
    if os.path.exists(swagger_path):
        return FileResponse(swagger_path, media_type="application/json")
    return {"error": "Documentação Swagger não encontrada"}