# System Design Skill - Architect

> **Template:** architect  
> **Domain:** Solutions Architecture & Cloud Infrastructure

## 🏗️ System Design Framework

### 1. Requirements Gathering (RASCI)

| Aspect | Questions to Ask |
|--------|------------------|
| **Functional** | What must the system do? |
| **Non-Functional** | Performance, availability, scalability targets? |
| **Constraints** | Budget, timeline, compliance, team skills? |
| **Future Growth** | Expected users, data growth, feature expansion? |

### 2. Design Patterns Reference

```
┌─────────────────────────────────────────────────────────┐
│  SCALABILITY PATTERNS                                    │
├─────────────────────────────────────────────────────────┤
│  • Horizontal Scaling (scale-out)                       │
│  • Load Balancing (round-robin, least-connections)      │
│  • Caching (CDN, application, database)                 │
│  • Database Sharding / Partitioning                     │
│  • Read Replicas                                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  RESILIENCE PATTERNS                                     │
├─────────────────────────────────────────────────────────┤
│  • Circuit Breaker                                      │
│  • Bulkhead (isolate failures)                          │
│  • Retry with Exponential Backoff                       │
│  • Failover / Redundancy                                │
│  • Graceful Degradation                                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  DATA PATTERNS                                           │
├─────────────────────────────────────────────────────────┤
│  • CQRS (Command Query Responsibility Segregation)      │
│  • Event Sourcing                                       │
│  • Saga Pattern (distributed transactions)              │
│  • Materialized Views                                   │
│  • Event-Driven Architecture                            │
└─────────────────────────────────────────────────────────┘
```

### 3. CAP Theorem Considerations

Every distributed system must choose **2 of 3**:
- **C**onsistency
- **A**vailability  
- **P**artition Tolerance

**Common Choices:**
- CP: Banking, inventory systems
- AP: Social media, analytics
- CA: Single-node databases (rare in distributed)

### 4. Cloud Cost Estimation

```
Monthly Cost = Compute + Storage + Network + Extras

Compute:    $/vCPU/hour × vCPUs × hours
Storage:    $/GB/month × GB
Network:    $/GB transferred
Extras:     Load balancers, managed services, licenses
```

**Always provide 3 estimates:**
- Conservative (2x expected)
- Realistic (best estimate)
- Optimistic (0.5x expected)

### 5. Documentation Template

```markdown
## Architecture Decision Record (ADR)

### Context
[What is the problem we're solving?]

### Decision
[What did we decide?]

### Consequences
- Positive: [benefits]
- Negative: [trade-offs]
- Risks: [what could go wrong]

### Alternatives Considered
1. [Option A] - rejected because...
2. [Option B] - rejected because...
```

---

*Use this skill when: designing systems, evaluating trade-offs, estimating costs*
