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
from utils import dump_messages

# Configuration du logging
logger = logging.getLogger(__name__)

# from agents.tools import search_listing

# Initialisation des outils
google_places = None
facebook = None

try:
    google_places = GooglePlaces()
    logger.info("GooglePlaces initialisé avec succès")
except Exception as e:
    logger.error(f"Erreur initialisation GooglePlaces: {e}")
    google_places = None

try:
    facebook = SearchFacebook()
    logger.info("SearchFacebook initialisé avec succès")
except Exception as e:
    logger.error(f"Erreur initialisation SearchFacebook: {e}")
    facebook = None


@tool
def search_listing(
    city: str,
    min_bedrooms: int,
    max_bedrooms: int,
    min_price: int,
    max_price: int,
    location_near: Optional[list] = None,
):
    """Search listings in listings website according to user preferences.

    Args:
        city: The city to search in
        min_bedrooms: Minimum bedrooms wanted
        max_bedrooms: Maximum bedrooms wanted
        min_price: Minimum price wanted
        max_price: Maximum price wanted
        location_near: Optional nearby locations in a list

    """
    logger.info(f"=== DÉBUT SEARCH_LISTING ===")
    logger.info(
        f"Paramètres reçus: city={city}, min_bedrooms={min_bedrooms}, max_bedrooms={max_bedrooms}, min_price={min_price}, max_price={max_price}, location_near={location_near}"
    )

    try:
        default_radius = 500
        logger.info("Appel de GooglePlaces.execute...")
        response = google_places.execute(city, location_near)
        logger.info(f"Réponse GooglePlaces: {response}")

        places = response.get("places", [])
        logger.info(f"Nombre de places trouvées: {len(places)}")

        if not places:
            logger.warning("Aucune place trouvée")
            return []

        randomIndex = random.randrange(len(places))
        selected_place = places[randomIndex]
        logger.info(f"Place sélectionnée (index {randomIndex}): {selected_place}")

        lat = selected_place["location"]["latitude"]
        lon = selected_place["location"]["longitude"]
        name = selected_place["displayName"]["text"]

        logger.info(f"Coordonnées extraites: lat={lat}, lon={lon}, name={name}")

        print("Selected location:", f"{name} (lat: {lat}, lon: {lon})")

        logger.info("Appel de Facebook.execute...")
        result = facebook.execute(
            lat, lon, min_price, max_price, min_bedrooms, max_bedrooms
        )
        logger.info(
            f"Résultat Facebook: {len(result) if isinstance(result, list) else 'Non-liste'} éléments"
        )
        logger.info("=== FIN SEARCH_LISTING ===")
        return result

    except Exception as e:
        logger.error(f"Erreur dans search_listing: {e}")
        logger.error(f"Traceback:", exc_info=True)
        raise


class IanGraph:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=1000,
        ).bind_tools([search_listing])
        self._client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
        self._graph: Optional[CompiledStateGraph] = None

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
        if self._graph is None:
            self._graph = await self.create_graph()

        config = {
            "configurable": {"thread_id": session_id},
            "metadata": {
                "debug": False,
            },
        }
        try:
            response = await self._graph.ainvoke(
                {"messages": dump_messages(messages), "session_id": session_id}, config
            )
            return self.__process_message(response["messages"])
        except Exception as e:
            logger.error(f"error_getting_response: {e}")
            raise e

    async def _chat(self, state: GraphState) -> dict:

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

        if self._graph is None:
            # ✅ Utilise MongoDB, pas PostgreSQL
            async with AsyncMongoDBSaver.from_conn_string(
                os.getenv("MONGO_URI")
            ) as checkpointer:
                # ... votre logique de graph
                self._graph = graph_builder.compile(checkpointer=checkpointer)
        return self._graph
