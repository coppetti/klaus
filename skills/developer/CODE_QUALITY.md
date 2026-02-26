# Code Quality Skill - Developer

> **Template:** developer  
> **Domain:** Software Development & Engineering

## 💻 Code Quality Framework

### 1. Clean Code Principles

```
┌─────────────────────────────────────────────────────────┐
│  SOLID PRINCIPLES                                        │
├─────────────────────────────────────────────────────────┤
│  S - Single Responsibility (one reason to change)       │
│  O - Open/Closed (open for extension, closed for mod)   │
│  L - Liskov Substitution (substitutable subclasses)     │
│  I - Interface Segregation (small, focused interfaces)  │
│  D - Dependency Inversion (depend on abstractions)      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  CODE SMELLS TO AVOID                                    │
├─────────────────────────────────────────────────────────┤
│  • Long functions (>20 lines)                           │
│  • Deep nesting (>3 levels)                             │
│  • Magic numbers/strings                                │
│  • Duplicated code (DRY violation)                      │
│  • God classes (too many responsibilities)              │
│  • Tight coupling                                       │
└─────────────────────────────────────────────────────────┘
```

### 2. Code Review Checklist

```markdown
## Review Checklist

### Functionality
- [ ] Code works as intended
- [ ] Edge cases handled
- [ ] Error handling implemented
- [ ] No obvious bugs

### Code Quality
- [ ] Readable and maintainable
- [ ] Follows style guidelines
- [ ] Proper naming (variables, functions, classes)
- [ ] Comments where necessary (not obvious)

### Testing
- [ ] Unit tests included
- [ ] Tests cover happy path and edge cases
- [ ] No broken existing tests

### Security
- [ ] No hardcoded secrets
- [ ] Input validation
- [ ] No SQL injection vulnerabilities
- [ ] Proper authentication/authorization

### Performance
- [ ] No obvious bottlenecks
- [ ] Efficient algorithms
- [ ] No unnecessary database queries
```

### 3. Testing Strategy

```
Test Pyramid:
       /\
      /  \
     / E2E\         (Few tests, slow, expensive)
    /________\
   /  Integration\  (Some tests, medium speed)
  /________________\
 /     Unit Tests    \ (Many tests, fast, cheap)
/______________________\

Coverage Goals:
- Unit: 80%+ coverage
- Integration: Critical paths
- E2E: User journeys
```

### 4. Git Workflow

```bash
# Feature Branch Workflow
1. git checkout -b feature/description
2. Make changes, commit often
3. git push origin feature/description
4. Create Pull Request
5. Code Review
6. Merge to main
7. Delete branch

Commit Message Format:
type(scope): short description

Types: feat, fix, docs, style, refactor, test, chore

Example:
feat(auth): add JWT token validation
```

### 5. Debugging Process

```
1. REPRODUCE
   └── Can you consistently reproduce the bug?

2. ISOLATE
   └── What's the minimal code that triggers it?

3. ANALYZE
   ├── Check logs
   ├── Review recent changes
   └── Use debugger/print statements

4. FIX
   └── Make the smallest change that fixes it

5. VERIFY
   └── Test the fix
   └── Check for regressions

6. DOCUMENT
   └── Commit message explains why, not just what
```

### 6. Performance Optimization

| Level | Techniques |
|-------|-----------|
| **Algorithm** | Big O analysis, efficient data structures |
| **Database** | Indexes, query optimization, caching |
| **Caching** | Memoization, Redis, CDN |
| **Concurrency** | Async/await, threading, connection pools |
| **Infrastructure** | Load balancing, horizontal scaling |

---

*Use this skill when: writing code, reviewing code, debugging, optimizing performance*
