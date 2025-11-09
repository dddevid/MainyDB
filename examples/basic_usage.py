import os
import sys
import time
import random
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from MainyDB import MainyDB, ObjectId
db = MainyDB("./example_db.mdb")
users = db.example.users
print("\n=== Basic CRUD Operations ===\n")
result = users.insert_one({
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30,
    "created_at": datetime.now()
})
user_id = result['inserted_id']
print(f"Inserted user with ID: {user_id}")
user = users.find_one({"name": "John Doe"})
print(f"Found user: {user['name']} ({user['email']})")
result = users.update_one(
    {"_id": user_id},
    {"$set": {"age": 31, "updated_at": datetime.now()}}
)
print(f"Updated {result['modified_count']} document")
user = users.find_one({"_id": user_id})
print(f"Updated user age: {user['age']}")
result = users.insert_many([
    {"name": "Jane Smith", "email": "jane@example.com", "age": 25},
    {"name": "Bob Johnson", "email": "bob@example.com", "age": 35},
    {"name": "Alice Brown", "email": "alice@example.com", "age": 28}
])
print(f"Inserted {len(result['inserted_ids'])} users")
count = users.count_documents({})
print(f"Total users: {count}")
print("\n=== Query Operators ===\n")
for user in users.find({"age": {"$gt": 30}}):
    print(f"User over 30: {user['name']} ({user['age']})")
for user in users.find({"age": {"$gte": 25, "$lte": 32}}):
    print(f"User 25-32: {user['name']} ({user['age']})")
for user in users.find({"name": {"$in": ["Jane Smith", "Bob Johnson"]}}):
    print(f"Selected user: {user['name']}")
print("\n=== Aggregation Pipeline ===\n")
users.insert_many([
    {"name": "Charlie Davis", "email": "charlie@example.com", "age": 42, "city": "New York"},
    {"name": "Diana Evans", "email": "diana@example.com", "age": 38, "city": "Boston"},
    {"name": "Edward Foster", "email": "edward@example.com", "age": 25, "city": "New York"},
    {"name": "Fiona Grant", "email": "fiona@example.com", "age": 31, "city": "Chicago"},
    {"name": "George Harris", "email": "george@example.com", "age": 29, "city": "Boston"}
])
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
users.create_index([("email", 1)])
print("Created index on email field")
users.create_index([("city", 1), ("age", -1)])
print("Created compound index on city and age fields")
user = users.find_one({"email": "diana@example.com"})
print(f"Found user by indexed field: {user['name']}")
print("\n=== Array Operations ===\n")
posts = db.example.posts
result = posts.insert_one({
    "title": "My First Post",
    "tags": ["mongodb", "database", "nosql"],
    "comments": [
        {"user": "user1", "text": "Great post!", "likes": 5},
        {"user": "user2", "text": "Thanks for sharing", "likes": 3}
    ]
})
post_id = result['inserted_id']
post = posts.find_one({"tags": "database"})
if post:
    print(f"Found post with 'database' tag: {post['title']}")
else:
    print("No post found with 'database' tag")
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
def create_test_image():
    from PIL import Image
    import io
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()
try:
    image_data = create_test_image()
    media = db.example.media
    result = media.insert_one({
        "name": "test_image.png",
        "description": "A test image",
        "data": image_data,
        "created_at": datetime.now()
    })
    media_id = result['inserted_id']
    print(f"Stored image with ID: {media_id}")
    stored_media = media.find_one({"_id": media_id})
    retrieved_image = stored_media['data']
    print(f"Retrieved image of type: {type(retrieved_image).__name__}")
    print(f"Image size: {len(retrieved_image)} bytes")
    with open("retrieved_image.png", "wb") as f:
        f.write(retrieved_image)
    print("Saved retrieved image to 'retrieved_image.png'")
except ImportError:
    print("Pillow library not installed. Skipping image example.")
print("\n=== PyMongo Compatibility Mode ===\n")
from MainyDB import MongoClient
client = MongoClient()
compat_db = client.compatibility_example
products = compat_db.products
result = products.insert_one({
    "name": "Awesome Product",
    "price": 99.99,
    "in_stock": True
})
product_id = result['inserted_id']
print(f"Inserted product with ID: {product_id}")
product = products.find_one({"name": "Awesome Product"})
print(f"Found product: {product['name']} (${product['price']})")
print("\n=== Cleanup ===\n")
users.drop()
posts.drop()
if 'media' in db.example.list_collection_names():
    db.example.media.drop()
products.drop()
db.close()
client.close()
print("Example completed successfully!")