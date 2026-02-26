# 🚀 Deploy Checklist - CI/CD Discipline

**NUNCA deployar sem completar todos os itens.**

---

## Pre-Deploy (Local)

### 1. Testes Automatizados
- [ ] Rodar `pytest tests/unit/` - deve passar 100%
- [ ] Verificar se não há imports quebrados
- [ ] Verificar se não há variáveis não definidas

### 2. Testes Manuais Locais
- [ ] Subir ambiente local (`./scripts/start-services.sh`)
- [ ] Testar: http://localhost:7070/health (API)
- [ ] Testar: http://localhost:7072/health (Web UI)
- [ ] Testar: Login/chat básico funciona
- [ ] Testar: Memory graph carrega (mesmo que vazio)
- [ ] Testar: Settings panel abre

### 3. Visual/UX
- [ ] UI não quebrou (cores, layout, fontes)
- [ ] Não há erros de console no navegador
- [ ] Responsividade ok (mobile/desktop)

### 4. Dados e Config
- [ ] `.env.example` atualizado se necessário
- [ ] Não há secrets hardcoded
- [ ] Não há dados de usuário no commit

---

## Deploy (Release)

### 5. Build
- [ ] `docker compose build` sem erros
- [ ] Container sobe sem crash
- [ ] Portas configuradas corretamente

### 6. Validação Final
- [ ] Testar endpoints no release
- [ ] Verificar logs por erros
- [ ] Confirmar versão correta

---

## 🚨 Se algo falhar

**STOP. NÃO DEPLOYAR.**

1. Reverter mudanças
2. Corrigir problema localmente
3. Recomeçar checklist do zero

---

**Disciplina: Testar primeiro. Deployar só quando 100%.**
