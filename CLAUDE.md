# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SurKAI is a FastAPI-based web search and AI agent API that combines web search, content crawling, vector storage, and LLM summarization. The application provides intelligent web search capabilities with context-aware responses.

## Development Commands

### Running the Application
```bash
# Development server with hot reload
just dev
# Or directly with uv
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Documentation Generation
```bash
# Generate Swagger/OpenAPI documentation
python scripts/generate_swagger_docs.py
```

### Infrastructure
```bash
# Start all services (Redis, SearXNG, Crawl4AI, Qdrant)
docker-compose up -d

# Stop all services
docker-compose down
```

## Architecture

### Core Components

The application follows a layered architecture:

**API Layer** (`src/api/v1/`)
- `web_search.py`: Main API endpoints for web search functionality
- Two main endpoints:
  - `/api/v1/web_search`: Returns summarized search results
  - `/api/v1/web_search/context`: Returns structured context snippets

**Service Layer** (`src/services/`)
- `search_service.py`: Core orchestration logic combining search, crawling, and summarization
- `searx_client.py`: SearXNG search engine integration
- `crawl_client.py`: Crawl4AI markdown content extraction
- `llm_client.py`: Google Gemini API integration for summarization

**Data Processing** (`src/helpers/`)
- `chunk_breaker.py`: Text chunking for vector storage
- `vectorstore.py`: Qdrant vector database operations

**Models** (`src/models/`)
- `web_search_model.py`: Pydantic models for request/response validation

### Data Flow

1. **Search Phase**: Query sent to SearXNG to get initial web results
2. **Crawling Phase**: Parallel crawling of top URLs using Crawl4AI to extract markdown content
3. **Processing Phase**: Content chunked and indexed in Qdrant vector database
4. **Retrieval Phase**: Semantic search to find most relevant chunks
5. **Summarization Phase**: LLM generates summary with extracted sources

### External Dependencies

- **SearXNG**: Privacy-focused search engine aggregator (port 8080)
- **Crawl4AI**: Docker-deployed web crawling service
  - Official Crawl4AI Docker API format with BrowserConfig/CrawlerRunConfig
  - Uses BM25ExtractionStrategy for intelligent content ranking
  - Headless browser with cache bypass and skip internal links
  - Extracts top-k relevant content with word count filtering
  - Returns markdown with fallback to cleaned_html/extracted_content
- **Qdrant**: Vector database for semantic search (ports 6333/6334)
- **Redis/Valkey**: Caching layer for SearXNG

### Environment Configuration

Required environment variables (managed via `src/config/env.py`):
- `QDRANT_URL`: Qdrant vector database URL
- `COLL`: Qdrant collection name
- `CRAWL_URL`: Crawl4AI service URL
- `SEARX_URL`: SearXNG search URL
- `GEMINI_API_KEY`: Google Gemini API key
- `SECRET_KEY_SEARXNG`: SearXNG authentication key

### Key Design Patterns

- **Async/Await**: All I/O operations are asynchronous for performance
- **Error Resilience**: Crawling failures are handled gracefully with `return_exceptions=True`
- **Content Deduplication**: Text chunks are deduplicated using sets
- **Source Extraction**: LLM responses parsed to extract cited URLs
- **Vector Retrieval**: Semantic search used instead of keyword matching
- **Auto-Cleanup**: Automatic removal of old chunks (24h TTL) when collection grows large (>10k points)

### Performance Optimizations

#### High-Concurrency Ready
- **Thread Pool Execution**: SentenceTransformer embeddings run in dedicated thread pool (4 workers)
- **Concurrency Limits**: Max 5 concurrent crawling operations via semaphore
- **Connection Pooling**: Reusable HTTP clients with keepalive connections
- **Background Tasks**: Cleanup operations run as non-blocking background tasks

#### Timeouts & Resilience
- **SearX**: 15s total, 3s connect timeout
- **Crawl4AI**: 30s total, 5s connect timeout  
- **Connection Limits**: 100 max connections, 20 keepalive for Crawl4AI
- **Graceful Degradation**: Individual service failures don't crash entire pipeline

#### Memory & CPU Efficiency
- **Async Embeddings**: CPU-intensive encoding moved to thread pool
- **Non-blocking Cleanup**: Background cleanup doesn't block requests
- **Connection Reuse**: HTTP clients shared across requests

### Vector Store Management

- **Timestamp Tracking**: All chunks include timestamp for age-based cleanup
- **Query Isolation**: Each search gets unique `query_id` to avoid cross-contamination
- **Automatic Cleanup**: Triggers when collection exceeds 10,000 points
- **Manual Cleanup**: Admin endpoints for collection stats and manual cleanup

#### Admin Endpoints
- `GET /api/v1/admin/collection-stats` - Get Qdrant collection statistics
- `POST /api/v1/admin/cleanup?max_age_hours=24` - Manual cleanup trigger

## Deployment

The application supports both development and production deployments:

- **Development**: Local `justfile` commands with hot reload
- **Staging**: Kubernetes deployment in `k8s/staging/`
- **Production**: Kubernetes deployment in `k8s/prod/`

### CI/CD Performance Optimizations

#### Fast Container Builds (~3-5 minutes vs 11-13 minutes)
- **Multi-stage Dockerfile**: Separates build and production stages
- **Layer Caching**: Dependencies cached separately from source code  
- **Parallel Jobs**: Documentation generation runs parallel to Docker build
- **Optimized Actions**: Using official actions instead of manual setup
- **Minimal Context**: `.dockerignore` excludes unnecessary files

#### Build Strategies
- **Dependency Caching**: `pyproject.toml` + `uv.lock` cached independently
- **GHA Cache**: GitHub Actions cache for Docker layers
- **Security**: Non-root user in production container
- **Health Checks**: Built-in container health monitoring

#### Workflow Structure
```yaml
jobs:
  docs:     # Parallel - only on staging
  build:    # Main container build
```

API documentation is automatically generated and served at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- Static docs: `/docs-static/swagger/`