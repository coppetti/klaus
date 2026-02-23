# 🏗️ Diagrama de Arquitetura - Visão Geral

## Arquitetura de Alto Nível

```mermaid
graph TB
    subgraph "External Layer"
        BIBHA["🤖 Bibha.ai<br/>Orchestration"]
        USER["👤 User<br/>Web/Mobile/WhatsApp"]
        API["🔌 External APIs"]
    end

    subgraph "Easy Agent Builder"
        direction TB
        
        subgraph "Interface Layer"
            ADAPTER["📡 Bibha Adapter<br/>FastAPI + Circuit Breaker"]
            CLI["💻 CLI<br/>eab create | eab deploy"]
        end
        
        subgraph "Core Framework"
            REGISTRY["📋 Agent Registry<br/>Discovery & Metadata"]
            ORCH["🔄 Orchestration<br/>Router | Sequential | Parallel"]
            ULTRA["⚡ Ultra Low-Code<br/>YAML Engine"]
            CB["🛡️ Circuit Breaker<br/>Fault Tolerance"]
        end
        
        subgraph "Agent Types"
            YAML_AGENTS["📝 YAML Agents<br/>80% use cases"]
            PY_AGENTS["🐍 Python Agents<br/>20% use cases"]
            HYBRID["🔗 Hybrid<br/>YAML + Python Tools"]
        end
    end

    subgraph "Google Cloud Platform"
        VERTEX["☁️ Vertex AI<br/>Agent Engine"]
        RUN["🚀 Cloud Run<br/>Containerized Agents"]
        STORAGE["💾 Cloud Storage<br/>Artifacts"]
        BQ["📊 BigQuery<br/>Analytics"]
    end

    subgraph "Memory & State"
        REDIS["⚡ Redis<br/>Session Store"]
        SQLITE["🗄️ SQLite<br/>Local Memory"]
    end

    %% Flows
    USER --> BIBHA
    BIBHA --> ADAPTER
    ADAPTER --> CB
    CB --> ORCH
    ORCH --> REGISTRY
    
    REGISTRY --> YAML_AGENTS
    REGISTRY --> PY_AGENTS
    REGISTRY --> HYBRID
    
    ULTRA --> YAML_AGENTS
    CLI --> REGISTRY
    CLI --> VERTEX
    CLI --> RUN
    
    ORCH --> VERTEX
    ORCH --> RUN
    
    VERTEX --> STORAGE
    VERTEX --> BQ
    RUN --> REDIS
    ADAPTER --> REDIS
    ADAPTER --> SQLITE

    style BIBHA fill:#e1f5ff
    style VERTEX fill:#e8f5e9
    style CB fill:#fff3e0
    style ULTRA fill:#f3e5f5
```

## Legenda

| Componente | Descrição |
|------------|-----------|
| **Bibha.ai** | Orquestração externa no-code/low-code |
| **Bibha Adapter** | API FastAPI com Circuit Breaker para integração |
| **Agent Registry** | Descoberta e metadados de agentes |
| **Orchestration** | Padrões: Router, Sequential, Parallel, Loop |
| **Ultra Low-Code** | Engine YAML com validação Pydantic |
| **Circuit Breaker** | Proteção contra falhas em cascata |
| **Vertex AI** | Deploy gerenciado na GCP |

---

## Fluxo de Requisição

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant B as Bibha.ai
    participant A as Adapter API
    participant CB as Circuit Breaker
    participant O as Orchestrator
    participant G as GCP Agent Engine
    participant R as Redis

    U->>B: Envia mensagem
    B->>A: POST /api/v1/prediction
    
    alt Circuit Closed
        A->>CB: Call external service
        CB->>O: Process request
        O->>G: Execute agent
        G-->>O: Response
        O-->>CB: Result
        CB-->>A: Success
        A-->>B: JSON response
        B-->>U: Display message
    else Circuit Open
        A->>CB: Call external service
        CB-->>A: CircuitBreakerOpen
        A->>A: Execute fallback
        A-->>B: Fallback response
        B-->>U: "Serviço temporariamente indisponível"
    end

    Note over A,R: Session Management
    A->>R: Get/Update session
```
