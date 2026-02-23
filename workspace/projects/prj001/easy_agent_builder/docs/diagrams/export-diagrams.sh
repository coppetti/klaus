#!/bin/bash
# Export Mermaid diagrams to PNG/SVG/PDF
# ======================================

set -e

echo "📊 Easy Agent Builder - Diagram Export"
echo "======================================="
echo ""

# Verificar se mmdc está instalado
if ! command -v mmdc &> /dev/null; then
    echo "❌ mmdc não encontrado. Instalando..."
    npm install -g @mermaid-js/mermaid-cli
fi

# Criar diretório de saída
mkdir -p exports/png
mkdir -p exports/svg
mkdir -p exports/pdf

# Configurações
THEME="default"
BACKGROUND="white"
WIDTH="1920"

# Exportar cada arquivo Markdown
for file in *.md; do
    # Pular README
    if [ "$file" = "README.md" ]; then
        continue
    fi
    
    basename=$(basename "$file" .md)
    echo "🔄 Exportando: $file"
    
    # PNG
    echo "   📷 PNG..."
    mmdc -i "$file" -o "exports/png/${basename}.png" \
         -b "$BACKGROUND" \
         -w "$WIDTH" \
         -t "$THEME" \
         2>/dev/null || echo "   ⚠️  PNG export failed"
    
    # SVG
    echo "   🎨 SVG..."
    mmdc -i "$file" -o "exports/svg/${basename}.svg" \
         -b "$BACKGROUND" \
         -t "$THEME" \
         2>/dev/null || echo "   ⚠️  SVG export failed"
    
    echo "   ✅ Concluído: $basename"
    echo ""
done

echo "======================================="
echo "✅ Exportação concluída!"
echo ""
echo "Arquivos gerados:"
echo "  📁 exports/png/  - Imagens PNG"
echo "  📁 exports/svg/  - Vetores SVG"
echo ""
echo "Para gerar PDF, use:"
echo "  ./export-diagrams-pdf.sh"
