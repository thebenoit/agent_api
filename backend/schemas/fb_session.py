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
    failure_count: int = Field(default=0, description="le nombre de fois que cela échoue")
    health_status: str
    failure_count: int = Field(default=0, description="Nombre d'échecs consécutifs")
    last_success: Optional[datetime] = Field(default=None, description="Dernière réussite")
    last_failure: Optional[datetime] = Field(default=None, description="Dernier échec")
    last_failure_reason: Optional[str] = Field(default=None, description="Raison du dernier échec")
    
    def get_health_status(self) -> str:
        """Retourne le statut de santé basé sur les échecs"""
        logger.info(
            "🔍 [get_health_status] Vérification du health status pour user_id=%s (failure_count=%d)",
            self.user_id, self.failure_count
        )
        if self.failure_count >= 3:
            logger.info("🚩 [get_health_status] La session est considérée comme unhealthy (user_id=%s)", self.user_id)
            return "unhealthy"
        elif self.failure_count >= 2:
            logger.info("⚠️ [get_health_status] La session est dégradée (user_id=%s)", self.user_id)
            return "degraded"
        else:
            logger.info("✅ [get_health_status] La session est healthy (user_id=%s)", self.user_id)
            return "healthy"
        
    def is_healthy(self) -> bool:
        """
        Une session est saine si:
        1. Elle est active
        2. Elle a moins de 3 échecs consécutifs
        3. Elle a les champs requis
        """
        logger.info("🔍 [is_healthy] Vérification de la santé de la session user_id=%s", self.user_id)
        result = (
            self.active 
            and self.failure_count < 3 
            and self.has_required_fields()
        )
        if result:
            logger.info("🟢 [is_healthy] La session user_id=%s est saine !", self.user_id)
        else:
            logger.warning("🔴 [is_healthy] La session user_id=%s n'est PAS saine.", self.user_id)
        return result
        
    def record_failure(self, reason: str = "Unknown error"):
        """Enregistre un échec d'utilisation de la session"""
        logger.error(
            "❌ [record_failure] Echec pour user_id=%s. Raison: %s | Compteur précédent: %d",
            self.user_id,
            reason,
            self.failure_count
        )
        self.failure_count += 1
        self.last_failure = datetime.utcnow()
        self.last_failure_reason = reason
        
        logger.error(
            "❌ [record_failure] Nouveau failure_count pour user_id=%s: %d",
            self.user_id,
            self.failure_count
        )

        if self.failure_count >= 3:
            self.active = False  # Désactiver automatiquement
            logger.critical(
                "☠️ [record_failure] Session user_id=%s marquée comme unhealthy après %d échecs consécutifs. Raison finale: %s",
                self.user_id,
                self.failure_count,
                reason
            )

    def record_success(self):
        """Enregistre une utilisation réussie - reset le compteur d'échecs"""
        logger.info(
            "🎉 [record_success] Succès pour user_id=%s. Reset du compteur de failure (avant: %d)",
            self.user_id,
            self.failure_count
        )
        self.failure_count = 0  # 🎉 Reset!
        self.last_success = datetime.now(datetime.UTC)
        self.last_used = datetime.now(datetime.UTC)
        self.last_failure_reason = None
        
        logger.info(
            "🟩 [record_success] Session user_id=%s: succès enregistré, failure_count remis à 0. last_success mis à jour.",
            self.user_id
        )
        
    
    def has_required_fields(self) -> bool:
        """
        Vérifie que les champs critiques sont présents
        """
        logger.debug("🔎 [has_required_fields] Vérification des champs requis pour user_id=%s ...", self.user_id)
        
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
                "🚨 [has_required_fields] Champs requis manquants pour user_id=%s: %s",
                self.user_id,
                missing_fields
            )
        else:
            logger.info("✅ [has_required_fields] Tous les champs requis sont présents pour user_id=%s", self.user_id)
        
        return is_valid
    
 
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
