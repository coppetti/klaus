# ⚡ Quick Start Guide

> From zero to running agent in **2 minutes**.

---

## Prerequisites (One-time setup)

### 1. Google Cloud Setup

```bash
# Login to Google Cloud
gcloud auth login
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable run.googleapis.com
```

### 2. Install Framework

```bash
# Clone or navigate to project
cd easy_agent_builder

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install
pip install -e ".[dev]"

# Verify installation
eab --version
```

---

## Method 1: Ultra Low-Code (YAML Only) - 2 Minutes

### Step 1: Create Agent

```bash
# Use the included example
cp agents/my_assistant.yaml agents/my_first_agent.yaml

# Or create new
eab create agent my_first_agent --type llm
```

### Step 2: Edit (Optional)

```yaml
# agents/my_first_agent.yaml
name: my_first_agent
type: llm
model: gemini-2.0-flash-exp

description: My first AI assistant

instruction: |
  You are a friendly virtual assistant.
  Always respond in English.
  Be concise but helpful.

tools:
  - google_search

temperature: 0.7
```

### Step 3: Validate

```bash
eab validate agents/my_first_agent.yaml

# Expected output:
# ✅ Configuration valid!
#    Name: my_first_agent
#    Type: llm
#    Model: gemini-2.0-flash-exp
#    Tools: 1
```

### Step 4: Run

```bash
eab run agents/my_first_agent.yaml

# Chat interface starts:
# 🤖 my_first_agent
#    My first AI assistant
#
# Type 'exit' to quit.
#
# You: Hello!
# Agent: Hello! How can I help you today?
```

---

## Method 2: With Custom Code (10 Minutes)

### Step 1: Create with Code Option

```bash
eab create agent sales_agent --type llm --code
```

### Step 2: Add Custom Tool

Edit `src/agents/sales_agent/tools.py`:

```python
from google.adk.tools import tool
import requests

@tool
def query_crm(customer_id: str) -> dict:
    """Query customer data from internal CRM."""
    response = requests.get(f"https://api.company.com/crm/{customer_id}")
    return response.json()

@tool
def calculate_discount(value: float, segment: str) -> dict:
    """Calculate discount based on business rules."""
    if segment == "Enterprise":
        discount = 0.20
    else:
        discount = 0.10
    
    return {
        "original": value,
        "discount": f"{discount:.0%}",
        "final": value * (1 - discount)
    }
```

### Step 3: Register Tools

Edit `src/agents/sales_agent/agent.py`:

```python
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from .tools import query_crm, calculate_discount

agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="sales_agent",
    description="Sales agent with CRM integration",
    instruction="""
    You are a B2B sales specialist.
    
    CAPABILITIES:
    - query_crm: Get customer information
    - calculate_discount: Apply pricing rules
    
    Always use CRM data before making offers.
    """,
    tools=[google_search, query_crm, calculate_discount],
)
```

### Step 4: Test

```bash
eab test sales_agent --interactive
```

---

## Deployment to GCP

### Deploy Single Agent

```bash
# From YAML
eab deploy --env production --yaml agents/my_first_agent.yaml

# From Python code
eab deploy --env production --agent sales_agent
```

### Deploy All Agents

```bash
eab deploy --env production --all
```

### Verify Deployment

```bash
# Check status
eab status

# View logs
eab logs my_first_agent

# Test endpoint
curl https://your-agent-url.run.app/health
```

---

## Common Commands

```bash
# List all agents
eab list

# Validate before deployment
eab validate agents/my_agent.yaml

# Compile YAML to Python (optional)
eab compile agents/my_agent.yaml --output src/agents/my_agent/

# Run local tests
pytest tests/ -v

# Format code
black src/ tests/

# Check code style
ruff check src/ tests/
```

---

## Next Steps

1. ✅ **Test included agents**: `eab run agents/my_assistant.yaml`
2. ✅ **Create your own**: Edit YAML or Python
3. ✅ **Add integrations**: Connect to your APIs
4. ✅ **Deploy**: `eab deploy --agent your_agent`
5. ✅ **Monitor**: Check logs and metrics

---

## Troubleshooting

### "Could not automatically determine credentials"
```bash
gcloud auth application-default login
```

### "API not enabled"
```bash
gcloud services enable aiplatform.googleapis.com
```

### "Module not found"
```bash
pip install -e ".[dev]"
```

### Validation fails
```bash
# Check YAML syntax
eab validate agents/your_agent.yaml

# Common issues:
# - Indentation (use spaces, not tabs)
# - Required fields: name, type, instruction
```

---

## Need Help?

- 📖 Full documentation in `docs/` folder
- 🧪 Examples in `examples/` folder
- 🐛 Issues: GitHub Issues page

---

**Ready to build? Start with:**
```bash
eab create agent my_bot --type llm && eab run agents/my_bot.yaml
```
