"""Facebook session schema for data validation."""

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field
# from ..sessionManager import SessionsManager
# from ..services.search_service import SearchService
import logging

logger = logging.getLogger(__name__)

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
    
    def has_required_fields(self) -> bool:
        """
        Vérifie que les champs critiques sont présents
        """
        logger.debug("Vérification des champs requis pour user_id=%s", self.user_id)
        
        required_checks = [
            bool(self.user_agent),
            bool(self.doc_id),
            bool(self.headers.get("x-fb-lsd")),
            bool(self.headers.get("user-agent")),
            len(self.payload) > 0
        ]
        
        is_valid = all(required_checks)
        
        if not is_valid:
            missing_fields = []
            if not bool(self.user_agent):
                missing_fields.append("user_agent")
            if not bool(self.doc_id):
                missing_fields.append("doc_id")
            if not bool(self.headers.get("x-fb-lsd")):
                missing_fields.append("headers.x-fb-lsd")
            if not bool(self.headers.get("user-agent")):
                missing_fields.append("headers.user-agent")
            if len(self.payload) == 0:
                missing_fields.append("payload")
            
            logger.warning(
                "Champs requis manquants pour user_id=%s: %s",
                self.user_id,
                missing_fields
            )
        else:
            logger.debug("Tous les champs requis sont présents pour user_id=%s", self.user_id)
        
        return is_valid
    
 
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
