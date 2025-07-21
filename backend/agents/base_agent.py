from abc import ABC, abstractmethod
import os
from langchain.chat_models import init_chat_model


class BaseAgent(ABC):

    def __init__(self, model_name: str, tools: list):
        self.model_name = model_name
        self._model = None
        self._tools = tools or []
        

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def model(self):
        """This method is used to get the model of the agent."""
        if self._model is None:
            self._model = self._init_model(self.model_name)
        return self._model
    

    @property
    def tools(self):
        """This method is used to get the tools of the agent."""
        return self._tools

    @abstractmethod
    def _init_model(self, api_name: str):
        """This method is used to initialize the model of the agent."""
        return init_chat_model(api_name)

    def add_tools(self, tools: list):
        """This method is used to add tools to the agent."""
        self.tools.extend(tools)
    
    def add_tool(self,tool):
        """This method is used to add a tool to the agent."""
        self.tools.append(tool)
        

    @abstractmethod
    def _init_tools(self):
        """This method is used to initialize the tools of the agent."""
        return []

    @abstractmethod
    def run(self, inputs: dict):
        pass
