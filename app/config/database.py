from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import dotenv_values

uri = dotenv_values(".env")['MONGO_URI']

client = MongoClient(uri, server_api = ServerApi('1'))
db = client.blog_fastapi
blogs_collection = db["blogs"]
users_collection = db["users"]

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)