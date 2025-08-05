"""This file contains the graph schema for the application."""

import re
import uuid
from typing import Annotated, Dict, List

from langgraph.graph.message import add_messages
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class RangeFilter(BaseModel):
    """Filter for range values (min/max)."""

    min: int = Field(..., description="Minimum value")
    max: int = Field(..., description="Maximum value")


class GraphState(BaseModel):
    """State definition for the LangGraph Agent/Workflow."""

    messages: Annotated[list, add_messages] = Field(
        default_factory=list, description="The messages in the conversation"
    )
    session_id: str = Field(
        ..., description="The unique identifier for the conversation session"
    )

    # Attributs transmis depuis ian.py State
    system_prompt: str = Field(
        default="", description="System prompt for the conversation"
    )
    what_to_avoid: str = Field(default="", description="Things to avoid in the search")
    what_worked_before: str = Field(
        default="", description="What worked in previous searches"
    )
    preferences: str = Field(default="", description="User preferences")
    bedrooms: Dict[str, RangeFilter] = Field(
        default_factory=dict, description="Bedroom preferences"
    )
    price: Dict[str, RangeFilter] = Field(
        default_factory=dict, description="Price preferences"
    )
    location: Dict[str, RangeFilter] = Field(
        default_factory=dict, description="Location preferences"
    )
    others: Dict[str, RangeFilter] = Field(
        default_factory=dict, description="Other preferences"
    )

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validate that the session ID is a valid UUID or follows safe pattern.

        Args:
            v: The thread ID to validate

        Returns:
            str: The validated session ID

        Raises:
            ValueError: If the session ID is not valid
        """
        # Try to validate as UUID
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            # If not a UUID, check for safe characters only
            if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
                raise ValueError(
                    "Session ID must contain only alphanumeric characters, underscores, and hyphens"
                )
            return v
