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


if __name__ == "__main__":
    asyncio.run(test_undetected_crawler())
