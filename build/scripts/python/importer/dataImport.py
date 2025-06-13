from pymongo import MongoClient
import time
import os
import json

data_path = "/python/data"

# Log files in the data directory
if os.path.exists(data_path):
    files = os.listdir(data_path)
    if files:
        print(f"Data directory '{data_path}' contains files:")
        for f in files:
            print(f" - {f}")
    else:
        print(f"Data directory '{data_path}' is empty.")
else:
    print(f"Data directory '{data_path}' does not exist.")
    exit(1)

# Connect to MongoDB
for i in range(10):
    try:
        client = MongoClient("mongodb://admin:nosql_2025@router01:27017/?authSource=admin")
        client.admin.command('ping')
        print("Connected to MongoDB!")
        break
    except Exception as e:
        print(f"Waiting for MongoDB... {e}")
        time.sleep(5)
else:
    print("Could not connect to MongoDB")
    exit(1)

db = client['OSM_DB']

print("\nChecking collections before import:")
for file_name in files:
    if file_name.endswith('.json'):
        collection_name = file_name[:-5]  # strip '.json'
        count = db[collection_name].count_documents({})
        print(f"Collection '{collection_name}': {count} documents")

print("\nStarting import...\n")

# Iterate over files and import
for file_name in files:
    if file_name.endswith('.json'):
        collection_name = file_name[:-5]  # strip '.json'
        file_path = os.path.join(data_path, file_name)
        print(f"Importing '{file_path}' into collection '{collection_name}'")

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Drop collection before import
            db[collection_name].drop()
            print(f"Dropped collection '{collection_name}' before import")

            # Insert data depending on whether it's an array or single object
            if isinstance(data, list):
                db[collection_name].insert_many(data)
                print(f"Inserted {len(data)} documents into '{collection_name}'")
            else:
                db[collection_name].insert_one(data)
                print(f"Inserted 1 document into '{collection_name}'")
        except Exception as e:
            print(f"Failed to import '{file_path}': {e}")
    else:
        print(f"Skipping non-JSON file: '{file_name}'")

print("\nImport completed.")
