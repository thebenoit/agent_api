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
    listings = await search_facebook.scrape(
        45.5017,
        -73.5673,
        {"minBudget": 100000, "maxBudget": 200000, "minBedrooms": 1, "maxBedrooms": 3},
        "66bd41ade6e37be2ef4b4fc2",
    )
    print("listings: ", listings)
    
    detail_listings = await search_facebook.execute_async(
        45.5017, -73.5673, 100000, 200000, 1, 3, "66bd41ade6e37be2ef4b4fc2", listings
    )
    print("detail_listings: ", detail_listings)

    print("test graphql... done")


if __name__ == "__main__":
    asyncio.run(main())
