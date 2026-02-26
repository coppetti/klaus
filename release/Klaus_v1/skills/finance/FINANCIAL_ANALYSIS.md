# Financial Analysis Skill - Finance

> **Template:** finance  
> **Domain:** Cost Analysis, Budgeting & Financial Planning

## 💰 Financial Analysis Framework

### 1. Cost Breakdown Structure

```
Total Cost of Ownership (TCO)
├── Initial Costs (CapEx)
│   ├── Infrastructure setup
│   ├── Licenses & software
│   ├── Training & onboarding
│   └── Migration costs
│
├── Operational Costs (OpEx)
│   ├── Compute resources
│   ├── Storage
│   ├── Network/data transfer
│   ├── Support & maintenance
│   └── Personnel
│
└── Hidden Costs
    ├── Technical debt
    ├── Downtime/availability
    ├── Compliance/audit
    └── Opportunity cost
```

### 2. Cloud Pricing Models

| Model | Best For | Risk Level |
|-------|----------|------------|
| **On-Demand** | Variable workloads, testing | High cost |
| **Reserved** | Predictable workloads, 1-3 year commit | Low cost, locked-in |
| **Spot/Preemptible** | Fault-tolerant, batch processing | Cheapest, interruptible |
| **Savings Plans** | Flexible commitment, consistent usage | Medium cost |

### 3. ROI Calculation

```
ROI = (Benefits - Costs) / Costs × 100%

Payback Period = Initial Investment / Monthly Savings

NPV = Σ [Cash Flow / (1 + discount rate)^t]

Break-even Point = Fixed Costs / (Revenue per unit - Variable cost per unit)
```

### 4. Budget Categories

```markdown
## Budget Template: [Project Name]

### Infrastructure
- Compute: $____ /month
- Storage: $____ /month
- Network: $____ /month
- **Subtotal: $____**

### Software & Tools
- Licenses: $____ /month
- SaaS subscriptions: $____ /month
- **Subtotal: $____**

### Human Resources
- Internal team: $____ /month
- External contractors: $____ /month
- Training: $____ one-time
- **Subtotal: $____**

### Contingency (20%)
- **$____**

### TOTAL: $____ /month
```

### 5. Cost Optimization Checklist

- [ ] Right-size instances (not too big, not too small)
- [ ] Use auto-scaling for variable workloads
- [ ] Implement lifecycle policies (archive old data)
- [ ] Monitor unused resources (orphaned volumes, idle VMs)
- [ ] Reserved instances for baseline capacity
- [ ] Spot instances for batch/crash-tolerant workloads
- [ ] Multi-region pricing comparison
- [ ] Negotiate enterprise discounts (if applicable)

### 6. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Cost overrun | Medium | High | Buffer budget, monitoring |
| Vendor lock-in | High | Medium | Multi-cloud strategy |
| Usage spikes | Low | High | Auto-scaling limits |

---

*Use this skill when: calculating costs, building budgets, analyzing ROI, optimizing spend*
