import asyncio

async def chunk_markdown(md: str, size: int = 1000, overlap: int = 150, yield_every: int = 100):
    """Quebra texto markdown em chunks com sobreposição de forma assíncrona"""
    chunks = []
    start = 0
    iterations = 0
    
    while start < len(md):
        end = min(len(md), start + size)
        chunk = md[start:end]
        chunks.append(chunk)
        start += size - overlap

        iterations += 1
        if iterations % yield_every == 0:
            await asyncio.sleep(0)
    
    return chunks
