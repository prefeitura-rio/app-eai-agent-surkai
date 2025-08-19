import re, asyncio, json, uuid
from typing import List
from loguru import logger

from src.models.web_search_model import WebSearchRequest, WebSearchResponse
from src.services.searx_client import searx_search
from src.services.crawl_client import crawl_markdown
from src.helpers.chunk_breaker import chunk_markdown
from src.helpers.vectorstore import ensure_collection, index_chunks, retrieve, cleanup_old_chunks, get_collection_stats
from src.services.llm_client import summarize

URL_REGEX = re.compile(r"^\*\s+(https?://\S+)")

# Semaphore to limit concurrent crawling operations
CRAWL_SEMAPHORE = asyncio.Semaphore(5)  # Max 5 concurrent crawls

async def limited_crawl_markdown(url: str):
    """Crawl with concurrency limit"""
    async with CRAWL_SEMAPHORE:
        return await crawl_markdown(url)


async def _background_cleanup_if_needed():
    """Background task to check and cleanup if needed"""
    try:
        stats = await get_collection_stats()
        if stats and stats.get("points_count", 0) > 10000:
            logger.info("Background cleanup: Large collection detected, starting cleanup")
            await cleanup_old_chunks(max_age_hours=24)
            logger.info("Background cleanup: Completed")
    except Exception as e:
        logger.error(f"Background cleanup failed: {e}")


async def _extract_sources(text: str, fallback: List[str] | None = None) -> tuple[str, List[str]]:
    """Extrai fontes (linhas iniciadas com * http) e devolve corpo limpo."""
    if text.lstrip().startswith("{"):
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "content" in data:
                text = str(data["content"])
        except json.JSONDecodeError:
            pass
    sources = []
    lines = []
    for line in text.splitlines():
        m = URL_REGEX.match(line.strip())
        if m:
            sources.append(m.group(1))
        else:
            lines.append(line)
    if not sources and fallback:
        sources = fallback[:4]
    seen = set()
    deduped = []
    for url in sources:
        if url not in seen:
            deduped.append(url)
            seen.add(url)
        if len(deduped) >= 8:
            break
    summary = "\n".join(lines).strip()
    return summary, deduped


async def web_search(request: WebSearchRequest) -> WebSearchResponse:
    logger.info(f"Starting web search for query: '{request.query}', k={request.k}, lang={request.lang}")
    
    try:
        results = await searx_search(request.query, k=request.k, lang=request.lang)
        logger.info(f"SearX returned {len(results)} results")
        
        if not results:
            logger.warning("No results from SearX search")
            return WebSearchResponse(summary="Não encontrei informação suficiente.", sources=[])

        top_urls = [r["url"] for r in results]
        top_titles = [r["title"] for r in results]
        logger.info(f"URLs to crawl: {top_urls}")
        
        crawled = await asyncio.gather(*(limited_crawl_markdown(u) for u in top_urls), return_exceptions=True)
        logger.info(f"Crawling completed. Results: {len(crawled)} items")

        markdown_docs = []
        for i, (url, res, title) in enumerate(zip(top_urls, crawled, top_titles)):
            if isinstance(res, Exception):
                logger.warning(f"Crawling failed for {url}: {res}")
                continue
            
            md = res.get("markdown") or res.get("content") or ""
            
            # Ensure md is a string
            if not isinstance(md, str):
                logger.warning(f"Content for {url} is not a string: {type(md)}, value: {md}")
                continue
                
            logger.debug(f"Content length for {url}: {len(md)} chars")
            
            if len(md.strip()) < 300:
                logger.warning(f"Content too short for {url}: {len(md.strip())} chars")
                continue
            markdown_docs.append({"url": url, "title": title, "markdown": md})

        logger.info(f"Valid markdown docs: {len(markdown_docs)}")
        if not markdown_docs:
            logger.error("No valid markdown documents after crawling")
            return WebSearchResponse(summary="Não encontrei informação suficiente.", sources=[])

        await ensure_collection()
        logger.info("Vector collection ensured")
        
        # Schedule background cleanup (non-blocking)
        asyncio.create_task(_background_cleanup_if_needed())
        
        query_id = str(uuid.uuid4())
        logger.info(f"Generated query ID: {query_id}")
        
        seen_texts: set[str] = set()
        all_chunks = []
        for doc in markdown_docs:
            try:
                chunks = await chunk_markdown(doc["markdown"])
                logger.debug(f"Generated {len(chunks)} chunks for {doc['url']}")
                for c in chunks:
                    txt = c.strip()
                    if len(txt) < 200 or txt in seen_texts:
                        continue
                    seen_texts.add(txt)
                    all_chunks.append({"url": doc["url"], "title": doc["title"], "text": txt})
            except Exception as e:
                logger.error(f"Error chunking content for {doc['url']}: {e}")

        logger.info(f"Total unique chunks: {len(all_chunks)}")
        
        if all_chunks:
            try:
                await index_chunks(all_chunks, query_id)
                logger.info(f"Indexed {len(all_chunks)} chunks")
            except Exception as e:
                logger.error(f"Error indexing chunks: {e}")
                return WebSearchResponse(summary="Erro ao indexar conteúdo.", sources=[])

        try:
            hits = await retrieve(request.query, query_id, top_k=8)
            logger.info(f"Retrieved {len(hits)} relevant chunks")
            
            if not hits:
                logger.warning("No relevant chunks found in vector search")
                return WebSearchResponse(summary="Não encontrei informação relevante.", sources=top_urls[:3])

            ctx_chunks = [h.payload["text"] for h in hits]
            context = "\n\n".join(ctx_chunks)
            logger.info(f"Context length: {len(context)} chars")

            raw_answer = await summarize(context, request.query, top_urls)
            logger.info(f"LLM response received, length: {len(raw_answer)} chars")

            summary, sources = await _extract_sources(raw_answer, fallback=top_urls)
            logger.info(f"Final summary length: {len(summary)}, sources: {len(sources)}")

            return WebSearchResponse(summary=summary, sources=sources)
            
        except Exception as e:
            logger.error(f"Error in retrieval or summarization: {e}")
            return WebSearchResponse(summary="Erro no processamento de informações.", sources=top_urls[:3])
            
    except Exception as e:
        logger.error(f"Unexpected error in web_search: {e}")
        return WebSearchResponse(summary="Erro inesperado na busca.", sources=[]) 


async def web_search_context(request: WebSearchRequest):
    """Gera contexto estruturado (snippets) sem resumir com LLM."""

    results = await searx_search(request.query, k=request.k, lang=request.lang)

    top_urls = [r["url"] for r in results]
    top_titles = [r["title"] for r in results]

    crawled = await asyncio.gather(*(limited_crawl_markdown(u) for u in top_urls), return_exceptions=True)

    markdown_docs = []
    for url, res, title in zip(top_urls, crawled, top_titles):
        if isinstance(res, Exception):
            continue
        md = res.get("markdown") or res.get("content") or ""
        
        # Ensure md is a string
        if not isinstance(md, str):
            continue

        if len(md.strip()) < 300:
            continue
        markdown_docs.append({"url": url, "title": title, "markdown": md})

    if not markdown_docs:
        from src.models.web_search_model import WebSearchContextResponse

        return WebSearchContextResponse(snippets=[])

    await ensure_collection()
    query_id = str(uuid.uuid4())

    seen_texts: set[str] = set()
    all_chunks = []
    for doc in markdown_docs:
        chunks = await chunk_markdown(doc["markdown"])
        for c in chunks:
            txt = c.strip()
            if len(txt) < 200 or txt in seen_texts:
                continue
            seen_texts.add(txt)
            all_chunks.append({"url": doc["url"], "title": doc["title"], "text": txt})

    if all_chunks:
        await index_chunks(all_chunks, query_id)

    hits = await retrieve(request.query, query_id, top_k=8)

    from src.models.web_search_model import WebSearchContextResponse, ContextSnippet

    snippets: list[ContextSnippet] = []
    for h in hits:
        pl = h.payload or {}
        snippet = ContextSnippet(
            url=pl.get("url"),
            title=pl.get("title") or "",
            snippet=pl.get("text") or "",
        )
        snippets.append(snippet)

    return WebSearchContextResponse(snippets=snippets) 