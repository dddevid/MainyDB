# MainyDB Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Basic Concepts](#basic-concepts)
4. [API Reference](#api-reference)
   - [MainyDB Class](#mainydb-class)
   - [Database Class](#database-class)
   - [Collection Class](#collection-class)
   - [Cursor Class](#cursor-class)
   - [ObjectId Class](#objectid-class)
5. [Query Operators](#query-operators)
6. [Update Operators](#update-operators)
7. [Aggregation Pipeline](#aggregation-pipeline)
8. [Indexing](#indexing)
9. [Media Handling](#media-handling)
10. [Thread Safety](#thread-safety)
11. [PyMongo Compatibility](#pymongo-compatibility)
12. [Performance Tips](#performance-tips)
13. [Examples](#examples)

## Introduction

MainyDB is an embedded MongoDB-like database that stores all data in a single `.mdb` file. It provides a PyMongo-compatible API, allowing you to use MongoDB-style queries, updates, and aggregations in a lightweight, file-based database.

MainyDB is designed to be ultra-fast, production-ready, and a drop-in replacement for MongoDB in scenarios where a full MongoDB server is not needed or desired.

## Installation

```bash
# Clone the repository
git clone https://github.com/dddevid/MainyDB.git

# Install dependencies
cd MainyDB
pip install -r requirements.txt
```

## Basic Concepts

### Database Structure

MainyDB stores all data in a single `.mdb` file. This file contains:

- Database metadata
- Collection definitions
- Document data
- Indexes

### Documents

Documents in MainyDB are JSON-like objects (Python dictionaries) with the following characteristics:

- Each document has a unique `_id` field (automatically generated if not provided)
- Documents can contain nested objects and arrays
- Documents can store binary data (automatically encoded as base64)

### Collections

Collections are groups of documents. They are similar to tables in relational databases but without a fixed schema.

### Databases

A MainyDB instance can contain multiple databases, each with its own collections.

## API Reference

### MainyDB Class

```python
MainyDB(file_path, **kwargs)
```

Creates or opens a MainyDB database.

**Parameters:**

- `file_path` (str): Path to the .mdb file
- `kwargs` (dict, optional): Additional options

**Methods:**

- `list_collection_names()`: Returns a list of collection names in the database
- `drop_collection(name)`: Drops a collection
- `stats()`: Returns database statistics
- `close()`: Closes the database connection

**Properties:**

- `<database_name>`: Access a database by attribute

**Example:**

```python
db = MainyDB("my_database.mdb")
my_app_db = db.my_app  # Access the 'my_app' database
db.close()  # Close the database when done
```

### Database Class

Represents a database within MainyDB.

**Methods:**

- `list_collection_names()`: Returns a list of collection names in the database
- `drop_collection(name)`: Drops a collection
- `create_collection(name, options=None)`: Creates a new collection
- `stats()`: Returns database statistics

**Properties:**

- `<collection_name>`: Access a collection by attribute

**Example:**

```python
db = MainyDB("my_database.mdb")
my_app = db.my_app  # Get the 'my_app' database

# List collections
collections = my_app.list_collection_names()

# Create a collection
my_app.create_collection("users")

# Access a collection
users = my_app.users
```

### Collection Class

Represents a collection of documents.

#### Collection Operations

- `create_collection(name, options=None)`: Creates a new collection
- `drop()`: Drops the collection
- `renameCollection(newName)`: Renames the collection
- `stats()`: Returns collection statistics
- `count_documents(query)`: Counts documents matching the query
- `create_index(keys, **kwargs)`: Creates an index on the specified fields

#### Document Operations

- `insert_one(document)`: Inserts a single document
  - Returns: `InsertOneResult` with `inserted_id` property
- `insert_many(documents)`: Inserts multiple documents
  - Returns: `InsertManyResult` with `inserted_ids` property
- `find(query=None, projection=None)`: Finds documents matching the query
  - Returns: `Cursor` object
- `find_one(query=None, projection=None)`: Finds a single document
  - Returns: Document or `None`
- `update_one(filter, update, options=None)`: Updates a single document
  - Returns: `UpdateResult` with `matched_count` and `modified_count` properties
- `update_many(filter, update, options=None)`: Updates multiple documents
  - Returns: `UpdateResult` with `matched_count` and `modified_count` properties
- `replace_one(filter, replacement, options=None)`: Replaces a document
  - Returns: `UpdateResult` with `matched_count` and `modified_count` properties
- `delete_one(filter)`: Deletes a single document
  - Returns: `DeleteResult` with `deleted_count` property
- `delete_many(filter)`: Deletes multiple documents
  - Returns: `DeleteResult` with `deleted_count` property
- `bulk_write(operations)`: Performs bulk write operations
  - Returns: `BulkWriteResult` with operation counts
- `distinct(field, query=None)`: Returns distinct values for a field
  - Returns: List of distinct values
- `aggregate(pipeline)`: Performs an aggregation pipeline
  - Returns: `Cursor` object with aggregation results

**Example:**

```python
db = MainyDB("my_database.mdb")
users = db.my_app.users

# Insert a document
result = users.insert_one({"name": "John", "age": 30})
user_id = result.inserted_id

# Find documents
for user in users.find({"age": {"$gt": 25}}):
    print(user["name"])

# Update a document
users.update_one({"_id": user_id}, {"$set": {"age": 31}})

# Delete a document
users.delete_one({"_id": user_id})
```

### Cursor Class

Represents a database cursor for iterating over query results.

**Methods:**

- `sort(key_or_list, direction=None)`: Sorts the results
- `skip(count)`: Skips the first `count` results
- `limit(count)`: Limits the number of results
- `count()`: Returns the count of documents in the result set
- `distinct(field)`: Returns distinct values for a field in the result set

**Example:**

```python
db = MainyDB("my_database.mdb")
users = db.my_app.users

# Create a cursor
cursor = users.find({"age": {"$gt": 25}})

# Sort, skip, and limit
results = cursor.sort("age", -1).skip(10).limit(5)

# Iterate over results
for user in results:
    print(user["name"])
```

### ObjectId Class

Represents a unique identifier for documents.

**Methods:**

- `__str__()`: Returns a string representation of the ObjectId
- `__eq__()`: Compares two ObjectIds for equality

**Example:**

```python
from MainyDB import ObjectId

# Create a new ObjectId
obj_id = ObjectId()

# Create an ObjectId from a string
obj_id = ObjectId("5f8d7e6b5e4d3c2b1a098765")

# Compare ObjectIds
if obj_id1 == obj_id2:
    print("The ObjectIds are equal")
```

## Query Operators

MainyDB supports all standard MongoDB query operators:

### Comparison Operators

- `$eq`: Equals
  ```python
  {"age": {"$eq": 30}}  # Equivalent to {"age": 30}
  ```

- `$ne`: Not equals
  ```python
  {"age": {"$ne": 30}}  # Age is not 30
  ```

- `$gt`: Greater than
  ```python
  {"age": {"$gt": 30}}  # Age is greater than 30
  ```

- `$gte`: Greater than or equal
  ```python
  {"age": {"$gte": 30}}  # Age is greater than or equal to 30
  ```

- `$lt`: Less than
  ```python
  {"age": {"$lt": 30}}  # Age is less than 30
  ```

- `$lte`: Less than or equal
  ```python
  {"age": {"$lte": 30}}  # Age is less than or equal to 30
  ```

- `$in`: In array
  ```python
  {"age": {"$in": [25, 30, 35]}}  # Age is 25, 30, or 35
  ```

- `$nin`: Not in array
  ```python
  {"age": {"$nin": [25, 30, 35]}}  # Age is not 25, 30, or 35
  ```

### Logical Operators

- `$and`: Logical AND
  ```python
  {"$and": [{"age": {"$gt": 25}}, {"name": "John"}]}  # Age > 25 AND name is John
  ```

- `$or`: Logical OR
  ```python
  {"$or": [{"age": {"$gt": 30}}, {"name": "John"}]}  # Age > 30 OR name is John
  ```

- `$not`: Logical NOT
  ```python
  {"age": {"$not": {"$gt": 30}}}  # Age is not greater than 30
  ```

- `$nor`: Logical NOR
  ```python
  {"$nor": [{"age": 30}, {"name": "John"}]}  # Age is not 30 AND name is not John
  ```

### Array Operators

- `$all`: All elements match
  ```python
  {"tags": {"$all": ["mongodb", "database"]}}  # Tags contains both "mongodb" and "database"
  ```

- `$elemMatch`: Element matches
  ```python
  {"comments": {"$elemMatch": {"author": "John", "score": {"$gt": 5}}}}  # Comments contains an element with author John and score > 5
  ```

- `$size`: Array size
  ```python
  {"tags": {"$size": 3}}  # Tags array has exactly 3 elements
  ```

## Update Operators

MainyDB supports all standard MongoDB update operators:

### Field Update Operators

- `$set`: Sets field values
  ```python
  {"$set": {"age": 31, "updated": True}}  # Set age to 31 and updated to True
  ```

- `$unset`: Removes fields
  ```python
  {"$unset": {"temporary_field": ""}}  # Remove temporary_field
  ```

- `$inc`: Increments field values
  ```python
  {"$inc": {"age": 1, "count": 5}}  # Increment age by 1 and count by 5
  ```

- `$mul`: Multiplies field values
  ```python
  {"$mul": {"price": 1.1}}  # Multiply price by 1.1 (10% increase)
  ```

- `$rename`: Renames fields
  ```python
  {"$rename": {"old_field": "new_field"}}  # Rename old_field to new_field
  ```

- `$min`: Updates if value is less than current
  ```python
  {"$min": {"lowest_score": 50}}  # Set lowest_score to 50 if current value is greater than 50
  ```

- `$max`: Updates if value is greater than current
  ```python
  {"$max": {"highest_score": 95}}  # Set highest_score to 95 if current value is less than 95
  ```

- `$currentDate`: Sets field to current date
  ```python
  {"$currentDate": {"last_updated": True}}  # Set last_updated to current date
  ```

### Array Update Operators

- `$push`: Adds elements to arrays
  ```python
  {"$push": {"tags": "new_tag"}}  # Add "new_tag" to tags array
  ```

- `$pop`: Removes first or last element from arrays
  ```python
  {"$pop": {"tags": 1}}  # Remove last element from tags array
  {"$pop": {"tags": -1}}  # Remove first element from tags array
  ```

- `$pull`: Removes elements from arrays
  ```python
  {"$pull": {"tags": "old_tag"}}  # Remove "old_tag" from tags array
  ```

- `$pullAll`: Removes all matching elements from arrays
  ```python
  {"$pullAll": {"tags": ["tag1", "tag2"]}}  # Remove "tag1" and "tag2" from tags array
  ```

- `$addToSet`: Adds elements to arrays if they don't exist
  ```python
  {"$addToSet": {"tags": "unique_tag"}}  # Add "unique_tag" to tags array if it doesn't exist
  ```

## Aggregation Pipeline

MainyDB supports MongoDB-style aggregation pipelines with the following stages:

- `$match`: Filters documents
  ```python
  {"$match": {"age": {"$gt": 30}}}  # Match documents where age > 30
  ```

- `$project`: Reshapes documents
  ```python
  {"$project": {"name": 1, "age": 1, "_id": 0}}  # Include only name and age fields, exclude _id
  ```

- `$group`: Groups documents
  ```python
  {"$group": {"_id": "$city", "count": {"$sum": 1}, "avg_age": {"$avg": "$age"}}}  # Group by city, count documents, and calculate average age
  ```

- `$sort`: Sorts documents
  ```python
  {"$sort": {"age": -1}}  # Sort by age in descending order
  ```

- `$limit`: Limits number of documents
  ```python
  {"$limit": 10}  # Limit to 10 documents
  ```

- `$skip`: Skips documents
  ```python
  {"$skip": 10}  # Skip the first 10 documents
  ```

- `$unwind`: Deconstructs arrays
  ```python
  {"$unwind": "$tags"}  # Create a document for each element in the tags array
  ```

- `$addFields`: Adds fields
  ```python
  {"$addFields": {"full_name": {"$concat": ["$first_name", " ", "$last_name"]}}}  # Add full_name field
  ```

- `$lookup`: Performs a left outer join
  ```python
  {"$lookup": {"from": "comments", "localField": "_id", "foreignField": "post_id", "as": "comments"}}  # Join with comments collection
  ```

- `$count`: Counts documents
  ```python
  {"$count": "total"}  # Count documents and store result in total field
  ```

**Example:**

```python
db = MainyDB("my_database.mdb")
users = db.my_app.users

# Group users by city and calculate average age
result = users.aggregate([
    {"$match": {"age": {"$gte": 18}}},  # Only include adults
    {"$group": {
        "_id": "$city",
        "count": {"$sum": 1},
        "avg_age": {"$avg": "$age"}
    }},
    {"$sort": {"count": -1}}  # Sort by count in descending order
])

for city_stats in result:
    print(f"{city_stats['_id']}: {city_stats['count']} users, avg age: {city_stats['avg_age']:.1f}")
```

## Indexing

MainyDB supports in-memory indexes for fast queries.

### Creating Indexes

```python
# Create a single-field index
users.create_index([("email", 1)])  # 1 for ascending, -1 for descending

# Create a compound index
users.create_index([("city", 1), ("age", -1)])
```

### Index Options

- `unique`: Ensures index keys are unique
  ```python
  users.create_index([("email", 1)], unique=True)
  ```

- `name`: Custom name for the index
  ```python
  users.create_index([("email", 1)], name="email_index")
  ```

## Media Handling

MainyDB can store and retrieve binary data like images and videos. Binary data is automatically encoded as base64 when stored and decoded when retrieved.

```python
# Store an image
with open("image.jpg", "rb") as f:
    image_data = f.read()
    
media = db.my_app.media
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

### Media Caching

MainyDB automatically caches decoded media for 2 hours to improve performance when the same media is accessed multiple times.

## Thread Safety

MainyDB is thread-safe and can be accessed from multiple threads. It uses locks to ensure that concurrent operations don't interfere with each other.

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

## PyMongo Compatibility

MainyDB can be used as a drop-in replacement for PyMongo:

```python
from MainyDB import MongoClient

# Connect to a "server" (actually uses the file-based database)
client = MongoClient()

# Get a database
db = client.my_app

# Get a collection
users = db.users

# Use the same PyMongo API
users.insert_one({"name": "Jane Smith"})
```

## Performance Tips

1. **Use Indexes**: Create indexes on fields that are frequently used in queries.

2. **Limit Query Results**: Use `limit()` to restrict the number of documents returned.

3. **Project Only Needed Fields**: Use projection to return only the fields you need.

4. **Use Bulk Operations**: Use `bulk_write()` for multiple operations.

5. **Close the Database**: Always call `close()` when you're done to ensure data is properly saved.

## Examples

See the `examples` directory for more detailed examples:

- `basic_usage.py`: Basic CRUD operations
- `advanced_usage.py`: Advanced queries, aggregations, and concurrency