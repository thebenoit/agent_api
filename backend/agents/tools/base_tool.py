from abc import ABC, abstractmethod
from typing import Any

class BaseTool(ABC):
    
    @property
    @abstractmethod
    def name(self) -> str:
        """name of the tool"""
        raise NotImplementedError
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of the tool(important because it's how the llm will understand that it should use this tool)"""
        raise NotImplementedError
    
    @abstractmethod
    def execute(self, inputs: dict[str, Any]) -> Any:
        """Execute the tool with the given parameters"""
        raise NotImplementedError
    