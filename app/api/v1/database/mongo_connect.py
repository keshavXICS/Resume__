from pymongo import MongoClient


mongodb_url = "mongodb://root:rootpassword@mongodb:27017/candidate_resume"
client = MongoClient(mongodb_url)
db = client["candidate_resume"]
collection = db["profiles"]
