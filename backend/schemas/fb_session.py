"""Facebook session schema for data validation."""

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field


class FacebookSession(BaseModel):
    """Schema for Facebook session data."""

    user_id: str = Field(..., description="User identifier")
    cookies: Dict[str, str] = Field(default_factory=dict, description="Session cookies")
    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")
    user_agent: str = Field(..., description="Browser user agent")
    payload: Dict[str, str] = Field(
        default_factory=dict, description="GraphQL payload template"
    )
    variables: Dict = Field(default_factory=dict, description="GraphQL variables")
    doc_id: str = Field(default="", description="Facebook document ID for GraphQL")
    x_fb_lsd: str = Field(default="", description="Facebook LSD token")
    active: bool = Field(default=True, description="Whether session is active")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    last_used: Optional[datetime] = Field(
        default=None, description="Last usage timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
