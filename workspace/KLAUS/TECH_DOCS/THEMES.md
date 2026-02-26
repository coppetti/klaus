# Sistema de Temas Deckard

## Visão Geral

Klaus suporta dois temas:
- **Deckard Light**: Tons quentes de papel (warm off-white)
- **Deckard Dark**: Tons escuros de fumaça (smoky noir)

Baseado no filme Blade Runner (Deckard = personagem principal).

---

## Paleta de Cores

### Deckard Light
```css
--bg-primary: #FAF9F7;      /* Fundo principal - papel quente */
--bg-secondary: #F2F0ED;    /* Cards, sidebars */
--bg-tertiary: #EBE8E4;     /* Inputs, hover states */
--text-primary: #201E1B;    /* Texto principal - quase preto */
--text-secondary: #5C5854;  /* Texto secundário - cinza quente */
--accent-orange: #F26B3A;   /* Laranja Deckard (destaque) */
--accent-teal: #229E8B;     /* Verde-azulado (status online) */
--success: #457A5C;         /* Verde sucesso */
--border-subtle: #E5E2DE;   /* Bordas sutis */
```

### Deckard Dark
```css
--bg-primary: #161412;      /* Fundo principal - quase preto */
--bg-secondary: #1E1C19;    /* Cards, sidebars */
--bg-tertiary: #282623;     /* Inputs, hover states */
--text-primary: #ECE9E4;    /* Texto principal - quase branco */
--text-secondary: #BDB8B0;  /* Texto secundário - cinza quente */
--accent-orange: #F0784A;   /* Laranja mais claro (dark mode) */
--accent-teal: #2CB5A0;     /* Teal mais brilhante */
--success: #5A9A7A;         /* Verde sucesso */
--border-subtle: #383532;   /* Bordas sutis */
```

---

## Arquitetura do Sistema

### Arquivos
```
docker/web-ui/static/themes.css    # Definição das variáveis
docker/web-ui/app.py               # HTML com classes do tema
```

### Como Funciona

1. **Inicialização**: JavaScript lê `localStorage.getItem('deckard-theme')`
2. **Aplicação**: Classe `theme-deckard-light` ou `theme-deckard-dark` no `<html>`
3. **CSS**: Usa `var(--bg-primary)` etc.
4. **Persistência**: Salva no localStorage ao trocar

### Toggle de Tema

```javascript
// app.py - função toggleTheme()
function toggleTheme() {
    const current = localStorage.getItem('deckard-theme') || 'deckard-light';
    const newTheme = current === 'deckard-light' ? 'deckard-dark' : 'deckard-light';
    
    // Aplica no documento principal
    applyTheme(newTheme);
    localStorage.setItem('deckard-theme', newTheme);
    
    // Sincroniza com iframes (grafo)
    syncThemeWithIframes(newTheme);
}
```

---

## Sincronização com Iframe (CRÍTICO)

O **Cognitive Memory Graph** é carregado via iframe. O tema precisa ser sincronizado:

### Página Principal (app.py)
```javascript
function syncThemeWithIframes(themeName) {
    const iframes = ['iframe-graph', 'iframe-episodic'];
    iframes.forEach(id => {
        const iframe = document.getElementById(id);
        if (iframe && iframe.contentWindow) {
            iframe.contentWindow.postMessage({
                type: 'theme-change',
                theme: themeName
            }, '*');
        }
    });
}
```

### Página do Grafo (cognitive-memory-graph)
```javascript
window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'theme-change') {
        const themeName = event.data.theme;
        document.documentElement.className = 
            themeName === 'deckard-dark' ? 'theme-deckard-dark' : 'theme-deckard-light';
        localStorage.setItem('deckard-theme', themeName);
    }
});
```

### Por que isso é necessário?
- Iframes são isolados (mesmo domínio, mas contexto separado)
- CSS do pai não afeta o iframe
- `localStorage` é compartilhado, mas a classe no `<html>` precisa ser aplicada manualmente

---

## Classes CSS

### Classes de Background
```css
.main-bg { background-color: var(--bg-primary); }
.card { background-color: var(--bg-secondary); }
```

### Classes de Texto
```css
.text-primary { color: var(--text-primary); }
.text-secondary { color: var(--text-secondary); }
```

### Botões
```css
.btn-primary {
    background-color: var(--accent-orange);
    color: white;
    border: 1px solid var(--accent-orange);
}

.btn-secondary {
    background-color: transparent;
    border: 1px solid var(--border-subtle);
    color: var(--text-primary);
}
```

### Status Badges
```css
.status-online {
    background-color: transparent;
    border: 1px solid var(--accent-teal);
    color: var(--accent-teal);
}
```

---

## Adicionando um Novo Componente

Se criar um novo elemento na UI, use as variáveis:

```html
<!-- Errado: cores hardcoded -->
<div style="background: #ffffff; color: #000000;">

<!-- Certo: usa variáveis do tema -->
<div class="card text-primary">
```

Ou no CSS inline:
```css
.meu-componente {
    background-color: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--border-subtle);
}
```

---

## Dark Mode Overrides (Vitiligo Fix)

Alguns elementos Tailwind precisam de `!important` no dark mode:

```css
.theme-deckard-dark .main-bg {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}

.theme-deckard-dark .card {
    background-color: var(--bg-secondary) !important;
    border-color: var(--border-subtle) !important;
}
```

Isso garante que cores do Tailwind não sobreponham as nossas.

---

## Testando Temas

### Teste Manual
1. Abra Web UI
2. Clique no ícone sol/lua no header
3. Verifique:
   - Header muda de cor
   - Sidebar muda de cor
   - Chat bubbles mudam
   - **Abra Memory tab** - grafo deve estar no tema correto

### Teste Automatizado
```python
# Verificar se tema foi aplicado
page.goto('http://localhost:7072')
page.click('#theme-toggle-btn')
theme_class = page.eval_on_selector('html', 'el => el.className')
assert 'theme-deckard-dark' in theme_class
```

---

## Troubleshooting

### Tema não persiste
- Verificar `localStorage` no DevTools
- Verificar se `theme_settings.json` existe

### Iframe não pega o tema
- Verificar se `postMessage` está sendo chamado
- Verificar listener no iframe
- Verificar console por erros de CSP (Content Security Policy)

### Flash de tema errado no load
- Adicionar script no `<head>` para aplicar tema antes do render:
```html
<script>
    (function() {
        const saved = localStorage.getItem('deckard-theme') || 'light';
        document.documentElement.className = 
            saved === 'dark' ? 'theme-deckard-dark' : 'theme-deckard-light';
    })();
</script>
```

---

**Próximo:** [WEB_UI_API.md](WEB_UI_API.md) - APIs da Web UI
