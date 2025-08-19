import os
import sys
import asyncio
import json


from agents.tools.searchFacebook import SearchFacebook
from models.fb_sessions import FacebookSessionModel


async def main():
    print("test graphql...")
    search_facebook = SearchFacebook()
    
    print("session init... done")
    data = await search_facebook.fb_graphql_call("66bd41ade6e37be2ef4b4fc2")
    print("data: ", data,"\n")
    print("test graphql... done")

if __name__ == "__main__":
    asyncio.run(main())