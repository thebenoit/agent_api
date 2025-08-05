"""This file contains the LangGraph Agent/workflow and interactions with the LLM."""

from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Literal,
    Optional,
)

from asgiref.sync import sync_to_async
from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
    convert_to_openai_messages,
)
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from langgraph.graph import (
    END,
    StateGraph,
)
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot
from openai import OpenAIError
from psycopg_pool import AsyncConnectionPool
import os
from agents.tools import search_listing


class IanGraph:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=1000,
        ).bind_tools([search_listing])
        self.connection_pool: Optional[AsyncConnectionPool] = None
        self._graph: Optional[CompiledStateGraph] = None
    
    
    async def _connection_pool(self):
        """Get a PostgreSQL connection pool using environment-specific settings.

        Returns:
            AsyncConnectionPool: A connection pool for PostgreSQL database.
        """
        
        if self._connection_pool is None:
            try:
                max_size = 20
                
                self.connection_pool = AsyncConnectionPool(
                    os.getenv("MONGO_URI"),
                    open=false,
                    max_size=max_size,
                    kwargs={
                        "autocommit": True,
                        "connect_timeout": 5,
                        "prepare_threshold": None,                        
                    }
                )
                await self._connection_pool.open()
                logger.info("connection_pool_created", max_size=max_size)  
            except Exception as e:
                logger.error("connection_pool_creation_failed", error=str(e))
                raise e
        return self.connection_pool
    
    def __process_message(self, messages: list[BaseMessage]) -> list[Message]:
        openai_style_messages = convert_to_openai_messages(messages)
        return [
            Message(**message)
            for message in openai_style_messages
            if message["role"] in ["assistant","user"] and message["content"]
        ]
    async def _get_response(
        self,
        messsages: list[Message],
        session_id: str,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """Get a response from the LLM.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for Langfuse tracking.
            user_id (Optional[str]): The user ID for Langfuse tracking.

        Returns:
            list[dict]: The response from the LLM.
        """
        if self._graph is None:
            self._graph = await self.create_graph()
        
        config = {
            "configurable": {"thread_id":session_id},
            "callbacks":[callbackHandle()],
            "metadata":{
            "debug":False,
            }
        }
        try:
            response = await self._graph.ainvoke(
                {"messages":dump_messages(messages),"session_id":session_id}, config
            )
            return self.__process_message(response["messages"])
        except Exception as e:
            logger.error("error_getting_response", error=str(e))
            raise e
      
    async def _chat(self,state: GraphState) -> dict:
        
        logger.info(f"=== DÉBUT CHATBOT ===")
        logger.info(f"State reçu: {state}")

        try:
            new_user_input = state.get("new_user_input")
            logger.info(f"Input utilisateur: {new_user_input}")

            state["messages"].append({"role": "user", "content": new_user_input})
            logger.info("Message ajouté au state")
            logger.info("=== FIN CHATBOT ===")
            return {}

        except Exception as e:
            logger.error(f"Erreur dans chatbot: {e}")
            logger.error(f"Traceback:", exc_info=True)
            raise
            
        
            
    
    async def create_graph(self) -> Optional[CompiledStateGraph]:
        """Create and configure the LangGraph workflow.

        Returns:
            Optional[CompiledStateGraph]: The configured LangGraph instance or None if init fails
        """
        if self._graph is None:
            try:
                tool_node = ToolNode([search_listing])
                logger.info("ToolNode initialisé avec succès")
            except Exception as e:
                logger.error(f"Erreur initialisation ToolNode: {e}")
                logger.error(f"Traceback:", exc_info=True)
                raise
                # Add edges
            
                logger.info("Ajout des nodes au graph...")
            try:
                graph_builder.add_node("chatbot", chatbot)
                # graph_builder.add_node("human_verif", human_pref_validator)
                graph_builder.add_node("tools", tool_node)
                logger.info("Nodes ajoutés avec succès")
            except Exception as e:
                logger.error(f"Erreur ajout des nodes: {e}")
                logger.error(f"Traceback:", exc_info=True)
                raise
            
            logger.info("Ajout des edges au graph...")
            try:
                graph_builder.add_edge(START, "chatbot")
                graph_builder.add_conditional_edges("chatbot", tools_condition)
                graph_builder.add_edge("tools", "chatbot")
                logger.info("Edges ajoutés avec succès")
            except Exception as e:
                logger.error(f"Erreur ajout des edges: {e}")
                logger.error(f"Traceback:", exc_info=True)
                raise
                
            connection_pool = await self._connection_pool()
            if connection_pool:
                checkpointer = AsyncMongoDBSaver(connection_pool)
                await checkpointer.setup()
            else:
                raise Exception("Connection pool init failed")
            
            self._graph = graph_builder.compile(checkpointer=checkpointer)
            
        return self._graph
                
                
    
        
        
    
    