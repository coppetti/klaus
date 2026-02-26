# Arquitetura do Klaus

## Visão Geral

Klaus é um agente AI local com múltiplas interfaces (IDE, Web, Telegram) e sistema de memória híbrida.

```
┌─────────────────────────────────────────────────────────────┐
│                        USUÁRIO                              │
└──────────────┬──────────────────┬───────────────────────────┘
               │                  │
    ┌──────────▼──────────┐      ▼
    │   IDE (Port 2019)   │   Telegram
    │   (VSCode/Cursor)   │   (Bot)
    └──────────┬──────────┘      │
               │                 │
               └────────┬────────┘
                        │
    ┌───────────────────▼───────────────────┐
    │           Web UI (Port 2049)          │
    │  - Chat interface                     │
    │  - Memory Graph Explorer              │
    │  - Settings (providers, themes)       │
    └───────────────────┬───────────────────┘
                        │
    ┌───────────────────▼───────────────────┐
    │      Kimi Agent (Port 2019/7070)      │
    │  - Core LLM processing                │
    │  - Multi-provider routing             │
    │  - File I/O interception              │
    └───────────────────┬───────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼────┐   ┌──────▼──────┐  ┌────▼─────┐
   │ SQLite  │   │ Cognitive   │  │  Kuzu    │
   │(episodes│   │ Memory      │  │ (não     │
   │ entities│   │ (JSON)      │  │ usado)   │
   │ etc)    │   │ Knowledge   │  └──────────┘
   └─────────┘   │ Graph       │
                 └─────────────┘
```

---

## Componentes Principais

### 1. Kimi Agent (`docker/kimi-agent-patch/`)
- **Função**: Processamento central de LLM
- **Porta interna**: 8080
- **Porta host (dev)**: 7070
- **Porta host (release)**: 2019
- **Tecnologia**: Python + FastAPI

**Responsabilidades:**
- Receber requisições de Web UI, Telegram, IDE
- Roteamento multi-provider (Kimi, Anthropic, OpenAI, etc.)
- Interceptação de tags XML (`<WRITE_FILE>`, `<READ_FILE>`)
- Comunicação com sistemas de memória

### 2. Web UI (`docker/web-ui/app.py`)
- **Função**: Interface web do usuário
- **Porta interna**: 8082
- **Porta host (dev)**: 7072
- **Porta host (release)**: 2049
- **Tecnologia**: FastAPI + HTML/JS/CSS

**Funcionalidades:**
- Chat multi-linha com markdown
- Memory Graph Explorer (vis.js)
- Settings (providers, modelos, temas)
- Session management
- Upload de arquivos

### 3. Telegram Bot (`bot/telegram_bot.py`)
- **Função**: Interface Telegram
- **Sem porta externa** (conecta via polling)
- **Tecnologia**: python-telegram-bot

**Configuração:**
- Via Web UI (Settings → Telegram)
- Bot Token do @BotFather
- Chat ID para autorização

### 4. Sistemas de Memória

#### SQLite (`workspace/memory/`)
- **Arquivo**: `agent_memory.db`
- **Uso**: Dados rápidos, sessões, preferências
- **Acesso**: Via `MemoryStore` class

#### Cognitive Memory (`workspace/cognitive_memory/`)
- **Arquivos**: `episodic_memories.json`, `knowledge_graph.json`
- **Uso**: Grafo semântico, entidades, relacionamentos
- **Acesso**: Via `CognitiveMemoryManager` class

#### Kuzu Graph (`workspace/memory/`)
- **Arquivos**: `agent_memory_graph`, `.wal`
- **Status**: NÃO USADO no container Web UI
- **Motivo**: Falha na instalação do Kuzu no build Docker
- **Alternativa**: Usamos Cognitive Memory (JSON)

---

## Fluxo de Dados

### Exemplo: Usuário envia mensagem no Web UI

1. **Web UI** recebe POST em `/api/chat`
2. **Web UI** consulta memória (contexto relevante)
3. **Web UI** envia para **Kimi Agent** (`/chat`)
4. **Kimi Agent** processa com LLM
5. **Kimi Agent** retorna resposta
6. **Web UI** armazena na memória (episódio)
7. **Web UI** extrai entidades/tópicos
8. **Web UI** atualiza Knowledge Graph
9. **Web UI** retorna resposta ao usuário

---

## Tecnologias Chave

| Tecnologia | Onde é usada | Por quê |
|------------|--------------|---------|
| **FastAPI** | Kimi Agent, Web UI | APIs async, auto-docs |
| **SQLite** | Memória primária | Simples, confiável |
| **JSON** | Cognitive Memory | Sem dependências complexas |
| **vis.js** | Graph Explorer | Visualização de grafos |
| **Tailwind** | Web UI styling | Utilitário, rápido |
| **CSS Vars** | Temas Deckard | Light/dark switching |
| **Docker** | Containerização | Isolamento, portabilidade |

---

## Decisões Arquiteturais Importantes

### Por que não usamos Kuzu no container?
- Build falha (falta cmake/espaço)
- Cognitive Memory (JSON) funciona bem
- Menos dependências = menos problemas

### Por que duas portas (dev vs release)?
- **Dev (7070/7072)**: Para desenvolvimento local
- **Release (2019/2049)**: Para distribuição (Blade Runner theme)

### Por que temas em CSS Variables?
- Troca instantânea (sem reload)
- Funciona em iframe (grafo)
- Persistente (localStorage)

---

## Pontos de Extensão

Quer adicionar uma feature? Aqui são os pontos de entrada:

| Feature | Onde mexer |
|---------|-----------|
| Novo provider LLM | `core/providers/`, `core/llm_router.py` |
| Nova página UI | `docker/web-ui/app.py` (endpoint + HTML) |
| Novo tipo de memória | `core/cognitive_memory.py` |
| Novo tema | `docker/web-ui/static/themes.css` |
| Novo comando Telegram | `bot/telegram_bot.py` |

---

**Próximo:** [GIT_REPOSITORIES.md](GIT_REPOSITORIES.md) - Estratégia de repositórios
