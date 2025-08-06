#!/usr/bin/env python3
"""
Script para gerar documentação Swagger automaticamente.
Este script é executado durante o processo de build para criar
a documentação OpenAPI da API.
"""

import json
import os
import sys
from pathlib import Path

# Adiciona o diretório src ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def generate_swagger_docs():
    """Gera a documentação Swagger/OpenAPI da aplicação"""
    try:
        from main import app
        
        # Cria o diretório de documentação
        docs_dir = Path("docs/swagger")
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Gera o schema OpenAPI
        openapi_schema = app.openapi()
        
        # Adiciona informações extras ao schema
        openapi_schema["info"]["contact"] = {
            "name": "Equipe de Desenvolvimento",
            "email": "dev@exemplo.com"
        }
        
        openapi_schema["info"]["license"] = {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
        
        # Salva o JSON do swagger
        swagger_file = docs_dir / "swagger.json"
        with open(swagger_file, 'w', encoding='utf-8') as f:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
        
        # Gera um arquivo HTML simples para visualizar a documentação
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui.css" />
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        *, *:before, *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin:0;
            background: #fafafa;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                url: './swagger.json',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            }});
        }};
    </script>
</body>
</html>"""
        
        html_file = docs_dir / "index.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Documentação Swagger gerada com sucesso!")
        print(f"📄 JSON: {swagger_file}")
        print(f"🌐 HTML: {html_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao gerar documentação Swagger: {e}")
        return False

if __name__ == "__main__":
    success = generate_swagger_docs()
    sys.exit(0 if success else 1)