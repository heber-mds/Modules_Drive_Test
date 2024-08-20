from typing import List

# import sqlalchemy
from pymongo import MongoClient

# DATABASE_URL = "sqlite:///./test.db"
DATABASE_URL = "mongodb+srv://username0:password0@cluster0.7diogwy.mongodb.net/?retryWrites=true&w=majority"

client = MongoClient(DATABASE_URL)

db = client.records
collection = db.records
