# Checklist para Mudanças

Use este checklist antes de qualquer commit ou release.

---

## 🔄 Para Mudanças no Código (Principal)

### Antes de Codar
- [ ] Criei branch? `git checkout -b feat/nome-da-feature`
- [ ] Documentei o plano neste arquivo se for complexo?

### Durante Desenvolvimento
- [ ] Testando na porta 7072 (dev)?
- [ ] Logs limpos (sem erros)?
- [ ] Não commitar dados de `workspace/`?

### Antes do Commit
- [ ] Testes passam? `python -m pytest tests/ -x`
- [ ] Não há secrets no código?
- [ ] Código segue padrões existentes?

### Após Commit no Principal
- [ ] Push para `main`? `git push origin main`
- [ ] CI/CD passou? (GitHub Actions)

---

## 📦 Para Sync com Release

### Copiar Arquivos
```bash
# Do principal para release
cp README.md release/Klaus_v1/
cp QUICKSTART.md release/Klaus_v1/
cp BOOT.md release/Klaus_v1/
cp docker/web-ui/app.py release/Klaus_v1/docker/web-ui/
cp docker/web-ui/static/* release/Klaus_v1/docker/web-ui/static/
cp docker/web-ui/templates/* release/Klaus_v1/docker/web-ui/templates/
```

### Verificar no Release
- [ ] Não copiei pasta `workspace/`?
- [ ] Não copiei `.env`?
- [ ] Não copiei `init.yaml`?

### Testar Release
```bash
cd release/Klaus_v1/docker
docker compose build --no-cache web-ui
docker compose up -d
```

- [ ] Web UI acessível em http://localhost:2049?
- [ ] Toggle de tema funciona?
- [ ] Grafo carrega?
- [ ] Stats mostram dados corretos?

### Commit no Release
```bash
cd release/Klaus_v1
git add -A
git commit -m "sync: vX.Y.Z from main"
git push --force origin main
```

---

## 🎨 Para Mudanças em CSS/Temas

### Obrigatório
- [ ] Rebuild sem cache? `docker compose build --no-cache web-ui`
- [ ] Testar Light mode?
- [ ] Testar Dark mode?
- [ ] Verificar iframe (grafo) pega tema?

### Verificar Cores
- [ ] Backgrounds usando `var(--bg-*)`?
- [ ] Textos usando `var(--text-*)`?
- [ ] Bordas usando `var(--border-*)`?
- [ ] Não há cores hardcoded (#fff, #000)?

---

## 🧠 Para Mudanças em Memória

### Se tocar em Cognitive Memory
- [ ] Backup dos JSON? `cp knowledge_graph.json kg.json.backup`
- [ ] Testar com dados reais?
- [ ] Scrub funciona? `POST /api/memory/scrub-graph`
- [ ] Stats retornam dados?

### Se tocar em SQLite
- [ ] Migration necessária?
- [ ] Schema atualizado?

---

## 🌐 Para Novos Endpoints API

### Implementação
- [ ] Rota adicionada em `app.py`?
- [ ] Documentado nesta pasta?
- [ ] Tratamento de erros?
- [ ] Content-Type correto?

### Teste
```bash
# Testar endpoint
curl http://localhost:7072/api/nova-rota | jq

# Verificar status
curl -I http://localhost:7072/api/nova-rota
```

---

## 🐛 Para Bug Fixes

### Documentação
- [ ] Descrevi o bug nesta pasta?
- [ ] Expliquei a solução?
- [ ] Lista de arquivos modificados?

### Teste
- [ ] Bug não reproduz mais?
- [ ] Não quebrou outras funcionalidades?
- [ ] Teste de regressão passou?

---

## 🚀 Para Release (Deploy)

### Preparação
- [ ] Versão atualizada em `VERSION`?
- [ ] `RELEASE_NOTES.md` atualizado?
- [ ] Tag criada? `git tag vX.Y.Z`

### Teste Final
- [ ] Setup limpo funciona? `./setup.sh`
- [ ] Reset funciona? `./reset.sh`
- [ ] Todos os testes passam?

### Deploy
- [ ] Push tags? `git push --tags`
- [ ] Criar release no GitHub?
- [ ] Anexar zip para download?

---

## 🆘 Emergência (Rollback)

Se algo quebrou em produção:

```bash
# 1. Reverter commit
git revert HEAD

# 2. Ou reset para commit anterior
git reset --hard COMMIT_ANTERIOR

# 3. Push forçado (se necessário)
git push --force origin main

# 4. Rebuild containers
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## 📋 Quick Checklist (Resumido)

**Mudança Simples:**
- [ ] Testar em 7072
- [ ] Commit no principal
- [ ] Push

**Mudança em CSS:**
- [ ] Rebuild --no-cache
- [ ] Testar Light/Dark
- [ ] Verificar iframe
- [ ] Commit + Push

**Novo Release:**
- [ ] Copiar para release/
- [ ] Testar em 2049
- [ ] Commit + Push --force
- [ ] Tag + GitHub Release

---

**Lembrete:** Quando em dúvida, documente nesta pasta antes de implementar.
