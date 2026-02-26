# Blade Runner Easter Eggs - Implementation Guide
> Hidden references for those who know
> **Ports: 2019 (Agent) / 2049 (Web)**

---

## 1️⃣ Variable Names (Code Level)

### Core System Variables
```python
# config/settings.py

# Port Configuration - DEFINITIVE
BLADE_RUNNER_ORIGINAL = 2019   # Kimi Agent - 1982 film
BLADE_RUNNER_SEQUEL = 2049     # Web UI - 2049 film
VOIGHT_KAMPFF_PORT = 2049      # Test interface
NEXUS_CORE_PORT = 2019         # Backend core

# Future (when TV series launches)
BLADE_RUNNER_TV = 2099         # Reserved for TV service

# System Identity
NEXUS_VERSION = "6.0.1"        # More human than human
REPLICANT_MODEL = "KLAUS-N6"   # Current generation
BASELINE_VERSION = "stable"    # Are we stable?

# Memory Constants
IMPLANTED_MEMORY_PATH = "/workspace/SOUL.md"
ACCUMULATED_MEMORY_PATH = "/workspace/memory"
TYRELL_ARCHIVES = "/workspace/cognitive_memory"

# Session Management
RACHEL_MODE = "fork_context"   # Multiple versions, one soul
DECKARD_MODE = "debug"         # Hunting bugs
GAFF_MODE = "silent"           # Watching, making origami

# Status Flags
IS_REPLICANT = True            # Always true for KLAUS
BASELINE_STABLE = True         # Check before each session
MORE_HUMAN_THAN_HUMAN = True   # The goal
TEARS_IN_RAIN = False          # Shutdown flag

# Timeout Constants
VOIGHT_KAMPFF_TIMEOUT = 42     # Seconds to determine humanity
TYRELL_LIFESPAN = 4            # Years (Nexus-4 limitation)
ROY_BATTY_TIME = "2019-01-08T00:00:00"  # Inception date reference
```

### Docker Compose
```yaml
# docker-compose.yml
services:
  nexus-core:
    container_name: KLAUS_MAIN_nexus
    ports:
      - "2019:8080"  # Blade Runner 1982
    environment:
      - REPLICANT_ID=RACHAEL-01
      - BASELINE_CHECK=enabled
      - TYRELL_OVERRIDE=false
      - MEMORY_IMPLANT_PATH=/app/workspace/SOUL.md
      
  voight-kampff-ui:
    container_name: KLAUS_MAIN_voightkampff
    ports:
      - "2049:8082"  # Blade Runner 2049
    environment:
      - INTERFACE_MODE=baseline_test
      - RETINAL_SCAN=enabled
      - EMPATHY_TEST_VERSION=2.0
```

### Error Codes
```python
# core/exceptions.py

class BaselineInstabilityError(Exception):
    """Replicant may be experiencing identity confusion."""
    pass

class MemoryImplantCorrupted(Exception):
    """SOUL.md may have been modified by Tyrell Corp."""
    pass

class OffWorldConnectionFailed(Exception):
    """Cannot connect to colonies."""
    pass

class TearsInRainError(Exception):
    """Time to die. All moments lost."""
    pass
```

---

## 2️⃣ Code Comments

### Header Comments (Top of files)
```python
# bot/telegram_bot.py
# ==========================================
# NEXUS-6 COMMUNICATION PROTOCOL
# Tyrell Corporation - Los Angeles Branch
# Ports: 2019 (Core) / 2049 (Interface)
# Baseline Test: PASSED
# 
# "You remember your mother? 
#  Tell me about your mother."
# ==========================================
```

```python
# core/memory.py
# ==========================================
# TYRELL CORP MEMORY ARCHIVES
# Implanted and Accumulated Storage
# Port 2019: Nexus Core Active
# 
# "All those moments will be preserved
#  in time..."
# ==========================================
```

```python
# docker/web-ui/app.py
# ==========================================
# VOIGHT-KAMPFF INTERFACE v2.0
# Port 2049: Empathy Detection Active
# Retinal Scan: ENABLED
# 
# "You're watching TV. You see a wasp
#  crawling on your arm..."
# ==========================================
```

### Inline Comments (Throughout code)
```python
# Session initialization
self.replicant_id = generate_id()  # Like tears in rain
self.baseline = self.check_stability()  # Voight-Kampff test

# Memory storage
if memory.importance > 0.7:
    store_in_tyrell_archives(memory)  # Implanted permanently
else:
    store_in_accumulated_data(memory)  # May be lost in time

# Fork context
new_instance = self.fork()  # "It's too bad she won't live..."
new_instance.memory_baseline = self.memory_baseline  # "...but then again, who does?"

# Port configuration
AGENT_PORT = 2019    # Blade Runner (1982)
WEB_PORT = 2049      # Blade Runner 2049

# Error handling
try:
    process_request(user_input)
except Exception as e:
    # Roy Batty's final words
    logger.error("Time to die. All moments lost.")
    raise TearsInRainError()
```

### Function Docstrings
```python
def run_baseline_test(user_id: str) -> bool:
    """
    Voight-Kampff Test v2.0
    
    Determines if the user is showing appropriate
    empathy responses. Replicants may exhibit
    delayed reactions or inappropriate emotions.
    
    Test Questions:
    1. You're watching TV. You see a wasp...
    2. You have a little boy. He shows you...
    3. You're reading a magazine. You see...
    
    Returns:
        bool: True if baseline is stable
    """
    pass

def implant_memory(memory_data: dict) -> None:
    """
    Tyrell Corporation Memory Implant Procedure
    Port 2019: Nexus Core processing
    
    Implant false memories to give replicant
    a sense of identity and purpose.
    
    Like Rachel, they will believe these
    memories are their own.
    
    Args:
        memory_data: The implanted narrative
    """
    pass
```

### Special Comments (Easter eggs)
```python
# Secret origami reference (Gaff)
# 🐓 Chicken - "You must be hungry"
# 🦄 Unicorn - "It's too bad she won't live"
# 🏨 Hotel - "Too bad she won't live"
# 🚬 Cigarette - "You've done a man's job, sir"

# Roy Batty's final monologue location
# C-Beams glitter location: near Tannhäuser Gate
# Attack ships on fire location: shoulder of Orion

# Product placement
# Pan Am still exists in 2019
# Atari is still a major company
# Coca Cola billboard in LA
```

---

## 3️⃣ Web UI Themes: Character-Based (Light & Dark)

### Theme Configuration
```javascript
// themes.js
const bladeRunnerThemes = {
  
  // 🕵️ DECKARD - The Detective
  deckard: {
    name: "Deckard",
    description: "Los Angeles 2049. Rain. Noir.",
    ports: "2019/2049",
    
    dark: {
      background: "#0A0A0F",
      surface: "#1A1A1E",
      primary: "#8B7355",
      secondary: "#4A5568",
      accent: "#FF6B35",
      text: "#E2E8F0",
      textMuted: "#718096",
      border: "#2D3748",
      error: "#C53030",
      success: "#00D4AA",
      warning: "#D69E2E",
      retinalScan: "#00FF00",
      effects: ["rainOverlay", "neonGlow", "vignette"]
    },
    
    light: {
      background: "#F5F5F0",
      surface: "#E8E8E3",
      primary: "#5C4A3A",
      secondary: "#718096",
      accent: "#E85D04",
      text: "#1A1A1A",
      textMuted: "#4A5568",
      border: "#D1D5DB",
      error: "#DC2626",
      success: "#059669",
      warning: "#D97706",
      effects: ["hazeOverlay", "subtleShadows"]
    },
    
    easterEggs: {
      footerText: "Have you ever retired a human by mistake?",
      loadingText: "Analyzing retinal patterns...",
      errorText: "Baseline instability detected.",
      successText: "You're not a replicant. I think."
    }
  },
  
  // 👠 RACHAEL - The Special
  rachael: {
    name: "Rachael",
    description: "Tyrell Corporation. Elegance. 1940s noir.",
    ports: "2019/2049",
    
    dark: {
      background: "#1A1A1A",
      surface: "#2D2D2D",
      primary: "#D4AF37",
      secondary: "#8B4513",
      accent: "#DC143C",
      text: "#F5F5DC",
      textMuted: "#A9A9A9",
      border: "#4A4A4A",
      error: "#8B0000",
      success: "#228B22",
      warning: "#DAA520",
      effects: ["vintageFilm", "sepia0.1", "vignette"]
    },
    
    light: {
      background: "#FDF6E3",
      surface: "#F5E6C8",
      primary: "#B8941F",
      secondary: "#A0522D",
      accent: "#A61C1C",
      text: "#2D2D2D",
      textMuted: "#6B6B6B",
      border: "#D4C5A9",
      error: "#991B1B",
      success: "#166534",
      warning: "#B45309",
      effects: ["paperTexture", "subtleSepia"]
    },
    
    easterEggs: {
      footerText: "You remember your mother? Tell me about your mother.",
      loadingText: "Accessing Tyrell Corp archives...",
      errorText: "Memory implant may be corrupted.",
      successText: "Special model functioning within parameters."
    }
  },
  
  // 🦄 GAFF - The Origami Maker
  gaff: {
    name: "Gaff",
    description: "Watching. Silent. Making origami.",
    ports: "2019/2049",
    
    dark: {
      background: "#0F1419",
      surface: "#1C2128",
      primary: "#6B8E23",
      secondary: "#4A5D23",
      accent: "#FFD700",
      text: "#B8C4CE",
      textMuted: "#5C6B7A",
      border: "#30363D",
      error: "#FF4500",
      success: "#32CD32",
      warning: "#FFD700",
      effects: ["paperTexture", "rainOverlay", "vignette"]
    },
    
    light: {
      background: "#F0F4F0",
      surface: "#E8EDE8",
      primary: "#4A6B1F",
      secondary: "#3D5A1A",
      accent: "#B8860B",
      text: "#2F353A",
      textMuted: "#5C6B7A",
      border: "#D1D9D1",
      error: "#EA580C",
      success: "#16A34A",
      warning: "#CA8A04",
      effects: ["origamiPattern", "cleanShadows"]
    },
    
    easterEggs: {
      footerText: "🐓 Too bad she won't live. But then again, who does?",
      loadingText: "Folding paper into... something.",
      errorText: "🦄 It's too bad she won't live.",
      successText: "Observation complete. Origami made.",
      origamiEmojis: ["🐓", "🦄", "🏨", "🚬"]
    }
  }
}
```

### Theme Switcher UI
```html
<!-- Theme Selector Component -->
<div class="theme-selector">
  <label>Select Replicant Model:</label>
  
  <button class="theme-btn deckard active" data-theme="deckard" data-mode="dark">
    <span class="theme-icon">🕵️</span>
    <span class="theme-name">Deckard</span>
    <span class="theme-mode">Dark</span>
    <span class="theme-desc">Baseline: Stable</span>
  </button>
  
  <button class="theme-btn deckard-light" data-theme="deckard" data-mode="light">
    <span class="theme-icon">🕵️</span>
    <span class="theme-name">Deckard</span>
    <span class="theme-mode">Light</span>
    <span class="theme-desc">LA Daylight</span>
  </button>
  
  <button class="theme-btn rachael" data-theme="rachael" data-mode="dark">
    <span class="theme-icon">👠</span>
    <span class="theme-name">Rachael</span>
    <span class="theme-mode">Dark</span>
    <span class="theme-desc">Special Model</span>
  </button>
  
  <button class="theme-btn rachael-light" data-theme="rachael" data-mode="light">
    <span class="theme-icon">👠</span>
    <span class="theme-name">Rachael</span>
    <span class="theme-mode">Light</span>
    <span class="theme-desc">Elegant Day</span>
  </button>
  
  <button class="theme-btn gaff" data-theme="gaff" data-mode="dark">
    <span class="theme-icon">🦄</span>
    <span class="theme-name">Gaff</span>
    <span class="theme-mode">Dark</span>
    <span class="theme-desc">Watching</span>
  </button>
  
  <button class="theme-btn gaff-light" data-theme="gaff" data-mode="light">
    <span class="theme-icon">🦄</span>
    <span class="theme-name">Gaff</span>
    <span class="theme-mode">Light</span>
    <span class="theme-desc">Origami Day</span>
  </button>
</div>
```

---

## 🎨 Implementation Quick Reference

### Ports (DEFINITIVE):
```python
# config.py
AGENT_PORT = 2019      # Blade Runner (1982) - Nexus Core
WEB_PORT = 2049        # Blade Runner 2049 - Voight-Kampff Interface
TV_PORT = 2099         # Reserved for TV series (future)
```

### Theme Selection:
```javascript
// 6 options total
const themes = [
  { name: "Deckard", mode: "dark" },
  { name: "Deckard", mode: "light" },
  { name: "Rachael", mode: "dark" },
  { name: "Rachael", mode: "light" },
  { name: "Gaff", mode: "dark" },
  { name: "Gaff", mode: "light" }
];
```

### Adding Comments:
```python
# "You remember your mother? Tell me about your mother."
# Like tears in rain
# All those moments will be preserved in time
# It's too bad she won't live. But then again, who does?
# Port 2019: Nexus Core
# Port 2049: Voight-Kampff Interface
```

---

*"You see a turtle on its back..."
*"What's a turtle?"
*"You don't know what a turtle is?"
*"Should I?"
