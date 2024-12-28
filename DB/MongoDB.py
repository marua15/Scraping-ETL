import json
import re
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

# MongoDB URI
# Load environment variables from .env file
load_dotenv()

# MongoDB URI
uri = os.getenv("MONGODB_URI")
client = MongoClient(uri, server_api=ServerApi('1'))

# Ping to confirm connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"Connection error: {e}")

# Load article data from JSON file
try:
    with open('articles_iot.json', 'r', encoding='utf-8') as f:
        article_data = json.load(f)
except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {e}")
    article_data = []

# Define the project database and collection name
database_name = "Scrapping"
collection_name = "Articles"

# Insert the articles into the MongoDB collection
try:
    db = client[database_name]
    collection = db[collection_name]
    collection.insert_many(article_data)
    print("Articles have been successfully inserted into the collection.")
except Exception as e:
    print(f"Error inserting articles into MongoDB collection: {e}")