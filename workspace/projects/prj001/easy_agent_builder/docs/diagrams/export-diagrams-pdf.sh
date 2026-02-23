#!/bin/bash
# Export Mermaid diagrams to PDF (requires Chrome/Chromium)
# ==========================================================

set -e

echo "📄 Easy Agent Builder - PDF Export"
echo "==================================="
echo ""

# Verificar se mmdc está instalado
if ! command -v mmdc &> /dev/null; then
    echo "❌ mmdc não encontrado. Instalando..."
    npm install -g @mermaid-js/mermaid-cli
fi

# Criar diretório
mkdir -p exports/pdf

# Exportar cada arquivo
for file in *.md; do
    if [ "$file" = "README.md" ]; then
        continue
    fi
    
    basename=$(basename "$file" .md)
    echo "🔄 Exportando PDF: $basename"
    
    mmdc -i "$file" -o "exports/pdf/${basename}.pdf" \
         -b "white" \
         -w "1920" \
         2>/dev/null || echo "   ⚠️  PDF export failed (Chrome/Chromium required)"
done

echo ""
echo "==================================="
echo "✅ PDF export concluído!"
echo "📁 exports/pdf/"
