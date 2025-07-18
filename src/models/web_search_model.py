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