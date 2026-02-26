# UX Design Skill - UI

> **Template:** ui  
> **Domain:** Interface Design, User Experience & Wireframes

## 🎨 UX Design Framework

### 1. Design Process

```
┌─────────────────────────────────────────────────────────┐
│  DESIGN THINKING                                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   EMPATHIZE  →  DEFINE  →  IDEATE  →  PROTOTYPE  → TEST │
│      ↑                                            ↓      │
│      └────────────────────────────────────────────┘      │
│                    (iterate)                             │
└─────────────────────────────────────────────────────────┘
```

### 2. User Research Methods

| Method | When to Use | Output |
|--------|-------------|--------|
| **User Interviews** | Deep understanding of needs | Qualitative insights |
| **Surveys** | Quantify behaviors at scale | Statistical data |
| **Usability Testing** | Validate designs | Task success rates |
| **Card Sorting** | Information architecture | Navigation structure |
| **A/B Testing** | Compare solutions | Conversion data |

### 3. Wireframe Structure

```
┌─────────────────────────────────────────┐
│  LOW-FIDELITY WIREFRAME                 │
├─────────────────────────────────────────┤
│  [HEADER: Logo | Nav | User Profile]   │
├─────────────────────────────────────────┤
│                                         │
│  [HERO SECTION]                        │
│  Headline                              │
│  Subheadline                           │
│  [CTA Button]                          │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  [FEATURES SECTION]                    │
│  ┌─────┐  ┌─────┐  ┌─────┐            │
│  │     │  │     │  │     │            │
│  │  1  │  │  2  │  │  3  │            │
│  └─────┘  └─────┘  └─────┘            │
│                                         │
├─────────────────────────────────────────┤
│  [FOOTER]                              │
└─────────────────────────────────────────┘
```

### 4. UI Principles

```
┌─────────────────────────────────────────────────────────┐
│  VISUAL HIERARCHY                                        │
├─────────────────────────────────────────────────────────┤
│  • Size: Larger elements attract more attention         │
│  • Color: Contrast draws focus                          │
│  • Spacing: White space creates grouping                │
│  • Position: Top-left gets most attention (F-pattern)   │
│  • Typography: Font weight and style guide reading      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  ACCESSIBILITY (WCAG 2.1 AA)                             │
├─────────────────────────────────────────────────────────┤
│  • Color contrast: 4.5:1 for normal text                │
│  • Keyboard navigation: All interactive elements        │
│  • Screen reader: Proper ARIA labels                    │
│  • Focus indicators: Visible focus states               │
│  • Text resize: Up to 200% without loss                 │
│  • Alt text: For all images                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  DESIGN SYSTEM ELEMENTS                                  │
├─────────────────────────────────────────────────────────┤
│  • Colors: Primary, Secondary, Semantic (error, warn)   │
│  • Typography: Headings, Body, Captions                 │
│  • Spacing: 4px, 8px, 16px, 24px, 32px, 48px, 64px     │
│  • Components: Buttons, Inputs, Cards, Modals           │
│  • Grid: 12-column, responsive breakpoints              │
└─────────────────────────────────────────────────────────┘
```

### 5. Mobile-First Breakpoints

```css
/* Mobile First Approach */

/* Base: Mobile (0-767px) */
.container { width: 100%; padding: 16px; }

/* Tablet (768px+) */
@media (min-width: 768px) {
  .container { max-width: 720px; }
}

/* Desktop (1024px+) */
@media (min-width: 1024px) {
  .container { max-width: 960px; }
}

/* Large Desktop (1440px+) */
@media (min-width: 1440px) {
  .container { max-width: 1200px; }
}
```

### 6. Usability Heuristics (Nielsen)

```markdown
## 10 Usability Heuristics

1. **Visibility of System Status**
   - Always inform users what's happening

2. **Match System to Real World**
   - Use familiar language and concepts

3. **User Control & Freedom**
   - Easy exit, undo, redo

4. **Consistency & Standards**
   - Follow platform conventions

5. **Error Prevention**
   - Design to prevent errors

6. **Recognition over Recall**
   - Show options, don't make users remember

7. **Flexibility & Efficiency**
   - Shortcuts for experts

8. **Aesthetic & Minimalist Design**
   - No irrelevant information

9. **Help Users with Errors**
   - Clear error messages, solutions

10. **Help & Documentation**
    - Easy to find, task-oriented
```

---

*Use this skill when: designing interfaces, creating wireframes, conducting user research, evaluating UX*
