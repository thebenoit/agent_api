from database import mongo_db
import asyncio
import jwt
import os


async def create_session_id(user_id):
    user = await mongo_db.get_user_by_id(user_id)
    if user:
        session_id = jwt.encode(
            {"user_id": user_id}, os.getenv("JWT_SECRET"), algorithm="HS256"
        )
        return session_id
    else:
        return None


async def decode_session_id(session_id):
    try:
        # Décodage avec votre clé secrète
        payload = jwt.decode(session_id, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        return payload["user_id"]
    except jwt.InvalidTokenError as e:
        print(f"Token invalide ou modifié {e}")
        return None  # Token invalide ou modifié
    

async def 
    
    
async def test_user_text_chat():
    user_id = "66bd41ade6e37be2ef4b4fc2"
    session_id = await create_session_id(user_id)
    
    chat_request = {
        "system_prompt": "You are a helpful assistant that can answer questions and help with tasks.",
        "message": "Hello, how are you?",
        "session_id": session_id
    }
    
    response = await requests.post("http://localhost:8000/chat", json=chat_request)
    print(response.json())
    
   
    #user_id_decoded = await decode_session_id(session_id)
    
    


async def main():
    user = await mongo_db.get_user_by_id("66bd41ade6e37be2ef4b4fc2")
    print(user)


if __name__ == "__main__":
    asyncio.run(main())
