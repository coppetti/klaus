# Guia de Deployment

## Visão Geral

O Easy Agent Builder suporta múltiplas estratégias de deployment em GCP:

1. **Vertex AI Agent Engine** - Runtime gerenciado para agentes
2. **Cloud Run** - Containers serverless para APIs HTTP
3. **Cloud Functions** - Para triggers simples (futuro)

---

## Pré-requisitos

### 1. Configurar Projeto GCP

```bash
# Definir projeto
gcloud config set project SEU_PROJETO

# Habilitar APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### 2. Criar Bucket de Staging

```bash
export BUCKET_NAME=${GOOGLE_CLOUD_PROJECT}-agent-staging

gsutil mb -l us-central1 gs://${BUCKET_NAME}
```

### 3. Criar Repositório Docker

```bash
gcloud artifacts repositories create agent-builder \
    --repository-format=docker \
    --location=us-central1
```

### 4. Configurar Service Account

```bash
# Criar service account
gcloud iam service-accounts create agent-builder \
    --display-name="Easy Agent Builder"

# Grant permissions
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} \
    --member="serviceAccount:agent-builder@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} \
    --member="serviceAccount:agent-builder@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"
```

---

## Deployment para Vertex AI Agent Engine

### Via CLI

```bash
# Configurar ambiente
export GOOGLE_CLOUD_PROJECT=seu-projeto
export GOOGLE_CLOUD_LOCATION=us-central1
export VERTEX_AI_STAGING_BUCKET=gs://seu-bucket-staging

# Deploy
eab deploy --env production --agent nome_do_agente
```

### Via Python

```python
from agent_builder.deployer import DeploymentConfig, GCPDeployer

config = DeploymentConfig(
    project_id="seu-projeto",
    location="us-central1",
    staging_bucket="gs://seu-bucket-staging",
)

deployer = GCPDeployer(config)
result = deployer.deploy_to_agent_engine(
    agent_module="src.agents.search.agent",
    agent_name="search_agent",
)

print(f"Endpoint: {result.endpoint}")
```

---

## Deployment para Cloud Run

### Via CLI

```bash
# Build e deploy
gcloud builds submit --config deployment/cloudbuild.yaml

# Ou diretamente
gcloud run deploy agent-builder \
    --source . \
    --region us-central1 \
    --allow-unauthenticated
```

### Características

- **Auto-scaling**: 0-N instâncias
- **Cold start**: ~2-3 segundos
- **Concorrência**: Até 1000 requests/instância
- **Timeout**: Até 60 minutos

---

## CI/CD com Cloud Build

### Pipeline

O arquivo `deployment/cloudbuild.yaml` define uma pipeline completa:

1. **Install** - Instala dependências
2. **Lint** - Valida código (black, ruff)
3. **Type Check** - Valida tipos (mypy)
4. **Test** - Executa testes (pytest)
5. **Build** - Constrói imagem Docker
6. **Push** - Envia para Artifact Registry
7. **Deploy** - Atualiza Cloud Run
8. **Integration Test** - Valida deployment

### Trigger

```bash
# Criar trigger para branch main
gcloud builds triggers create github \
    --repo-name=easy-agent-builder \
    --repo-owner=sua-org \
    --branch-pattern="^main$" \
    --build-config=deployment/cloudbuild.yaml
```

---

## Configuração de Ambientes

### Staging

```bash
# Arquivo: config/deployment.staging.yaml
environment: staging
cloud_run:
  min_instances: 0
  max_instances: 5
  memory: 512Mi
```

### Production

```bash
# Arquivo: config/deployment.production.yaml
environment: production
cloud_run:
  min_instances: 1  # Warm instances
  max_instances: 20
  memory: 1Gi
  cpu: 2
```

---

## Integração Bibha.ai

### Configuração

1. **Criar endpoint no Cloud Run**:
```bash
gcloud run deploy agent-bibha \
    --image gcr.io/PROJECT/agent-builder:latest \
    --set-env-vars="BIBHA_API_KEY=seu-key"
```

2. **Configurar HTTP Tool na Bibha**:
   - URL: `https://agent-bibha-xxx.run.app/invoke`
   - Method: POST
   - Headers: `Content-Type: application/json`
   - Body: `{"message": "{{user_message}}", "session_id": "{{session_id}}"}`

3. **Testar**:
```bash
curl -X POST https://agent-bibha-xxx.run.app/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá, qual seu nome?"}'
```

---

## Monitoramento

### Logs

```bash
# Ver logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=agent-builder" --limit=50

# Stream logs
gcloud alpha logging tail "resource.type=cloud_run_revision"
```

### Métricas

```bash
# CPU e Memory
gcloud monitoring metrics list | grep run

# Custom metrics via Cloud Monitoring API
```

### Alertas

Recomendados:
- Error rate > 1%
- Latency p99 > 5s
- Memory usage > 80%

---

## Troubleshooting

### Problema: Agent não inicia

```bash
# Verificar logs
gcloud logging read "resource.labels.service_name=agent-builder" --format="value(textPayload)"

# Testar localmente
docker run -p 8080:8080 gcr.io/PROJECT/agent-builder:latest
```

### Problema: Permissão negada

```bash
# Verificar IAM
gcloud projects get-iam-policy PROJECT_ID \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:agent-builder"
```

### Problema: Timeout

```bash
# Aumentar timeout
gcloud run services update agent-builder \
    --timeout=300s \
    --region=us-central1
```

---

## Custos Estimados

| Componente | Custo Mensal (estimado) |
|------------|------------------------|
| Cloud Run (1M requests) | ~$0 |
| Vertex AI Agent Engine | ~$50-200 |
| Cloud Build | ~$10-50 |
| Artifact Registry | ~$5-20 |

---

## Checklist de Produção

- [ ] Service account configurada com permissões mínimas
- [ ] Secrets gerenciados via Secret Manager
- [ ] HTTPS habilitado (padrão no Cloud Run)
- [ ] Rate limiting configurado
- [ ] Logging estruturado implementado
- [ ] Alertas configurados
- [ ] Backup/recovery testado
- [ ] Documentação de runbooks
- [ ] Testes de carga realizados
