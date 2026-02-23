# Dockerfile para Easy Agent Builder
# Build multi-stage para otimização

# ===========================================
# Stage 1: Builder
# ===========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Instalar dependências de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivos de dependências
COPY pyproject.toml ./

# Criar virtual environment e instalar dependências
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install -e "."

# ===========================================
# Stage 2: Runtime
# ===========================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copiar virtual environment do builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Não rodar como root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copiar código fonte
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser config/ ./config/

# Criar diretório para logs
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

USER appuser

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Expor porta
EXPOSE 8080

# Comando padrão (pode ser sobrescrito)
CMD ["python", "-m", "uvicorn", "src.agent_builder.serving:app", "--host", "0.0.0.0", "--port", "8080"]
