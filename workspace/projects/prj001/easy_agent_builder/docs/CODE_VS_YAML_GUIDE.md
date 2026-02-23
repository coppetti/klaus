# Guia: Quando Usar YAML vs Código

## Resumo Rápido

| Cenário | Recomendação | Exemplo |
|---------|-------------|---------|
| Respostas simples baseadas em instruções | **YAML** | FAQ, chatbots básicos |
| Tools prontas (google_search) | **YAML** | Pesquisador web |
| Router entre agentes | **YAML** | Direcionador de atendimento |
| Integração com APIs internas | **CÓDIGO** | Consulta CRM, ERP |
| Lógica de negócio complexa | **CÓDIGO** | Cálculo de pricing, workflow |
| Validações customizadas | **CÓDIGO** | Validação de CPF, regras fiscais |
| Acesso a bancos de dados | **CÓDIGO** | Query SQL, MongoDB |
| Comunicação com serviços internos | **CÓDIGO** | Kafka, RabbitMQ, filas |

---

## 🟢 Use YAML Quando...

### 1. Agente é "Pergunta → Resposta"
```yaml
# Perfeito para YAML
name: faq_assistente
instruction: |
  Responda perguntas frequentes sobre nosso produto.
  
  Tópicos:
  - Preços e planos
  - Funcionalidades
  - Suporte técnico básico
tools:
  - google_search
```

### 2. Comportamento é baseado em instruções claras
- "Seja amigável"
- "Responda em português"
- "Use tom profissional"

### 3. Usa tools já existentes
- google_search
- code_execution
- ferramentas do ADK

### 4. Estrutura é Router/Workflow simples
```yaml
# Router simples = YAML
name: router
type: router
sub_agents:
  - vendas
  - suporte
```

---

## 🔴 Use CÓDIGO Quando...

### 1. Precisa de Tool Customizada
```python
@tool
def consultar_crm(cliente_id: str):
    # Chamada à sua API interna
    response = requests.get(f"https://api.company.com/crm/{cliente_id}")
    return response.json()
```

### 2. Lógica de Negócio Complexa
```python
@tool
def calcular_preco(quantidade: int, segmento: str, regiao: str):
    # Regras complexas de pricing
    base = TABELA_PRECO[segmento]
    
    if regiao in ["Norte", "Nordeste"]:
        base *= 0.9  # Desconto regional
    
    if quantidade > 100:
        base *= 0.85  # Desconto volume
    
    # Verificar limite de desconto
    if base < PRECO_MINIMO:
        return {"erro": "Preço abaixo do permitido"}
    
    return {"preco_final": base}
```

### 3. Acesso a Dados Internos
- Banco de dados SQL
- MongoDB
- Redis
- Firebase

### 4. Integrações Específicas
- Salesforce API
- SAP
- Webhook interno
- Message queue (Kafka, SQS)

### 5. Transformações de Dados
```python
@tool
def gerar_relatorio_pdf(dados: dict):
    # Usa bibliotecas como ReportLab
    pdf = criar_pdf(dados)
    salvar_no_storage(pdf)
    return {"url": "https://storage.company.com/relatorio.pdf"}
```

---

## 🟡 Use ABORDAGEM HÍBRIDA Quando...

### Estrutura em YAML + Tools em Código

```yaml
# agents/analista.yaml
name: analista_dados
instruction: |
  Analise dados e gere insights.
  Use ferramentas disponíveis para processar dados.
```

```python
# src/agents/analista/tools.py
@tool
def query_bigquery(sql: str):
    # Código complexo de acesso ao BigQuery
    pass

@tool
def gerar_grafico(dados: list):
    # Geração de visualização
    pass
```

**Ideal para:**
- Times mistos (PMs editam YAML, Devs mantêm tools)
- Projetos onde instruções mudam frequentemente
- Tools reutilizáveis entre múltiplos agentes

---

## 📊 Matriz de Decisão

```
Precisa de integração com API interna?
├── SIM → CÓDIGO
└── NÃO → 
    Precisa de lógica condicional complexa?
    ├── SIM → CÓDIGO
    └── NÃO →
        É perguntar/responder com instruções?
        ├── SIM → YAML
        └── NÃO →
            É orquestração multi-agent?
            ├── SIM → YAML
            └── NÃO → Analisar caso a caso
```

---

## 💡 Exemplos Práticos

### Cenário 1: Agente de Vendas Simples
**Escolha:** YAML ✅
```yaml
name: vendedor
instruction: |
  Você é um vendedor. Apresente nossos produtos.
tools:
  - google_search  # Para pesquisar concorrência
```

### Cenário 2: Agente de Vendas com CRM
**Escolha:** CÓDIGO 🔧
```python
@tool
def consultar_oportunidades(vendedor_id: str):
    # Integração com Salesforce
    pass

agent = LlmAgent(
    tools=[consultar_oportunidades, gerar_proposta]
)
```

### Cenário 3: Suporte Técnico com KB
**Escolha:** HÍBRIDO 🔄
```yaml
# YAML: comportamento
name: suporte
instruction: |
  Consulte a base de conhecimento antes de responder.
```

```python
# CÓDIGO: integração
@tool
def consultar_kb(problema: str):
    # Query no Elasticsearch/Algolia
    pass
```

---

## 🚀 Workflow Recomendado

### Fase 1: Comece com YAML (Dia 1)
```bash
eab create agent novo --type llm
# Edite o YAML e teste
```

### Fase 2: Adicione Tools quando necessário (Semana 1)
```bash
# Crie tool customizada
vim src/agents/novo/tools.py

# Registre no agente
vim src/agents/novo/agent.py
```

### Fase 3: Refatore para código se crescer (Mês 2+)
- YAML → Python quando a lógica ficar complexa
- Mantenha YAML para instruções que mudam frequentemente

---

## 🎯 Regra de Ouro

> **"Se você precisa abrir um IDE para entender o que o agente faz,
> use YAML. Se precisa de imports, classes e lógica, use código."**

---

## Checklist Final

Antes de escolher, pergunte:

- [ ] Precisa acessar banco de dados interno? → CÓDIGO
- [ ] Precisa chamar API proprietária? → CÓDIGO  
- [ ] Tem regras de negócio não-triviais? → CÓDIGO
- [ ] Precisa de bibliotecas específicas? → CÓDIGO
- [ ] É apenas comportamento + tools prontas? → YAML
- [ ] Instruções mudam frequentemente? → YAML
- [ ] PM/Analista precisa editar sem dev? → YAML

---

**Dúvida? Comece com YAML. Migre para código só quando necessário.**
