import pytest
from datetime import datetime, timedelta
from schemas.fb_session import FacebookSession
from models.fb_sessions import FacebookSessionModel

class TestSessionHealthTracking:
    """Tests pour le tracking de santé des sessions"""
    
    def test_new_session_is_healthy(self):
        """Une nouvelle session devrait être healthy"""
        session = FacebookSession(
            user_id="test_user_123",
            user_agent="Mozilla/5.0",
            doc_id="123456",
            headers={"x-fb-lsd": "abc", "user-agent": "Mozilla/5.0"},
            payload={"doc_id": "123"}
        )
        
        assert session.failure_count == 0
        assert session.health_status == "healthy"
        assert session.is_healthy() == True
    
    def test_session_with_one_failure_still_healthy(self):
        """Une session avec 1 échec reste healthy (tolérance)"""
        session = FacebookSession(
            user_id="test_user_123",
            user_agent="Mozilla/5.0",
            doc_id="123456",
            headers={"x-fb-lsd": "abc", "user-agent": "Mozilla/5.0"},
            payload={"doc_id": "123"},
            failure_count=1
        )
        
        assert session.is_healthy() == True
        assert session.get_health_status() == "healthy"
    
    def test_session_with_two_failures_is_degraded(self):
        """Une session avec 2 échecs est degraded (attention)"""
        session = FacebookSession(
            user_id="test_user_123",
            user_agent="Mozilla/5.0",
            doc_id="123456",
            headers={"x-fb-lsd": "abc", "user-agent": "Mozilla/5.0"},
            payload={"doc_id": "123"},
            failure_count=2
        )
        
        assert session.is_healthy() == True  # Encore utilisable
        assert session.get_health_status() == "degraded"
    
    def test_session_with_three_failures_is_unhealthy(self):
        """Une session avec 3 échecs est unhealthy (morte)"""
        session = FacebookSession(
            user_id="test_user_123",
            user_agent="Mozilla/5.0",
            doc_id="123456",
            headers={"x-fb-lsd": "abc", "user-agent": "Mozilla/5.0"},
            payload={"doc_id": "123"},
            failure_count=3
        )
        
        assert session.is_healthy() == False
        assert session.get_health_status() == "unhealthy"
    
    def test_record_failure_increments_count(self):
        """Enregistrer un échec incrémente le compteur"""
        session = FacebookSession(
            user_id="test_user_123",
            user_agent="Mozilla/5.0",
            doc_id="123456",
            headers={"x-fb-lsd": "abc", "user-agent": "Mozilla/5.0"},
            payload={"doc_id": "123"}
        )
        
        session.record_failure("Connection timeout")
        assert session.failure_count == 1
        assert session.last_failure is not None
    
    def test_record_success_resets_failure_count(self):
        """Un succès remet le compteur d'échecs à 0"""
        session = FacebookSession(
            user_id="test_user_123",
            user_agent="Mozilla/5.0",
            doc_id="123456",
            headers={"x-fb-lsd": "abc", "user-agent": "Mozilla/5.0"},
            payload={"doc_id": "123"},
            failure_count=2  # Avait 2 échecs
        )
        
        session.record_success()
        
        assert session.failure_count == 0  # Remis à zéro!
        assert session.last_success is not None
        assert session.is_healthy() == True


class TestFacebookSessionModelHealth:
    """Tests pour les opérations DB de health tracking"""
    
    def test_mark_failure_updates_count(self):
        """mark_failure devrait incrémenter le compteur"""
        # Ce test nécessite une vraie DB ou un mock
        # On va le faire avec pytest fixtures
        pass
    
    def test_mark_success_resets_failures(self):
        """mark_success devrait remettre à 0"""
        pass
    
    def test_get_unhealthy_sessions(self):
        """Devrait retourner toutes les sessions avec 3+ échecs"""
        pass