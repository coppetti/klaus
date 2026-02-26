# Task List - Correções Pendentes
> Criado em: 2026-02-26  
> Status: Aguardando execução

---

## 🔴 PRIORIDADE 1: Correções Críticas

### [ ] 1. Corrigir a cagada do Klaus com o anthropic
**Problema:** Telegram bot está crashando com `ModuleNotFoundError: No module named 'anthropic'`

**Causa raiz:** 
- `core/providers/kimi_provider.py` importa `from anthropic import Anthropic` (linha 8)
- `docker/Dockerfile` não instala a dependência `anthropic`
- Resultado: Container do Telegram não inicia

**Possíveis soluções:**
- Opção A: Adicionar `anthropic>=0.8.0` ao `Dockerfile` (RUN pip install)
- Opção B: Adicionar ao `requirements.txt` (descomentar linha existente)
- Opção C: Tornar o import opcional (try/except) se anthropic não for obrigatório

**Arquivos envolvidos:**
- `docker/Dockerfile`
- `requirements.txt` 
- `core/providers/kimi_provider.py`

**Teste após correção:**
```bash
docker compose -f docker/docker-compose.yml build telegram-bot
docker compose -f docker/docker-compose.yml up -d telegram-bot
docker logs KLAUS_MAIN_telegram  # Deve iniciar sem erro
```

---

### [ ] 2. Verificar mensagens do bot e comandos do Telegram
**Contexto:** As mensagens podem estar desatualizadas ou sem o branding correto (2077)

**Itens para verificar:**
- [ ] Mensagem `/start` - Deve ter branding 2077?
- [ ] Mensagem `/help` - Comandos estão corretos?
- [ ] Mensagens de erro - Estão amigáveis?
- [ ] Referências a portas - Estão mostrando 7070/7072 (DEV) ou 2013/2077 (RELEASE)?
- [ ] Nome do agente - Está dinâmico (lendo SOUL.md) ou hardcoded?

**Arquivo a verificar:**
- `bot/telegram_bot.py` (funções: `start_command`, `help_command`, etc.) >>/Users/matheussilveira/Documents/CODE/klaus/release/20260225_v2_1_1 deve ter uma implementacao funcional ou /Users/matheussilveira/Documents/CODE/klaus/release/20260224-v2_1

**Nota:** Antes havia uma feature branch (`feature/telegram-dynamic-identity`) que adicionava leitura dinâmica do SOUL.md, mas foi deletada. Avaliar se reimplementar ou manter simplificado.

---

### [ ] 6. Configurar Membership Tiers no Ko-fi
**Status:** Aguardando  
**Contexto:** Página Ko-fi criada, faltam tiers de doação mensal

**Tiers a configurar:**
- **Tyrell Employee** — $5/month (baseline, coffee fund)
- **Blade Runner** — $25/month (priority support, roadmap vote)
- **Tyrell Executive** — $100/month (1:1 consultation, early access)

**Benefícios detalhados:** Ver `workspace/KLAUS/CONTENT/KOFI_SETUP_GUIDE.md`

**Arquivo:** Configuração direta no site ko-fi.com/klaus_ai

---

## 🟡 PRIORIDADE 2: Prevenção de Cagadas

### [ ] 3. Mais testes para evitar o Klaus de fuder com tudo denovo

**Problema:** Mudanças foram feitas sem testar antes do deploy

**Soluções propostas:**

#### 3.1 Script de Teste Pré-Deploy
Criar `scripts/pre_deploy_check.sh` que verifica:
- [ ] Containers constroem sem erro (`docker compose build`)
- [ ] Containers iniciam e ficam healthy (`docker compose up -d` + healthcheck)
- [ ] Portas respondem corretamente (7070, 7072)
- [ ] Telegram bot inicia sem crash
- [ ] Web UI responde com 200 OK

#### 3.2 Testes de Import
Verificar se todos os imports em `core/` estão satisfeitos:
```python
# scripts/test_imports.py
import sys

def test_imports():
    try:
        from core.providers import create_provider
        from core.memory import MemoryStore
        from core.hybrid_memory import HybridMemoryStore
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
```

#### 3.3 CI/CD Local (Git Hooks)
Pre-commit hook que:
- [ ] Valida sintaxe Python de todos os arquivos modificados
- [ ] Verifica se Dockerfile pode buildar
- [ ] Roda testes básicos

#### 3.4 Checklist de Deploy
Arquivo `DEPLOY_CHECKLIST.md`:
- [ ] Criar feature branch
- [ ] Fazer alterações
- [ ] Testar localmente (./scripts/test_local.sh)
- [ ] Merge para main
- [ ] Testar na main
- [ ] Solicitar autorização para push
- [ ] Deploy

---

## 🟢 PRIORIDADE 3: Correções de Documentação

### [x] 5. Correções no README.md ✅ COMPLETO

**Problemas corrigidos:**
- [x] **"Rachel" → "Rachael"**: Nome da replicante corrigido
- [x] **Referência a "cloud AI"**: Mudado para "OpenClaw agents that touch your entire system"
- [x] **Remover seção "The Future"**: Seção 2099 removida
- [x] **Remover referência "42"**: Referência removida

**Arquivo:** `README.md`

---

## ✅ MIGRAÇÃO DE MARKETING COMPLETA

### Status: CONCLUÍDO ✅

**Data:** 2026-02-26  
**Localização:** `/workspace/KLAUS/`  
**Tema:** Blade Runner (2019/2049)

---

### 📁 Arquivos Criados

| Arquivo | Descrição |
|---------|-----------|
| `INDEX.md` | Hub central do projeto KLAUS |
| `BRANDING/BLADE_RUNNER_BRAND_GUIDELINES.md` | Guia completo de marca |
| `BRANDING/BLADE_RUNNER_EASTER_EGGS.md` | Guia de Easter eggs |
| `CONTENT/VOICE_GUIDELINES.md` | Diretrizes de tom de voz |
| `CONTENT/CONTENT_STRATEGY.md` | Estratégia de conteúdo |
| `CONTENT/CONTENT_CALENDAR.md` | Calendário de 30 dias |
| `CONTENT/SOCIAL/linkedin_posts.md` | 5 posts para LinkedIn |
| `STRATEGY/LAUNCH_PLAN.md` | Plano de lançamento |
| `STRATEGY/POSITIONING.md` | Posicionamento da marca |

---

### 🎨 Portas e Branding

- **2019** — Agent (Blade Runner original)
- **2049** — Web UI (Blade Runner 2049)
- **2099** — Reservado para expansão futura

### 🎭 Temas de UI

1. **Deckard** — Noir clássico
2. **Rachael** — Elegância corporativa
3. **Gaff** — Artista urbano

### 📱 Landing Page
- Local: `/docs/index.html` e `/docs/landing-page.html`
- Comutação de tema via botão Voight-Kampff
- Contador interativo 2019 → 2049 → ???

---

## 📝 Notas para o Futuro

### Workflow Git Correto (APRENDER DE UMA VEZ)
```bash
# 1. NUNCA commite direto na main
git checkout -b feature/nome-da-feature

# 2. Faça as alterações
# ... edite arquivos ...

# 3. Commit na branch
git add .
git commit -m "feat: descrição"

# 4. TESTE TUDO antes de merge
./scripts/test_local.sh  # ou manualmente

# 5. Merge para main
git checkout main
git merge feature/nome-da-feature

# 6. Teste novamente na main
./scripts/test_local.sh

# 7. SÓ DEPOIS DA AUTORIZAÇÃO DO USUÁRIO:
# git push origin main
```

### Regra de Ouro
**SEMPRE TESTAR ANTES DE DIZER QUE ESTÁ PRONTO**

---

## 🚫 O QUE NÃO FAZER

- ❌ Commitar direto na main
- ❌ Fazer push sem autorização explícita do usuário
- ❌ Sugerir código sem entender o problema completo
- ❌ Modificar múltiplos arquivos sem testar entre cada um
- ❌ Ignorar erros de build
- ❌ Assumir que "vai funcionar"

---

## 🟢 PRIORIDADE 3: Correções de Documentação

### [ ] 4. Corrigir referência ao Memory Graph Explorer no README

**Problema:** O README.md atual menciona:
```
Visualize your memories at http://localhost:2049/memory-graph
```

**Realidade:** O Memory Graph é uma **aba** dentro da Web UI, não uma URL separada.

**Correção necessária:**
- Remover a URL `http://localhost:2049/memory-graph`
- Substituir por: "Access the Memory Graph tab in the Web UI"
- Ou: "Navigate to the Memory Graph section in the left sidebar"

**Arquivo:** `README.md` (linha referente ao Memory Graph Explorer)

**Nota:** A funcionalidade existe, mas a forma de acessar está documentada incorretamente.

---

*Lista criada após incidente em 2026-02-26*  
*Próxima ação: Executar item 1 quando autorizado*
