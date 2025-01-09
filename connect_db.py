from pymongo import MongoClient


# MongoDB Client Setup
client = MongoClient("mongodb://localhost:27017/")
db = client["candidate_profiles"]
collection = db["profiles"]