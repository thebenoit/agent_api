"""Facebook session model for database operations."""

from datetime import datetime
from typing import Optional, Dict, Any
from database_manager import mongo_manager
from schemas.fb_session import FacebookSession
import logging

logger = logging.getLogger(__name__)


class FacebookSessionModel:
    """Model for managing Facebook sessions in MongoDB."""

    def __init__(self):
        self.db = mongo_manager.get_sync_db()
        self.collection = self.db["fb_sessions"]
        logger.debug("FacebookSessionModel initialisé avec collection: fb_sessions")

    def save_session(self, session: FacebookSession) -> str:
        """Save a Facebook session to database."""
        logger.info("Sauvegarde d'une session pour user_id=%s", session.user_id)
        try:
            session_dict = session.dict()
            result = self.collection.insert_one(session_dict)
            inserted_id = str(result.inserted_id)
            logger.info(
                "Session sauvegardée avec succès pour user_id=%s, inserted_id=%s",
                session.user_id,
                inserted_id
            )
            return inserted_id
        except Exception as e:
            logger.error(
                "Erreur lors de la sauvegarde de la session pour user_id=%s: %s",
                session.user_id,
                e,
                exc_info=True
            )
            return None

    def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active session for a user."""
        logger.debug("Recherche d'une session active pour user_id=%s", user_id)
        try:
            session = self.collection.find_one({"user_id": user_id, "active": True})
            if session:
                logger.info("Session active trouvée pour user_id=%s", user_id)
            else:
                logger.debug("Aucune session active trouvée pour user_id=%s", user_id)
            return session
        except Exception as e:
            logger.error(
                "Erreur lors de la recherche de session pour user_id=%s: %s",
                user_id,
                e,
                exc_info=True
            )
            return None

    def update_session(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update session data for a user."""
        logger.info(
            "Mise à jour de la session pour user_id=%s avec %d champs",
            user_id,
            len(updates)
        )
        try:
            updates["last_used"] = datetime.utcnow()
            result = self.collection.update_one(
                {"user_id": user_id, "active": True}, {"$set": updates}
            )
            success = result.modified_count > 0
            if success:
                logger.info(
                    "Session mise à jour avec succès pour user_id=%s (modified_count=%d)",
                    user_id,
                    result.modified_count
                )
            else:
                logger.warning(
                    "Aucune session modifiée pour user_id=%s (matched_count=%d, modified_count=%d)",
                    user_id,
                    result.matched_count,
                    result.modified_count
                )
            return success
        except Exception as e:
            logger.error(
                "Erreur lors de la mise à jour de la session pour user_id=%s: %s",
                user_id,
                e,
                exc_info=True
            )
            return None

    def deactivate_session(self, user_id: str) -> bool:
        """Deactivate a user's session."""
        logger.info("Désactivation de la session pour user_id=%s", user_id)
        try:
            result = self.collection.update_one(
                {"user_id": user_id, "active": True}, {"$set": {"active": False}}
            )
            success = result.modified_count > 0
            if success:
                logger.info(
                    "Session désactivée avec succès pour user_id=%s (modified_count=%d)",
                    user_id,
                    result.modified_count
                )
            else:
                logger.warning(
                    "Aucune session désactivée pour user_id=%s (matched_count=%d, modified_count=%d)",
                    user_id,
                    result.matched_count,
                    result.modified_count
                )
            return success
        except Exception as e:
            logger.error(
                "Erreur lors de la désactivation de la session pour user_id=%s: %s",
                user_id,
                e,
                exc_info=True
            )
            return None

    def init_fb_session(self, user_id):
        logger.info("Initialisation de la session Facebook pour user_id=%s", user_id)
        try:
            session = self.get_session(user_id)

            if session:
                headers = session.get("headers")
                payload = session.get("payload")
                variables = session.get("variables")

                # Vérifier que les données nécessaires sont présentes
                if headers and payload:
                    logger.info(
                        "Session Facebook initialisée avec succès pour user_id=%s: headers=%d items, payload=%s",
                        user_id,
                        len(headers) if isinstance(headers, dict) else 0,
                        "présent" if payload else "absent"
                    )
                    return headers, payload, variables
                else:
                    logger.warning(
                        "Session trouvée mais données incomplètes pour user_id=%s: headers=%s, payload=%s",
                        user_id,
                        "présent" if headers else "absent",
                        "présent" if payload else "absent"
                    )
                    return None, None, None
            else:
                logger.warning("Aucune session active trouvée pour user_id=%s", user_id)
                return None, None, None

        except Exception as e:
            logger.error(
                "Erreur lors de l'initialisation de la session Facebook pour user_id=%s: %s",
                user_id,
                e,
                exc_info=True
            )
            return None, None, None

    def mark_session_failure(self, user_id: str, reason: str = "Unknown") -> bool:
        """
        Enregistre un échec pour une session.
        Désactive automatiquement si 3 échecs consécutifs.
        """
        logger.warning(
            "Enregistrement d'un échec pour user_id=%s. Raison: %s",
            user_id,
            reason
        )

        try:
            # Récupérer la session actuelle
            session_dict = self.get_session(user_id)
            if not session_dict:
                logger.error("Impossible de marquer l'échec: session inexistante pour user_id=%s", user_id)
                return False

            # Créer l'objet pour utiliser la méthode record_failure
            session = FacebookSession(**session_dict)
            session.record_failure(reason)

            # Préparer les updates
            updates = {
                "failure_count": session.failure_count,
                "last_failure": session.last_failure,
                "last_failure_reason": session.last_failure_reason,
            }

            # Si 3 échecs ou plus, désactiver
            if session.failure_count >= 3:
                updates["active"] = False
                logger.error(
                    "Session user_id=%s désactivée après %d échecs consécutifs",
                    user_id,
                    session.failure_count
                )

            # Sauvegarder en DB
            result = self.collection.update_one(
                {"user_id": user_id},
                {"$set": updates}
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(
                "Erreur lors du marquage d'échec pour user_id=%s: %s",
                user_id,
                e,
                exc_info=True
            )
            return False

    def mark_session_success(self, user_id: str) -> bool:
        """
        Enregistre un succès - remet le compteur d'échecs à 0.
        """
        logger.debug("Enregistrement d'un succès pour user_id=%s", user_id)

        try:
            updates = {
                "failure_count": 0,
                "last_success": datetime.utcnow(),
                "last_used": datetime.utcnow(),
                "last_failure_reason": None
            }

            result = self.collection.update_one(
                {"user_id": user_id, "active": True},
                {"$set": updates}
            )

            if result.modified_count > 0:
                logger.info("Succès enregistré pour user_id=%s, compteur d'échecs remis à 0", user_id)

            return result.modified_count > 0

        except Exception as e:
            logger.error(
                "Erreur lors du marquage de succès pour user_id=%s: %s",
                user_id,
                e,
                exc_info=True
            )
            return False

    def get_healthy_sessions(self) -> list:
        """Retourne toutes les sessions saines (failure_count < 3)"""
        try:
            sessions = self.collection.find({
                "active": True,
                "failure_count": {"$lt": 3}
            })
            return list(sessions)
        except Exception as e:
            logger.error("Erreur lors de la récupération des sessions saines: %s", e)
            return []

    def get_degraded_sessions(self) -> list:
        """Retourne les sessions dégradées (2 échecs)"""
        try:
            sessions = self.collection.find({
                "active": True,
                "failure_count": 2
            })
            return list(sessions)
        except Exception as e:
            logger.error("Erreur lors de la récupération des sessions dégradées: %s", e)
            return []