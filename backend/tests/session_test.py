import os
import sys
import asyncio

# Ajouter le chemin du projet à sys.path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sessionManager import SessionsManager

# def test_get_req_info():
#     print("test starting...")
#     session_manager = SessionsManager()
#     headers, body, resp_body = session_manager.get_first_req()

#     print("headers: ", headers,"\n")
#     print("body: ", body,"\n")
#     print("resp_body: ", resp_body,"\n")


async def test_undetected_crawler():
    print("test starting...")
    session_manager = SessionsManager()
    await session_manager.init_undetected_crawler(
        "https://www.facebook.com/marketplace/montreal/propertyrentals?exact=false&latitude=45.50889&longitude=-73.63167&radius=7&locale=fr_CA"
    )
    
async def test_multiple_users():
    session_manager = SessionsManager()
    
    user_ids = [
        "66bd41ade6e37be2ef4b4fc2",
        "66bd5b9fdcd4af9a94dcf0d1", 
        "66bdaf9fe9323c652408aed3",
        "66c7b62e7cd43356cfcd27d1",
        "66ca004528030b150449d7c8"
        "66d8682198f8caa20e6eda4e",
        "66ee43924d5a2df7dc1aeee4",
        "66f9a467ff6ca2377c0bd1e5",
        "66fdd8560ee12414146cfba0",
        "66feada73bb163ba70411f27",
        "6700aefdbc85baf45b7d5a93"
    ]
    for user_id in user_ids:
        print(f"\n=== Création session pour {user_id} ===")
        success = await session_manager.create_session_for_user(user_id)
        print(f"Résultat: {'✅ Succès' if success else '❌ Échec'}")

    


if __name__ == "__main__":
    asyncio.run(test_multiple_users())
