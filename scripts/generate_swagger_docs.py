#!/usr/bin/env python3
"""
Script para gerar documentação Swagger automaticamente, incluindo
Bearer Token security e server base.
"""

import json
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz do projeto ao PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def generate_swagger_docs():
    """Gera a documentação Swagger/OpenAPI da aplicação"""
    try:
        # Variáveis de ambiente mínimas para evitar erros de importação
        os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
        os.environ.setdefault("COLL", "default")
        os.environ.setdefault("CRAWL_URL", "http://localhost:3000")
        os.environ.setdefault("SEARX_URL", "http://localhost:8080")
        os.environ.setdefault("GEMINI_API_KEY", "dummy-key")

        from src.main import app

        # Cria o diretório de documentação
        docs_dir = Path("docs/swagger")
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Gera o schema OpenAPI
        openapi_schema = app.openapi()

        # ------------------------ CUSTOMIZAÇÕES ------------------------ #
        # 1) Servidor
        openapi_schema["servers"] = [
            {
                "url": "https://services.staging.app.dados.rio/eai-agent-surkai/",
                "description": "Staging"
            }
        ]

        # 2) Segurança Bearer Token (JWT)
        bearer_security = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
        openapi_schema.setdefault("components", {}).setdefault(
            "securitySchemes", {}
        ).update(bearer_security)

        # 3) Aplica requisito de segurança global
        #    (todas as rotas exigem Authorization: Bearer <token>)
        openapi_schema.setdefault("security", []).append({"bearerAuth": []})

        # 4) Informações extras (contato e licença)
        openapi_schema["info"]["contact"] = {
            "name": "Equipe de Desenvolvimento",
            "email": "dev@exemplo.com"
        }
        openapi_schema["info"]["license"] = {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
        # ---------------------------------------------------------------- #

        # Salva o JSON do Swagger
        swagger_file = docs_dir / "swagger.json"
        with open(swagger_file, "w", encoding="utf-8") as f:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

        # Gera um HTML simples para visualização local
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <title>API Documentation</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui.css"/>
  <style>
    html {{ box-sizing: border-box; overflow-y: scroll; }}
    *,*:before,*:after {{ box-sizing: inherit; }}
    body {{ margin:0; background:#fafafa; }}
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = () => {{
      SwaggerUIBundle({{
        url: './swagger.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
        plugins: [SwaggerUIBundle.plugins.DownloadUrl],
        layout: 'StandaloneLayout'
      }});
    }};
  </script>
</body>
</html>"""

        html_file = docs_dir / "index.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print("✅ Documentação Swagger gerada com sucesso!")
        print(f"📄 JSON: {swagger_file}")
        print(f"🌐 HTML: {html_file}")
        return True

    except Exception as e:
        print(f"❌ Erro ao gerar documentação Swagger: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if generate_swagger_docs() else 1)
