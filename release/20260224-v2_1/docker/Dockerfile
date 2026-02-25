# IDE Agent Wizard - Telegram Bot
# ================================
# Multi-provider LLM agent with Telegram interface

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY core/ ./core/
COPY bot/telegram_bot.py .

# Create directories
RUN mkdir -p /app/workspace /app/memory

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '.'); from core.agent import Agent; print('OK')" || exit 1

# Run bot
CMD ["python", "telegram_bot.py"]

