import re
from typing import List, Dict
from loguru import logger


def _calculate_chunk_score(chunk_text: str, query_terms: set[str]) -> float:
    """Calcula score de relevância para um chunk baseado na query."""
    text_lower = chunk_text.lower()
    text_terms = set(re.findall(r'\b\w+\b', text_lower))
    
    if not text_terms:
        return 0.0
    
    # 1. Jaccard similarity (intersecção / união)
    intersection = query_terms & text_terms
    union = query_terms | text_terms
    jaccard = len(intersection) / len(union) if union else 0
    
    # 2. Densidade de termos da query no texto
    density = len(intersection) / len(text_terms) if text_terms else 0
    
    # 3. Boost para chunks que contêm termos consecutivos da query
    consecutive_boost = 0
    query_phrase = ' '.join(query_terms)
    if len(query_phrase) > 5 and query_phrase in text_lower:
        consecutive_boost = 0.2
    
    # 4. Boost para termos no início do chunk (primeiras 200 palavras)
    first_words = ' '.join(text_lower.split()[:200])
    early_terms = len(query_terms & set(re.findall(r'\b\w+\b', first_words)))
    position_boost = (early_terms / len(query_terms)) * 0.1 if query_terms else 0
    
    # Score final combinado
    final_score = (jaccard * 0.5) + (density * 0.3) + consecutive_boost + position_boost
    
    return min(final_score, 1.0)  # Cap em 1.0


async def select_relevant_chunks(chunks: List[Dict], query: str, max_chunks: int = 25) -> List[Dict]:
    """
    Seleciona chunks mais relevantes usando análise textual simples.
    
    Args:
        chunks: Lista de dicionários com 'text', 'url', 'title'
        query: Query do usuário
        max_chunks: Número máximo de chunks a retornar
    
    Returns:
        Lista de chunks ordenados por relevância
    """
    logger.info(f"Selecting relevant chunks from {len(chunks)} total chunks for query: '{query}'")
    
    if not chunks:
        return []
    
    # Preprocessa query - extrai termos relevantes
    query_lower = query.lower()
    query_terms = set(re.findall(r'\b\w+\b', query_lower))
    
    # Remove stop words comuns em português
    stop_words = {
        'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'de', 'do', 'da', 'dos', 'das',
        'e', 'ou', 'mas', 'que', 'para', 'por', 'com', 'em', 'no', 'na', 'nos', 'nas',
        'se', 'é', 'são', 'foi', 'ser', 'ter', 'tem', 'seu', 'sua', 'seus', 'suas',
        'esse', 'essa', 'esses', 'essas', 'este', 'esta', 'estes', 'estas', 'aquele',
        'aquela', 'aqueles', 'aquelas', 'como', 'quando', 'onde', 'porque', 'qual',
        'quais', 'quanto', 'quantos', 'quanta', 'quantas'
    }
    query_terms = query_terms - stop_words
    
    logger.debug(f"Query terms after stop word removal: {query_terms}")
    
    if not query_terms:
        # Se não há termos relevantes, retorna chunks em ordem original
        logger.warning("No relevant query terms found, returning first chunks")
        return chunks[:max_chunks]
    
    # Calcula score para cada chunk
    scored_chunks = []
    for i, chunk in enumerate(chunks):
        chunk_text = chunk.get("text", "")
        if not chunk_text:
            continue
            
        score = _calculate_chunk_score(chunk_text, query_terms)
        scored_chunks.append((score, i, chunk))
        
        logger.debug(f"Chunk {i} score: {score:.4f}, URL: {chunk.get('url', 'N/A')}")
    
    # Ordena por score (maior primeiro) e depois por ordem original (menor índice primeiro)
    scored_chunks.sort(key=lambda x: (-x[0], x[1]))
    
    # Retorna os top chunks
    selected = [chunk for _, _, chunk in scored_chunks[:max_chunks]]
    
    logger.info(f"Selected {len(selected)} chunks. Top scores: {[round(score, 4) for score, _, _ in scored_chunks[:5]]}")
    
    return selected


async def estimate_context_tokens(chunks: List[Dict]) -> int:
    """
    Estima aproximadamente quantos tokens o contexto dos chunks vai usar.
    Aproximação: 1 token ≈ 4 caracteres para texto em português.
    """
    total_chars = sum(len(chunk.get("text", "")) for chunk in chunks)
    estimated_tokens = total_chars // 4
    logger.debug(f"Estimated context tokens: {estimated_tokens} (from {total_chars} chars)")
    return estimated_tokens


async def select_chunks_within_token_limit(chunks: List[Dict], query: str, max_tokens: int = 100000) -> List[Dict]:
    """
    Seleciona chunks relevantes respeitando limite de tokens do contexto.
    
    Args:
        chunks: Lista de chunks disponíveis
        query: Query do usuário  
        max_tokens: Limite máximo de tokens para o contexto
    
    Returns:
        Lista de chunks selecionados dentro do limite
    """
    logger.info(f"Selecting chunks within token limit of {max_tokens}")
    
    # Começa com seleção inicial mais ampla
    selected_chunks = await select_relevant_chunks(chunks, query, max_chunks=50)
    
    # Reduz gradualmente até caber no limite
    while selected_chunks:
        estimated_tokens = await estimate_context_tokens(selected_chunks)
        
        if estimated_tokens <= max_tokens:
            logger.info(f"Final selection: {len(selected_chunks)} chunks, ~{estimated_tokens} tokens")
            return selected_chunks
        
        # Remove chunk menos relevante (último da lista)
        selected_chunks = selected_chunks[:-1]
        logger.debug(f"Reducing to {len(selected_chunks)} chunks to fit token limit")
    
    logger.warning("Could not fit any chunks within token limit")
    return []
