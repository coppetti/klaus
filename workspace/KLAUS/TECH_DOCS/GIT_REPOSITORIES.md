# Estratégia de Repositórios Git

## ⚠️ CRÍTICO: Entenda Isso Antes de Commitar

Klaus usa **DOIS repositórios** para propósitos diferentes. Commitar no lugar errado = caos.

---

## Repositório 1: Principal (Dev)

**Path:** `/Users/matheussilveira/Documents/CODE/klaus`  
**Remote:** `github.com:coppetti/klaus.git`  
**Branch principal:** `main`

### Características
- Tem `.git/` completo (histórico de commits)
- Inclui `workspace/` com dados de desenvolvimento
- Ports: 7070 (Agent), 7072 (Web UI)
- Inclui pasta `release/` (cópia estática)

### Quando usar
- **Desenvolvimento diário**
- Testar novas features
- Debugar problemas
- Rodar testes

### O QUE NÃO DEVE IR AQUI
❌ Dados pessoais do usuário (embora estejam em `.gitignore`)  
❌ Configurações locais (`.env`, `init.yaml`)

---

## Repositório 2: Release (Distribuição)

**Path:** `/Users/matheussilveira/Documents/CODE/klaus/release/Klaus_v1`  
**Remote:** `github.com:coppetti/klaus.git` (MESMO remote!)  
**Branch principal:** `main` (forçado)

### Características
- Código LIMPO para usuários finais
- SEM dados de desenvolvimento
- Ports: 2019 (Agent), 2049 (Web UI)
- SEM pasta `.git` própria (usa a do pai)

### Quando usar
- **Release para produção**
- Zip para download
- Docker image build

### O QUE INCLUI
✅ Código fonte limpo  
✅ Docker configs  
✅ Documentação  
✅ Templates  

### O QUE NÃO INCLUI
❌ `workspace/` (dados do dev)  
❌ `.env` (cada user cria o seu)  
❌ `.pytest_cache/`  
❌ `__pycache__/`  

---

## Fluxo de Trabalho Corretos

### Cenário 1: Nova Feature

```bash
# 1. Trabalhe no principal
cd /Users/matheussilveira/Documents/CODE/klaus

# 2. Faça mudanças nos arquivos
# ... edite docker/web-ui/app.py ...

# 3. Teste localmente (porta 7072)
docker compose up -d web-ui

# 4. Commit no principal
git add .
git commit -m "feat: nova feature X"
git push origin main

# 5. Sincronize o release
cp docker/web-ui/app.py release/Klaus_v1/docker/web-ui/

# 6. Commit no release
cd release/Klaus_v1
git add .
git commit -m "feat: sync nova feature X"
git push --force origin main
```

### Cenário 2: Hotfix Urgente

```bash
# Mesmo processo, mas em ambos os repos
# 1. Fix no principal
# 2. Testa em 7072
# 3. Copia para release
# 4. Commit em ambos
```

---

## Estrutura do Release

```
release/Klaus_v1/
├── README.md              # Documentação usuário
├── QUICKSTART.md          # Guia rápido
├── BOOT.md                # Guia para AI
├── setup.sh               # Script instalação
├── docker/
│   ├── docker-compose.yml # Ports 2019/2049
│   ├── Dockerfile
│   └── web-ui/
│       ├── app.py         # Código Web UI
│       ├── static/
│       │   └── themes.css # Temas Deckard
│       └── templates/
│           └── index.html
├── core/                  # Código core
├── bot/                   # Telegram
├── templates/             # SOUL.md templates
└── docs/                  # Documentação

# NÃO INCLUI:
# ❌ workspace/
# ❌ .env
# ❌ init.yaml
# ❌ .gitignore (usa o do pai)
```

---

## Comparação Direta

| Aspecto | Principal (Dev) | Release |
|---------|-----------------|---------|
| **Porta Agent** | 7070 | 2019 |
| **Porta Web UI** | 7072 | 2049 |
| **Tem workspace/** | ✅ Sim | ❌ Não |
| **Tem dados de teste** | ✅ Sim | ❌ Não |
| **Histórico git** | ✅ Completo | ⚠️ Usa o do pai |
| **Uso** | Desenvolvimento | Produção |

---

## Comandos Úteis

### Sincronizar Release após mudanças

```bash
# Copiar arquivos modificados
cd /Users/matheussilveira/Documents/CODE/klaus
cp README.md QUICKSTART.md BOOT.md release/Klaus_v1/
cp docker/web-ui/static/*.css release/Klaus_v1/docker/web-ui/static/
cp docker/web-ui/templates/*.html release/Klaus_v1/docker/web-ui/templates/

# Rebuild com --no-cache (se CSS mudou)
cd release/Klaus_v1/docker
docker compose build --no-cache web-ui
docker compose up -d web-ui
```

### Verificar estado antes de push

```bash
# No principal
git status
git log --oneline -3

# No release
cd release/Klaus_v1
git status
git log --oneline -3
```

---

## ⚠️ Armadilhas Comuns

### 1. Commitou no release sem testar
**Problema:** Quebrou produção  
**Solução:** Sempre teste no principal (7072) primeiro

### 2. Esqueceu de copiar arquivo para release
**Problema:** Mudança não aparece no release  
**Solução:** Use checklist de sincronização

### 3. Commitou dados do workspace no release
**Problema:** Vazou dados pessoais  
**Solução:** Release NUNCA deve ter `workspace/`

### 4. Push no release sobrou histórico
**Problema:** Divergência de histórico  
**Solução:** Use `git push --force` no release (aceitável lá)

---

## Checklist Antes do Push

### Principal
- [ ] Testado localmente (7072)
- [ ] Testes passando (`pytest`)
- [ ] Sem dados sensíveis no commit

### Release
- [ ] Arquivos copiados do principal
- [ ] Sem pasta `workspace/` no stage
- [ ] Testado com ports 2019/2049
- [ ] `git push --force` (se necessário)

---

**Próximo:** [MEMORY_SYSTEMS.md](MEMORY_SYSTEMS.md) - Sistemas de memória
