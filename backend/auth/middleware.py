from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import jwt
from typing import Optional
from .database import mongodb

async def auth_middleware(request: Request, call_next):
    """middleware to authenticate the user"""
    secret_key = os.getenv("SECRET_KEY")
    
    
    # Extraire le token du header Authorisation
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token d'authentification manquant")
    
    
    token = auth_header.split(" ")[1]
    
    try:
      # Decode le token
      decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
      user_id = decoded.get("user_id")
      
      if not user_id:
          raise HTTPException(status_code=401, detail="Token invalide")
    
      user = mongo_db.get_user_by_id(user_id)
      
      if not user:
          raise HTTPException(status_code=401, detail="Utilisateur non trouve")
      
# 5. Injecter les données dans request.state
        request.state.user_id = user_id
        request.state.thread_id = user.get("threadID")
        request.state.user = user
        
        # 6. Continuer vers l'endpoint
        return await call_next(request)
        
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'authentification: {str(e)}")
     
      
    
    
    