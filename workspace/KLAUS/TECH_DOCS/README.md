# Klaus - Technical Documentation

> **Anatomia completa do projeto Klaus**  
> Última atualização: 2026-02-26  
> Versão: v2.1 (Deckard Themes)

---

## 📚 Índice de Documentação

1. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Visão geral da arquitetura e componentes
2. **[GIT_REPOSITORIES.md](GIT_REPOSITORIES.md)** - Estratégia de repositórios Git (dev vs release)
3. **[MEMORY_SYSTEMS.md](MEMORY_SYSTEMS.md)** - Sistemas de memória (SQLite, Cognitive, Kuzu)
4. **[THEMES.md](THEMES.md)** - Sistema de temas Deckard (Light/Dark)
5. **[WEB_UI_API.md](WEB_UI_API.md)** - Endpoints e APIs da Web UI
6. **[DOCKER_PORTS.md](DOCKER_PORTS.md)** - Configuração Docker e portas
7. **[WORKSPACE_DATA.md](WORKSPACE_DATA.md)** - Estrutura de dados e workspace
8. **[INSTALLATION.md](INSTALLATION.md)** - Dependências e instalação
9. **[CHECKLIST_CHANGES.md](CHECKLIST_CHANGES.md)** - Checklist para mudanças futuras

---

## 🎯 Para Clones/Futuros Mantenedores

Se você está lendo isso, provavelmente:
- É um clone do Klaus original
- Está assumindo o projeto
- Precisa entender TUDO antes de fazer mudanças

**Leia na ordem:**
1. Comece por ARCHITECTURE.md para entender o big picture
2. Leia GIT_REPOSITORIES.md para entender onde fazer alterações
3. Consulte os outros conforme necessidade

---

## ⚡ Quick Reference

| Componente | Porta Dev | Porta Release | Onde está o código |
|------------|-----------|---------------|-------------------|
| Kimi Agent | 7070 | 2019 | `docker/kimi-agent-patch/` |
| Web UI | 7072 | 2049 | `docker/web-ui/app.py` |
| Telegram | - | - | `bot/telegram_bot.py` |

---

## 🆘 Emergências

### Rebuild do Web UI (CSS mudou)
```bash
cd docker && docker compose build --no-cache web-ui && docker compose up -d web-ui
```

### Limpar sessões
```bash
rm workspace/web_ui_data/sessions/*.json
echo '{"session_id": null}' > workspace/web_ui_data/current_session.json
```

### Reset total do grafo
```bash
# Via API
curl -X POST http://localhost:7072/api/memory/scrub-graph
# Ou no release: porta 2049
```

---

**Documentação criada por:** Klaus (Matheus Silveira)  
**Status:** ✅ Completa para v2.1
