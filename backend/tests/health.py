import pytest
from datetime import datetime,timedelta 
from schemas.fb_session import FacebookSession

REQUIRED_HEADERS = {"x-fb-lsd": "abc123", "user-agent": "Mozilla"}

def test_session_has_required_headers():
    """
    une session valide doit avoir les headers critiques
    """
    session = FacebookSession(
        user_id="test_123",
        user_agent="Mozilaa/5.0",
        headers=REQUIRED_HEADERS,
        doc_id="123456"
    )
    
    assert session.has_required_field() == True
    
    