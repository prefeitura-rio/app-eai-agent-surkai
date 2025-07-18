from pydantic import BaseModel, Field, HttpUrl
from typing import List

class WebSearchRequest(BaseModel):
    """Schema da requisição para /web_search."""

    query: str = Field(..., description="Pergunta ou termos de busca.")
    k: int = Field(6, ge=1, le=20, description="Número máximo de resultados iniciais.")
    lang: str = Field("pt-BR", description="Idioma preferido para resultados e summary.")
    freshness_days: int | None = Field(
        None, ge=1, description="Restringe busca a conteúdos recentes (opcional)."
    )


class WebSearchResponse(BaseModel):
    """Schema da resposta retornada pela rota /web_search."""

    summary: str = Field(..., description="Resumo objetivo que responde à query.")
    sources: List[HttpUrl] = Field(
        ..., min_items=0, max_items=8, description="Lista de URLs citadas na resposta."
    )


# Novo modelo para trechos de contexto organizados
class ContextSnippet(BaseModel):
    """Trecho individual retornado por /web_search/context."""

    url: HttpUrl = Field(..., description="URL de origem do trecho.")
    title: str = Field(..., description="Título da página.")
    snippet: str = Field(..., description="Trecho em texto extraído da página.")


class WebSearchContextResponse(BaseModel):
    """Schema da resposta para /web_search/context."""

    snippets: List[ContextSnippet] = Field(
        ..., min_items=0, description="Lista de trechos relevantes para a query."
    ) 