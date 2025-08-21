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


from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
    convert_to_openai_messages,
)
from langchain_openai import ChatOpenAI

from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from langgraph.prebuilt import ToolNode, tools_condition
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
from langchain_core.tools import tool
from agents.tools.searchFacebook import SearchFacebook
from agents.tools.googlePlaces import GooglePlaces
from schemas import (
    GraphState,
    Message,
    RangeFilter,
)
from utils import dump_messages, prepare_messages
from database_manager import mongo_manager

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

    """
    logger.info(f"=== DÉBUT SEARCH_LISTING ===")
    logger.info(
        f"Paramètres reçus: city={city}, min_bedrooms={min_bedrooms}, max_bedrooms={max_bedrooms}, min_price={min_price}, max_price={max_price}, location_near={location_near}, enrich_top_k={enrich_top_k}"
    )

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
        user_id = "default_user"

        logger.info("Appel de SearchService.search_listings...")
        result = await search_service.search_listings(
            search_params,
            user_ip,
            user_id,
        )

        logger.info(f"Résultat SearchService: {result}")

        if result["status"] == "cached":
            logger.info("✅ Cache hit - Réponse instantanée")
            return {
                "status": "success",
                "data": result["data"],
                "source": "cache",
                "cached_at": result["cached_at"],
            }
        elif result["status"] == "queued":
            # 🔄 JOB EN QUEUE : Non-bloquant !
            logger.info("🔄 Job mis en queue - Non-bloquant")
            return {
                "status": "queued",
                "job_id": result["job_id"],
                "message": result["message"],
                "estimated_wait": result["estimated_wait"],
                "source": "queue",
            }
        elif result["status"] == "processing":
            # ⏳ JOB EN COURS : Déjà lancé
            logger.info("⏳ Job déjà en cours")
            return {
                "status": "processing",
                "job_id": result["job_id"],
                "estimated_wait": result["estimated_wait"],
                "source": "existing_job",
            }

        elif result["status"] == "completed":
            # ✅ JOB TERMINÉ : Résultat disponible
            logger.info("✅ Job terminé - Résultat disponible")
            return {
                "status": "success",
                "data": result["data"],
                "source": "completed_job",
            }
        elif result["status"] == "rate_limited":
            # 🚫 RATE LIMIT : Trop de requêtes
            logger.warning("🚫 Rate limit dépassé")
            return {
                "status": "rate_limited",
                "message": result["message"],
                "retry_after": result["retry_after"],
            }

        else:
            # ❌ ERREUR : Gestion d'erreur
            logger.error(f"❌ Statut inattendu: {result}")
            return {
                "status": "error",
                "message": result.get("message", "Erreur inconnue"),
                "error": result.get("error", "Erreur non spécifiée"),
            }

    except Exception as e:
        logger.error(f"Erreur dans search_listing: {e}")
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
        ).bind_tools([search_listing, check_job_status])
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

    async def _get_response(
        self,
        messages: list[Message],
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
                return self.__process_message(response["messages"])
        except Exception as e:
            logger.error(f"error_getting_response: {e}")
            raise e

    async def _create_graph_builder(self):
        """Create the graph builder (without compilation)."""
        try:
            tool_node = ToolNode([search_listing, check_job_status])
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

        return graph_builder

    async def _chat(self, state: GraphState) -> dict:

        logger.info(f"=== DÉBUT CHATBOT ===")
        logger.info(f"State reçu: {state}")

        try:

            messages = prepare_messages(
                state.messages,
                self.llm,
                "You are a helpful assistant that can search for listings and provide information about them.",
            )

            logger.info("Message ajouté au state")
            logger.info("=== FIN CHATBOT ===")
            generated_state = {
                "messages": [await self.llm.ainvoke(dump_messages(messages))]
            }
            return generated_state

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
            # ✅ Utilise une connexion séparée pour le checkpointer
            # pour éviter de fermer la connexion principale
            checkpointer = AsyncMongoDBSaver.from_conn_string(
                os.getenv("MONGO_URI"),
                db_name=os.getenv("MONGO_DB"),
                collection_name="checkpointers",
            )
            # Créer le graph builder si pas encore fait
            if not hasattr(self, "_graph_builder"):
                self._graph_builder = await self._create_graph_builder()
                
            self._graph = self._graph_builder.compile(checkpointer=checkpointer)
        return self._graph
