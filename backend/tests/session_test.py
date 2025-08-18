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
        "66bd41ade6e37be2ef4b4fc2"
        "66bd5b9fdcd4af9a94dcf0d1", 
        "66bdaf9fe9323c652408aed3",
        "66c7b62e7cd43356cfcd27d1",
        "66ca004528030b150449d7c8"
        "66d8682198f8caa20e6eda4e",
        "66ee43924d5a2df7dc1aeee4",
        "66f9a467ff6ca2377c0bd1e5",
        "66fdd8560ee12414146cfba0",
        "66feada73bb163ba70411f27",
        "6700aefdbc85baf45b7d5a93",
        "670feba2a9557bc6c0b48ef3",
        "671047c9523cbf5ddebdfb29",
        "6716c6486ffbf8bf4e2ccfd9",
        "671828b2a66b1dc61761ea5f",
        "67199575f67738b2031a9809",
        "6719a957fbc85ae097f9a2a1",
        "671fbad06cb65c3e91228690",
        "671fe6c234170e7048b98339",
        "6720ab7c26bf9f5e6b59afa6",
        "67763e39302fa56cd30159bb",
        "67763f7d302fa56cd30159be",
        "679172a2efd95d050699b103",
        "67a6c79b100c5bd25d73992d",
        "67aaa73915ccb24e87ce3a14"
        
        
    ]
    for user_id in user_ids:
        print(f"\n=== Création session pour {user_id} ===")
        success = await session_manager.create_session_for_user(user_id)
        print(f"Résultat: {'✅ Succès' if success else '❌ Échec'}")

    


if __name__ == "__main__":
    asyncio.run(test_multiple_users())
