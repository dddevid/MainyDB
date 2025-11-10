# MainyDB

MainyDB is an ultra-fast, embedded MongoDB-like database in a single `.mdb` file. It provides a PyMongo-compatible API, allowing you to use MongoDB-style queries, updates, and aggregations in a lightweight, file-based database.

## Features

- **Single File Storage**: All data is stored in a single `.mdb` file
- **PyMongo-Compatible API**: Use the same API as PyMongo for seamless integration
- **JSON-like Document Storage**: Store and query JSON-like documents (Python dictionaries)
- **Full MongoDB Query Support**: Includes comparison, logical, array, and update operators
- **Aggregation Pipeline**: Perform complex data transformations with MongoDB-style aggregation pipelines
- **In-Memory Indexes**: Fast queries with automatic indexing
- **Asynchronous File Writing**: Non-blocking operations for better performance
- **Thread-Safe**: Concurrent access with proper locking mechanisms
- **Media Support**: Store and retrieve images and videos with automatic base64 encoding/decoding
- **Media Caching**: Automatic caching of decoded media for 2 hours

## Installation
```bash
pip install MainyDB
```

The Library is also available on PyPI: https://pypi.org/project/MainyDB/


```bash
# Clone the repository
git clone https://github.com/dddevid/MainyDB.git

# Install dependencies
cd MainyDB
pip install -r requirements.txt
```

## Quick Start

```python
from MainyDB import MainyDB

# Create or open a database
db = MainyDB("my_database.mdb")

# Get a collection (creates it if it doesn't exist)
users = db.myapp.users

# Insert a document
user_id = users.insert_one({
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30
}).inserted_id

# Find documents
for user in users.find({"age": {"$gt": 25}}):
    print(f"{user['name']}: {user['email']}")

# Update a document
users.update_one(
    {"_id": user_id},
    {"$set": {"age": 31}}
)

# Delete a document
users.delete_one({"email": "john@example.com"})

# Close the database when done
db.close()
```

## PyMongo Compatibility Mode

MainyDB can be used as a drop-in replacement for PyMongo:

```python
from MainyDB import MongoClient

# Connect to a "server" (actually uses the file-based database)
client = MongoClient()

# Get a database
db = client.myapp

# Get a collection
users = db.users

# Use the same PyMongo API
users.insert_one({"name": "Jane Smith"})
```

## API Reference

### MainyDB Class

```python
MainyDB(file_path, **kwargs)
```

Creates or opens a MainyDB database.

- `file_path`: Path to the .mdb file
- `kwargs`: Additional options

Methods:
- `list_collection_names()`: Returns a list of collection names in the database
- `drop_collection(name)`: Drops a collection
- `stats()`: Returns database statistics
- `close()`: Closes the database connection

### Collection Class

Methods for working with collections:

#### Collection Operations

- `create_collection(name, options=None)`: Creates a new collection
- `drop()`: Drops the collection
- `renameCollection(newName)`: Renames the collection
- `stats()`: Returns collection statistics
- `count_documents(query)`: Counts documents matching the query
- `create_index(keys, **kwargs)`: Creates an index on the specified fields

#### Document Operations

- `insert_one(document)`: Inserts a single document
- `insert_many(documents)`: Inserts multiple documents
- `find(query=None, projection=None)`: Finds documents matching the query
- `find_one(query=None, projection=None)`: Finds a single document
- `update_one(filter, update, options=None)`: Updates a single document
- `update_many(filter, update, options=None)`: Updates multiple documents
- `replace_one(filter, replacement, options=None)`: Replaces a document
- `delete_one(filter)`: Deletes a single document
- `delete_many(filter)`: Deletes multiple documents
- `bulk_write(operations)`: Performs bulk write operations
- `distinct(field, query=None)`: Returns distinct values for a field

### Query Operators

MainyDB supports all standard MongoDB query operators:

#### Comparison Operators

- `$eq`: Equals
- `$ne`: Not equals
- `$gt`: Greater than
- `$gte`: Greater than or equal
- `$lt`: Less than
- `$lte`: Less than or equal
- `$in`: In array
- `$nin`: Not in array

#### Logical Operators

- `$and`: Logical AND
- `$or`: Logical OR
- `$not`: Logical NOT
- `$nor`: Logical NOR

#### Array Operators

- `$all`: All elements match
- `$elemMatch`: Element matches
- `$size`: Array size

### Update Operators

- `$set`: Sets field values
- `$unset`: Removes fields
- `$inc`: Increments field values
- `$mul`: Multiplies field values
- `$rename`: Renames fields
- `$min`: Updates if value is less than current
- `$max`: Updates if value is greater than current
- `$currentDate`: Sets field to current date
- `$push`: Adds elements to arrays
- `$pop`: Removes first or last element from arrays
- `$pull`: Removes elements from arrays
- `$pullAll`: Removes all matching elements from arrays
- `$addToSet`: Adds elements to arrays if they don't exist

### Aggregation Pipeline

MainyDB supports MongoDB-style aggregation pipelines with stages like:

- `$match`: Filters documents
- `$project`: Reshapes documents
- `$group`: Groups documents
- `$sort`: Sorts documents
- `$limit`: Limits number of documents
- `$skip`: Skips documents
- `$unwind`: Deconstructs arrays
- `$addFields`: Adds fields
- `$lookup`: Performs a left outer join
- `$count`: Counts documents

## Media Handling

MainyDB can store and retrieve binary data like images and videos:

```python
# Store an image
with open("image.jpg", "rb") as f:
    image_data = f.read()
    
media = db.myapp.media
media.insert_one({
    "name": "profile_pic.jpg",
    "data": image_data  # Automatically encoded as base64
})

# Retrieve the image
stored_media = media.find_one({"name": "profile_pic.jpg"})
image_data = stored_media["data"]  # Automatically decoded from base64

# Save the image
with open("retrieved_image.jpg", "wb") as f:
    f.write(image_data)
```

### Direct Image Upload (file path)

- You can upload images by passing a file path string directly; MainyDB reads the file, stores it as base64, and returns `bytes` on read.
- Supported extensions: `.png`, `.jpg`, `.jpeg`, `.webp`, `.tiff`, `.heic`, `.gif`.

```python
# Insert from file path (the image is stored as base64 internally)
images = db.myapp.images
res = images.insert_one({
    "name": "logo",
    "image": "./assets/logo.png"  # path to an existing image file
})

# Read: returns raw bytes (not a base64 string)
logo_doc = images.find_one({"name": "logo"})
logo_bytes = logo_doc["image"]
with open("retrieved_logo.png", "wb") as f:
    f.write(logo_bytes)
```

## Thread Safety

MainyDB is thread-safe and can be accessed from multiple threads:

```python
import threading

def update_counter(thread_id):
    for i in range(1000):
        # Atomic update operation
        counters.update_one(
            {"_id": "counter1"}, 
            {"$inc": {"value": 1}}
        )

# Create threads
threads = []
for i in range(10):
    thread = threading.Thread(target=update_counter, args=(i,))
    threads.append(thread)
    thread.start()

# Wait for all threads to complete
for thread in threads:
    thread.join()
```

## Stress Test

Stress test scripts are available under `tests/stress`. Each script can be run directly:

```bash
# Massive inserts and throughput
python tests/stress/stress_large_insert.py

# Concurrent read/write with multiple threads
python tests/stress/stress_concurrent_rw.py

# Mixed CRUD operations, projections, skip/limit, and aggregations
python tests/stress/stress_mixed_operations.py

# Index stress (single and composite) and targeted queries
python tests/stress/stress_indexing.py
```

Notes:
- The scripts use a temporary database and do not modify existing files.
- Outputs include summaries (time, ops/sec, counts) and basic correctness asserts.
- Run the scripts from the project root (`e:\Progetti\MainyDB`).

## Author

Made with ❤️ by devid
