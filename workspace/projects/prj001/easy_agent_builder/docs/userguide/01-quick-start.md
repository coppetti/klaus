# 🚀 Quick Start Guide

> Get your first AI agent running in **5 minutes**

---

## 📋 Prerequisites

- Python 3.11+
- Google Cloud account (for deployment)
- Git

---

## ⚡ 3-Step Quick Start

### Step 1: Install (1 minute)

```bash
# Clone the repository
git clone https://github.com/your-org/easy-agent-builder.git
cd easy-agent-builder

# Install dependencies
pip install -e ".[dev]"
```

### Step 2: Create Your First Agent (2 minutes)

```bash
# Create a new agent
eab create agent my_first_agent --type llm

# Edit the generated file
# agents/my_first_agent.yaml
```

**Generated agent file:**
```yaml
name: my_first_agent
type: llm
model: gemini-2.0-flash-exp

description: My first AI agent

instruction: |
  You are a helpful assistant. Answer user questions
  clearly and concisely.

tools:
  - google_search

temperature: 0.7
```

### Step 3: Run & Test (2 minutes)

```bash
# Validate your agent
eab validate agents/my_first_agent.yaml

# Run interactively
eab run agents/my_first_agent.yaml

# Test with a message
> Hello! What's the weather today?
```

---

## 🎯 What You Can Build

### Level 1: Simple Assistant (5 min)
```yaml
name: simple_bot
type: llm
instruction: Be helpful and friendly
tools: [google_search]
```

### Level 2: Router Agent (10 min)
```yaml
name: support_router
type: router
instruction: Route to appropriate specialist
sub_agents: [sales, support, billing]
```

### Level 3: Workflow Pipeline (15 min)
```yaml
name: data_pipeline
type: sequential
steps:
  - agent: extractor
  - agent: transformer
  - agent: loader
```

---

## 🚀 Deploy to Production

```bash
# Deploy to Cloud Run (staging)
eab deploy --env staging --agent my_first_agent

# Deploy to Vertex AI (production)
eab deploy --env production --agent my_first_agent

# Check status
eab status
```

---

## 📚 Next Steps

- [Complete Guide](02-complete-guide.md) - Deep dive into all features
- [YAML Reference](03-yaml-reference.md) - All configuration options
- [Examples](../examples/) - 10+ working examples
- [Architecture Diagrams](../diagrams/) - Visual system overview

---

## 🆘 Need Help?

```bash
# CLI help
eab --help
eab create --help

# Run tests
./run_tests.sh unit

# Check logs
eab logs my_first_agent
```

---

**You're ready to build!** 🎉

For detailed documentation, see the [Complete Guide](02-complete-guide.md).
