"""
Ultra Low-Code Engine
=====================

Create agents without writing Python code.
Just YAML + CLI.

Inspired by Go's static validation, but with Python's simplicity.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, validator


# ============================================================================
# Configuration Schema (Static Validation like Go)
# ============================================================================

class ToolConfig(BaseModel):
    """Tool configuration."""
    name: str
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    """
    Complete agent configuration schema.
    Static validation like Go, but with Python.
    """
    name: str
    type: str = "llm"  # llm, sequential, parallel, router
    model: str = "gemini-2.0-flash-exp"
    description: Optional[str] = None
    instruction: str
    tools: List[str] = Field(default_factory=list)
    sub_agents: List[str] = Field(default_factory=list)  # para router
    temperature: float = 0.7
    max_tokens: int = 2048
    
    # Go-inspired validation (explicit)
    @validator('name')
    def name_must_be_valid(cls, v):
        if not v or len(v) < 2:
            raise ValueError('name must be at least 2 characters')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('name must be alphanumeric (use _ or -)')
        return v
    
    @validator('instruction')
    def instruction_must_exist(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('instruction too short (min 10 chars)')
        return v
    
    @validator('type')
    def type_must_be_valid(cls, v):
        valid = ['llm', 'sequential', 'parallel', 'router', 'loop']
        if v not in valid:
            raise ValueError(f'type must be one of: {valid}')
        return v


class WorkflowStep(BaseModel):
    """Sequential workflow step."""
    agent: str
    output_key: Optional[str] = None


class WorkflowConfig(BaseModel):
    """Multi-agent workflow configuration."""
    name: str
    type: str  # sequential, parallel
    steps: Optional[List[WorkflowStep]] = None
    agents: Optional[List[str]] = None  # for parallel
    description: Optional[str] = None


# ============================================================================
# Static Loader and Validator
# ============================================================================

class ConfigLoader:
    """
    Configuration loader with static validation.
    
    Similar to Go compiler: validates everything before running.
    """
    
    def __init__(self, config_dir: str = "./agents"):
        self.config_dir = Path(config_dir)
        self.agents: Dict[str, AgentConfig] = {}
        self.workflows: Dict[str, WorkflowConfig] = {}
    
    def load_agent_yaml(self, yaml_path: str) -> AgentConfig:
        """
        Load and validate agent config.
        
        Args:
            yaml_path: Path to .yaml file
            
        Returns:
            Validated AgentConfig
            
        Raises:
            ValueError: If config is invalid
        """
        path = Path(yaml_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {yaml_path}")
        
        # Parse YAML
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Validate (like Go compilation)
        try:
            config = AgentConfig(**data)
            return config
        except Exception as e:
            raise ValueError(f"Invalid configuration in {yaml_path}: {e}")
    
    def validate_directory(self) -> List[str]:
        """
        Validate all configs in directory.
        
        Returns:
            List of errors found (empty = all ok)
        """
        errors = []
        
        if not self.config_dir.exists():
            return [f"Directory does not exist: {self.config_dir}"]
        
        yaml_files = list(self.config_dir.glob("*.yaml")) + list(self.config_dir.glob("*.yml"))
        
        for yaml_file in yaml_files:
            try:
                config = self.load_agent_yaml(str(yaml_file))
                self.agents[config.name] = config
            except Exception as e:
                errors.append(f"{yaml_file.name}: {e}")
        
        # Check dependencies (like Go import verification)
        for name, config in self.agents.items():
            if config.type == 'router':
                for sub in config.sub_agents:
                    if sub not in self.agents:
                        errors.append(f"{name}: sub-agent '{sub}' not found")
        
        return errors
    
    def generate_python_code(self, config: AgentConfig) -> str:
        """
        Generate Python code from config.
        
        Args:
            config: Validated configuration
            
        Returns:
            Generated Python code
        """
        tools_import = ""
        tools_list = ""
        
        if config.tools:
            imports = []
            tool_names = []
            
            for tool in config.tools:
                if tool == "google_search":
                    imports.append("from google.adk.tools import google_search")
                    tool_names.append("google_search")
                elif tool == "calculator":
                    imports.append("from src.agent_builder.tools import calculator")
                    tool_names.append("calculator")
                else:
                    tool_names.append(f'"{tool}"')  # Placeholder
            
            tools_import = "\n".join(imports)
            tools_list = f"tools=[{', '.join(tool_names)}],"
        
        code = f'''"""
Agent generated automatically from YAML.
Config: {config.name}
"""

from google.adk.agents import LlmAgent
{tools_import}

agent = LlmAgent(
    model="{config.model}",
    name="{config.name}",
    description="{config.description or config.name}",
    instruction="""
{config.instruction}
    """,
    {tools_list}
)

__all__ = ["agent"]
'''
        return code
    
    def compile_to_file(self, yaml_path: str, output_dir: str = "src/agents") -> Path:
        """
        "Compilar" YAML para arquivo Python.
        
        Args:
            yaml_path: Arquivo YAML de entrada
            output_dir: Diretório de saída
            
        Returns:
            Path do arquivo gerado
        """
        config = self.load_agent_yaml(yaml_path)
        code = self.generate_python_code(config)
        
        # Create directory
        out_dir = Path(output_dir) / config.name
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Write file
        agent_file = out_dir / "agent.py"
        agent_file.write_text(code, encoding='utf-8')
        
        # Create __init__.py
        init_file = out_dir / "__init__.py"
        init_file.write_text('from .agent import agent\n__all__ = ["agent"]\n')
        
        return agent_file


# ============================================================================
# Runner Ultra Simples
# ============================================================================

class UltraRunner:
    """
    Runner simplificado para execução direta de YAML.
    Sem necessidade de código Python intermediário.
    """
    
    def __init__(self):
        self.loader = ConfigLoader()
    
    async def run_yaml(self, yaml_path: str, message: str) -> str:
        """
        Run agent directly from YAML file.
        
        Args:
            yaml_path: Path to YAML file
            message: User message
            
        Returns:
            Agent response
        """
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        
        # Validate and load
        config = self.loader.load_agent_yaml(yaml_path)
        
        # Create agent in memory (without generating file)
        agent = self._create_agent_from_config(config)
        
        # Execute
        session_service = InMemorySessionService()
        runner = Runner(agent=agent, session_service=session_service)
        
        session = session_service.create_session(
            app_name=config.name,
            user_id="user"
        )
        
        events = []
        async for event in runner.run_async(
            user_id="user",
            session_id=session.id,
            new_message=message
        ):
            events.append(event)
        
        # Extrair resposta
        if events:
            last = events[-1]
            if hasattr(last, 'content') and last.content:
                return str(last.content)
            if hasattr(last, 'text') and last.text:
                return str(last.text)
        
        return "(no response)"
    
    def _create_agent_from_config(self, config: AgentConfig):
        """Create agent instance from config."""
        from google.adk.agents import LlmAgent
        from google.adk.tools import google_search
        
        # Map tools
        tools = []
        for tool_name in config.tools:
            if tool_name == "google_search":
                tools.append(google_search)
        
        return LlmAgent(
            model=config.model,
            name=config.name,
            description=config.description or config.name,
            instruction=config.instruction,
            tools=tools,
        )
    
    async def interactive_chat(self, yaml_path: str):
        """Interactive chat with YAML agent."""
        config = self.loader.load_agent_yaml(yaml_path)
        
        print(f"🤖 {config.name}")
        print(f"   {config.description or 'Agent created via YAML'}\n")
        print("Type 'exit' to quit.\n")
        
        while True:
            user_input = input("👤 You: ").strip()
            
            if user_input.lower() in ["exit", "quit"]:
                print("\n👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            print("🤖 Agent: ", end="", flush=True)
            response = await self.run_yaml(yaml_path, user_input)
            print(response)
            print()


# ============================================================================
# CLI Ultra Simples
# ============================================================================

def validate_cmd(yaml_path: str) -> bool:
    """
    Validate command: checks config without running.
    Similar to 'go build' that compiles and checks.
    """
    print(f"🔍 Validating: {yaml_path}")
    
    loader = ConfigLoader()
    
    try:
        config = loader.load_agent_yaml(yaml_path)
        print(f"✅ Valid configuration!")
        print(f"   Name: {config.name}")
        print(f"   Type: {config.type}")
        print(f"   Model: {config.model}")
        print(f"   Tools: {len(config.tools)}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def compile_cmd(yaml_path: str):
    """
    Compile command: generates Python code.
    Similar to 'go build' that generates binary.
    """
    print(f"🔨 Compiling: {yaml_path}")
    
    loader = ConfigLoader()
    
    try:
        output = loader.compile_to_file(yaml_path)
        print(f"✅ Compiled successfully!")
        print(f"   Output: {output}")
    except Exception as e:
        print(f"❌ Error: {e}")


def run_cmd(yaml_path: str):
    """Run command: executes directly from YAML."""
    print(f"🚀 Running: {yaml_path}\n")
    
    runner = UltraRunner()
    asyncio.run(runner.interactive_chat(yaml_path))


# ============================================================================
# Templates de Exemplo
# ============================================================================

SIMPLE_AGENT_YAML = """# Simple Agent - Just edit and run!
name: my_assistant
type: llm
model: gemini-2.0-flash-exp

description: A friendly virtual assistant

instruction: |
  You are a helpful virtual assistant.
  Always respond in English.
  Be courteous, direct and objective.
  
  If you don't know something, admit it honestly.

tools:
  - google_search

temperature: 0.7
max_tokens: 2048
"""

ROUTER_YAML = """# Multi-Agent Router
name: support_router
type: router
model: gemini-2.0-flash-exp

description: Router that directs to specialists

instruction: |
  You are a support coordinator.
  Analyze the request and delegate to the correct specialist.

sub_agents:
  - sales
  - support
  - billing
"""


def create_example_yaml(output_path: str = "agent.yaml"):
    """Create example YAML file."""
    path = Path(output_path)
    path.write_text(SIMPLE_AGENT_YAML, encoding='utf-8')
    print(f"✅ Example created: {path}")
    print("\nEdit the file and run:")
    print(f"  eab run {path}")


if __name__ == "__main__":
    # Teste rápido
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "validate" and len(sys.argv) > 2:
            validate_cmd(sys.argv[2])
        elif cmd == "compile" and len(sys.argv) > 2:
            compile_cmd(sys.argv[2])
        elif cmd == "run" and len(sys.argv) > 2:
            run_cmd(sys.argv[2])
        elif cmd == "init":
            create_example_yaml()
        else:
            print("Commands: validate|compile|run <yaml> | init")
    else:
        print("Ultra Low-Code Engine")
        print("Commands:")
        print("  init                  - Create agent.yaml example")
        print("  validate <yaml>       - Validate configuration")
        print("  compile <yaml>        - Generate Python code")
        print("  run <yaml>            - Run agent")
