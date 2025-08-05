from typing import Annotated, TypedDict, List, Dict, Optional
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

# Initialisation synchrone du checkpointer
from langgraph.checkpoint.mongodb import MongoDBSaver, AsyncMongoDBSaver

# from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from dotenv import load_dotenv
from tools.searchFacebook import SearchFacebook
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from langchain.tools import Tool
from langchain.tools import StructuredTool
import os
import random
import json
from langchain_core.messages import ToolMessage
from tools.googlePlaces import GooglePlaces
import asyncio
import logging

from database import MongoDB


# from IPython.display import Image, display  # Commenté car problématique
from tools.base_tool import BaseTool
from langgraph.checkpoint.memory import MemorySaver
import time
from pydantic import BaseModel, Field
from typing import Any
from langgraph.types import interrupt, Command

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Désactiver les logs de debug de PyMongo
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
logging.getLogger("pymongo.connection").setLevel(logging.WARNING)
logging.getLogger("pymongo.server").setLevel(logging.WARNING)
logging.getLogger("pymongo.pool").setLevel(logging.WARNING)


async def initialize_graph_with_checkpointer(
    graph_builder, mongo_uri: str, enable_logging: bool = True
):
    """
    Initialise le checkpointer MongoDB et compile le graph avec gestion d'erreurs.

    Args:
        graph_builder: Le StateGraph builder à compiler
        mongo_uri: L'URI de connexion MongoDB
        enable_logging: Active/désactive les logs (défaut: True)

    Returns:
        Le graph compilé avec le checkpointer

    Raises:
        Exception: Si l'initialisation échoue
    """
    try:
        async with AsyncMongoDBSaver.from_conn_string(mongo_uri) as checkpointer:
            if enable_logging:
                logger.info("Checkpointer MongoDB initialisé avec succès")

            if enable_logging:
                logger.info("Compilation du graph...")
            graph = graph_builder.compile(checkpointer=checkpointer)
            if enable_logging:
                logger.info("Graph compilé avec succès")

            return graph

    except Exception as e:
        if enable_logging:
            logger.error(f"Erreur compilation du graph: {e}")
            logger.error(f"Traceback:", exc_info=True)
        raise


def create_graph_with_mongodb_checkpointer(
    graph_builder, mongo_uri: str = None, enable_logging: bool = True
):
    """
    Fonction utilitaire pour créer un graph avec checkpointer MongoDB.

    Args:
        graph_builder: Le StateGraph builder à compiler
        mongo_uri: L'URI de connexion MongoDB (utilise MONGO_URI env si None)
        enable_logging: Active/désactive les logs (défaut: True)

    Returns:
        Le graph compilé avec le checkpointer
    """
    if mongo_uri is None:
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError(
                "MONGO_URI non configurée dans les variables d'environnement"
            )

    return asyncio.run(
        initialize_graph_with_checkpointer(graph_builder, mongo_uri, enable_logging)
    )


print("Imports terminés, chargement des variables d'environnement...")
logger.info("=== DÉBUT INITIALISATION IAN ===")

# Charger les variables d'environnement
load_dotenv()
logger.info("Variables d'environnement chargées")


# Classes for state variables
class RangeFilter(TypedDict, total=False):
    min: int
    max: int


print("Initialisation du state...")
logger.info("Initialisation des classes de state")


class State(TypedDict):
    messages: Annotated[List, add_messages]
    system_prompt: str
    what_to_avoid: str
    what_worked_before: str
    preferences: str
    bedrooms: Dict[str, RangeFilter]
    price: Dict[str, RangeFilter]
    location: Dict[str, RangeFilter]
    others: Dict[str, RangeFilter]


logger.info("Tentative de connexion à MongoDB pour le checkpointer...")
mongo_uri = os.getenv("MONGO_URI")
logger.info(f"MONGO_URI configurée: {'Oui' if mongo_uri else 'Non'}")

# Variables globales pour les services
facebook = None
google_places = None
graph = None

try:

    # Initialize services
    logger.info("Initialisation des services...")

    try:
        facebook = SearchFacebook()
        logger.info("SearchFacebook initialisé avec succès")
    except Exception as e:
        logger.error(f"Erreur initialisation SearchFacebook: {e}")
        logger.error(f"Traceback:", exc_info=True)
        facebook = None

    try:
        google_places = GooglePlaces()
        logger.info("GooglePlaces initialisé avec succès")
    except Exception as e:
        logger.error(f"Erreur initialisation GooglePlaces: {e}")
        logger.error(f"Traceback:", exc_info=True)
        google_places = None

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

    def find_fields_missing(state: State) -> List[str]:
        """Find missing fields in preferences"""
        logger.info(f"Vérification des champs manquants dans state: {state}")
        missing = []
        if not state.get("price"):
            missing.append("price")
        if not state.get("bedrooms"):
            missing.append("bedrooms")
        if not state.get("location"):
            missing.append("location")
        logger.info(f"Champs manquants: {missing}")
        return missing

    def human_pref_validator(state: State, tool_call_id: str) -> Command:
        logger.info(f"=== DÉBUT HUMAN_PREF_VALIDATOR ===")
        logger.info(f"State reçu: {state}")
        logger.info(f"Tool call ID: {tool_call_id}")

        try:
            missing_fields = find_fields_missing(state)

            if not missing_fields:
                logger.info("Tous les champs requis sont présents")
                result = interrupt(
                    f"Si je comprends bien vous cherchez un appartement avec ces caractéristiques?",
                    price=state.get("price"),
                    bedrooms=state.get("bedrooms"),
                    location=state.get("location"),
                    others=state.get("others"),
                )
                logger.info(f"Résultat interrupt: {result}")

                if result["type"] == "correct":
                    logger.info("Validation correcte")
                    return Command(
                        update={
                            "validation_complete": True,
                            "messages": [
                                ToolMessage(
                                    "Préférences OK, recherche en cours...",
                                    tool_call_id=tool_call_id,
                                )
                            ],
                        }
                    )
                elif result["type"] == "edit":
                    logger.info("Édition des préférences")
                    updated_preferences = result.get("preferences", {})
                    return Command(
                        goto="human_pref_validator",
                        update={
                            "price": updated_preferences.get("price", state["price"]),
                            "bedrooms": updated_preferences.get(
                                "bedrooms", state["bedrooms"]
                            ),
                            "location": updated_preferences.get(
                                "location", state["location"]
                            ),
                            "others": updated_preferences.get(
                                "others", state["others"]
                            ),
                            "messages": [
                                ToolMessage(
                                    "Préférences mises à jour",
                                    tool_call_id=tool_call_id,
                                )
                            ],
                        },
                    )
                else:
                    logger.error(f"Type de réponse inconnu: {result['type']}")
                    raise ValueError(f"Type de réponse inconnu: {result['type']}")

            else:
                logger.info(f"Champs manquants: {missing_fields}")
                result = interrupt(
                    f"Il me manque ces informations pour vous aider :\n"
                    f"{', '.join(missing_fields)}\n"
                    "Veuillez les fournir."
                )
                logger.info(f"Résultat interrupt pour champs manquants: {result}")

                verified_bedrooms = result.get("bedrooms", state["bedrooms"])
                verified_price = result.get("price", state["price"])
                verified_location = result.get("location", state["location"])

                state_update = {
                    "messages": [
                        ToolMessage(
                            f"Préférences confirmées: {result}",
                            tool_call_id=tool_call_id,
                        )
                    ],
                    "bedrooms": verified_bedrooms,
                    "price": verified_price,
                    "location": verified_location,
                }

                logger.info(f"State update: {state_update}")
                logger.info("=== FIN HUMAN_PREF_VALIDATOR ===")
                return Command(goto="human_pref_validator", update=state_update)

        except Exception as e:
            logger.error(f"Erreur dans human_pref_validator: {e}")
            logger.error(f"Traceback:", exc_info=True)
            raise

    def get_messages(state: State):
        """Get the messages from the state"""
        logger.info(f"=== DÉBUT GET_MESSAGES ===")
        logger.info(f"State reçu: {state}")

        thread_id = state.get("thread_id")
        logger.info(f"thread_id trouvée: {thread_id}")

        print("thread_id touvée!: ", thread_id)

        if not thread_id:
            logger.warning("Aucun thread_id trouvé")
            return {"messages": []}

        try:
            logger.info("Récupération de l'historique de chat...")
            chat_history = mongo_db.get_chat_history(thread_id)
            logger.info(f"Historique de chat récupéré: {chat_history is not None}")

            if chat_history is None:
                logger.warning("Aucun historique de chat trouvé")
                return {"messages": []}

            messages = chat_history.get("messages", [])
            logger.info(f"Nombre de messages récupérés: {len(messages)}")
            logger.info("=== FIN GET_MESSAGES ===")
            return {"messages": messages}

        except Exception as e:
            logger.error(f"Erreur dans get_messages: {e}")
            logger.error(f"Traceback:", exc_info=True)
            return {"messages": []}

    def chatbot(state: State):
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

    # Initialize graph components
    logger.info("Initialisation des composants du graph...")

    try:
        tool_node = ToolNode([search_listing])
        logger.info("ToolNode initialisé avec succès")
    except Exception as e:
        logger.error(f"Erreur initialisation ToolNode: {e}")
        logger.error(f"Traceback:", exc_info=True)
        raise

    # Utiliser init_chat_model au lieu de ChatOpenAI directement
    try:
        logger.info("Initialisation du modèle ChatOpenAI...")
        moveout = ChatOpenAI(model="gpt-4o-mini")
        moveout = moveout.bind_tools([search_listing], parallel_tool_calls=False)
        logger.info("Modèle ChatOpenAI initialisé avec succès")
    except Exception as e:
        logger.error(f"Erreur initialisation ChatOpenAI: {e}")
        logger.error(f"Traceback:", exc_info=True)
        raise

    try:
        graph_builder = StateGraph(State)
        logger.info("StateGraph initialisé avec succès")
    except Exception as e:
        logger.error(f"Erreur initialisation StateGraph: {e}")
        logger.error(f"Traceback:", exc_info=True)
        raise

    # Add nodes
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

    # Add edges
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

    # try:
    #     logger.info(f"Checkpointer disponible: {checkpointer}")
    # except Exception as e:
    #     logger.error(f"Error initializing checkpointer: {e}")
    #     logger.error(f"Traceback:", exc_info=True)
    #     raise

    try:

        graph = initialize_graph_with_checkpointer(graph_builder, mongo_uri)

    except Exception as e:
        logger.error(f"Erreur compilation du graph: {e}")
        logger.error(f"Traceback:", exc_info=True)
        raise

    logger.info("=== FIN INITIALISATION IAN ===")

except Exception as e:
    logger.error(f"Erreur critique lors de l'initialisation d'Ian: {e}")
    logger.error(f"Traceback complet:", exc_info=True)
    raise
finally:
    logger.info("Nettoyage des ressources d'Ian")
