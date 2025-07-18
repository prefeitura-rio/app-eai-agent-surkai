from typing import List
from google import genai
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel

from src.config.env import GEMINI_API_KEY

MODEL_NAME = "gemini-2.5-flash"


class Response(BaseModel):
    content: str
    
def get_client():
    return genai.Client(api_key=GEMINI_API_KEY)

async def summarize(context: str, query: str) -> str:
    if not GEMINI_API_KEY:
        return context[:1000]
    
    client = get_client()
    
    system_prompt = [
        "Você é um assistente que compila resultados de busca para outro agente de IA.",
        "Use APENAS o contexto fornecido. Responda em português claro e objetivo.",
        "O resultado deve ser bem completo, com informações relevantes e detalhadas.",
        "Quanto mais detalhado, melhor.",
        "Forneça instruções quando necessário.",
        "Você precisa compilar o contexto recebido para dar uma resposta completa e detalhada, rica em instruções, informações de como fazer, como resolver e como atender a pergunta do usuário.",
        "Se o usuário perguntar sobre um assunto que não está no contexto, você deve dizer que não tem informações sobre o assunto."
    ]
    
    config = GenerateContentConfig(
        response_schema=Response,
        response_mime_type="application/json",
        system_instruction=system_prompt,
    )
    
    response = await client.aio.models.generate_content(
        model=MODEL_NAME,
        config=config,
        contents=[
            {
                "role": "user",
                "parts": [
                    {"text": f"Search context:\n{context}\nUser question: {query}"},
                ]
            }
        ],
    )
    
    return response.text