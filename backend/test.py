from database import mongo_db

user = mongo_db.get_user_by_id("66bd41ade6e37be2ef4b4fc2")
print(user)