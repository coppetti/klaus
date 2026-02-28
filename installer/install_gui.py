#!/usr/bin/env python3
"""
Klaus Installer GUI
===================

Wizard-style installer with Next/Back navigation.
Each screen fits in 700x600 without scrolling.

Usage:
    python installer/install_gui.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import sys
import shutil
from pathlib import Path
import threading
import webbrowser


class KlausInstaller:
    """Wizard-style installer."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Klaus Installer")
        self.root.geometry("700x600")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f5f5")
        
        # Center window
        self.center_window()
        
        # Colors
        self.bg_color = "#f5f5f5"
        self.accent_color = "#7c3aed"
        self.text_color = "#1f2937"
        
        # State
        self.current_step = 0
        
        # Config variables
        self.config = {
            'setup_mode': tk.StringVar(value='web+ide'),
            'provider': tk.StringVar(value='kimi'),
            'kimi_key': tk.StringVar(),
            'anthropic_key': tk.StringVar(),
            'google_key': tk.StringVar(),
            'openrouter_key': tk.StringVar(),
            'custom_base_url': tk.StringVar(value='http://localhost:11434/v1'),
            'custom_model': tk.StringVar(value='llama3.2'),
            'agent_name': tk.StringVar(value='Klaus'),
            'agent_persona': tk.StringVar(value='architect'),
            'user_name': tk.StringVar(),
            'user_role': tk.StringVar(),
            'user_tone': tk.StringVar(value='professional'),
            'user_detail': tk.StringVar(value='balanced'),
        }
        
        # Main frame (500px height for content)
        self.main_frame = tk.Frame(self.root, bg=self.bg_color, width=700, height=500)
        self.main_frame.place(x=0, y=0, width=700, height=500)
        
        # Button frame (100px height, fixed at bottom)
        self.button_frame = tk.Frame(self.root, bg=self.bg_color, width=700, height=100)
        self.button_frame.pack(side='bottom', fill='x')
        self.button_frame.pack_propagate(False)
        
        # Show first step
        self.show_welcome()
    
    def center_window(self):
        """Center window on screen."""
        self.root.update_idletasks()
        width = 700
        height = 600
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def clear_frame(self):
        """Clear main frame."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        for widget in self.button_frame.winfo_children():
            widget.destroy()
    
    def create_header(self, title):
        """Create header with title only."""
        # Title
        tk.Label(
            self.main_frame,
            text="🧙 Klaus Installer",
            font=('Inter', 24, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(20, 0))
        
        # Subtitle - Blade Runner quote
        tk.Label(
            self.main_frame,
            text="Wake up, time to install!",
            font=('Inter', 12),
            bg=self.bg_color,
            fg='#6b7280'
        ).pack(anchor='w', padx=40)
        
        # Separator
        ttk.Separator(self.main_frame, orient='horizontal').pack(
            fill='x', padx=40, pady=15
        )
        
        # Step title
        tk.Label(
            self.main_frame,
            text=title,
            font=('Inter', 16, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(10, 20))
    
    def create_buttons(self, back_text=None, next_text="Continue →", next_cmd=None, back_cmd=None):
        """Create navigation buttons at bottom."""
        # Back button
        if back_text:
            tk.Button(
                self.button_frame,
                text=back_text,
                font=('Inter', 11),
                bg='#e5e7eb',
                fg=self.text_color,
                activebackground='#d1d5db',
                cursor='hand2',
                padx=20,
                pady=8,
                bd=0,
                command=back_cmd or self.go_back
            ).place(x=40, y=30)
        
        # Cancel button (if not on last screen)
        if next_text != "Finish":
            tk.Button(
                self.button_frame,
                text="Cancel",
                font=('Inter', 11),
                bg='#e5e7eb',
                fg=self.text_color,
                activebackground='#d1d5db',
                cursor='hand2',
                padx=20,
                pady=8,
                bd=0,
                command=self.root.quit
            ).place(x=140 if back_text else 40, y=30)
        
        # Next/Install button
        btn_color = self.accent_color if next_text in ["Continue →", "Install Klaus", "Open Browser"] else self.accent_color
        tk.Button(
            self.button_frame,
            text=next_text,
            font=('Inter', 11, 'bold'),
            bg=btn_color,
            fg='white',
            activebackground="#6d28d9",
            activeforeground='white',
            cursor='hand2',
            padx=25,
            pady=8,
            bd=0,
            command=next_cmd or self.go_next
        ).place(x=580, y=30, anchor='ne')
    
    def go_next(self):
        """Go to next step."""
        if self.validate_step():
            steps = [self.show_welcome, self.show_setup_mode, self.show_provider,
                    self.show_api_key, self.show_agent_config, self.show_user_profile,
                    self.show_summary, self.show_installing, self.show_complete]
            
            self.current_step += 1
            if self.current_step < len(steps):
                self.clear_frame()
                steps[self.current_step]()
    
    def go_back(self):
        """Go to previous step."""
        steps = [self.show_welcome, self.show_setup_mode, self.show_provider,
                self.show_api_key, self.show_agent_config, self.show_user_profile,
                self.show_summary, self.show_installing, self.show_complete]
        
        self.current_step -= 1
        if self.current_step >= 0:
            self.clear_frame()
            steps[self.current_step]()
    
    def validate_step(self):
        """Validate current step."""
        if self.current_step == 3:  # API Key
            provider = self.config['provider'].get()
            keys = {
                'kimi': self.config['kimi_key'],
                'anthropic': self.config['anthropic_key'],
                'google': self.config['google_key'],
                'openrouter': self.config['openrouter_key'],
            }
            if provider in keys and not keys[provider].get().strip():
                messagebox.showerror("API Key Required", f"Please enter your {provider.capitalize()} API key.")
                return False
        return True
    
    # ========== STEP 1: WELCOME ==========
    def show_welcome(self):
        """Welcome screen."""
        self.current_step = 0
        self.clear_frame()
        
        # Title without create_header to have custom layout
        tk.Label(
            self.main_frame,
            text="🧙 Klaus Installer",
            font=('Inter', 24, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(20, 5))
        
        tk.Label(
            self.main_frame,
            text='"Wake up, time to install!"',
            font=('Inter', 12),
            bg=self.bg_color,
            fg='#6b7280'
        ).pack(anchor='w', padx=40)
        
        ttk.Separator(self.main_frame, orient='horizontal').pack(
            fill='x', padx=40, pady=15
        )
        
        # Description
        tk.Label(
            self.main_frame,
            text="This wizard will configure Klaus with your preferences.",
            font=('Inter', 11),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(10, 5))
        
        tk.Label(
            self.main_frame,
            text="You'll need:",
            font=('Inter', 11),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(10, 5))
        
        # Requirements
        reqs = [
            "• Docker & Docker Compose installed",
            "• At least one AI provider API key"
        ]
        for req in reqs:
            tk.Label(
                self.main_frame,
                text=req,
                font=('Inter', 11),
                bg=self.bg_color,
                fg=self.text_color
            ).pack(anchor='w', padx=60, pady=2)
        
        self.create_buttons(None, "Continue")
    
    # ========== STEP 2: SETUP MODE ==========
    def show_setup_mode(self):
        """Setup mode selection."""
        self.clear_frame()
        self.create_header("Setup Mode")
        
        modes = [
            ('web+ide', 'Web + IDE (Recommended)', 'Full experience with browser UI and VS Code integration'),
            ('ide-only', 'IDE Only', 'Chat directly in VS Code, no browser needed'),
            ('web-only', 'Web Only', 'Browser-based workflow')
        ]
        
        for value, label, desc in modes:
            frame = tk.Frame(self.main_frame, bg=self.bg_color)
            frame.pack(fill='x', padx=40, pady=10)
            
            tk.Radiobutton(
                frame,
                text=label,
                variable=self.config['setup_mode'],
                value=value,
                font=('Inter', 12, 'bold'),
                bg=self.bg_color,
                fg=self.text_color,
                selectcolor=self.bg_color
            ).pack(anchor='w')
            
            tk.Label(
                frame,
                text=desc,
                font=('Inter', 10),
                bg=self.bg_color,
                fg='#6b7280'
            ).pack(anchor='w', padx=(25, 0))
        
        self.create_buttons("← Back", "Continue →")
    
    # ========== STEP 3: PROVIDER ==========
    def show_provider(self):
        """AI provider selection."""
        self.clear_frame()
        self.create_header("Choose Your AI Provider")
        
        providers = [
            ('kimi', 'Kimi (Recommended)', 'Moonshot AI - Fast and reliable'),
            ('anthropic', 'Anthropic', 'Claude models - Great for coding'),
            ('google', 'Google', 'Gemini via AI Studio'),
            ('openrouter', 'OpenRouter', 'Access multiple models'),
            ('custom', 'Custom (Ollama)', 'Local models - runs on your machine')
        ]
        
        for value, label, desc in providers:
            frame = tk.Frame(self.main_frame, bg=self.bg_color)
            frame.pack(fill='x', padx=40, pady=8)
            
            tk.Radiobutton(
                frame,
                text=label,
                variable=self.config['provider'],
                value=value,
                font=('Inter', 12, 'bold'),
                bg=self.bg_color,
                fg=self.text_color,
                selectcolor=self.bg_color
            ).pack(anchor='w')
            
            tk.Label(
                frame,
                text=desc,
                font=('Inter', 10),
                bg=self.bg_color,
                fg='#6b7280'
            ).pack(anchor='w', padx=(25, 0))
        
        self.create_buttons("← Back", "Continue →")
    
    # ========== STEP 4: API KEY ==========
    def show_api_key(self):
        """API key input."""
        self.clear_frame()
        
        provider = self.config['provider'].get()
        labels = {
            'kimi': ('Kimi Configuration', 'https://platform.moonshot.cn'),
            'anthropic': ('Anthropic Configuration', 'https://console.anthropic.com'),
            'google': ('Google Configuration', 'https://aistudio.google.com'),
            'openrouter': ('OpenRouter Configuration', 'https://openrouter.ai'),
        }
        
        if provider == 'custom':
            self.create_header("Custom Provider (Ollama)")
            
            tk.Label(
                self.main_frame,
                text="Base URL:",
                font=('Inter', 11, 'bold'),
                bg=self.bg_color,
                fg=self.text_color
            ).pack(anchor='w', padx=40, pady=(10, 5))
            
            tk.Entry(
                self.main_frame,
                textvariable=self.config['custom_base_url'],
                font=('Inter', 11),
                bg='white',
                relief='solid',
                bd=1
            ).pack(fill='x', padx=40, pady=(0, 15))
            
            tk.Label(
                self.main_frame,
                text="Model Name:",
                font=('Inter', 11, 'bold'),
                bg=self.bg_color,
                fg=self.text_color
            ).pack(anchor='w', padx=40, pady=(10, 5))
            
            tk.Entry(
                self.main_frame,
                textvariable=self.config['custom_model'],
                font=('Inter', 11),
                bg='white',
                relief='solid',
                bd=1
            ).pack(fill='x', padx=40, pady=(0, 15))
            
            tk.Label(
                self.main_frame,
                text="💡 Examples: llama3.2, deepseek-r1:14b, mistral",
                font=('Inter', 10),
                bg=self.bg_color,
                fg='#6b7280'
            ).pack(anchor='w', padx=40)
            
        else:
            title, url = labels.get(provider, ('Configuration', ''))
            self.create_header(title)
            
            tk.Label(
                self.main_frame,
                text="API Key:",
                font=('Inter', 11, 'bold'),
                bg=self.bg_color,
                fg=self.text_color
            ).pack(anchor='w', padx=40, pady=(10, 5))
            
            # API Key entry - simple and functional
            self.api_entry = tk.Entry(
                self.main_frame,
                textvariable=self.config[f'{provider}_key'],
                font=('Inter', 12),
                bg='white',
                relief='solid',
                bd=2,
                show='*'
            )
            self.api_entry.place(x=40, y=200, width=620, height=35)
            self.api_entry.focus_set()
            
            tk.Label(
                self.main_frame,
                text=f"💡 Get your key at: {url}",
                font=('Inter', 10),
                bg=self.bg_color,
                fg='#6b7280'
            ).pack(anchor='w', padx=40)
        
        self.create_buttons("← Back", "Continue →")
    
    # ========== STEP 5: AGENT CONFIG ==========
    def show_agent_config(self):
        """Agent configuration."""
        self.clear_frame()
        self.create_header("Agent Configuration")
        
        # Agent Name
        tk.Label(
            self.main_frame,
            text="Agent Name:",
            font=('Inter', 11, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(10, 5))
        
        tk.Entry(
            self.main_frame,
            textvariable=self.config['agent_name'],
            font=('Inter', 11),
            bg='white',
            relief='solid',
            bd=1
        ).pack(fill='x', padx=40, pady=(0, 20))
        
        # Persona
        tk.Label(
            self.main_frame,
            text="Persona / Template:",
            font=('Inter', 11, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(10, 5))
        
        personas = ['architect', 'developer', 'finance', 'general', 'legal', 'marketing', 'ui']
        combo = ttk.Combobox(
            self.main_frame,
            textvariable=self.config['agent_persona'],
            values=personas,
            state='readonly',
            font=('Inter', 11)
        )
        combo.pack(fill='x', padx=40, pady=(0, 10))
        
        # Persona descriptions
        descriptions = {
            'architect': 'Solutions Architect',
            'developer': 'Software Developer',
            'finance': 'Financial Analyst',
            'general': 'General Assistant',
            'legal': 'Legal Assistant',
            'marketing': 'Marketing Specialist',
            'ui': 'UI/UX Designer'
        }
        
        for key, desc in descriptions.items():
            tk.Label(
                self.main_frame,
                text=f"  • {key:<12} - {desc}",
                font=('Inter', 10),
                bg=self.bg_color,
                fg='#6b7280'
            ).pack(anchor='w', padx=40)
        
        self.create_buttons("← Back", "Continue →")
    
    # ========== STEP 6: USER PROFILE ==========
    def show_user_profile(self):
        """User profile configuration."""
        self.clear_frame()
        self.create_header("Your Profile")
        
        # Name
        tk.Label(
            self.main_frame,
            text="Your Name:",
            font=('Inter', 11, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(10, 5))
        
        tk.Entry(
            self.main_frame,
            textvariable=self.config['user_name'],
            font=('Inter', 11),
            bg='white',
            relief='solid',
            bd=1
        ).pack(fill='x', padx=40, pady=(0, 15))
        
        # Role
        tk.Label(
            self.main_frame,
            text="Your Role:",
            font=('Inter', 11, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(10, 5))
        
        tk.Entry(
            self.main_frame,
            textvariable=self.config['user_role'],
            font=('Inter', 11),
            bg='white',
            relief='solid',
            bd=1
        ).pack(fill='x', padx=40, pady=(0, 5))
        
        tk.Label(
            self.main_frame,
            text="💡 e.g., Developer, Team Lead, Student, etc.",
            font=('Inter', 10),
            bg=self.bg_color,
            fg='#6b7280'
        ).pack(anchor='w', padx=40, pady=(0, 15))
        
        # Tone
        tk.Label(
            self.main_frame,
            text="Tone of Voice:",
            font=('Inter', 11, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(10, 5))
        
        tones = ['professional', 'casual', 'enthusiastic', 'direct']
        ttk.Combobox(
            self.main_frame,
            textvariable=self.config['user_tone'],
            values=tones,
            state='readonly',
            font=('Inter', 11)
        ).pack(fill='x', padx=40, pady=(0, 15))
        
        # Detail Level
        tk.Label(
            self.main_frame,
            text="Detail Level:",
            font=('Inter', 11, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(10, 5))
        
        details = ['concise', 'balanced', 'detailed', 'exhaustive']
        ttk.Combobox(
            self.main_frame,
            textvariable=self.config['user_detail'],
            values=details,
            state='readonly',
            font=('Inter', 11)
        ).pack(fill='x', padx=40, pady=(0, 5))
        
        self.create_buttons("← Back", "Continue →")
    
    # ========== STEP 7: SUMMARY ==========
    def show_summary(self):
        """Installation summary."""
        self.clear_frame()
        self.create_header("Ready to Install")
        
        # Summary frame
        summary = tk.LabelFrame(
            self.main_frame,
            text=" Configuration ",
            font=('Inter', 11, 'bold'),
            bg=self.bg_color,
            fg=self.text_color,
            padx=15,
            pady=10
        )
        summary.pack(fill='x', padx=40, pady=10)
        
        items = [
            ("Setup Mode", self.config['setup_mode'].get()),
            ("Provider", self.config['provider'].get()),
            ("Agent Name", self.config['agent_name'].get()),
            ("Persona", self.config['agent_persona'].get()),
            ("User", f"{self.config['user_name'].get() or 'Not set'} ({self.config['user_role'].get() or 'Not set'})"),
        ]
        
        for label, value in items:
            row = tk.Frame(summary, bg=self.bg_color)
            row.pack(fill='x', pady=2)
            
            tk.Label(
                row,
                text=f"{label}:",
                font=('Inter', 10, 'bold'),
                bg=self.bg_color,
                fg=self.text_color,
                width=12,
                anchor='w'
            ).pack(side='left')
            
            tk.Label(
                row,
                text=value,
                font=('Inter', 10),
                bg=self.bg_color,
                fg='#6b7280'
            ).pack(side='left')
        
        # What will happen
        tk.Label(
            self.main_frame,
            text="This will:",
            font=('Inter', 11, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(20, 10))
        
        actions = [
            "✓ Create workspace/SOUL.md and workspace/init.yaml",
            "✓ Create .env with your API keys",
            "✓ Build and start Docker containers",
            "✓ Open http://localhost:2049 in your browser"
        ]
        
        for action in actions:
            tk.Label(
                self.main_frame,
                text=action,
                font=('Inter', 10),
                bg=self.bg_color,
                fg=self.text_color
            ).pack(anchor='w', padx=60, pady=2)
        
        self.create_buttons("← Back", "Install Klaus", self.start_installation)
    
    # ========== STEP 8: INSTALLING ==========
    def show_installing(self):
        """Installation progress."""
        self.clear_frame()
        self.create_header("Installing...")
        
        # Quote
        tk.Label(
            self.main_frame,
            text='"I\'ve seen things you people wouldn\'t believe..."',
            font=('Inter', 12, 'italic'),
            bg=self.bg_color,
            fg='#6b7280'
        ).pack(pady=10)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self.main_frame,
            mode='determinate',
            length=620
        )
        self.progress_bar.pack(padx=40, pady=10)
        
        # Status
        self.status_label = tk.Label(
            self.main_frame,
            text="Starting installation...",
            font=('Inter', 10),
            bg=self.bg_color,
            fg='#6b7280'
        )
        self.status_label.pack()
        
        # Steps
        self.steps_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.steps_frame.pack(fill='x', padx=40, pady=15)
        
        self.step_labels = []
        steps_text = [
            "[ ] Creating configuration files",
            "[ ] Validating Docker installation",
            "[ ] Pulling base images",
            "[ ] Building containers",
            "[ ] Starting services",
            "[ ] Opening browser..."
        ]
        
        for step in steps_text:
            lbl = tk.Label(
                self.steps_frame,
                text=step,
                font=('Inter', 10),
                bg=self.bg_color,
                fg='#9ca3af'
            )
            lbl.pack(anchor='w', pady=1)
            self.step_labels.append(lbl)
        
        # Clear buttons during install
        for widget in self.button_frame.winfo_children():
            widget.destroy()
        
        # Start installation
        thread = threading.Thread(target=self.run_installation)
        thread.daemon = True
        thread.start()
    
    def update_step(self, idx, status):
        """Update step status."""
        symbols = {'pending': '[ ]', 'active': '[→]', 'done': '[✓]', 'error': '[✗]'}
        colors = {'pending': '#9ca3af', 'active': '#7c3aed', 'done': '#10b981', 'error': '#ef4444'}
        
        text = self.step_labels[idx].cget('text')[4:]  # Remove symbol
        self.step_labels[idx].config(
            text=f"{symbols.get(status, '[ ]')} {text}",
            fg=colors.get(status, '#9ca3af')
        )
    
    def run_installation(self):
        """Run installation steps."""
        try:
            steps = [
                ("Creating configuration files...", 15, self.create_config_files),
                ("Validating Docker...", 30, self.check_docker),
                ("Pulling Docker images...", 50, self.pull_images),
                ("Building containers...", 70, self.build_containers),
                ("Starting services...", 85, self.start_services),
                ("Finalizing...", 100, self.finalize_setup)
            ]
            
            for i, (status, progress, func) in enumerate(steps):
                self.root.after(0, lambda idx=i: self.update_step(idx, 'active'))
                self.root.after(0, lambda s=status, p=progress: self.update_progress(s, p))
                
                if not func():
                    self.root.after(0, lambda idx=i: self.update_step(idx, 'error'))
                    return
                
                self.root.after(0, lambda idx=i: self.update_step(idx, 'done'))
            
            self.root.after(0, self.show_complete)
            
        except Exception as e:
            print(f"Install error: {e}")
    
    def update_progress(self, status, progress):
        """Update progress."""
        self.status_label.config(text=status)
        self.progress_bar.config(value=progress)
    
    def create_config_files(self):
        """Create configuration files."""
        try:
            repo_root = Path(__file__).parent.parent
            workspace_dir = repo_root / "workspace"
            workspace_dir.mkdir(exist_ok=True)
            
            provider = self.config['provider'].get()
            
            # .env
            env_content = f"""# Klaus Configuration
KIMI_API_KEY={self.config['kimi_key'].get()}
ANTHROPIC_API_KEY={self.config['anthropic_key'].get()}
GOOGLE_API_KEY={self.config['google_key'].get()}
OPENROUTER_API_KEY={self.config['openrouter_key'].get()}
CUSTOM_BASE_URL={self.config['custom_base_url'].get()}
CUSTOM_MODEL={self.config['custom_model'].get()}

KIMI_AGENT_PORT=2019
WEB_UI_PORT=2049
KLAUS_MODE={self.config['setup_mode'].get()}
"""
            (workspace_dir / ".env").write_text(env_content)
            (repo_root / ".env").write_text(env_content)
            
            # init.yaml
            init_content = f"""agent:
  name: {self.config['agent_name'].get() or 'Klaus'}
  template: {self.config['agent_persona'].get()}
  personality:
    style: {self.config['user_detail'].get()}
    tone: {self.config['user_tone'].get()}

user:
  name: {self.config['user_name'].get() or 'User'}
  role: {self.config['user_role'].get() or 'Developer'}

mode:
  primary: hybrid
  ide:
    enabled: true
  telegram:
    enabled: false

provider:
  name: {provider}
  parameters:
    temperature: 0.7
    max_tokens: 4096

defaults:
  provider: {provider}
"""
            (workspace_dir / "init.yaml").write_text(init_content)
            
            # SOUL.md
            soul_content = f"""# {self.config['agent_name'].get() or 'Klaus'} - Agent Profile

## User Profile
**Name:** {self.config['user_name'].get() or 'User'}
**Role:** {self.config['user_role'].get() or 'Developer'}
**Preferences:**
- **Tone:** {self.config['user_tone'].get()}
- **Detail Level:** {self.config['user_detail'].get()}

## Agent Configuration
**Name:** {self.config['agent_name'].get() or 'Klaus'}
**Persona:** {self.config['agent_persona'].get()}
**Provider:** {provider}
"""
            (workspace_dir / "SOUL.md").write_text(soul_content)
            
            return True
        except Exception as e:
            print(f"Config error: {e}")
            return False
    
    def check_docker(self):
        """Check Docker."""
        if not shutil.which("docker"):
            return False
        result = subprocess.run(["docker", "compose", "version"], capture_output=True)
        return result.returncode == 0
    
    def pull_images(self):
        """Pull images."""
        try:
            result = subprocess.run(["docker", "pull", "python:3.11-slim"], capture_output=True)
            return result.returncode == 0
        except:
            return False
    
    def build_containers(self):
        """Build containers."""
        try:
            repo_root = Path(__file__).parent.parent
            result = subprocess.run(
                ["docker", "compose", "-f", "docker/docker-compose.yml", "build"],
                cwd=repo_root,
                capture_output=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Build error: {e}")
            return False
    
    def start_services(self):
        """Start services."""
        try:
            repo_root = Path(__file__).parent.parent
            setup_mode = self.config['setup_mode'].get()
            
            # Determine profile based on mode
            if setup_mode in ['web+ide', 'web-only']:
                profile = "web"
            else:
                profile = "web"  # IDE-only still uses web for now
            
            result = subprocess.run(
                ["docker", "compose", "-f", "docker/docker-compose.yml", "--profile", profile, "up", "-d"],
                cwd=repo_root,
                capture_output=True
            )
            import time
            time.sleep(5)
            return result.returncode == 0
        except Exception as e:
            print(f"Start error: {e}")
            return False
    
    def finalize_setup(self):
        """Finalize."""
        return True
    
    # ========== STEP 9: COMPLETE ==========
    def show_complete(self):
        """Installation complete."""
        self.current_step = 8
        self.clear_frame()
        self.create_header("Installation Complete! 🎉")
        
        # Quote
        tk.Label(
            self.main_frame,
            text='"Like tears in rain... time to code."',
            font=('Inter', 12, 'italic'),
            bg=self.bg_color,
            fg='#6b7280'
        ).pack(pady=10)
        
        # URL
        tk.Label(
            self.main_frame,
            text="Klaus is running at:",
            font=('Inter', 11),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(20, 5))
        
        url_frame = tk.Frame(self.main_frame, bg='#e0e7ff', padx=15, pady=10)
        url_frame.pack(anchor='w', padx=40)
        
        tk.Label(
            url_frame,
            text="🌐 http://localhost:2049",
            font=('Inter', 12, 'bold'),
            bg='#e0e7ff',
            fg='#7c3aed'
        ).pack()
        
        # Commands
        tk.Label(
            self.main_frame,
            text="Your configuration:",
            font=('Inter', 11, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w', padx=40, pady=(20, 10))
        
        commands = [
            ("Config files", "workspace/"),
            ("Logs", "docker logs -f KLAUS_MAIN_web"),
            ("Stop", "docker compose -f docker/docker-compose.yml down")
        ]
        
        for label, cmd in commands:
            row = tk.Frame(self.main_frame, bg=self.bg_color)
            row.pack(anchor='w', padx=60, pady=2)
            
            tk.Label(
                row,
                text=f"• {label}:",
                font=('Inter', 10),
                bg=self.bg_color,
                fg=self.text_color
            ).pack(side='left')
            
            tk.Label(
                row,
                text=cmd,
                font=('Inter', 10),
                bg=self.bg_color,
                fg='#6b7280'
            ).pack(side='left', padx=(5, 0))
        
        # Buttons
        for widget in self.button_frame.winfo_children():
            widget.destroy()
        
        tk.Button(
            self.button_frame,
            text="Open Browser",
            font=('Inter', 11, 'bold'),
            bg=self.accent_color,
            fg='white',
            activebackground="#6d28d9",
            cursor='hand2',
            padx=20,
            pady=8,
            bd=0,
            command=lambda: webbrowser.open("http://localhost:2049")
        ).place(x=40, y=30)
        
        tk.Button(
            self.button_frame,
            text="Finish",
            font=('Inter', 11),
            bg='#e5e7eb',
            fg=self.text_color,
            activebackground='#d1d5db',
            cursor='hand2',
            padx=20,
            pady=8,
            bd=0,
            command=self.root.quit
        ).place(x=580, y=30, anchor='ne')
    
    def run(self):
        """Run installer."""
        self.root.mainloop()


def main():
    """Main entry."""
    try:
        import tkinter
    except ImportError:
        print("Error: tkinter not installed.")
        print("  macOS: brew install python-tk@3.11")
        print("  Linux: sudo apt-get install python3-tk")
        sys.exit(1)
    
    installer = KlausInstaller()
    installer.run()


if __name__ == "__main__":
    main()
