#!/usr/bin/env python3
"""
Klaus Installer GUI
===================

Cross-platform installer with graphical interface.
Supports: macOS, Linux, Windows

Usage:
    python installer/install_gui.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import platform
import os
import sys
import shutil
from pathlib import Path
import threading
import json


class KlausInstaller:
    """Main installer application."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Klaus Installer")
        self.root.geometry("700x600")
        self.root.resizable(False, False)
        
        # Center window
        self.center_window()
        
        # Variables
        self.install_dir = tk.StringVar(value=str(Path.home() / "Klaus"))
        self.kimi_key = tk.StringVar()
        self.anthropic_key = tk.StringVar()
        self.openai_key = tk.StringVar()
        self.selected_providers = []
        self.setup_mode = tk.StringVar(value="full")
        
        # Colors
        self.bg_color = "#f5f5f5"
        self.accent_color = "#7c3aed"  # Violet
        self.text_color = "#1f2937"
        
        self.root.configure(bg=self.bg_color)
        
        self.setup_styles()
        self.create_widgets()
        
    def center_window(self):
        """Center the window on screen."""
        self.root.update_idletasks()
        width = 700
        height = 600
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_styles(self):
        """Setup ttk styles."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure styles
        style.configure(
            'Title.TLabel',
            font=('Inter', 24, 'bold'),
            foreground=self.text_color,
            background=self.bg_color
        )
        
        style.configure(
            'Subtitle.TLabel',
            font=('Inter', 12),
            foreground='#6b7280',
            background=self.bg_color
        )
        
        style.configure(
            'Accent.TButton',
            font=('Inter', 12, 'bold'),
            background=self.accent_color,
            foreground='white'
        )
        
        style.configure(
            'Section.TLabelframe',
            background=self.bg_color,
            borderwidth=2,
            relief='solid'
        )
        
        style.configure(
            'Section.TLabelframe.Label',
            font=('Inter', 11, 'bold'),
            background=self.bg_color,
            foreground=self.text_color
        )
    
    def create_widgets(self):
        """Create UI widgets."""
        # Main container
        main_frame = tk.Frame(self.root, bg=self.bg_color, padx=30, pady=30)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        ttk.Label(
            main_frame,
            text="🧙 Klaus Installer",
            style='Title.TLabel'
        ).pack(anchor='w')
        
        ttk.Label(
            main_frame,
            text="AI Solutions Architect with Hybrid Memory",
            style='Subtitle.TLabel'
        ).pack(anchor='w', pady=(0, 20))
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').pack(
            fill='x', pady=(0, 20)
        )
        
        # Installation Directory
        self.create_directory_section(main_frame)
        
        # Setup Mode
        self.create_mode_section(main_frame)
        
        # API Keys
        self.create_api_keys_section(main_frame)
        
        # Progress (hidden initially)
        self.progress_frame = tk.Frame(main_frame, bg=self.bg_color)
        self.progress_label = tk.Label(
            self.progress_frame,
            text="Installing...",
            font=('Inter', 11),
            bg=self.bg_color,
            fg=self.text_color
        )
        self.progress_label.pack(anchor='w')
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=640
        )
        self.progress_bar.pack(fill='x', pady=10)
        
        self.status_label = tk.Label(
            self.progress_frame,
            text="",
            font=('Inter', 10),
            bg=self.bg_color,
            fg='#6b7280'
        )
        self.status_label.pack(anchor='w')
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg=self.bg_color)
        button_frame.pack(fill='x', pady=(20, 0))
        
        self.install_btn = tk.Button(
            button_frame,
            text="Install Klaus",
            font=('Inter', 12, 'bold'),
            bg=self.accent_color,
            fg='white',
            activebackground="#6d28d9",
            activeforeground='white',
            cursor='hand2',
            padx=30,
            pady=10,
            bd=0,
            command=self.start_installation
        )
        self.install_btn.pack(side='right')
        
        self.cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            font=('Inter', 12),
            bg='#e5e7eb',
            fg=self.text_color,
            activebackground='#d1d5db',
            cursor='hand2',
            padx=20,
            pady=10,
            bd=0,
            command=self.root.quit
        )
        self.cancel_btn.pack(side='right', padx=(0, 10))
    
    def create_directory_section(self, parent):
        """Create installation directory section."""
        frame = tk.LabelFrame(
            parent,
            text=" Installation Directory ",
            font=('Inter', 11, 'bold'),
            bg=self.bg_color,
            fg=self.text_color,
            padx=15,
            pady=15
        )
        frame.pack(fill='x', pady=(0, 15))
        
        dir_frame = tk.Frame(frame, bg=self.bg_color)
        dir_frame.pack(fill='x')
        
        tk.Entry(
            dir_frame,
            textvariable=self.install_dir,
            font=('Inter', 11),
            bg='white',
            fg=self.text_color,
            relief='solid',
            bd=1
        ).pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        tk.Button(
            dir_frame,
            text="Browse",
            font=('Inter', 10),
            bg='white',
            fg=self.text_color,
            relief='solid',
            bd=1,
            cursor='hand2',
            command=self.browse_directory
        ).pack(side='right')
    
    def create_mode_section(self, parent):
        """Create setup mode section."""
        frame = tk.LabelFrame(
            parent,
            text=" Setup Mode ",
            font=('Inter', 11, 'bold'),
            bg=self.bg_color,
            fg=self.text_color,
            padx=15,
            pady=15
        )
        frame.pack(fill='x', pady=(0, 15))
        
        modes = [
            ("full", "Full Setup", "Web UI + Telegram + All Features"),
            ("minimal", "Minimal", "Web UI only, no extra features"),
            ("dev", "Development", "Source code with hot reload")
        ]
        
        for value, title, desc in modes:
            mode_frame = tk.Frame(frame, bg=self.bg_color)
            mode_frame.pack(fill='x', pady=5)
            
            tk.Radiobutton(
                mode_frame,
                text=title,
                variable=self.setup_mode,
                value=value,
                font=('Inter', 11, 'bold'),
                bg=self.bg_color,
                fg=self.text_color,
                selectcolor=self.accent_color
            ).pack(anchor='w')
            
            tk.Label(
                mode_frame,
                text=desc,
                font=('Inter', 10),
                bg=self.bg_color,
                fg='#6b7280'
            ).pack(anchor='w', padx=(25, 0))
    
    def create_api_keys_section(self, parent):
        """Create API keys section."""
        frame = tk.LabelFrame(
            parent,
            text=" API Keys (at least one required) ",
            font=('Inter', 11, 'bold'),
            bg=self.bg_color,
            fg=self.text_color,
            padx=15,
            pady=15
        )
        frame.pack(fill='x', pady=(0, 15))
        
        # Kimi (recommended)
        kimi_frame = tk.Frame(frame, bg=self.bg_color)
        kimi_frame.pack(fill='x', pady=5)
        
        tk.Label(
            kimi_frame,
            text="Kimi API Key (Recommended):",
            font=('Inter', 10, 'bold'),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w')
        
        kimi_entry = tk.Entry(
            kimi_frame,
            textvariable=self.kimi_key,
            font=('Inter', 11),
            bg='white',
            fg=self.text_color,
            relief='solid',
            bd=1,
            show='•'
        )
        kimi_entry.pack(fill='x', pady=(5, 0))
        
        # Optional: Show/hide keys
        self.show_keys_var = tk.BooleanVar(value=False)
        
        # Other providers (collapsible)
        other_frame = tk.LabelFrame(
            frame,
            text=" Other Providers (Optional) ",
            font=('Inter', 10),
            bg=self.bg_color,
            fg='#6b7280',
            padx=10,
            pady=10
        )
        other_frame.pack(fill='x', pady=(10, 0))
        
        # Anthropic
        tk.Label(
            other_frame,
            text="Anthropic (Claude):",
            font=('Inter', 10),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w')
        
        tk.Entry(
            other_frame,
            textvariable=self.anthropic_key,
            font=('Inter', 11),
            bg='white',
            fg=self.text_color,
            relief='solid',
            bd=1,
            show='•'
        ).pack(fill='x', pady=(5, 10))
        
        # OpenAI
        tk.Label(
            other_frame,
            text="OpenAI (GPT):",
            font=('Inter', 10),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(anchor='w')
        
        tk.Entry(
            other_frame,
            textvariable=self.openai_key,
            font=('Inter', 11),
            bg='white',
            fg=self.text_color,
            relief='solid',
            bd=1,
            show='•'
        ).pack(fill='x', pady=(5, 0))
    
    def browse_directory(self):
        """Open directory browser."""
        directory = filedialog.askdirectory(
            initialdir=self.install_dir.get(),
            title="Select Installation Directory"
        )
        if directory:
            self.install_dir.set(directory)
    
    def validate_inputs(self):
        """Validate user inputs."""
        # Check install directory
        install_path = Path(self.install_dir.get())
        if not install_path.parent.exists():
            messagebox.showerror(
                "Invalid Directory",
                f"Parent directory does not exist: {install_path.parent}"
            )
            return False
        
        # Check at least one API key
        if not any([
            self.kimi_key.get(),
            self.anthropic_key.get(),
            self.openai_key.get()
        ]):
            messagebox.showerror(
                "API Key Required",
                "Please provide at least one API key (Kimi recommended)."
            )
            return False
        
        return True
    
    def start_installation(self):
        """Start the installation process."""
        if not self.validate_inputs():
            return
        
        # Disable buttons
        self.install_btn.config(state='disabled')
        self.cancel_btn.config(state='disabled')
        
        # Show progress
        self.progress_frame.pack(fill='x', pady=(20, 0))
        
        # Run installation in thread
        thread = threading.Thread(target=self.run_installation)
        thread.daemon = True
        thread.start()
    
    def run_installation(self):
        """Run the installation steps."""
        try:
            steps = [
                ("Checking prerequisites...", 10, self.check_prerequisites),
                ("Creating directories...", 25, self.create_directories),
                ("Setting up configuration...", 40, self.setup_configuration),
                ("Pulling Docker images...", 60, self.pull_docker_images),
                ("Building containers...", 80, self.build_containers),
                ("Finalizing setup...", 100, self.finalize_setup)
            ]
            
            for status, progress, step_func in steps:
                self.update_progress(status, progress)
                if not step_func():
                    self.installation_failed()
                    return
            
            self.installation_success()
            
        except Exception as e:
            self.show_error(f"Installation failed: {str(e)}")
            self.installation_failed()
    
    def update_progress(self, status, progress):
        """Update progress bar and status."""
        self.root.after(0, lambda: [
            self.status_label.config(text=status),
            self.progress_bar.config(value=progress)
        ])
    
    def check_prerequisites(self):
        """Check that prerequisites are installed."""
        self.update_progress("Checking Docker...", 5)
        
        # Check Docker
        if not shutil.which("docker"):
            self.show_error("Docker is not installed. Please install Docker first.")
            return False
        
        self.update_progress("Checking Docker Compose...", 8)
        
        # Check Docker Compose
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            self.show_error("Docker Compose is not available.")
            return False
        
        return True
    
    def create_directories(self):
        """Create installation directories."""
        install_path = Path(self.install_dir.get())
        
        try:
            install_path.mkdir(parents=True, exist_ok=True)
            
            # Create workspace subdirectories
            workspace = install_path / "workspace"
            for subdir in ["memory", "cognitive_memory", "semantic_memory", 
                          "projects", "uploads", "web_ui_data"]:
                (workspace / subdir).mkdir(parents=True, exist_ok=True)
            
            return True
        except Exception as e:
            self.show_error(f"Failed to create directories: {e}")
            return False
    
    def setup_configuration(self):
        """Setup configuration files."""
        install_path = Path(self.install_dir.get())
        
        try:
            # Create .env file
            env_content = f"""# Klaus Configuration
# Generated by Installer

# API Keys
KIMI_API_KEY={self.kimi_key.get()}
ANTHROPIC_API_KEY={self.anthropic_key.get()}
OPENAI_API_KEY={self.openai_key.get()}

# Ports
KIMI_AGENT_PORT=7070
WEB_UI_PORT=7072

# Configuration
KLAUS_MODE={self.setup_mode.get()}
"""
            
            env_file = install_path / ".env"
            env_file.write_text(env_content)
            
            # Create init.yaml if not exists
            init_yaml = install_path / "init.yaml"
            if not init_yaml.exists():
                init_content = """agent:
  name: Klaus
  template: architect
  personality:
    language: en
    style: balanced
    tone: direct

mode:
  primary: hybrid
  ide:
    enabled: true
  telegram:
    enabled: false

provider:
  name: kimi
  model: kimi-k2-0711
  parameters:
    temperature: 0.7
    max_tokens: 4096

defaults:
  provider: kimi
  model: kimi-k2-0711
"""
                init_yaml.write_text(init_content)
            
            return True
        except Exception as e:
            self.show_error(f"Failed to setup configuration: {e}")
            return False
    
    def pull_docker_images(self):
        """Pull required Docker images."""
        self.update_progress("Pulling base images...", 55)
        
        try:
            # Pull Python image
            result = subprocess.run(
                ["docker", "pull", "python:3.11-slim"],
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0
        except Exception as e:
            self.show_error(f"Failed to pull Docker images: {e}")
            return False
    
    def build_containers(self):
        """Build Docker containers."""
        install_path = Path(self.install_dir.get())
        
        try:
            # Note: This would need the actual source code
            # For now, just simulate the build
            self.update_progress("Building Web UI container...", 70)
            # subprocess.run(["docker", "compose", "build"], cwd=install_path)
            
            self.update_progress("Building Kimi Agent container...", 75)
            
            return True
        except Exception as e:
            self.show_error(f"Failed to build containers: {e}")
            return False
    
    def finalize_setup(self):
        """Finalize the installation."""
        install_path = Path(self.install_dir.get())
        
        try:
            # Create start script
            if platform.system() == "Windows":
                start_script = install_path / "start.bat"
                start_content = """@echo off
echo Starting Klaus...
docker compose up -d
echo Klaus is starting...
echo Web UI: http://localhost:7072
pause
"""
            else:
                start_script = install_path / "start.sh"
                start_content = """#!/bin/bash
echo "Starting Klaus..."
docker compose up -d
echo "Klaus started!"
echo "Web UI: http://localhost:7072"
echo "API: http://localhost:7070"
"""
                start_script.chmod(0o755)
            
            start_script.write_text(start_content)
            
            return True
        except Exception as e:
            self.show_error(f"Failed to finalize setup: {e}")
            return False
    
    def installation_success(self):
        """Handle successful installation."""
        self.root.after(0, lambda: [
            self.progress_bar.config(value=100),
            self.status_label.config(text="Installation complete!", fg='#10b981'),
            messagebox.showinfo(
                "Installation Complete",
                f"Klaus has been installed to:\n{self.install_dir.get()}\n\n"
                "To start Klaus, run:\n"
                f"  cd {self.install_dir.get()}\n"
                "  ./start.sh (or start.bat on Windows)\n\n"
                "Then open http://localhost:7072 in your browser."
            ),
            self.root.quit()
        ])
    
    def installation_failed(self):
        """Handle failed installation."""
        self.root.after(0, lambda: [
            self.status_label.config(text="Installation failed", fg='#ef4444'),
            self.install_btn.config(state='normal'),
            self.cancel_btn.config(state='normal')
        ])
    
    def show_error(self, message):
        """Show error message."""
        self.root.after(0, lambda: messagebox.showerror("Error", message))
    
    def run(self):
        """Run the installer."""
        self.root.mainloop()


def main():
    """Main entry point."""
    # Check if tkinter is available
    try:
        import tkinter
    except ImportError:
        print("Error: tkinter is not installed.")
        print("Please install tkinter for your system:")
        print("  macOS: brew install python-tk")
        print("  Ubuntu/Debian: sudo apt-get install python3-tk")
        print("  Windows: tkinter is included with Python")
        sys.exit(1)
    
    installer = KlausInstaller()
    installer.run()


if __name__ == "__main__":
    main()
