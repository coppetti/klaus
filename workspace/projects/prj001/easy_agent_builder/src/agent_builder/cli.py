#!/usr/bin/env python
"""
Easy Agent Builder CLI - Command line interface.

Commands:
    eab create agent <name> [--type llm|router|workflow] [--code]
    eab create tool <name>
    eab validate <yaml>
    eab compile <yaml>
    eab run <yaml|agent>
    eab test <agent> [--interactive]
    eab deploy [--env staging|prod] [--agent <name>|--all]
    eab list
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

console = Console()


# ============================================================================
# TEMPLATES
# ============================================================================

AGENT_YAML_TEMPLATE = """# Agent: {name}
# Type: {type}
# Created: {timestamp}

name: {name}
type: {type}
model: gemini-2.0-flash-exp

description: {description}

instruction: |
  {instruction}

tools:
{tools_yaml}

temperature: 0.7
max_tokens: 2048
"""

AGENT_CODE_TEMPLATE = '''"""
Agent: {name}
Type: {type} with custom Python code
"""

from google.adk.agents import LlmAgent
from google.adk.tools import tool, google_search


# ============================================================================
# CUSTOM TOOLS (add your functions here)
# ============================================================================

@tool
def my_example_tool(parameter: str) -> dict:
    """
    Description of your tool.
    
    Args:
        parameter: Parameter description
        
    Returns:
        Operation result
    """
    # Implement your logic here
    return {{
        "result": f"Processed: {{parameter}}",
        "status": "success"
    }}


# ============================================================================
# AGENT
# ============================================================================

agent = LlmAgent(
    model="{model}",
    name="{name}",
    description="{description}",
    instruction="""
{instruction}

YOU HAVE ACCESS TO:
- google_search: for web searches
- my_example_tool: custom tool (edit as needed)
    """,
    tools=[
        google_search,
        my_example_tool,  # Add more tools here
    ],
)

__all__ = ["agent", "my_example_tool"]
'''

SUBAGENT_TEMPLATE = '''from google.adk.agents import LlmAgent

{name} = LlmAgent(
    model="{model}",
    name="{name}",
    description="{description}",
    instruction="{instruction}",
)
'''

ROUTER_TEMPLATE = '''"""
Router: {name}
Coordinates multiple specialist agents.
"""

from google.adk.agents import LlmAgent

# Import sub-agents
{imports}

router_agent = LlmAgent(
    model="{model}",
    name="{name}",
    description="{description}",
    instruction="""
You are an intelligent coordinator. Analyze the request and delegate
to the most appropriate specialist agent.

AVAILABLE SPECIALISTS:
{specialists}

RULES:
1. Analyze the intent of the message
2. Choose the most specific specialist
3. If no specialist is appropriate, respond directly
4. Confirm to user: "I'll transfer you to [specialist]"
    """,
    sub_agents=[{sub_agents_list}],
)

__all__ = ["router_agent"]
'''


# ============================================================================
# CLI GROUP
# ============================================================================

@click.group()
@click.version_option(version="0.1.0", prog_name="eab")
def main():
    """🚀 Easy Agent Builder - Create and deploy AI agents quickly."""
    console.print(Panel.fit(
        "[bold blue]🚀 Easy Agent Builder[/bold blue]\n"
        "[dim]Create agents with YAML (low-code) or Python (full-code)[/dim]",
        border_style="blue"
    ))


# ============================================================================
# CREATE COMMANDS
# ============================================================================

@main.group()
def create():
    """Create new components (agents, tools, workflows)."""
    pass


@create.command()
@click.argument("name")
@click.option("--type", "agent_type", 
              type=click.Choice(["llm", "router", "sequential", "parallel", "loop"], case_sensitive=False),
              default="llm",
              help="Agent type")
@click.option("--model", default="gemini-2.0-flash-exp", help="LLM model")
@click.option("--description", default=None, help="Agent description")
@click.option("--tools", default="google_search", help="Comma-separated tools")
@click.option("--sub-agents", default="", help="Sub-agents (for router)")
@click.option("--code", is_flag=True, help="Create with Python code (not YAML)")
def agent(name: str, agent_type: str, model: str, description: Optional[str], 
          tools: str, sub_agents: str, code: bool):
    """Create a new agent (YAML or code)."""
    
    if code or agent_type in ["sequential", "parallel", "loop"]:
        # Create Python code
        _create_agent_code(name, agent_type, model, description, tools, sub_agents)
    else:
        # Create YAML
        _create_agent_yaml(name, agent_type, model, description, tools, sub_agents)


def _create_agent_yaml(name: str, agent_type: str, model: str, description: Optional[str], 
                       tools: str, sub_agents: str):
    """Create YAML agent."""
    
    agents_dir = Path("agents")
    agents_dir.mkdir(exist_ok=True)
    
    yaml_file = agents_dir / f"{name}.yaml"
    
    # Prepare content
    tool_list = [t.strip() for t in tools.split(",") if t.strip()]
    tools_yaml = "\n".join([f"  - {t}" for t in tool_list])
    
    desc = description or f"Agent {name}"
    
    if agent_type == "router":
        instruction = f"""You are a coordinator that delegates to specialists.

Analyze the request and choose the appropriate agent:
{chr(10).join([f"- {s.strip()}: specialist in {s.strip()}" for s in sub_agents.split(",") if s.strip()])}

Always confirm to the user when transferring."""
    else:
        instruction = f"""You are the agent {name}.

YOUR ROLE:
{desc}

RULES:
1. Be helpful and courteous
2. Respond in English
3. If you don't know something, admit it honestly
4. Use available tools when necessary"""
    
    content = AGENT_YAML_TEMPLATE.format(
        name=name,
        type=agent_type,
        description=desc,
        instruction=instruction,
        tools_yaml=tools_yaml,
        timestamp="auto-generated"
    )
    
    yaml_file.write_text(content, encoding='utf-8')
    
    console.print(f"✅ [green]YAML agent created:[/green] {yaml_file}")
    console.print(f"   [dim]Type: {agent_type}, Model: {model}[/dim]")
    console.print(f"\n[blue]To test:[/blue]")
    console.print(f"   python src/agent_builder/ultra_lowcode.py run {yaml_file}")


def _create_agent_code(name: str, agent_type: str, model: str, description: Optional[str], 
                       tools: str, sub_agents: str):
    """Create agent with Python code."""
    
    agent_dir = Path("src/agents") / name
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    desc = description or f"Agent {name}"
    
    if agent_type == "router":
        # Create router with sub-agents
        sub_agent_list = [s.strip() for s in sub_agents.split(",") if s.strip()]
        
        # Create sub-agents
        imports = []
        specialists = []
        for sub in sub_agent_list:
            sub_file = agent_dir / f"{sub}.py"
            sub_content = SUBAGENT_TEMPLATE.format(
                name=sub,
                model=model,
                description=f"Specialist in {sub}",
                instruction=f"You are the specialist in {sub}. Help the user with related topics."
            )
            sub_file.write_text(sub_content, encoding='utf-8')
            imports.append(f"from .{sub} import {sub}")
            specialists.append(f"- {sub}: {sub.replace('_', ' ').title()}")
        
        # Create router
        content = ROUTER_TEMPLATE.format(
            name=name,
            model=model,
            description=desc,
            imports="\n".join(imports),
            specialists="\n".join(specialists),
            sub_agents_list=", ".join(sub_agent_list)
        )
    else:
        # Create simple agent with code
        instruction = f"You are the agent {name}. {desc}. Be helpful and courteous."
        content = AGENT_CODE_TEMPLATE.format(
            name=name,
            type=agent_type,
            model=model,
            description=desc,
            instruction=instruction
        )
    
    # Write main file
    agent_file = agent_dir / "agent.py"
    agent_file.write_text(content, encoding='utf-8')
    
    # Create __init__.py
    init_file = agent_dir / "__init__.py"
    init_file.write_text('from .agent import agent\n__all__ = ["agent"]\n')
    
    console.print(f"✅ [green]Code agent created:[/green] {agent_dir}")
    console.print(f"   [dim]Type: {agent_type}, Model: {model}[/dim]")
    
    if agent_type == "router" and sub_agents:
        console.print(f"   [dim]Sub-agents: {sub_agents}[/dim]")
    
    console.print(f"\n[blue]To test:[/blue]")
    console.print(f"   eab test {name} --interactive")


@create.command()
@click.argument("name")
def tool(name: str):
    """Create custom tool template."""
    
    tools_dir = Path("src/tools")
    tools_dir.mkdir(exist_ok=True)
    
    tool_file = tools_dir / f"{name}.py"
    
    content = f'''"""
Tool: {name}
"""

from google.adk.tools import tool


@tool
def {name}(parameter: str) -> dict:
    """
    Description of tool {name}.
    
    Args:
        parameter: Parameter description
        
    Returns:
        Return description
    """
    # TODO: Implement your logic here
    
    return {{
        "result": f"Processed: {{parameter}}",
        "status": "success"
    }}
'''
    
    tool_file.write_text(content, encoding='utf-8')
    console.print(f"✅ [green]Tool created:[/green] {tool_file}")
    console.print(f"   [dim]Edit the file to implement logic[/dim]")


# ============================================================================
# VALIDATE COMMAND
# ============================================================================

@main.command()
@click.argument("yaml_path")
def validate(yaml_path: str):
    """Validate agent YAML configuration."""
    try:
        from agent_builder.ultra_lowcode import ConfigLoader
        
        loader = ConfigLoader()
        config = loader.load_agent_yaml(yaml_path)
        
        console.print(f"✅ [green]Valid configuration![/green]")
        console.print(f"   Name: {config.name}")
        console.print(f"   Type: {config.type}")
        console.print(f"   Model: {config.model}")
        console.print(f"   Tools: {len(config.tools)}")
        
    except Exception as e:
        console.print(f"❌ [red]Error:[/red] {e}")


# ============================================================================
# COMPILE COMMAND
# ============================================================================

@main.command()
@click.argument("yaml_path")
@click.option("--output", "-o", default=None, help="Output directory")
def compile(yaml_path: str, output: Optional[str]):
    """Compile YAML to Python code."""
    try:
        from agent_builder.ultra_lowcode import ConfigLoader
        
        loader = ConfigLoader()
        output_path = loader.compile_to_file(yaml_path, output or "src/agents")
        
        console.print(f"✅ [green]Compiled successfully![/green]")
        console.print(f"   Output: {output_path}")
        
    except Exception as e:
        console.print(f"❌ [red]Error:[/red] {e}")


# ============================================================================
# RUN COMMAND
# ============================================================================

@main.command()
@click.argument("target")
@click.option("--interactive", "-i", is_flag=True, default=True, help="Interactive mode")
def run(target: str, interactive: bool):
    """Run agent (YAML or agent name)."""
    
    if target.endswith('.yaml') or target.endswith('.yml'):
        # Run directly from YAML
        try:
            from agent_builder.ultra_lowcode import UltraRunner
            import asyncio
            
            runner = UltraRunner()
            asyncio.run(runner.interactive_chat(target))
            
        except Exception as e:
            console.print(f"❌ [red]Error:[/red] {e}")
    else:
        # Run registered agent
        console.print(f"🚀 [blue]Starting agent:[/blue] {target}")
        console.print(f"   [dim]Mode: {'interactive' if interactive else 'single-shot'}[/dim]")
        
        # TODO: Implement agent loading by name
        console.print("[yellow]Use: eab test {target} --interactive[/yellow]")


# ============================================================================
# TEST COMMAND
# ============================================================================

@main.command()
@click.argument("agent_name")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--input", "user_input", default=None, help="Single input")
def test(agent_name: str, interactive: bool, user_input: Optional[str]):
    """Test an agent."""
    
    console.print(f"🧪 [yellow]Testing:[/yellow] {agent_name}")
    
    if interactive:
        console.print("[dim]Interactive mode. Type 'exit' to quit.\n[/dim]")
        
        while True:
            user_input = console.input("[bold blue]You:[/bold blue] ")
            
            if user_input.lower() in ["exit", "quit"]:
                console.print("\n👋 Goodbye!")
                break
            
            console.print(f"[bold green]Agent:[/bold green] Processing '{user_input}'...")
            console.print()
    else:
        if not user_input:
            user_input = "Hello, how can you help me?"
        console.print(f"[bold blue]Input:[/bold blue] {user_input}")
        console.print(f"[bold green]Agent:[/bold green] Simulated response")


# ============================================================================
# DEPLOY COMMAND
# ============================================================================

@main.command()
@click.option("--env", default="staging", type=click.Choice(["staging", "production"]))
@click.option("--agent", "agent_name", default=None, help="Specific agent name")
@click.option("--yaml", "yaml_path", default=None, help="YAML file path")
@click.option("--all", "deploy_all", is_flag=True, help="Deploy all agents")
def deploy(env: str, agent_name: Optional[str], yaml_path: Optional[str], deploy_all: bool):
    """Deploy agents to GCP."""
    
    console.print(f"🚀 [blue]Deploy to {env}...[/blue]")
    
    if yaml_path:
        # Compile YAML first
        console.print(f"[yellow]Compiling {yaml_path}...[/yellow]")
        try:
            from agent_builder.ultra_lowcode import ConfigLoader
            loader = ConfigLoader()
            loader.compile_to_file(yaml_path)
            console.print("✅ [green]Compiled[/green]")
        except Exception as e:
            console.print(f"❌ [red]Compilation error:[/red] {e}")
            return
    
    if deploy_all:
        console.print("[yellow]Deploying all agents...[/yellow]")
    elif agent_name:
        console.print(f"[yellow]Deploy: {agent_name}...[/yellow]")
    else:
        console.print("[red]Specify --agent, --yaml, or --all[/red]")
        return
    
    console.print("[green]✅ Deploy simulated successfully![/green]")
    console.print(f"[dim]Environment: {env}[/dim]")


# ============================================================================
# LIST COMMAND
# ============================================================================

@main.command()
def list():
    """List all agents (YAML and code)."""
    
    table = Table(title="Available Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Format", style="yellow")
    table.add_column("Location", style="dim")
    
    # List YAMLs
    agents_dir = Path("agents")
    if agents_dir.exists():
        for yaml_file in sorted(agents_dir.glob("*.yaml")):
            table.add_row(
                yaml_file.stem,
                "llm",
                "YAML",
                f"agents/{yaml_file.name}"
            )
    
    # List code
    src_agents_dir = Path("src/agents")
    if src_agents_dir.exists():
        for agent_dir in sorted(src_agents_dir.iterdir()):
            if agent_dir.is_dir() and (agent_dir / "agent.py").exists():
                # Check if not already listed as YAML
                if not (agents_dir / f"{agent_dir.name}.yaml").exists():
                    table.add_row(
                        agent_dir.name,
                        "code",
                        "Python",
                        f"src/agents/{agent_dir.name}"
                    )
    
    console.print(table)


# ============================================================================
# DEV COMMAND
# ============================================================================

@main.command()
def dev():
    """Start development server (ADK Web UI)."""
    console.print("🌐 [blue]Starting ADK Web UI...[/blue]")
    
    try:
        subprocess.run(["adk", "web"], check=True)
    except FileNotFoundError:
        console.print("[red]❌ ADK CLI not found.[/red]")
        console.print("[dim]Install: pip install google-adk[/dim]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error: {e}[/red]")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    main()
