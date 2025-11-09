import os
import sys
import time
import threading
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from MainyDB import MainyDB, ObjectId
db = MainyDB("./advanced_example.mdb")
print("\n=== Advanced Query Operations ===\n")
products = db.store.products
products.insert_many([
    {
        "name": "Laptop",
        "category": "Electronics",
        "price": 999.99,
        "specs": {
            "cpu": "Intel i7",
            "ram": 16,
            "storage": 512,
            "units": "GB"
        },
        "tags": ["computer", "portable", "work"],
        "in_stock": True,
        "reviews": [
            {"user": "user123", "rating": 4.5, "comment": "Great laptop!"},
            {"user": "user456", "rating": 5.0, "comment": "Excellent performance"}
        ],
        "created_at": datetime.now() - timedelta(days=30)
    },
    {
        "name": "Smartphone",
        "category": "Electronics",
        "price": 699.99,
        "specs": {
            "cpu": "Snapdragon 8",
            "ram": 8,
            "storage": 256,
            "units": "GB"
        },
        "tags": ["mobile", "portable", "communication"],
        "in_stock": True,
        "reviews": [
            {"user": "user789", "rating": 4.0, "comment": "Good phone"}
        ],
        "created_at": datetime.now() - timedelta(days=15)
    },
    {
        "name": "Headphones",
        "category": "Audio",
        "price": 199.99,
        "specs": {
            "type": "Over-ear",
            "wireless": True,
            "battery_life": 20,
            "units": "hours"
        },
        "tags": ["audio", "portable", "music"],
        "in_stock": False,
        "reviews": [
            {"user": "user123", "rating": 5.0, "comment": "Amazing sound quality"},
            {"user": "user456", "rating": 4.5, "comment": "Comfortable to wear"},
            {"user": "user789", "rating": 4.8, "comment": "Great battery life"}
        ],
        "created_at": datetime.now() - timedelta(days=45)
    },
    {
        "name": "Monitor",
        "category": "Electronics",
        "price": 349.99,
        "specs": {
            "size": 27,
            "resolution": "4K",
            "refresh_rate": 144,
            "units": "Hz"
        },
        "tags": ["computer", "display", "work"],
        "in_stock": True,
        "reviews": [],
        "created_at": datetime.now() - timedelta(days=10)
    },
    {
        "name": "Keyboard",
        "category": "Computer Accessories",
        "price": 129.99,
        "specs": {
            "type": "Mechanical",
            "wireless": False,
            "backlit": True
        },
        "tags": ["computer", "input", "work"],
        "in_stock": True,
        "reviews": [
            {"user": "user123", "rating": 4.2, "comment": "Nice typing experience"}
        ],
        "created_at": datetime.now() - timedelta(days=20)
    }
])
print(f"Inserted {products.count_documents({})} products")
print("\n--- Complex Queries ---\n")
query = {
    "specs.ram": {"$gte": 8},
    "price": {"$lt": 800},
    "in_stock": True
}
for product in products.find(query):
    print(f"Found: {product['name']} - ${product['price']} - RAM: {product['specs'].get('ram', 'N/A')}GB")
query = {
    "$or": [
        {"category": "Electronics"},
        {"price": {"$gt": 150}}
    ],
    "$and": [
        {"in_stock": True},
        {"tags": {"$in": ["portable"]}}
    ]
}
print("\nIn-stock portable electronics or items over $150:")
for product in products.find(query):
    print(f"- {product['name']} (${product['price']})")
query = {
    "tags": {"$all": ["portable", "work"]},
    "reviews": {"$size": {"$gte": 1}}
}
print("\nPortable work items with at least one review:")
for product in products.find(query):
    print(f"- {product['name']} with {len(product['reviews'])} reviews")
query = {
    "reviews": {
        "$elemMatch": {
            "user": "user123",
            "rating": {"$gte": 4.5}
        }
    }
}
print("\nProducts with high ratings from user123:")
for product in products.find(query):
    print(f"- {product['name']}")
print("\n=== Advanced Aggregation Pipeline ===\n")
pipeline = [
    {"$group": {
        "_id": "$category",
        "avg_price": {"$avg": "$price"},
        "count": {"$count": {}},
        "products": {"$push": "$name"}
    }},
    {"$sort": {"avg_price": -1}}
]
print("Average price by category:")
for result in products.aggregate(pipeline):
    print(f"- {result['_id']}: ${result['avg_price']:.2f} ({result['count']} products)")
    print(f"  Products: {', '.join(result['products'])}")
pipeline = [
    {"$match": {"reviews": {"$ne": []}}},
    {"$project": {
        "name": 1,
        "review_count": {"$size": "$reviews"},
        "reviews": 1
    }},
    {"$unwind": "$reviews"},
    {"$group": {
        "_id": "$_id",
        "name": {"$first": "$name"},
        "avg_rating": {"$avg": "$reviews.rating"},
        "review_count": {"$first": "$review_count"}
    }},
    {"$sort": {"avg_rating": -1}}
]
print("\nProducts by average rating:")
for result in products.aggregate(pipeline):
    print(f"- {result['name']}: {result['avg_rating']:.1f} stars ({result['review_count']} reviews)")
pipeline = [
    {"$unwind": "$tags"},
    {"$group": {
        "_id": "$tags",
        "count": {"$count": {}},
        "products": {"$push": "$name"}
    }},
    {"$sort": {"count": -1}},
    {"$limit": 3}
]
print("\nMost common tags:")
for result in products.aggregate(pipeline):
    print(f"- {result['_id']}: {result['count']} products")
    print(f"  Used in: {', '.join(result['products'])}")
print("\n=== Thread Safety and Concurrency ===\n")
concurrent = db.test.concurrent
concurrent.drop()
concurrent.insert_one({"counter": 0})
def increment_counter(thread_id, iterations):
    for i in range(iterations):
        concurrent.update_one({}, {"$inc": {"counter": 1}})
        if i % 100 == 0:
            time.sleep(0.001)
threads = []
num_threads = 5
iterations = 500
print(f"Starting {num_threads} threads, each incrementing counter {iterations} times...")
for i in range(num_threads):
    thread = threading.Thread(target=increment_counter, args=(i, iterations))
    threads.append(thread)
    thread.start()
for thread in threads:
    thread.join()
final_doc = concurrent.find_one({})
expected = num_threads * iterations
actual = final_doc["counter"]
print(f"Expected counter value: {expected}")
print(f"Actual counter value: {actual}")
print(f"Thread safety: {'SUCCESS' if expected == actual else 'FAILED'}")
print("\n=== Bulk Operations ===\n")
bulk = db.test.bulk
bulk.drop()
operations = []
for i in range(1000):
    operations.append({
        "insert_one": {
            "document": {
                "index": i,
                "value": f"bulk-{i}",
                "even": (i % 2 == 0)
            }
        }
    })
for i in range(0, 500, 50):
    operations.append({
        "update_one": {
            "filter": {"index": i},
            "update": {"$set": {"updated": True}}
        }
    })
for i in range(900, 1000, 10):
    operations.append({
        "delete_one": {
            "filter": {"index": i}
        }
    })
start_time = time.time()
result = bulk.bulk_write(operations)
end_time = time.time()
print(f"Bulk operations completed in {end_time - start_time:.4f} seconds")
print(f"Inserted: {result['inserted_count']}")
print(f"Updated: {result['modified_count']}")
print(f"Deleted: {result['deleted_count']}")
count = bulk.count_documents({})
print(f"Total documents: {count}")
updated = bulk.count_documents({"updated": True})
print(f"Updated documents: {updated}")
print("\n=== Database Statistics ===\n")
stats = products.stats()
print("Products collection stats:")
print(f"- Document count: {stats['count']}")
print(f"- Size: {stats['size']} bytes")
print(f"- Average document size: {stats['avgObjSize']} bytes")
print("\nDatabase stats:")
collections = ['store.products', 'concurrent.counter', 'bulk.items']
print(f"- Collections: {len(collections)}")
total_size = 0
for name in ['products', 'counter', 'items']:
    try:
        if name == 'products':
            total_size += products.stats()['size']
    except:
        pass
print(f"- Total size: {total_size} bytes")
print(f"\nCollections in database: {', '.join(collections)}")
print("\n=== Cleanup ===\n")
products.drop()
concurrent.drop()
bulk.drop()
db.close()
print("Advanced example completed successfully!")