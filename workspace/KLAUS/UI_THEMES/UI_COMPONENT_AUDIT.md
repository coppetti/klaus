# Klaus UI Component Audit

> Based on `docker/web-ui/app.py` analysis
> Date: 2026-02-26

---

## 1. Layout Structure

```
┌─────────────────┬───────────────────────────┬─────────────────┐
│                 │                           │                 │
│  LEFT SIDEBAR   │       CHAT AREA           │  RIGHT SIDEBAR  │
│  w-64 fixed     │       flex-1              │  w-96 fixed     │
│                 │                           │                 │
│ • Sessions      │  ┌─────────────────────┐  │ • Settings      │
│ • New Session   │  │ Header              │  │ • Provider      │
│ • Context       │  │ - Avatar (gradient) │  │   Status        │
│   Info          │  │ - Tabs (Chat/Graph) │  │ • Telegram      │
│ • Context       │  │ - Fork Context      │  │ • Ngrok         │
│   Analyzer      │  └─────────────────────┘  │ • Session Info  │
│ • Semantic      │                           │                 │
│   Memory        │  ┌─────────────────────┐  │                 │
│                 │  │ Chat Messages       │  │                 │
│  (collapsible   │  │ - Welcome state     │  │                 │
│   sections)     │  │ - Bubbles (user/    │  │                 │
│                 │  │   assistant)        │  │                 │
└─────────────────┘  │ - Typing indicator  │  └─────────────────┘
                     └─────────────────────┘
                     
                     ┌─────────────────────┐
                     │ Input Area          │
                     │ - Model selector    │
                     │ - Textarea          │
                     │ - Attach button     │
                     │ - Send button       │
                     └─────────────────────┘
```

---

## 2. Color System (Current - Shadcn Light)

### CSS Variables
```css
:root {
    --background: 0 0% 100%;           /* #FFFFFF */
    --foreground: 240 10% 3.9%;        /* #09090B */
    --card: 0 0% 100%;                 /* #FFFFFF */
    --primary: 240 5.9% 10%;           /* #18181B */
    --secondary: 240 4.8% 95.9%;       /* #F4F4F5 */
    --muted: 240 4.8% 95.9%;           /* #F4F4F5 */
    --border: 240 5.9% 90%;            /* #E4E4E7 */
    --radius: 0.5rem;
}
```

### Accent Colors (Hardcoded)
- **Primary accent**: `violet-500` / `violet-600` (#8B5CF6)
- **Status online**: `green-500`
- **Status offline**: `gray-400`
- **Status warning**: `yellow-500`
- **Context analyzer**: `indigo-500`
- **Semantic memory**: `pink-500`
- **Telegram**: `blue-600`

---

## 3. Typography

### Fonts
- Inter: 400, 500, 600 (body)
- Outfit: 500, 600, 700 (headings)
- JetBrains Mono: 400 (code)

### Size Scale
- **H1**: `text-lg font-semibold` (sidebar titles)
- **H2**: `text-xl font-semibold` (welcome title)
- **H3**: `text-sm font-medium` (card titles)
- **Body**: `text-sm` (chat messages)
- **Small**: `text-xs` (labels, status)
- **Tiny**: `text-[10px]` (badges, metadata)

---

## 4. Components Inventory

### Chat Bubbles
```html
<!-- User -->
<div class="bg-violet-600 text-white rounded-2xl rounded-br-sm px-4 py-2">

<!-- Assistant -->
<div class="bg-gray-100 text-gray-900 rounded-2xl rounded-bl-sm px-4 py-2">
```

### Sidebar Card
```html
<div class="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
```

### Status Badge
```html
<span class="status-badge online|offline|warning">
    <i class="fas fa-circle text-xs"></i>
    <span>Status Text</span>
</span>
```

---

## 5. Deckard Light Theme Mapping

| UI Element | Current | Deckard Light |
|------------|---------|---------------|
| Background | white | #F5F3EF (warm white) |
| Card | white | #FAF8F5 (paper white) |
| Border | gray-200 | #D4CFC5 (aged paper) |
| Primary accent | violet-500 | #FF6B35 (LA Orange) |
| Secondary accent | - | #00D4AA (Neon Blue) |
| Text primary | gray-900 | #1A1612 (warm black) |
| Text secondary | gray-500 | #5C554D (sepia) |
| Success | green-500 | #2D5A3D (film green) |
| Warning | yellow-500 | #C9A227 (faded gold) |
| Error | red-500 | #8B2635 (blood red) |

### Typography
| Usage | Current | Deckard |
|-------|---------|---------|
| Headings | Outfit | Orbitron |
| Body | Inter | Inter (keep) |
