"""This file contains the chat schema for the application."""

import re
from typing import (
    List,
    Literal,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

class Listing(BaseModel):
    """Listing model for chat endpoint.w
    """
    id: str = Field(..., description="The ID of the listing")
    title: str = Field(..., description="The title of the listing")
    price: str = Field(..., description="The price of the listing")
    images: List[str] = Field(..., description="The images of the listing")
    bedrooms: int = Field(..., description="The number of bedrooms of the listing")
    bathrooms: int = Field(..., description="The number of bathrooms of the listing")
    area: int = Field(..., description="The area of the listing")
    location: str = Field(..., description="The location of the listing")
    description: str = Field(..., description="The description of the listing")
    url: str = Field(..., description="The URL of the listing")

class Message(BaseModel):
    """Message model for chat endpoint.

    Attributes:
        role: The role of the message sender (user or assistant).
        content: The content of the message.
    """

    model_config = {"extra": "ignore"}

    role: Literal["user", "assistant", "system"] = Field(..., description="The role of the message sender")
    content: str = Field(..., description="The content of the message", min_length=1, max_length=3000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate the message content.

        Args:
            v: The content to validate

        Returns:
            str: The validated content

        Raises:
            ValueError: If the content contains disallowed patterns
        """
        # Check for potentially harmful content
        if re.search(r"<script.*?>.*?</script>", v, re.IGNORECASE | re.DOTALL):
            raise ValueError("Content contains potentially harmful script tags")

        # Check for null bytes
        if "\0" in v:
            raise ValueError("Content contains null bytes")

        return v


class ChatRequest(BaseModel):
    """Request model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
    """

    messages: List[Message] = Field(
        ...,
        description="List of messages in the conversation",
        min_length=1,
    
    )
    
    


class ChatResponse(BaseModel):
    """Response model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
    """

    messages: List[Message] = Field(..., description="List of messages in the conversation")
    job_id: str = Field(..., description="Job ID")
    listings: List[dict] = Field(..., description="List of listings")
    map_data: dict = Field(..., description="Map data")


class StreamResponse(BaseModel):
    """Response model for streaming chat endpoint.

    Attributes:
        content: The content of the current chunk.
        done: Whether the stream is complete.
    """

    content: str = Field(default="", description="The content of the current chunk")
    done: bool = Field(default=False, description="Whether the stream is complete")
