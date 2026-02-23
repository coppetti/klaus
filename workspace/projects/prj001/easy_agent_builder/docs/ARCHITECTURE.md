# Architecture Overview

## Executive Summary

**Easy Agent Builder** is a framework for rapidly creating, orchestrating, and deploying AI agents on Google Cloud Platform using Google's Agent Development Kit (ADK).

---

## Core Architecture

### Hub & Spoke with External Orchestration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     EXTERNAL ORCHESTRATION                               │
│                       (Bibha.ai)                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   Chat UI    │  │   Voice AI   │  │  Pipelines   │                  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
│         │                 │                 │                           │
│         └─────────────────┴─────────────────┘                           │
│                         │                                               │
│                    API Gateway                                          │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         GCP - VERTEX AI                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ADK AGENT ENGINE                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │   Router    │  │  Sequential │  │   Parallel  │             │   │
│  │  │   Agent     │  │   Workflow  │  │   Workflow  │             │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │   │
│  │         │                │                │                     │   │
│  │         └────────────────┴────────────────┘                     │   │
│  │                          │                                      │   │
│  │              ┌───────────┴───────────┐                         │   │
│  │              ▼                       ▼                         │   │
│  │  ┌──────────────────┐  ┌──────────────────┐                   │   │
│  │  │ Specialized      │  │ Specialized      │                   │   │
│  │  │ Agent A          │  │ Agent B          │  ...              │   │
│  │  │ (RAG/Search)     │  │ (API/DB)         │                   │   │
│  │  └──────────────────┘  └──────────────────┘                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │  Cloud Storage   │  │   Cloud Run      │  │   BigQuery       │     │
│  │  (Artifacts)     │  │   (Microservices)│  │   (Analytics)    │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Layers

### Layer 1: Interface & External Orchestration (Bibha.ai)

**Role:** Entry point for non-technical users

**Responsibilities:**
- UX/UI (chat, voice)
- High-level conversation management
- Workflow triggers
- Handoff to specialized ADK agents

### Layer 2: API Gateway & Security

**Components:**
- Cloud Endpoints or Apigee
- IAM / API Key authentication
- Rate limiting
- Centralized logging

### Layer 3: ADK Agent Engine (Core)

**Runtime:** Vertex AI Agent Engine

**Orchestration Patterns:**
- **Router Pattern:** Central agent delegating to specialists
- **Sequential:** Deterministic pipelines
- **Parallel:** Concurrent independent tasks
- **Loop:** Iteration until quality criteria met

### Layer 4: Specialized Agents (ADK)

| Agent | Function | Tools |
|-------|----------|-------|
| `search_agent` | RAG / Search | Vertex AI Search, BigQuery |
| `api_agent` | API Integration | OpenAPITool, FunctionTool |
| `data_agent` | Data Analysis | BigQuery, Cloud Storage |
| `code_agent` | Code Generation | Code Execution Tool |
| `validation_agent` | Validation/Review | LLM + business rules |

---

## Three Implementation Approaches

### 1. YAML Only (Ultra Low-Code)

**For:** Product managers, business analysts, rapid prototyping

**Example:**
```yaml
name: support_agent
type: llm
instruction: Be helpful and professional
tools: [google_search]
```

**Time to deploy:** 2 minutes

### 2. Hybrid (YAML + Python)

**For:** Developers needing custom integrations

**YAML:** Defines behavior
**Python:** Implements custom tools

```yaml
# YAML
name: sales_agent
tools: [google_search, query_crm]
```

```python
# Python
@tool
def query_crm(customer_id: str):
    return requests.get(f"https://api.company.com/crm/{customer_id}").json()
```

**Time to deploy:** 10 minutes

### 3. Full Code (Python)

**For:** Complex logic, multi-agent workflows

```python
@tool
def complex_pricing_logic(...):
    # Complex business rules
    pass

agent = SequentialAgent(
    sub_agents=[qualifier, negotiator, closer]
)
```

**Time to deploy:** 30 minutes

---

## Deployment Strategy

### Environments

| Environment | Infrastructure | Purpose |
|-------------|---------------|---------|
| **Dev** | Local + ADK CLI | Development, quick tests |
| **Staging** | Cloud Run | Validation, integration tests |
| **Prod** | Vertex AI Agent Engine | Production, auto-scaling |

### CI/CD Pipeline

```yaml
# cloudbuild.yaml

1. Lint (black, ruff)
2. Type Check (mypy)
3. Unit Tests (pytest)
4. Build Docker Image
5. Push to Artifact Registry
6. Deploy to Cloud Run
7. Integration Tests
```

---

## Integration with External Systems

### Bibha.ai Integration

**Pattern:** Capability Exposure

```python
# ADK Agent exposes capability via API
@fastapi_app.post("/agents/{agent_id}/invoke")
async def invoke_agent(agent_id: str, request: InvokeRequest):
    agent = registry.get(agent_id)
    result = await runner.run(agent, request.input)
    return {"output": result}
```

**Data Flow:**
```
User → Bibha.ai Chat → Intent Classifier → 
    ├─→ Native Bibha capability (small talk)
    └─→ HTTP Call → ADK Agent (complex task) →
        ├─→ Tool Execution (Search/API/DB)
        └─→ Response → Bibha.ai → User
```

---

## Technology Stack

### Core
- **Python 3.11+**
- **Google ADK** (Agent Development Kit)
- **FastAPI** (API layer)
- **Pydantic** (Data validation)

### GCP Services
- **Vertex AI** (LLM, Agent Engine)
- **Cloud Run** (Container deployment)
- **Cloud Build** (CI/CD)
- **Secret Manager** (Credentials)
- **Cloud Storage** (Artifacts)

### External (Optional)
- **Bibha.ai** (Orchestration)
- **Redis** (Session management)

---

## Security Considerations

### Authentication
- API Keys for external access
- IAM for GCP resources
- Service accounts with minimal permissions

### Data Protection
- Secrets in Secret Manager
- Encryption at rest (default GCP)
- VPC Service Controls (optional)

### Compliance
- Audit logs enabled
- Access logs for all API calls
- PII handling in custom tools

---

## Scalability

### Horizontal Scaling
- Cloud Run: Auto-scales 0-N instances
- Vertex AI Agent Engine: Managed scaling
- Stateless design for easy scaling

### Performance Optimization
- Redis for session caching
- Parallel workflows for I/O bound tasks
- Streaming responses for real-time UX

---

## Monitoring & Observability

### Logs
- Cloud Logging (structured JSON)
- Agent execution traces
- Tool call logs

### Metrics
- Request count/latency
- Agent execution time
- Error rates
- Token usage

### Alerting
- Error rate > 1%
- Latency p99 > 5s
- Memory usage > 80%

---

## Cost Optimization

| Component | Optimization Strategy |
|-----------|----------------------|
| Cloud Run | Min instances = 0 (scales to zero) |
| Vertex AI | Use appropriate model size |
| Storage | Lifecycle policies for old artifacts |
| CI/CD | Cache Docker layers |

---

## Anti-Patterns to Avoid

1. ❌ Tight coupling with Bibha (keep APIs clean)
2. ❌ Ignoring evaluation (use ADK eval from start)
3. ❌ Over-engineering (start simple, scale as needed)
4. ❌ Hardcoded secrets (use Secret Manager)
5. ❌ No error handling (implement retries, circuit breakers)

---

## Next Steps

See implementation guides:
- [QUICKSTART.md](../QUICKSTART.md) - Get started in 2 minutes
- [ULTRA_LOWCODE_GUIDE.md](ULTRA_LOWCODE_GUIDE.md) - YAML-only development
- [BIBHA_INTEGRATION.md](BIBHA_INTEGRATION.md) - External orchestration
