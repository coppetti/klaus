# 🚀 Easy Agent Builder

> Build and deploy AI agents in minutes, not weeks.

## 🎯 Vision

**Low-code agent building framework for Google Cloud Platform (GCP) using Google's Agent Development Kit (ADK).**

- **Ultra Low-Code**: Create agents with just YAML (no code)
- **Full Code**: Python when you need complex logic
- **Hybrid**: Best of both worlds
- **GCP Native**: Vertex AI, Cloud Run, Agent Engine
- **External Integration**: Ready for Bibha.ai and other platforms

---

## 🏗️ Architecture

### Quick Overview

```
┌─────────────────────────────────────────────────────────────┐
│  External Interface (Bibha.ai / API / CLI)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  Easy Agent Builder Framework                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   Router    │ │  Sequential │ │   Parallel  │           │
│  │   Agent     │ │  Workflows  │ │  Workflows  │           │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘           │
│         └───────────────┴───────────────┘                   │
│                         │                                   │
│              ┌──────────┴──────────┐                       │
│              ▼                     ▼                       │
│  ┌─────────────────┐  ┌─────────────────┐                 │
│  │ Specialized     │  │ Specialized     │                 │
│  │ Agent A         │  │ Agent B         │  ...            │
│  │ (RAG/Search)    │  │ (API/DB)        │                 │
│  └─────────────────┘  └─────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  GCP - Vertex AI Agent Engine                               │
└─────────────────────────────────────────────────────────────┘
```

### 📚 Documentation

**User Guides:**
- [Quick Start Guide](docs/userguide/01-quick-start.md) - Get running in 5 minutes
- [Complete User Guide](docs/userguide/02-complete-guide.md) - Comprehensive documentation

**Business Documentation:**
- [Executive Summary](docs/go-to-market/01-executive-summary.md) - For decision makers
- [Business Guide](docs/go-to-market/02-business-guide.md) - ROI and business case

**Architecture Diagrams:**
- [System Overview](docs/diagrams/01-architecture-overview.md) - High-level design
- [Circuit Breaker](docs/diagrams/02-circuit-breaker-flow.md) - Fault tolerance
- [Agent Types](docs/diagrams/03-agent-types-hierarchy.md) - Three complexity levels
- [Testing Strategy](docs/diagrams/04-testing-pyramid.md) - Test architecture
- [Deployment](docs/diagrams/05-deployment-pipeline.md) - CI/CD workflows
- [Bibha Integration](docs/diagrams/06-bibha-integration-detail.md) - Platform integration

**Export diagrams:**
```bash
cd docs/diagrams
./export-diagrams.sh  # Export to PNG/SVG
./export-diagrams-pdf.sh  # Export to PDF
```

---

## 🚀 Quick Start (2 Minutes)

### Prerequisites
- Python 3.11+
- Google Cloud account with Vertex AI enabled
- `GOOGLE_CLOUD_PROJECT` configured

### Installation

```bash
# Clone
git clone https://github.com/ai-solutions/easy-agent-builder.git
cd easy-agent-builder

# Install
pip install -e ".[dev]"
```

### 1. Create an Agent (YAML - Ultra Low-Code)

```bash
# Create agent
eab create agent my_assistant --type llm

# Edit YAML
vim agents/my_assistant.yaml
```

```yaml
# agents/my_assistant.yaml
name: my_assistant
type: llm
model: gemini-2.0-flash-exp

description: A friendly virtual assistant

instruction: |
  You are a helpful virtual assistant.
  Always respond in a professional and friendly tone.

tools:
  - google_search

temperature: 0.7
```

### 2. Test Locally

```bash
# Validate
eab validate agents/my_assistant.yaml

# Run interactively
eab run agents/my_assistant.yaml
```

### 3. Deploy to GCP

```bash
# Deploy to Cloud Run
eab deploy --env production --agent my_assistant

# Or deploy all agents
eab deploy --env production --all
```

---

## 📁 Project Structure

```
easy_agent_builder/
│
├── 📦 Core Framework
│   └── src/agent_builder/
│       ├── __init__.py              # Main exports
│       ├── cli.py                   # CLI: eab create, eab deploy
│       ├── registry.py              # Agent registry & discovery
│       ├── orchestration.py         # Workflow patterns
│       ├── deployer.py              # GCP deployment
│       ├── ultra_lowcode.py         # YAML engine
│       ├── circuit_breaker.py       # 🛡️ Fault tolerance
│       ├── bibha_adapter_real.py    # Bibha.ai integration
│       └── integration_abstract.py  # Base for external integrations
│
├── 🤖 Agents
│   ├── agents/                      # YAML agents (no-code)
│   │   ├── my_assistant.yaml
│   │   ├── router_attendance.yaml
│   │   └── sales_agent.yaml
│   └── src/agents/                  # Python agents (code)
│       └── root_agent.py
│
├── ⚙️ Configuration
│   ├── config/
│   │   ├── agents.yaml              # Declarative definitions
│   │   └── deployment.yaml          # GCP config
│   └── .env                         # Environment variables
│
├── 📚 Examples
│   └── examples/
│       ├── 01_basic_agent.py
│       ├── 02_router_pattern.py
│       ├── 03_sequential_workflow.py
│       ├── 04_parallel_workflow.py
│       └── 10_bibha_integration_real.py
│
├── 🧪 Tests
│   └── tests/
│       ├── unit/                    # Unit tests
│       │   ├── test_circuit_breaker.py
│       │   └── test_ultra_lowcode.py
│       ├── integration/             # Integration tests
│       │   └── test_bibha_adapter.py
│       ├── load/                    # Load tests (Locust)
│       │   └── test_adapter_load.py
│       └── fixtures/                # Test data
│           ├── agents/
│           └── responses/
│
├── 🚀 Deployment
│   ├── deployment/
│   │   ├── Dockerfile
│   │   ├── cloudbuild.yaml          # CI/CD pipeline
│   │   └── terraform/               # IaC (future)
│   └── setup_test.sh                # Automated setup
│
└── 📖 Documentation
    ├── README.md                    # This file
    ├── QUICKSTART.md                # Quick start guide
    ├── ARCHITECTURE.md              # Architecture details
    ├── BIBHA_INTEGRATION.md         # Bibha.ai integration
    └── ULTRA_LOWCODE_GUIDE.md       # YAML-only guide
```

---

## 🎨 Three Levels of Complexity

### Level 1: YAML Only (80% of cases)
```yaml
# agents/simple_bot.yaml
name: simple_bot
type: llm
instruction: Be helpful and friendly
tools: [google_search]
```
**Time:** 2 minutes | **Code:** 0 lines

### Level 2: Hybrid (15% of cases)
```yaml
# YAML for behavior
tools: [google_search, query_crm]
```
```python
# Python for custom tools
@tool
def query_crm(customer_id: str):
    return requests.get(f"https://api.company.com/crm/{customer_id}").json()
```
**Time:** 10 minutes | **Use:** Custom integrations

### Level 3: Full Code (5% of cases)
```python
# Complete Python implementation
@tool
def complex_business_logic(...):
    # Complex calculations
    pass

agent = LlmAgent(tools=[complex_business_logic, ...])
```
**Time:** 30 minutes | **Use:** Complex workflows

---

## 🔌 Integration with Bibha.ai

Bibha.ai serves as the external orchestrator handling multi-channel (WhatsApp, Web, Phone).

### Setup

```bash
# Deploy adapter
gcloud run deploy bibha-adapter \
  --set-env-vars BIBHA_API_KEY=bah-sk-xxx \
  --set-env-vars BIBHA_API_HOST=https://your-instance.bibha.ai
```

### Configure HTTP Tool in Bibha
```
Name: ADK Agent Bridge
Method: POST
URL: https://your-adapter.run.app/api/v1/prediction/{chatflowId}
Body: {
  "question": "{{user_message}}",
  "sessionId": "{{session_id}}",
  "chatflowId": "{{chatflow_id}}"
}
```

See [BIBHA_INTEGRATION.md](docs/BIBHA_INTEGRATION.md) for complete setup.

---

## 🛠️ CLI Reference

```bash
# Create components
eab create agent <name> [--type llm|router|workflow] [--code]
eab create workflow <name> [--type sequential|parallel|loop]
eab create tool <name>

# Development
eab validate <yaml>              # Validate YAML configuration
eab compile <yaml>               # Generate Python code
eab run <yaml>                   # Run agent interactively
eab test <agent> [--interactive] # Test agent

# Deployment
eab deploy [--env staging|prod] [--agent <name>|--all]
eab status                       # Deployment status
eab logs <agent>                 # View logs

# Management
eab list                         # List all agents
eab describe <agent>             # Agent details
```

---

## 🔧 Environment Variables

```bash
# GCP Configuration
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

# Bibha.ai Integration
export BIBHA_API_KEY=bah-sk-your-key
export BIBHA_API_HOST=https://your-instance.bibha.ai
export BIBHA_CHATFLOW_ID=your-chatflow-id

# Application
export ENVIRONMENT=development
export LOG_LEVEL=INFO
```

---

## 🧪 Testing & CI/CD

### Run Tests Locally
```bash
# All tests
./run_tests.sh all

# Unit tests only
./run_tests.sh unit

# With coverage
./run_tests.sh coverage

# CI mode (with coverage check)
./run_tests.sh ci

# Load tests
./run_tests.sh load

# Or use pytest directly
pytest tests/unit -v
pytest tests/integration -v
pytest tests/ --cov=agent_builder --cov-report=html
```

### CI/CD Pipeline
See [CI/CD Test Guide](CI_CD_TEST_GUIDE.md) for detailed information about continuous integration and deployment.
```

### CI/CD Pipeline (Cloud Build)
```bash
# Automatic on git push:
# 1. Lint (black, ruff)
# 2. Type check (mypy)
# 3. Run tests (pytest)
# 4. Build Docker image
# 5. Deploy to Cloud Run
# 6. Integration tests
```

---

## 📊 Cost Estimates (GCP)

| Component | Monthly Cost (Estimated) |
|-----------|-------------------------|
| Cloud Run (idle) | $0 |
| Cloud Run (1M requests) | ~$0 (free tier) |
| Vertex AI API | ~$0.50-2.00 per 1M tokens |
| Cloud Build | ~$10-50 |
| **Total** | **~$20-100** for moderate usage |

**Free tier:** $300 credits for 90 days.

---

## 🤝 Contributing

1. Fork the project
2. Create your branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -am 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🆘 Support

- **Documentation**: See `docs/` folder
- **Issues**: GitHub Issues
- **Email**: support@ai-solutions.com

---

<p align="center">
  <strong>Built with ❤️ by AI Solutions Architect</strong><br>
  <em>Empowering enterprises with intelligent agents</em>
</p>
