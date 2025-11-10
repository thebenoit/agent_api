import pytest
import asyncio
from agents.tools.searchFacebook import SearchFacebook
from models.fb_sessions import FacebookSessionModel
from schemas.fb_session import FacebookSession
from datetime import datetime

class TestSessionIntegration:
    
    def setup_method(self):
        """
        Setup avant chaque test
        """
        
        self.fb_model = FacebookSessionModel()
        self.searcher = SearchFacebook()
        self.test_user_id = "test_user_integration_123"
        
    def teardown_method(self):
        """Cleanup après chaque test"""
        # Nettoyer la session de test
        self.fb_model.collection.delete_many({"user_id": self.test_user_id})

    def test_session_success_resets_failure_count(self):
        """
        Scenario: Une session échoue 2 fois puis réussit
        Résultat attendu: Le compteur est remis à 0
        """
        # 1. Créer une session avec 2 échecs
        session = FacebookSession(
            user_id=self.test_user_id,
            user_agent="Mozilla/5.0",
            failure_count=2,
            doc_id="123",
            headers={"x-fb-lsd": "test", "user-agent": "test"},
            payload={"doc_id": "123"}
        )
        self.fb_model.save_session(session)
        
        # 2. Marquer un succès
        self.fb_model.mark_session_success(self.test_user_id)
        
        # 3. Vérifier que le compteur est à 0
        updated = self.fb_model.get_session(self.test_user_id)
        assert updated["failure_count"] == 0
        assert updated["active"] == True
        print("✅ Test passed: Success resets failure count")
        
    def test_session_deactivated_after_3_failures(self):
            """
            Scenario: Une session échoue 3 fois consécutives
            Résultat attendu: La session est désactivée
            """
            # 1. Créer une session saine
            session = FacebookSession(
                user_id=self.test_user_id,
                user_agent="Mozilla/5.0",
                doc_id="123",
                headers={"x-fb-lsd": "test", "user-agent": "test"},
                payload={"doc_id": "123"}
            )
            self.fb_model.save_session(session)
            
            # 2. Marquer 3 échecs
            self.fb_model.mark_session_failure(self.test_user_id, "Échec 1")
            self.fb_model.mark_session_failure(self.test_user_id, "Échec 2")
            self.fb_model.mark_session_failure(self.test_user_id, "Échec 3")
            
             # 3. Vérifier que la session est désactivée
            updated = self.fb_model.get_session(self.test_user_id)
            assert updated is None, "Session devrait être désactivée (None)"
            
            # Vérifier dans la DB directement
            inactive_session = self.fb_model.collection.find_one({
                "user_id": self.test_user_id
            })
            assert inactive_session["active"] == False
            assert inactive_session["failure_count"] == 3
            print("✅ Test passed: Session deactivated after 3 failures")
            
            
    #pytest tests/sessions/IntegrationTests.py -v -s --log-cli-level=INFO        
    @pytest.mark.asyncio
    async def test_real_search_marks_success(self):
        """
        TEST RÉEL: Faire une vraie recherche et vérifier le tracking
        ⚠️ Nécessite une session valide en DB
        """
        
        real_user_id = "66bd41ade6e37be2ef4b4fc2"
        
        session = self.fb_model.get_session(real_user_id)
        if not session:
            pytest.skip("Pas de session valide pour le test réel")
            
        initial_failure_count = session.get("failure_count",0)

        try:
            listings = await self.searcher.scrape(
                lat=45.5044,
                lon=-73.5761,
                query={
                    "minBudget": 100000,
                    "maxBudget": 200000,
                    "minBedrooms": 1,
                    "maxBedrooms": 3
                },
                user_id=real_user_id,
                job_id="test_job_123"
            )
            
            # Si on a des listings, vérifier que la session est marquée success
            if listings and len(listings) > 0:
                updated = self.fb_model.get_session(real_user_id)
                assert updated["failure_count"] == 0
                assert updated["last_success"] is not None
                print(f"✅ Real search success: {len(listings)} listings, failure_count reset")
            
        except Exception as e:
            # Si erreur, vérifier que failure_count a augmenté
            updated = self.fb_model.get_session(real_user_id)
            if updated:  # Si pas désactivée
                assert updated["failure_count"] > initial_failure_count
                print(f"✅ Real search failure tracked: failure_count increased")


if __name__ == "__main__":
    # Pour exécuter manuellement
    pytest.main([__file__, "-v", "-s"])
        
           
        