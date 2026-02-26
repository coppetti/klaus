# Instalação e Dependências

## Requisitos de Sistema

### Mínimos
- **OS**: macOS 11+, Ubuntu 20.04+, Windows 10+
- **RAM**: 4 GB (8 GB recomendado)
- **Disco**: 5 GB livre
- **Docker**: 20.10+ com Docker Compose
- **Python**: 3.11+ (para desenvolvimento)

### Rede
- Conexão com internet (para API calls)
- Portas livres: 7070/7072 (dev) ou 2019/2049 (release)

---

## Instalação Rápida (Release)

```bash
# 1. Baixar release
cd ~/Downloads
unzip Klaus_v1.zip
cd Klaus_v1

# 2. Configurar API keys
cp .env.example .env
# Editar .env com suas chaves:
#   KIMI_API_KEY=sk-sua-chave-aqui

# 3. Rodar setup
./setup.sh

# 4. Acessar
open http://localhost:2049
```

---

## Instalação Dev (Contribuidores)

```bash
# 1. Clonar repo
git clone git@github.com:coppetti/klaus.git
cd klaus

# 2. Criar venv
python3 -m venv .venv
source .venv/bin/activate

# 3. Instalar deps
pip install -r requirements.txt

# 4. Configurar
cp .env.example .env
# Editar .env

# 5. Subir containers
cd docker
docker compose up -d

# 6. Acessar
open http://localhost:7072
```

---

## Dependências Python

### Core (requirements.txt)
```
# Core
pyyaml>=6.0
httpx>=0.25.0

# Telegram
python-telegram-bot>=20.6
aiohttp>=3.9.0

# Web Search
duckduckgo-search>=3.9.0

# Optional
kuzu>=0.4.0                    # Não usado no container
sentence-transformers>=2.2.0   # Embeddings

# Dev
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

### Container (Dockerfile)
```dockerfile
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
    aiofiles

# Tenta instalar Kuzu (pode falhar)
RUN pip install --no-cache-dir kuzu sentence-transformers || echo "Skipped"
```

---

## Configuração de API Keys

### .env.example
```bash
# Kimi (Moonshot AI) - Recomendado
KIMI_API_KEY=sk-sua-chave-aqui

# Anthropic (opcional)
ANTHROPIC_API_KEY=sk-ant-sua-chave

# OpenAI (opcional)
OPENAI_API_KEY=sk-openai-sua-chave

# OpenRouter (opcional)
OPENROUTER_API_KEY=sk-or-sua-chave
```

### Onde obter
- **Kimi**: https://platform.moonshot.cn
- **Anthropic**: https://console.anthropic.com
- **OpenAI**: https://platform.openai.com
- **OpenRouter**: https://openrouter.ai

---

## Troubleshooting Instalação

### Docker não encontrado
```bash
# macOS
brew install --cask docker

# Ubuntu
curl -fsSL https://get.docker.com | sh
```

### Portas em uso
```bash
# Verificar
lsof -i :7072

# Mudar portas em docker/docker-compose.yml
# Ou matar processo: kill -9 <PID>
```

### Permissão negada (Docker)
```bash
# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER
# Relogar
```

### Build falha (sem espaço)
```bash
# Limpar caches
docker system prune -a
docker volume prune
```

---

## Estrutura de Diretórios Pós-Instalação

```
klaus/
├── docker/                 # Docker configs
├── core/                   # Código Python core
├── bot/                    # Telegram bot
├── workspace/              # Dados do usuário (persistente)
│   ├── memory/            # SQLite + Kuzu
│   ├── cognitive_memory/  # JSON memories
│   ├── web_ui_data/       # Sessions, settings
│   ├── SOUL.md           # Identidade do agente
│   └── USER.md           # Perfil do usuário
├── docs/                   # Documentação
├── templates/              # SOUL templates
└── scripts/                # Utilitários
```

---

**Próximo:** Volte para [README.md](README.md) para índice completo.
