from sessionManager import SessionsManager
import asyncio

def create_fb_session_job(user_id: str) -> bool:
    """
    Job RQ : crée ou rafraîchit la session FB pour user_id
    """
    
    manager = SessionsManager()
    
    return asyncio.run(manager.create_session_for_user(user_id))