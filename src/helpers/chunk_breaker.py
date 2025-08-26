import asyncio, re


# Regex simples para identificar sentenças. Não depende de bibliotecas externas.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


async def _yield_every(n: int):
    """Força o event-loop a respirar a cada *n* iterações."""
    if n % 100 == 0:
        await asyncio.sleep(0)


async def chunk_markdown(md: str, max_tokens: int = 800, overlap_tokens: int = 150, min_tokens: int = 100):
    """Quebra *markdown* em blocos baseados em sentenças.

    max_tokens: tamanho máximo (aprox. nº de palavras) por chunk.
    overlap_tokens: nº de palavras a reaproveitar entre chunks consecutivos.
    min_tokens: descarta chunks menores que esse valor (ruído).
    """

    sentences = _SENT_SPLIT.split(md)
    chunks: list[str] = []
    curr_words: list[str] = []

    for idx, sent in enumerate(sentences):
        words = sent.strip().split()
        if not words:
            continue

        if len(curr_words) + len(words) > max_tokens:
            if len(curr_words) >= min_tokens:
                chunks.append(" ".join(curr_words).strip())

            overlap = curr_words[-overlap_tokens:] if overlap_tokens else []
            curr_words = overlap + words
        else:
            curr_words.extend(words)

        await _yield_every(idx)

    if len(curr_words) >= min_tokens:
        chunks.append(" ".join(curr_words).strip())

    return chunks
