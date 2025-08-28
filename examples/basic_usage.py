#!/usr/bin/env python3
# Basic usage example for MainyDB

import os
import sys
import time
import random
from datetime import datetime

# Add parent directory to path to import MainyDB
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from MainyDB import MainyDB, ObjectId

# Create a new database
db = MainyDB("./example_db.mdb")

# Get a reference to a collection (creates it if it doesn't exist)
users = db.example.users

print("\n=== Basic CRUD Operations ===\n")

# Insert a document
result = users.insert_one({
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30,
    "created_at": datetime.now()
})
user_id = result['inserted_id']

print(f"Inserted user with ID: {user_id}")

# Find the document
user = users.find_one({"name": "John Doe"})
print(f"Found user: {user['name']} ({user['email']})")

# Update the document
result = users.update_one(
    {"_id": user_id},
    {"$set": {"age": 31, "updated_at": datetime.now()}}
)
print(f"Updated {result['modified_count']} document")

# Find the updated document
user = users.find_one({"_id": user_id})
print(f"Updated user age: {user['age']}")

# Insert multiple documents
result = users.insert_many([
    {"name": "Jane Smith", "email": "jane@example.com", "age": 25},
    {"name": "Bob Johnson", "email": "bob@example.com", "age": 35},
    {"name": "Alice Brown", "email": "alice@example.com", "age": 28}
])
print(f"Inserted {len(result['inserted_ids'])} users")

# Count documents
count = users.count_documents({})
print(f"Total users: {count}")

# Query with operators
print("\n=== Query Operators ===\n")

# Find users with age greater than 30
for user in users.find({"age": {"$gt": 30}}):
    print(f"User over 30: {user['name']} ({user['age']})")

# Find users with age between 25 and 32
for user in users.find({"age": {"$gte": 25, "$lte": 32}}):
    print(f"User 25-32: {user['name']} ({user['age']})")

# Find users with specific names
for user in users.find({"name": {"$in": ["Jane Smith", "Bob Johnson"]}}):
    print(f"Selected user: {user['name']}")

print("\n=== Aggregation Pipeline ===\n")

# Add some more data for aggregation examples
users.insert_many([
    {"name": "Charlie Davis", "email": "charlie@example.com", "age": 42, "city": "New York"},
    {"name": "Diana Evans", "email": "diana@example.com", "age": 38, "city": "Boston"},
    {"name": "Edward Foster", "email": "edward@example.com", "age": 25, "city": "New York"},
    {"name": "Fiona Grant", "email": "fiona@example.com", "age": 31, "city": "Chicago"},
    {"name": "George Harris", "email": "george@example.com", "age": 29, "city": "Boston"}
])

# Group by city and calculate average age
result = users.aggregate([
    {"$match": {"city": {"$exists": True}}},
    {"$group": {
        "_id": "$city",
        "count": {"$count": {}},
        "avg_age": {"$avg": "$age"}
    }},
    {"$sort": {"count": -1}}
])

for city_stats in result:
    print(f"City: {city_stats['_id']}, Users: {city_stats['count']}, Avg Age: {city_stats['avg_age']:.1f}")

print("\n=== Indexing ===\n")

# Create an index
users.create_index([("email", 1)])
print("Created index on email field")

# Create a compound index
users.create_index([("city", 1), ("age", -1)])
print("Created compound index on city and age fields")

# Query using the index
user = users.find_one({"email": "diana@example.com"})
print(f"Found user by indexed field: {user['name']}")

print("\n=== Array Operations ===\n")

# Create a collection for posts
posts = db.example.posts

# Insert a document with an array
result = posts.insert_one({
    "title": "My First Post",
    "tags": ["mongodb", "database", "nosql"],
    "comments": [
        {"user": "user1", "text": "Great post!", "likes": 5},
        {"user": "user2", "text": "Thanks for sharing", "likes": 3}
    ]
})
post_id = result['inserted_id']

# Query array elements
post = posts.find_one({"tags": "database"})
if post:
    print(f"Found post with 'database' tag: {post['title']}")
else:
    print("No post found with 'database' tag")

# Array operators
posts.update_one(
    {"_id": post_id},
    {"$push": {"tags": "tutorial"}}
)

posts.update_one(
    {"_id": post_id},
    {"$addToSet": {"tags": "beginner"}}
)

post = posts.find_one({"_id": post_id})
print(f"Updated tags: {post['tags']}")

# Query with $elemMatch
posts.update_one(
    {"_id": post_id, "comments.user": "user1"},
    {"$inc": {"comments.$.likes": 1}}
)

post = posts.find_one({
    "comments": {"$elemMatch": {"user": "user1", "likes": {"$gt": 5}}}
})
if post:
    print(f"Found post with comment from user1 with >5 likes: {post['title']}")
else:
    print("No post found with comment from user1 with >5 likes")

print("\n=== Media Handling ===\n")

# Create a simple image (a colored square) for demonstration
def create_test_image():
    from PIL import Image
    import io
    
    # Create a 100x100 red square image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()

try:
    # This requires Pillow to be installed
    image_data = create_test_image()
    
    # Store image in database
    media = db.example.media
    result = media.insert_one({
        "name": "test_image.png",
        "description": "A test image",
        "data": image_data,
        "created_at": datetime.now()
    })
    media_id = result['inserted_id']
    
    print(f"Stored image with ID: {media_id}")
    
    # Retrieve image
    stored_media = media.find_one({"_id": media_id})
    
    # The image data is automatically decoded when accessed
    retrieved_image = stored_media['data']
    print(f"Retrieved image of type: {type(retrieved_image).__name__}")
    print(f"Image size: {len(retrieved_image)} bytes")
    
    # Save the retrieved image to a file
    with open("retrieved_image.png", "wb") as f:
        f.write(retrieved_image)
    print("Saved retrieved image to 'retrieved_image.png'")
    
except ImportError:
    print("Pillow library not installed. Skipping image example.")

print("\n=== PyMongo Compatibility Mode ===\n")

# Use the MongoClient interface
from MainyDB import MongoClient

# Connect to a "server"
client = MongoClient()

# Get a database
compat_db = client.compatibility_example

# Get a collection
products = compat_db.products

# Insert a document
result = products.insert_one({
    "name": "Awesome Product",
    "price": 99.99,
    "in_stock": True
})
product_id = result['inserted_id']

print(f"Inserted product with ID: {product_id}")

# Find the document
product = products.find_one({"name": "Awesome Product"})
print(f"Found product: {product['name']} (${product['price']})")

print("\n=== Cleanup ===\n")

# Drop collections
users.drop()
posts.drop()
if 'media' in db.example.list_collection_names():
    db.example.media.drop()
products.drop()

# Close the database
db.close()
client.close()

print("Example completed successfully!")