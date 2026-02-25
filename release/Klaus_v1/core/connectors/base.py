"""
IDE Connector Base
==================
Abstract interface for connecting to different IDEs.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FileContext:
    """Represents a file in the IDE."""
    path: str
    content: str
    language: Optional[str] = None
    cursor_line: Optional[int] = None
    cursor_column: Optional[int] = None

@dataclass
class IDEContext:
    """Complete context from the IDE."""
    workspace_path: str
    open_files: List[FileContext]
    current_file: Optional[FileContext] = None
    selected_text: Optional[str] = None
    terminal_output: Optional[str] = None

class BaseIDEConnector(ABC):
    """Abstract base for IDE connectors."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.ide_name: str = "unknown"
        
    @abstractmethod
    def detect(self) -> bool:
        """Detect if this IDE is available."""
        pass
    
    @abstractmethod
    def get_context(self) -> IDEContext:
        """Get current context from IDE."""
        pass
    
    @abstractmethod
    def send_message(self, message: str) -> None:
        """Send message to IDE."""
        pass
    
    @abstractmethod
    def apply_edit(self, file_path: str, edit: Dict[str, Any]) -> bool:
        """Apply an edit to a file."""
        pass
    
    def read_file(self, file_path: str) -> str:
        """Read file content."""
        full_path = self.workspace_path / file_path
        if full_path.exists():
            return full_path.read_text()
        return ""
    
    def write_file(self, file_path: str, content: str) -> bool:
        """Write file content."""
        try:
            full_path = self.workspace_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            return True
        except Exception:
            return False
