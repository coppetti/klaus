# Sistemas de Memória

## Visão Geral

Klaus tem **3 sistemas de memória** com propósitos diferentes:

| Sistema | Tecnologia | Onde fica | Uso principal |
|---------|------------|-----------|---------------|
| **SQLite** | SQLite DB | `workspace/memory/agent_memory.db` | Dados rápidos, sessões, preferências |
| **Cognitive** | JSON | `workspace/cognitive_memory/` | Grafo semântico, entidades, relações |
| **Kuzu** | Graph DB | `workspace/memory/agent_memory_graph*` | **NÃO USADO** no container |

---

## 1. SQLite Memory

### Arquivo
```
workspace/memory/agent_memory.db
```

### Estrutura de Tabelas
- `memories` - Memórias episódicas (conversas)
- `sessions` - Sessões de chat
- `settings` - Preferências do usuário

### Acesso no Código
```python
from core.memory_store import MemoryStore

memory = MemoryStore("workspace/memory/agent_memory.db")
memory.store(content="Eu gosto de Python", category="preference")
results = memory.recall("Python", limit=5)
```

### Quando Usar
- Recuperação rápida por keyword
- Dados estruturados (sessões, settings)
- Fallback quando Cognitive Memory falha

---

## 2. Cognitive Memory (JSON) ⭐ PRINCIPAL

### Arquivos
```
workspace/cognitive_memory/
├── episodic_memories.json    # Conversas com metadados
├── knowledge_graph.json      # Entidades e relações
└── procedural_memories.json  # Procedures aprendidas
```

### Estrutura do Knowledge Graph
```json
{
  "entities": {
    "technology_python": {
      "id": "technology_python",
      "type": "Technology",
      "name": "Python",
      "properties": {...}
    },
    "topic_api": {
      "id": "topic_api", 
      "type": "Topic",
      "name": "api",
      "properties": {...}
    }
  },
  "relationships": {
    "ep_xxx-MENTIONS-technology_python": {
      "id": "...",
      "type": "MENTIONS",
      "source_id": "ep_xxx",
      "target_id": "technology_python",
      "properties": {...}
    }
  }
}
```

### Tipos de Entidades
| Tipo | Exemplo | Cor no Grafo |
|------|---------|--------------|
| `Technology` | Python, React | Verde (#10b981) |
| `Topic` | api, cloud | Verde (#10b981) |
| `Company` | Google, TechCorp | Azul (#3b82f6) |
| `Person` | Matheus | Laranja (#F26B3A) |
| `Conversation` | ep_2026... | Cinza (#6b7280) |

### Tipos de Relações
- `MENTIONS` - Episódio menciona entidade
- `HAS_TOPIC` - Episódio tem tópico
- `RELATED_TO` - Memórias semanticamente relacionadas
- `FLOWS_INTO` - Sequência temporal

### Acesso no Código
```python
from core.cognitive_memory import get_cognitive_memory_manager

manager = get_cognitive_memory_manager()
kg = manager.knowledge_graph

# Listar entidades
for entity in kg.entities.values():
    print(f"{entity.name} ({entity.type})")

# Listar relações
for rel in kg.relationships.values():
    print(f"{rel.source_id} -> {rel.target_id}")
```

### API Endpoints
```
GET  /api/memory/graph-data          # Dados do grafo (nodes/edges)
POST /api/memory/scrub-graph         # Limpar órfãos
GET  /api/memory/stats               # Estatísticas
```

---

## 3. Kuzu Graph (NÃO USADO)

### Status
❌ **NÃO USADO** no container Web UI atual

### Por quê?
- Build do Docker falha (falta cmake/espaço)
- Cognitive Memory (JSON) funciona bem
- Menos dependências = menos problemas

### Arquivos (existem mas não usados)
```
workspace/memory/
├── agent_memory_graph          # Kuzu DB
└── agent_memory_graph.wal      # Write-ahead log
```

### Se quiser reativar no futuro
1. Instalar Kuzu no host: `pip install kuzu`
2. Adicionar ao Dockerfile: `pip install kuzu`
3. Atualizar endpoints para usar Kuzu diretamente
4. Testar build: `docker compose build --no-cache web-ui`

---

## Política de Relevância

### O que é armazenado?

**✅ ARMAZENA (score >= 0.3):**
- Mensagens técnicas ("Como faço X em Python?")
- Decisões de projeto ("Vamos usar Docker")
- Preferências do usuário ("Eu prefere React")
- Erros e soluções

**❌ IGNORA (score < 0.3):**
- Saudações ("Oi", "Olá", "Hey")
- Confirmações curtas ("ok", "valeu", "beleza")
- Perguntas de identidade ("Quem é você?")
- Mensagens muito curtas (< 10 chars)

### Implementação
Arquivo: `core/memory_relevance_gate.py`

```python
class MemoryRelevanceGate:
    HIGH_THRESHOLD = 0.6   # Importance "high"
    LOW_THRESHOLD = 0.3    # Importance "medium"
    
    def evaluate(self, user_msg, assistant_msg):
        # 1. Check noise patterns
        # 2. Score with ContextAnalyzer
        # 3. Apply keyword boost
        # 4. Return decision
```

---

## Limpeza de Dados (Scrub)

### Quando fazer
- Grafo muito grande
- Muitos nós órfãos
- Dados antigos irrelevantes

### Como fazer
```bash
# Via API
curl -X POST http://localhost:7072/api/memory/scrub-graph

# Ou via Web UI
# Memory tab → Refresh (chama scrub internamente)
```

### O que o scrub remove
1. **Episódios de baixa relevância** (score < 0.3)
2. **Relacionamentos órfãos** (apontando para episódios deletados)
3. **Entidades desconectadas** (sem relações)

### Backup antes do scrub
```bash
cp workspace/cognitive_memory/episodic_memories.json \
   workspace/cognitive_memory/episodic_memories.json.backup
   
cp workspace/cognitive_memory/knowledge_graph.json \
   workspace/cognitive_memory/knowledge_graph.json.backup
```

---

## Visualização do Grafo

### Tecnologia
- **Biblioteca**: vis.js (network)
- **Endpoint**: `/cognitive-memory-graph`
- **Iframe**: Carregado em `/memory` tab

### Sincronização de Tema
O grafo é carregado via iframe. Para temas funcionarem:

```javascript
// Pai envia tema para iframe
iframe.contentWindow.postMessage({
    type: 'theme-change',
    theme: 'deckard-dark'
}, '*');

// Iframe escuta e aplica
window.addEventListener('message', (e) => {
    if (e.data.type === 'theme-change') {
        document.documentElement.className = 
            e.data.theme === 'deckard-dark' ? 'theme-deckard-dark' : 'theme-deckard-light';
    }
});
```

---

## Troubleshooting

### Grafo aparece vazio
```bash
# Verificar se há dados
curl http://localhost:7072/api/memory/graph-data | jq '.nodes | length'

# Se 0, verificar arquivos JSON
ls -la workspace/cognitive_memory/
cat workspace/cognitive_memory/knowledge_graph.json | jq '.entities | length'
```

### Stats mostram "0 real nodes"
- Verificar se endpoint está usando cognitive memory (não Kuzu)
- Verificar `CognitiveMemoryManager` está inicializando

### Muitos nós órfãos
- Rodar scrub: `POST /api/memory/scrub-graph`
- Verificar filtro de relevância está funcionando

---

**Próximo:** [THEMES.md](THEMES.md) - Sistema de temas Deckard
