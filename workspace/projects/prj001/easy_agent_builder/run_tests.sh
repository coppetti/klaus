#!/bin/bash
# Script de execução de testes - Easy Agent Builder
# =================================================

set -e

echo "🧪 Easy Agent Builder - Test Runner"
echo "===================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se está no diretório correto
if [ ! -f "pytest.ini" ]; then
    echo -e "${RED}❌ Erro: Execute este script do diretório easy_agent_builder${NC}"
    exit 1
fi

# Função para rodar testes
run_tests() {
    local test_type=$1
    local marker=$2
    local description=$3
    
    echo -e "${YELLOW}▶️  Rodando: $description${NC}"
    echo "----------------------------------------"
    
    if [ -n "$marker" ]; then
        python -m pytest -m "$marker" -v --tb=short
    else
        python -m pytest -v --tb=short
    fi
    
    echo ""
}

# Verificar argumentos
if [ $# -eq 0 ]; then
    echo "Uso: $0 [all|unit|integration|circuit|coverage|ci]"
    echo ""
    echo "Opções:"
    echo "  all         - Rodar todos os testes (exceto carga)"
    echo "  unit        - Rodar apenas testes unitários"
    echo "  integration - Rodar testes de integração"
    echo "  circuit     - Rodar testes de circuit breaker"
    echo "  coverage    - Rodar com cobertura de código"
    echo "  ci          - Modo CI (com cobertura e relatórios)"
    echo "  load        - Rodar testes de carga (requer Locust)"
    echo ""
    exit 1
fi

# Processar argumento
case $1 in
    all)
        echo -e "${GREEN}🚀 Modo: Todos os testes${NC}\n"
        run_tests "all" "not load" "Todos os testes (exceto carga)"
        ;;
    
    unit)
        echo -e "${GREEN}🚀 Modo: Testes Unitários${NC}\n"
        run_tests "unit" "unit" "Testes Unitários"
        ;;
    
    integration)
        echo -e "${GREEN}🚀 Modo: Testes de Integração${NC}\n"
        run_tests "integration" "integration" "Testes de Integração"
        ;;
    
    circuit)
        echo -e "${GREEN}🚀 Modo: Circuit Breaker${NC}\n"
        run_tests "circuit" "circuit_breaker" "Testes de Circuit Breaker"
        ;;
    
    coverage)
        echo -e "${GREEN}🚀 Modo: Cobertura${NC}\n"
        echo "Gerando relatório de cobertura..."
        python -m pytest --cov=src/agent_builder --cov-report=html --cov-report=term-missing -v
        echo ""
        echo -e "${GREEN}✅ Relatório HTML gerado em: htmlcov/index.html${NC}"
        ;;
    
    ci)
        echo -e "${GREEN}🚀 Modo: CI/CD${NC}\n"
        echo "Executando testes para CI..."
        python -m pytest \
            --cov=src/agent_builder \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=70 \
            -v \
            --tb=short \
            -m "not load"
        ;;
    
    load)
        echo -e "${GREEN}🚀 Modo: Testes de Carga${NC}\n"
        echo "Iniciando Locust..."
        echo "Acesse http://localhost:8089 para interface web"
        echo ""
        locust -f tests/load/test_adapter_load.py --host=http://localhost:8080
        ;;
    
    *)
        echo -e "${RED}❌ Opção inválida: $1${NC}"
        echo "Use: all, unit, integration, circuit, coverage, ci, ou load"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Testes concluídos!${NC}"
