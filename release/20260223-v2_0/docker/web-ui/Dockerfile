# Web UI for IDE Agent Wizard
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
    python-multipart

# Try to install kuzu (graph database) - optional
RUN pip install --no-cache-dir kuzu || echo "Kuzu installation skipped (optional)"

# Copy app
COPY app.py /app/

# Expose port
EXPOSE 8082

# Environment variables
ENV KIMI_AGENT_URL=http://kimi-agent:8081
ENV WEB_UI_PORT=8082

# Run
CMD ["python", "app.py"]
