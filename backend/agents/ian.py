from typing import Annotated, TypedDict, List, Dict, Optional
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
#from langchain_openai import ChatOpenAI
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


# from IPython.display import Image, display  # Commenté car problématique
from tools.base_tool import BaseTool
from langgraph.checkpoint.memory import MemorySaver
import time
from pydantic import BaseModel, Field
from typing import Any
from langgraph.types import interrupt, Command

print("Imports terminés, chargement des variables d'environnement...")

# Charger les variables d'environnement
load_dotenv()


# Classes for state variables
class RangeFilter(TypedDict, total=False):
    min: int
    max: int


print("Initialisation du state...")


class State(TypedDict):
    messages: Annotated[List, add_messages]
    bedrooms: Dict[str, RangeFilter]
    price: Dict[str, RangeFilter]
    location: Dict[str, RangeFilter]
    others: Dict[str, RangeFilter]


# Initialize services
facebook = SearchFacebook()
google_places = GooglePlaces()

config = {"configurable": {"thread_id": "1"}}


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
    default_radius = 500
    response = google_places.execute(city, location_near)
    places = response.get('places', [])
    if not places:
        return []
        
    randomIndex = random.randrange(len(places))
    selected_place = places[randomIndex]
    lat = selected_place['location']['latitude']
    lon = selected_place['location']['longitude']
    name = selected_place['displayName']['text']
    
    print(
        "Selected location:",
        f"{name} (lat: {lat}, lon: {lon})"
    )
    
    return facebook.execute(lat, lon, min_price, max_price, min_bedrooms, max_bedrooms)


def find_fields_missing(state: State) -> List[str]:
    """Find missing fields in preferences"""
    missing = []
    if not state.get("price"):
        missing.append("price")
    if not state.get("bedrooms"):
        missing.append("bedrooms")
    if not state.get("location"):
        missing.append("location")
    return missing


def human_pref_validator(state: State, tool_call_id: str) -> Command:
    missing_fields = find_fields_missing(state)

    if not missing_fields:
        result = interrupt(
            f"Si je comprends bien vous cherchez un appartement avec ces caractéristiques?",
            price=state.get("price"),
            bedrooms=state.get("bedrooms"),
            location=state.get("location"),
            others=state.get("others"),
        )

        if result["type"] == "correct":
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
            updated_preferences = result.get("preferences", {})
            return Command(
                goto="human_pref_validator",
                update={
                    "price": updated_preferences.get("price", state["price"]),
                    "bedrooms": updated_preferences.get("bedrooms", state["bedrooms"]),
                    "location": updated_preferences.get("location", state["location"]),
                    "others": updated_preferences.get("others", state["others"]),
                    "messages": [
                        ToolMessage(
                            "Préférences mises à jour", tool_call_id=tool_call_id
                        )
                    ],
                },
            )
        else:
            raise ValueError(f"Type de réponse inconnu: {result['type']}")

    else:
        result = interrupt(
            f"Il me manque ces informations pour vous aider :\n"
            f"{', '.join(missing_fields)}\n"
            "Veuillez les fournir."
        )

        verified_bedrooms = result.get("bedrooms", state["bedrooms"])
        verified_price = result.get("price", state["price"])
        verified_location = result.get("location", state["location"])

        state_update = {
            "messages": [
                ToolMessage(
                    f"Préférences confirmées: {result}", tool_call_id=tool_call_id
                )
            ],
            "bedrooms": verified_bedrooms,
            "price": verified_price,
            "location": verified_location,
        }

        return Command(goto="human_pref_validator", update=state_update)


def chatbot(state: State):
    """Send message list to LLM and return response"""
    return {"messages": [moveout.invoke(state["messages"])]}


# Initialize graph components
tool_node = ToolNode([search_listing])

# Utiliser init_chat_model au lieu de ChatOpenAI directement
moveout = init_chat_model("gpt-4o-mini", model_provider="openai")
moveout = moveout.bind_tools([search_listing], parallel_tool_calls=False)

graph_builder = StateGraph(State)

# Add nodes
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("human_verif", human_pref_validator)
graph_builder.add_node("tools", tool_node)

# Add edges
graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")

# Compile graph
memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)


# stream the graph updates(display the messages)
def stream_graph_updates(user_input: str):
    for event in graph.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config=config,
    ):
        for value in event.values():
            if "messages" in value:
                message = value["messages"][-1]
                if isinstance(message, ToolMessage):
                    print(f"TOOL RESULT: {message.content}")
                print("moveout3.0:", message.pretty_print())


# while True:
#     try:
#         user_input = input("User: ")
#         if user_input.lower() in ["quit", "exit", "q"]:
#             print("Goodbye!")
#             break
#         stream_graph_updates(user_input)
#     except:
#         # fallback if input() is not available
#         user_input = "What do you know about LangGraph?"
#         print("User: " + user_input)
#         stream_graph_updates(user_input)
#         break
    
    
if __name__ == "__main__":
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            stream_graph_updates(user_input)
        except:
            # fallback if input() is not available
            user_input = "What do you know about LangGraph?"
            print("User: " + user_input)
            stream_graph_updates(user_input)
            break
    
    
