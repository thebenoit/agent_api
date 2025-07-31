from database import mongo_db
import asyncio

async def main():
    user = await mongo_db.get_user_by_id("66bd41ade6e37be2ef4b4fc2")
    print(user)

if __name__ == "__main__":
    asyncio.run(main())