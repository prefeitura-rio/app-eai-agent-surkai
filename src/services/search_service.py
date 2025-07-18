import re, asyncio, json
from typing import List

from src.models.web_search_model import WebSearchRequest, WebSearchResponse
from src.services.searx_client import searx_search
from src.services.crawl_client import crawl_markdown
from src.helpers.chunk_breaker import chunk_markdown
from src.helpers.vectorstore import ensure_collection, index_chunks, retrieve
from src.services.llm_client import summarize

URL_REGEX = re.compile(r"^\*\s+(https?://\S+)")


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
    results = await searx_search(request.query, k=request.k, lang=request.lang)
    top_urls = [r["url"] for r in results]

    crawled = await asyncio.gather(*(crawl_markdown(u) for u in top_urls), return_exceptions=True)

    markdown_docs = []
    for url, res in zip(top_urls, crawled):
        if isinstance(res, Exception):
            continue
        md = res.get("markdown") or res.get("content") or ""
        title = res.get("metadata", {}).get("title", url)
        if md:
            markdown_docs.append({"url": url, "title": title, "markdown": md})

    if not markdown_docs:
        return WebSearchResponse(summary="Não encontrei informação suficiente.", sources=[])

    await ensure_collection()
    all_chunks = []
    for doc in markdown_docs:
        chunks = await chunk_markdown(doc["markdown"])
        for c in chunks:
            all_chunks.append({"url": doc["url"], "title": doc["title"], "text": c})

    if all_chunks:
        await index_chunks(all_chunks)
        
    hits = await retrieve(request.query, top_k=4)
    ctx_chunks = [h.payload["text"] for h in hits]
    context = "\n\n".join(ctx_chunks)

    raw_answer = await summarize(context, request.query)

    summary, sources = await _extract_sources(raw_answer, fallback=top_urls)

    return WebSearchResponse(summary=summary, sources=sources) 