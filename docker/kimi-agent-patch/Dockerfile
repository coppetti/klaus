FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    anthropic \
    pydantic \
    pyyaml \
    httpx \
    google-genai

COPY . /app/kimi-agent/

WORKDIR /app/kimi-agent

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
