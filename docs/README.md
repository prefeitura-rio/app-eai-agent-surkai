# Documentação Automática da API

Este diretório contém a documentação gerada automaticamente da API.

## 📖 Swagger/OpenAPI

A documentação Swagger é gerada automaticamente durante o processo de build da aplicação.

### Arquivos Gerados

- `swagger/swagger.json` - Schema OpenAPI completo em formato JSON
- `swagger/index.html` - Interface visual para navegar na documentação

### Como é Gerado

1. **Durante o CI/CD**: O workflow do GitHub Actions executa o script `scripts/generate_swagger_docs.py` automaticamente
2. **Localmente**: Execute `./scripts/test_swagger_generation.sh` para gerar a documentação local

### Acessando a Documentação

Quando a aplicação estiver rodando, você pode acessar:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **JSON Raw**: `http://localhost:8000/swagger.json`
- **Documentação Estática**: `http://localhost:8000/docs-static/swagger/`

### Estrutura da API

A API segue o padrão de versionamento com prefixos `/api/v1/` para manter compatibilidade e permitir evolução controlada.

#### Endpoints Disponíveis

- `POST /api/v1/web_search` - Busca web básica
- `POST /api/v1/web_search_context` - Busca web com contexto

### Personalização

Para customizar a documentação gerada, edite o arquivo `scripts/generate_swagger_docs.py`.

### Notas Técnicas

- A geração é feita usando o esquema OpenAPI nativo do FastAPI
- Suporte a múltiplos formatos de saída (JSON, HTML)
- Integração com Swagger UI para interface interativa
- Metadados adicionais são inseridos automaticamente (contato, licença, etc.)