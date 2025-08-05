from tools.base_tool import BaseTool
from langchain_core.tools import InjectedToolCallId, tool

from langgraph.types import Command, interrupt


class ValidatePreferences(BaseTool):
    """Validate the preferences of the user"""

    @property
    def name(self):
        return "validate_preferences"

    @property
    def description(self):
        return "Validate the preferences of the user"
    
    def execute(self, inputs: dict):
        return "Preferences validated"
    
    def __init__(self):
        super().__init__()