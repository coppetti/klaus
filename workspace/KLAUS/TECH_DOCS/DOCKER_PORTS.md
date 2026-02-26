# Docker e Portas

## Resumo das Portas

| Serviço | Porta Interna | Porta Dev | Porta Release | Descrição |
|---------|---------------|-----------|---------------|-----------|
| Kimi Agent | 8080 | 7070 | 2019 | Core LLM API |
| Web UI | 8082 | 7072 | 2049 | Interface web |
| Telegram | - | - | - | Polling (sem porta) |

---

## Configuração Docker Compose

### Dev (`docker/docker-compose.yml`)
```yaml
kimi-agent:
  ports:
    - "7070:8080"  # Host:Container

web-ui:
  ports:
    - "7072:8082"
```

### Release (`release/Klaus_v1/docker/docker-compose.yml`)
```yaml
kimi-agent:
  ports:
    - "2019:8080"  # Blade Runner theme

web-ui:
  ports:
    - "2049:8082"  # Blade Runner 2049
```

---

## Volumes e Permissões

### Kimi Agent (Full Access)
```yaml
volumes:
  # Full workspace access (rw) - para marketing/docs
  - ../workspace:/app/workspace:rw
  - ../docs:/app/docs:rw
  # Core modules (ro)
  - ../core:/app/core:ro
```

**Por que rw em docs?**
- Permite salvar materiais de marketing
- Geração de documentação automática
- Acesso a templates

### Web UI
```yaml
volumes:
  # Workspace para persistência
  - ../workspace:/app/workspace:rw
  - ../init.yaml:/app/init.yaml:ro
  - ../core:/app/core:ro
  - ../templates:/app/templates:ro
```

---

## Comandos Docker Essenciais

### Build com cache
```bash
cd docker
docker compose build web-ui
docker compose up -d web-ui
```

### Build sem cache (SEMPRE use para CSS/JS)
```bash
cd docker
docker compose build --no-cache web-ui
docker compose up -d web-ui
```

### Ver logs
```bash
docker compose logs -f web-ui
docker compose logs -f kimi-agent
```

### Restart serviço
```bash
docker compose restart web-ui
```

### Parar tudo
```bash
docker compose down
```

### Parar e remover volumes (CUIDADO)
```bash
docker compose down -v
```

---

## Rebuild Obrigatório

**Sempre** faça rebuild sem cache quando:
- ✅ Mudar CSS (`themes.css`)
- ✅ Mudar templates HTML
- ✅ Mudar JavaScript inline
- ✅ Adicionar nova dependência pip

**Não precisa** rebuild quando:
- ❌ Mudar código Python (hot reload)
- ❌ Mudar dados em `workspace/`
- ❌ Mudar config em `.env`

---

## Healthchecks

### Kimi Agent
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Web UI
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8082/health').read()"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

## Troubleshooting Docker

### Container não sobe
```bash
# Ver erro
docker compose logs web-ui

# Verificar se porta está em uso
lsof -i :7072

# Matar processo na porta
kill -9 <PID>
```

### CSS não atualizou
```bash
# Forçar rebuild sem cache
docker compose build --no-cache web-ui
docker compose up -d web-ui

# Verificar se arquivo foi copiado
docker compose exec web-ui cat /app/static/themes.css | head
```

### Permissão negada em workspace
```bash
# Verificar ownership
ls -la workspace/

# Fixar (se necessário)
sudo chown -R $USER:$USER workspace/
```

---

**Próximo:** [CHECKLIST_CHANGES.md](CHECKLIST_CHANGES.md) - Checklist para mudanças
