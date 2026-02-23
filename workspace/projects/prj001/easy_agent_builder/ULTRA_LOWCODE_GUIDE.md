# 🚀 Ultra Low-Code Guide

> Crie agentes AI **sem escrever código Python**. Apenas YAML.

## 💡 Conceito

```
YAML (config) → CLI (eab) → Agente rodando
```

**Tempo para primeiro agente:** 2 minutos  
**Linhas de código necessárias:** 0  
**Conhecimento técnico:** Mínimo (editar texto)

---

## 🎯 Quick Start (2 minutos)

### 1. Configure GCP (uma vez)
```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project SEU_PROJETO
export GOOGLE_CLOUD_PROJECT=SEU_PROJETO
```

### 2. Crie seu primeiro agente
```bash
# Edite o arquivo YAML existente
vim agents/meu_assistente.yaml

# Ou crie um novo copiando
cp agents/meu_assistente.yaml agents/meu_novo_agente.yaml
```

### 3. Teste local
```bash
# Valide a configuração (tipo 'go build')
python src/agent_builder/ultra_lowcode.py validate agents/meu_assistente.yaml

# Rode o agente
python src/agent_builder/ultra_lowcode.py run agents/meu_assistente.yaml
```

---

## 📋 Estrutura do YAML

```yaml
# agents/meu_agente.yaml

name: nome_do_agente           # Identificador único
type: llm                      # llm | router | sequential | parallel
model: gemini-2.0-flash-exp    # Modelo Vertex AI

description: "Descrição curta"  # Para documentação

instruction: |                 # Comportamento do agente
  Você é um assistente...
  Regras:
  1. ...
  2. ...

tools:                         # Ferramentas disponíveis
  - google_search              # Busca na web
  # Outras tools serão adicionadas

temperature: 0.7              # Criatividade (0-1)
max_tokens: 2048              # Limite de resposta

# Para routers apenas:
sub_agents:                   # Lista de agentes filhos
  - vendas
  - suporte
  - financeiro
```

---

## 🎨 Exemplos Prontos

### Agente Simples
**Arquivo:** `agents/meu_assistente.yaml`

```yaml
name: meu_assistente
type: llm
model: gemini-2.0-flash-exp
description: Assistente virtual amigável
instruction: |
  Você é um assistente prestativo.
  Responda sempre em português.
tools:
  - google_search
temperature: 0.7
```

**Uso:**
```bash
python src/agent_builder/ultra_lowcode.py run agents/meu_assistente.yaml
```

---

### Router Multi-Agent (Atendimento)
**Arquivo:** `agents/router_atendimento.yaml`

```yaml
name: router_atendimento
type: router
model: gemini-2.0-flash-exp
description: Coordenador de atendimento
instruction: |
  Delegue para o especialista correto:
  - vendas: orçamentos, preços
  - suporte: problemas técnicos
  - financeiro: pagamentos
sub_agents:
  - vendas
  - suporte
  - financeiro
```

**Também crie os especialistas:**
- `agents/vendas.yaml` (type: llm)
- `agents/suporte.yaml` (type: llm)
- `agents/financeiro.yaml` (type: llm)

**Uso:**
```bash
python src/agent_builder/ultra_lowcode.py run agents/router_atendimento.yaml
```

---

## 🛠️ Comandos CLI

### Validar Configuração
```bash
python src/agent_builder/ultra_lowcode.py validate agents/meu_agente.yaml
```

**Saída esperada:**
```
🔍 Validando: agents/meu_agente.yaml
✅ Configuração válida!
   Nome: meu_agente
   Tipo: llm
   Modelo: gemini-2.0-flash-exp
   Tools: 1
```

### "Compilar" para Python (opcional)
```bash
python src/agent_builder/ultra_lowcode.py compile agents/meu_agente.yaml
```

Gera código Python em `src/agents/meu_agente/agent.py`

### Executar Direto
```bash
python src/agent_builder/ultra_lowcode.py run agents/meu_agente.yaml
```

Inicia chat interativo.

### Criar Template
```bash
python src/agent_builder/ultra_lowcode.py init
```

Cria `agent.yaml` com exemplo básico.

---

## 🆚 Comparação: Ultra Low-Code vs Código Python

### Cenário: Criar um chatbot

| Abordagem | Linhas de Código | Tempo | Complexidade |
|-----------|-----------------|-------|--------------|
| **Go puro** | ~50 linhas Go | 30 min | Alta |
| **Python puro** | ~30 linhas Python | 15 min | Média |
| **Nosso Framework CLI** | ~5 comandos | 5 min | Baixa |
| **Ultra Low-Code (YAML)** | **~15 linhas YAML** | **2 min** | **Mínima** |

### Exemplo Visual

**Python (modo tradicional):**
```python
from google.adk.agents import LlmAgent
from google.adk.tools import google_search

agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="assistente",
    description="Um assistente",
    instruction="Você é um assistente...",
    tools=[google_search],
)
```

**Ultra Low-Code (YAML):**
```yaml
name: assistente
description: Um assistente
instruction: Você é um assistente...
tools:
  - google_search
```

**Ganho:** 70% menos código, sem sintaxe para errar.

---

## 🔧 Validação Estática (Inspirada no Go)

Assim como Go compila e verifica antes de rodar, nosso YAML é validado:

### Erros Detectados

```bash
# Erro: nome inválido
❌ Erro: nome deve ser alfanumérico

# Erro: instruction vazia
❌ Erro: instruction muito curta (mín 10 chars)

# Erro: sub-agente inexistente
❌ router_atendimento: sub-agente 'vendas' não encontrado

# Erro: tipo inválido
❌ Erro: tipo deve ser um de: ['llm', 'sequential', 'parallel', 'router', 'loop']
```

### Vantagens
- ✅ Descobre erros antes de gastar tokens na API
- ✅ Feedback imediato (igual compilação Go)
- ✅ Segurança de tipos (campos obrigatórios)

---

## 📊 Schema Completo

### Campos Obrigatórios
```yaml
name: string          # ID único (alfanumérico, _, -)
type: string          # llm | router | sequential | parallel | loop
instruction: string   # Mínimo 10 caracteres
```

### Campos Opcionais
```yaml
model: string         # Default: gemini-2.0-flash-exp
description: string   # Default: igual ao name
tools: list           # Default: [] (sem tools)
temperature: float    # Default: 0.7 (0-1)
max_tokens: int       # Default: 2048
sub_agents: list      # Apenas para type: router
```

---

## 🚀 Deploy

### Opção 1: Compilar e Deployar
```bash
# Gera código Python
python src/agent_builder/ultra_lowcode.py compile agents/meu_agente.yaml

# Deploy (usa código gerado)
eab deploy --agent meu_agente --env production
```

### Opção 2: Deploy Direto do YAML (futuro)
```bash
# Ideal
eab deploy agents/meu_agente.yaml
```

---

## 💡 Dicas de Produtividade

### 1. Use templates
```bash
# Crie templates para sua empresa
cp agents/meu_assistente.yaml agents/template_vendas.yaml
cp agents/meu_assistente.yaml agents/template_suporte.yaml

# Novo agente = copiar + editar 3 campos
```

### 2. Versione seus agentes
```
agents/
  vendas_v1.yaml
  vendas_v2.yaml  # Melhorado
  vendas_v2.1.yaml  # Hotfix
```

### 3. Use instruções estruturadas
```yaml
instruction: |
  ## PERSONALIDADE
  - Amigável e profissional
  
  ## REGRAS
  1. Sempre confirme dados
  2. Nunca prometa prazos
  
  ## PROCESSO
  1. Entenda o problema
  2. Proponha solução
  3. Confirme resolução
```

---

## ❓ FAQ

**Q: Preciso saber Python?**  
A: Não! Apenas editar YAML (texto estruturado).

**Q: Posso misturar YAML e código Python?**  
A: Sim! Use YAML para 90% dos casos, Python apenas quando precisar de lógica customizada.

**Q: É seguro?**  
A: O YAML é validado antes de executar, igual compilação.

**Q: Funciona com Bibha.ai?**  
A: Sim! O YAML gera código Python compatível com nossos adapters de integração.

---

## 🎯 Próximos Passos

1. ✅ **Edite** `agents/meu_assistente.yaml`
2. ✅ **Valide** com `validate` command
3. ✅ **Teste** com `run` command
4. ✅ **Crie** seus próprios agentes
5. ✅ **Compartilhe** templates com equipe

---

**Low-code não significa low-power.** 🚀
