# Web UI for Klaus
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx \
    pyyaml \
    anthropic \
    openai \
    pydantic \
    python-multipart \
    pyngrok \
    jinja2 \
    aiofiles \
    docker

# Try to install kuzu and sentence-transformers (graph + embeddings) - optional
RUN pip install --no-cache-dir kuzu sentence-transformers || echo "Graph/embedding deps skipped"

# Copy app and static files
COPY app.py /app/
COPY static/ /app/static/
COPY templates/ /app/templates/

# Expose port
EXPOSE 8082

# Environment variables
ENV KIMI_AGENT_URL=http://kimi-agent:8080
ENV WEB_UI_PORT=8082

# Run
CMD ["python", "app.py"]
