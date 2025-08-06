#!/bin/bash

# Script para testar a geração da documentação Swagger localmente

set -e

echo "🔍 Testando geração da documentação Swagger..."

# Verifica se o diretório scripts existe
if [ ! -d "scripts" ]; then
    echo "❌ Erro: Execute este script a partir da raiz do projeto"
    exit 1
fi

# Gera a documentação
echo "📖 Gerando documentação..."
python scripts/generate_swagger_docs.py

# Verifica se os arquivos foram criados
if [ -f "docs/swagger/swagger.json" ]; then
    echo "✅ swagger.json criado com sucesso"
    echo "📄 Tamanho: $(stat -c%s docs/swagger/swagger.json) bytes"
else
    echo "❌ Erro: swagger.json não foi criado"
    exit 1
fi

if [ -f "docs/swagger/index.html" ]; then
    echo "✅ index.html criado com sucesso"
    echo "🌐 Você pode abrir docs/swagger/index.html no browser para visualizar"
else
    echo "❌ Erro: index.html não foi criado"
    exit 1
fi

echo ""
echo "🎉 Teste concluído com sucesso!"
echo "📁 Arquivos gerados em: docs/swagger/"
echo "🔗 Para visualizar: abra docs/swagger/index.html no seu navegador"