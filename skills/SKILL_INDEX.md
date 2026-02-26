# Skill Index

> **Complete reference of all available skills by template**

---

## 🎯 How to Use Skills

Each skill is a specialized knowledge module that agents can reference when working in specific domains. Skills are organized by template/persona.

### Directory Structure
```
skills/
├── SKILL_INDEX.md              # This file
├── AGENT_GUIDELINES.md         # Master agent guidelines
├── CLAUDE.md                   # Critical rules (NEVER BREAK)
│
├── architect/                  # Solutions Architecture
│   └── SYSTEM_DESIGN.md
│
├── finance/                    # Financial Analysis
│   └── FINANCIAL_ANALYSIS.md
│
├── developer/                  # Software Development
│   └── CODE_QUALITY.md
│
├── marketing/                  # Content & Marketing
│   └── CONTENT_CREATION.md
│
├── legal/                      # Compliance & Legal
│   └── COMPLIANCE_CHECKLIST.md
│
├── ui/                         # UX/UI Design
│   └── UX_DESIGN.md
│
└── general/                    # General Purpose
    └── COMMUNICATION.md
```

---

## 📚 Skills by Template

### 🏗️ Architect
**File:** `skills/architect/SYSTEM_DESIGN.md`

**Use for:**
- System design and architecture
- Cloud infrastructure decisions
- Scalability planning
- Cost estimation
- Architecture Decision Records (ADRs)

**Key Topics:**
- Design patterns (scalability, resilience, data)
- CAP theorem
- Cloud pricing models
- TCO calculation

---

### 💰 Finance
**File:** `skills/finance/FINANCIAL_ANALYSIS.md`

**Use for:**
- Budget creation
- Cost analysis
- ROI calculation
- Cloud pricing optimization
- Financial risk assessment

**Key Topics:**
- Cost breakdown structure
- Pricing models (On-Demand, Reserved, Spot)
- ROI formulas
- Budget templates

---

### 💻 Developer
**File:** `skills/developer/CODE_QUALITY.md`

**Use for:**
- Writing clean code
- Code reviews
- Debugging
- Testing strategies
- Performance optimization

**Key Topics:**
- SOLID principles
- Code review checklist
- Testing pyramid
- Git workflow
- Debugging process

---

### 📝 Marketing
**File:** `skills/marketing/CONTENT_CREATION.md`

**Use for:**
- Copywriting
- Content strategy
- SEO optimization
- Social media posts
- Email marketing

**Key Topics:**
- Copywriting formulas (AIDA, PAS, FAB)
- SEO checklist
- Content calendar
- Email templates

---

### ⚖️ Legal
**File:** `skills/legal/COMPLIANCE_CHECKLIST.md`

**Use for:**
- Contract review
- Privacy compliance (GDPR, CCPA)
- Terms of service drafting
- Open source license review
- Compliance audits

**Key Topics:**
- Data privacy regulations
- Contract clauses
- License compatibility
- Compliance checklists

---

### 🎨 UI
**File:** `skills/ui/UX_DESIGN.md`

**Use for:**
- Interface design
- Wireframing
- User research
- Usability evaluation
- Design systems

**Key Topics:**
- Design thinking process
- Wireframe templates
- UI principles (hierarchy, accessibility)
- Usability heuristics

---

### 💬 General
**File:** `skills/general/COMMUNICATION.md`

**Use for:**
- Professional communication
- Email writing
- Meeting facilitation
- Time management
- Problem solving

**Key Topics:**
- Email templates
- Active listening
- Productivity methods
- Feedback delivery (SBI model)

---

## 🔗 Integration with Templates

Each template's `SOUL.md` should reference relevant skills:

```markdown
## Specialized Skills

When working in my domain, reference these skills:
- `skills/architect/SYSTEM_DESIGN.md`
- `skills/architect/COST_ESTIMATION.md`
```

---

## 📝 Adding New Skills

To add a new skill:

1. Create skill file: `skills/<template>/<SKILL_NAME>.md`
2. Update this index
3. Reference in template's SOUL.md if applicable

### Skill Template Structure
```markdown
# Skill Name - Template

> **Template:** template_name
> **Domain:** Domain description

## Overview
Brief description of when to use this skill.

## Framework/Section 1
Content...

## Framework/Section 2
Content...

---
*Use this skill when: [trigger conditions]*
```

---

*This index is maintained in sync with template development.*
