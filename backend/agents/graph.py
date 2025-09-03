"""This file contains the LangGraph Agent/workflow and interactions with the LLM."""

from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Literal,
    Optional,
    List,
)
from motor.motor_asyncio import AsyncIOMotorClient

from typing_extensions import Annotated


from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
    convert_to_openai_messages,
    AIMessageChunk,
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langchain_openai import ChatOpenAI

from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from langgraph.prebuilt import ToolNode, tools_condition, InjectedState
from langgraph.graph import (
    END,
    START,
    StateGraph,
)
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot, Command, interrupt
from openai import OpenAIError
from services.search_service import SearchService

import os
import random
import logging
import json
from langchain_core.tools import tool
from langchain_core.callbacks.manager import AsyncCallbackManager
from langchain_core.callbacks.base import AsyncCallbackHandler
from agents.tools.searchFacebook import SearchFacebook
from agents.tools.googlePlaces import GooglePlaces
from schemas import (
    GraphState,
    Message,
    RangeFilter,
)
from utils import dump_messages, prepare_messages
from database_manager import mongo_manager
from database import mongo_db

# Configuration du logging
logger = logging.getLogger(__name__)

# Initialisation des outils
search_service = None
google_places = None
facebook = None

try:
    google_places = GooglePlaces()
    logger.info("GooglePlaces initialisé avec succès")
except Exception as e:
    logger.error(f"Erreur initialisation GooglePlaces: {e}")
    google_places = None

try:
    search_service = SearchService()
    logger.info("SearchService initialisé avec succès")
except Exception as e:
    logger.error(f"Erreur initialisation SearchService: {e}")
    search_service = None

try:
    facebook = SearchFacebook()
    logger.info("SearchFacebook initialisé avec succès")
except Exception as e:
    logger.error(f"Erreur initialisation SearchFacebook: {e}")
    facebook = None


@tool
async def search_listing(
    city: str,
    min_bedrooms: int,
    max_bedrooms: int,
    min_price: int,
    max_price: int,
    location_near: Optional[list] = None,
    enrich_top_k: int = 3,
    session_id: Annotated[str, InjectedState("session_id")] = None
):
    """Search listings in listings website according to user preferences.

    Args:
        city: The city to search in
        min_bedrooms: Minimum bedrooms wanted
        max_bedrooms: Maximum bedrooms wanted
        min_price: Minimum price wanted
        max_price: Maximum price wanted
        location_near: Optional nearby locations in a list
        enrich_top_k: Number of listings to enrich with page details
        state: The state of the graph

    """
    logger.info(f"=== DÉBUT SEARCH_LISTING ===")
    # logger.info(
    #     f"Paramètres reçus: city={city}, min_bedrooms={min_bedrooms}, max_bedrooms={max_bedrooms}, min_price={min_price}, max_price={max_price}, location_near={location_near}, enrich_top_k={enrich_top_k}"
    # )

    try:
        if not search_service:
            logger.error("SearchService non initialisé")
            return {"error": "Service de recherche non disponible"}


        search_params = {
            "city": city,
            "min_bedrooms": min_bedrooms,
            "max_bedrooms": max_bedrooms,
            "min_price": min_price,
            "max_price": max_price,
            "location_near": location_near,
            "enrich_top_k": enrich_top_k,
        }

        user_ip = "127.0.0.1"
        
        

        result = await search_service.search_listings(
            search_params,
            user_ip,
            session_id,
        )

        logger.info(f"Résultat SearchService: {result}\n")

        if result["status"] == "cached":
            logger.info("✅ Cache hit - Réponse instantanée\n")
            return {
                "status": "success",
                "data": result["data"],
                "source": "cache",
                "cached_at": result["cached_at"],
            }
        elif result["status"] == "queued":
            # 📋 JOB EN QUEUE : Non-bloquant !
            logger.info("📋 Job mis en queue - Non-bloquant\n")
            return {
                "status": "queued",
                "job_id": result["job_id"],
                "message": result["message"],
                "estimated_wait": result["estimated_wait"],
                "source": "queue",
            }
        elif result["status"] == "processing":
            # ⏳ JOB EN COURS : Déjà lancé
            logger.info("⏳ Job déjà en cours\n")
            return {
                "status": "processing",
                "job_id": result["job_id"],
                "estimated_wait": result["estimated_wait"],
                "source": "existing_job",
            }

        elif result["status"] == "completed":
            # ✅ JOB TERMINÉ : Résultat disponible
            logger.info("✅ Job terminé - Résultat disponible\n")
            return {
                "status": "success",
                "data": result["data"],
                "source": "completed_job",
            }
        elif result["status"] == "rate_limited":
            # 🚫 RATE LIMIT : Trop de requêtes
            logger.warning("🚫 Rate limit dépassé\n")
            return {
                "status": "rate_limited",
                "message": result["message"],
                "retry_after": result["retry_after"],
            }

        else:
            # ❌ ERREUR : Gestion d'erreur
            logger.error(f"❌ Statut inattendu: {result}\n")
            return {
                "status": "error",
                "message": result.get("message", "Erreur inconnue"),
                "error": result.get("error", "Erreur non spécifiée"),
            }

    except Exception as e:
        logger.error(f"Erreur dans search_listing: {e}\n")
        logger.error(f"Traceback:", exc_info=True)
        return {
            "status": "error",
            "message": "Erreur lors de la recherche",
            "error": str(e),
        }
    finally:
        logger.info("=== FIN SEARCH_LISTING ===")


@tool
async def check_job_status(job_id: str):
    """Check the status of a job.

    Args:
        job_id: The ID of the job to check

    Returns:
        dict: The status of the job
    """
    try:
        if not search_service:
            logger.error("SearchService non initialisé")
            return {"error": "Service de recherche non disponible"}

        result = await search_service.get_job_status(job_id)
        logger.info(f"Statut du job {job_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Erreur dans check_job_status: {e}")
        return {
            "status": "error",
            "message": "Erreur lors de la vérification du statut du job",
            "error": str(e),
        }


class IanGraph:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=1000,
         ).bind_tools([search_listing])
        # Utiliser le manager au lieu d'une connexion directe
        self._client = mongo_manager.get_async_client()
        self._graph: Optional[CompiledStateGraph] = None
        self._checkpointer: Optional[AsyncMongoDBSaver] = None
       
    def __process_message(self, messages: list[BaseMessage]) -> list[Message]:
        openai_style_messages = convert_to_openai_messages(messages)
        return [
            Message(**message)
            for message in openai_style_messages
            if message["role"] in ["assistant", "user"] and message["content"]
        ]
          
    def serialise_ai_message_chunk(self, chunk: dict) -> str:
        if(isinstance(chunk, AIMessageChunk)):
            return chunk.content
        else:
            raise TypeError(f"Expected AIMessageChunk, got {type(chunk).__name__}")

    def _coerce_messages(self, msgs: list[Any]) -> list[BaseMessage]:
        """Ensure history is a list of LangChain BaseMessage, preserving ToolMessages.

        Accepts history items as BaseMessage or dicts with role/content (and optional tool fields).
        """
        coerced: list[BaseMessage] = []
        for item in msgs:
            if isinstance(item, BaseMessage):
                coerced.append(item)
                continue
            if isinstance(item, dict):
                role = item.get("role")
                content = item.get("content", "")
                if role == "user":
                    coerced.append(HumanMessage(content=content))
                elif role == "assistant":
                    # Note: tool_calls not reconstructed here; if present, it's already BaseMessage upstream
                    coerced.append(AIMessage(content=content))
                elif role == "system":
                    coerced.append(SystemMessage(content=content))
                elif role == "tool":
                    coerced.append(
                        ToolMessage(
                            content=str(content),
                            tool_call_id=item.get("tool_call_id", ""),
                            name=item.get("name"),
                        )
                    )
        return coerced

    def _sanitize_messages(self, history: list[BaseMessage]) -> list[BaseMessage]:
        """Remove assistant messages with tool_calls that are not immediately followed by a ToolMessage.

        This prevents OpenAI 400 errors when an orphan tool_call appears in the trimmed history.
        """
        if not history:
            return history
        sanitized: list[BaseMessage] = []
        i = 0
        n = len(history)
        while i < n:
            msg = history[i]
            has_tool_calls = isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None)
            if has_tool_calls:
                next_is_tool = (i + 1 < n) and isinstance(history[i + 1], ToolMessage)
                if not next_is_tool:
                    # Skip this orphan tool_call message
                    i += 1
                    continue
            sanitized.append(msg)
            i += 1
        return sanitized

    async def get_stream_response(self, messages: list[Message], session_id: str):
        
        config = {
            "configurable": {"thread_id": session_id},
            "metadata": {
                "debug": False,
            },
        }
        
        try:
            # ✅ Créer le checkpointer et compiler le graph pour cette invocation
            async with AsyncMongoDBSaver.from_conn_string(
                os.getenv("MONGO_URI"),
                db_name=os.getenv("MONGO_DB"),
                collection_name="checkpointers",
            ) as checkpointer:

                # Créer le graph builder si pas encore fait
                if not hasattr(self, "_graph_builder"):
                    self._graph_builder = await self._create_graph_builder()

                # Compiler le graph avec le checkpointer pour cette invocation
                graph_with_checkpointer = self._graph_builder.compile(
                    checkpointer=checkpointer
                )
                
                events = graph_with_checkpointer.astream_events(
                    {"messages": dump_messages(messages), "session_id": session_id},
                    config=config,
                )
                async for event in events:
                    event_type = event["event"]
                    
                    # 🔍 DEBUG : Voir la structure de l'event
                    #print(f"Event reçu: {event}\n")
                    # print(f"Event type: {event_type}\n")
                    # print(f"Event data keys: {event.get('data', {}).keys()}")
                    
                    # ✅ APRÈS (sécurisé) - Vérifier AVANT d'accéder
                    if event_type in ("on_llm_stream","on_chat_model_stream") and "chunk" in event.get("data", {}):
                        chunk_content = self.serialise_ai_message_chunk(event["data"]["chunk"])
                        payload = {"type": "content", "content": chunk_content}
                        yield f"data: {json.dumps(payload)}\n\n"
                    # elif event_type == "on_chat_model_stream":
                    
                    
                    elif event_type == "on_chat_model_end":
                        data = event.get("data", {})
                        output = data.get("output")
                        if output and hasattr(output, "tool_calls"):
                            tool_calls = output.tool_calls
                            payload = {"type": "tool_calls", "tool_calls": tool_calls}
                            yield f"data: {json.dumps(payload)}\n\n"
                        
                    elif event_type == "on_tool_start":
                        data = event.get("data", {})
                        # certains événements ont 'name' et 'tool_input' directement
                        tool_name = data.get("name") or getattr(data.get("output"), "tool_name", "unknown")
                        tool_args = data.get("tool_input") or getattr(data.get("output"), "tool_input", {})
                        payload = {
                            "type": "tool_start",
                            "tool": tool_name,
                            "args": tool_args,
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                    
                    elif event_type == "on_tool_end":
                        print(f"Event reçu: {event}\n")
                        data = event.get("data", {})
                        # L'objet output contient la ToolMessage avec JSON dans content
                        output: ToolMessage = data.get("output")
                        if output:
                            # Émettre d'abord l'événement tool_end
                            payload = {"type": "tool_end", "tool": output.name, "result": output.content}
                            yield f"data: {json.dumps(payload)}\n\n"
                            # Puis parser le JSON de output.content
                            try:
                                result_data = json.loads(output.content)
                                print(f"result_data reçu: {result_data}\n")
                                if result_data.get("status") in ("queued", "processing") and result_data.get("job_id"):
                                    job_payload = {
                                        "type": "job",
                                        "job_id": result_data["job_id"],
                                        "status": result_data["status"],
                                        "estimated_wait": result_data.get("estimated_wait"),
                                    }
                                    print(f"job_payload reçu: {job_payload}\n")
                                    yield f"data: {json.dumps(job_payload)}\n\n"
                            except Exception as e:
                                print(f"Erreur parsing output.content: {e}")
                        
                    
                    elif event_type == "end" or (
                        event_type == "on_chain_end" and event.get("name") == "LangGraph"
                    ):
                        yield f"data: {json.dumps({'type': '[DONE]'})}\n\n"
                        break
                    
 

        except Exception as e:
            logger.error(f"error_getting_response: {e}")
            raise e
      

    async def _get_response(
        self,
        messages: list[Message],
        session_id: str,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """Get a response from the LLM."""
        logger.info(f"Session_id stocké pour cette session: {session_id}")
        
        config = {
            "configurable": {"thread_id": session_id},
            "metadata": {
                "debug": False,
            },
        }
        try:
            # ✅ Créer le checkpointer et compiler le graph pour cette invocation
            async with AsyncMongoDBSaver.from_conn_string(
                os.getenv("MONGO_URI"),
                db_name=os.getenv("MONGO_DB"),
                collection_name="checkpointers",
            ) as checkpointer:

                # Créer le graph builder si pas encore fait
                if not hasattr(self, "_graph_builder"):
                    self._graph_builder = await self._create_graph_builder()

                # Compiler le graph avec le checkpointer pour cette invocation
                graph_with_checkpointer = self._graph_builder.compile(
                    checkpointer=checkpointer
                )

                # Convertir session_id en string si c'est un ObjectId
                session_id_str = (
                    str(session_id) if hasattr(session_id, "__str__") else session_id
                )

                response = await graph_with_checkpointer.ainvoke(
                    {"messages": dump_messages(messages), "session_id": session_id_str},
                    config=config,
                )
                
                logger.info(f"response: {response} \n")
                
                
                
                return self.__process_message(response["messages"])
        except Exception as e:
            logger.error(f"error_getting_response: {e}")
            raise e

    async def _create_graph_builder(self):
        """Create the graph builder (without compilation)."""
        try:
            tool_node = ToolNode([search_listing])
            logger.info("ToolNode initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur initialisation ToolNode: {e}")
            logger.error(f"Traceback:", exc_info=True)
            raise

        try:
            graph_builder = StateGraph(GraphState)
            logger.info("StateGraph initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur initialisation StateGraph: {e}")
            logger.error(f"Traceback:", exc_info=True)
            raise
        

        logger.info("Ajout des nodes au graph...")
        try:
            graph_builder.add_node("chatbot", self._chat)
            # graph_builder.add_node("human_verif", human_pref_validator)
            graph_builder.add_node("tools",tool_node)
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

        return graph_builder

    async def _chat(self, state: GraphState) -> dict:

        logger.info(f"=== DÉBUT CHATBOT ===")
        
        if hasattr(state, "session_id"):
            logger.info(f"Session_id récupéré: {state.session_id}")
        else:
            logger.warning("Impossible de récupérer le session_id, utilisation du fallback")
            state.session_id = None

        try:
            
            logger.info(f"lenght of state.messages: {len(state.messages)}")

            # Build safe history: preserve ToolMessages, remove orphan tool_calls
            history = self._coerce_messages(state.messages)
            history = self._sanitize_messages(history)

            system_msg = SystemMessage(
                content="You are a helpful assistant that can search for listings and provide information about them."
            )
            llm_input: list[BaseMessage] = [system_msg] + history

            logger.info("Message ajouté au state")
            logger.info("=== FIN CHATBOT ===")

            ai_msg = await self.llm.ainvoke(llm_input)
            return {"messages": [ai_msg]}

        except Exception as e:
            logger.error(f"Erreur dans chatbot: {e}")
            logger.error(f"Traceback:", exc_info=True)
            raise
        
    
    async def tools_router(self,state: GraphState):
        logger.info(f"=== DÉBUT TOOLS_ROUTER ===")
        
        last_message = state["messages"][-1]
        
        if(hasattr(last_message, "tool_calls" and len(last_message.tool_calls) > 0)):
            logger.info(f"Tool calls detected: {last_message.tool_calls}")
            return "tool_node"
        else: 
            logger.info(f"No tool calls detected")
            return END
            
            
    async def custom_tool_node(self,state: GraphState):
        """custom handle that handle tool calls from the LLm"""
        logger.info(f"=== DÉBUT CUSTOM_TOOL_NODE ===")
        tool_calls = state["messages"][-1].tool_calls
        
        # Initialize list to store tool messaes
        tool_messages = []
        
        #process each tool call
        for tool_call in tool_calls:
            logger.info(f"Processing tool call: {tool_call}")
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]
            
            if tool_name == "search_listing":
                logger.info(f"Processing search_listing tool call: {tool_args}")
                args = dict(tool_args)
                if "session_id" not in args:
                    args["session_id"] = state.session_id

                search_results = await search_listing.ainvoke(args)

                tool_message = ToolMessage(
                    content=json.dumps(search_results),
                    tool_call_id=tool_id,
                    name=tool_name,
                )

                tool_messages.append(tool_message)
        
        return {"messages": tool_messages}
                
                
               
        
        
        
