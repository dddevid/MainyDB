import os
import json
import time
import uuid
import base64
import pickle
import threading
import datetime
import hashlib
import asyncio
import concurrent.futures
from typing import Dict, List, Any, Union, Optional, Callable, Iterator
from collections import defaultdict
from bson.objectid import ObjectId as BSONObjectId
from .utils import (
    apply_query_operators,
    apply_update_operators,
    apply_aggregation_pipeline,
    build_index,
    query_with_index,
    encode_media,
    decode_media,
    is_media_type
)
class ObjectId:
    def __init__(self, oid=None):
        if oid is None:
            self._id = str(uuid.uuid4())
        else:
            self._id = str(oid)
    def __str__(self):
        return self._id
    def __repr__(self):
        return f"ObjectId('{self._id}')"
    def __eq__(self, other):
        if isinstance(other, ObjectId):
            return self._id == other._id
        return False
    def __hash__(self):
        return hash(self._id)
class MediaCache:
    def __init__(self, max_age=7200):
        self.cache = {}
        self.timestamps = {}
        self.max_age = max_age
        self.lock = threading.RLock()
        self._start_cleanup_thread()
    def _start_cleanup_thread(self):
        def cleanup_task():
            while True:
                time.sleep(300)
                self._cleanup()
        thread = threading.Thread(target=cleanup_task, daemon=True)
        thread.start()
    def _cleanup(self):
        now = time.time()
        with self.lock:
            expired_keys = [k for k, t in self.timestamps.items() if now - t > self.max_age]
            for key in expired_keys:
                if key in self.cache:
                    del self.cache[key]
                if key in self.timestamps:
                    del self.timestamps[key]
    def get(self, key):
        with self.lock:
            if key in self.cache:
                self.timestamps[key] = time.time()
                return self.cache[key]
            return None
    def set(self, key, value):
        with self.lock:
            self.cache[key] = value
            self.timestamps[key] = time.time()
class AsyncFileWriter:
    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.queue = []
        self.lock = threading.Lock()
        self.event = threading.Event()
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    def _worker(self):
        while self.running:
            tasks = []
            with self.lock:
                if self.queue:
                    tasks = self.queue.copy()
                    self.queue.clear()
            for file_path, data in tasks:
                try:
                    with open(file_path, 'wb') as f:
                        pickle.dump(data, f)
                except Exception as e:
                    print(f"Error writing to {file_path}: {e}")
            if not tasks:
                self.event.wait(0.1)
                self.event.clear()
    def write(self, file_path, data):
        with self.lock:
            self.queue.append((file_path, data))
            self.event.set()
    def sync_write(self, file_path, data):
        with open(file_path, 'wb') as f:
            pickle.dump(data, f)
    def shutdown(self):
        self.running = False
        self.event.set()
        self.worker_thread.join()
        self.executor.shutdown()
class Collection:
    def __init__(self, database, name, file_path, options=None):
        self.database = database
        self.name = name
        self.file_path = file_path
        self.options = options or {}
        self.lock = threading.RLock()
        self.documents = []
        self.indexes = {}
        self._load_data()
    def _load_data(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data.get('documents', [])
                    self.indexes = data.get('indexes', {})
            except Exception as e:
                print(f"Error loading collection {self.name}: {e}")
                self.documents = []
                self.indexes = {}
    def _save_data(self, async_write=True):
        data = {
            'documents': self.documents,
            'indexes': self.indexes
        }
        if async_write:
            self.database.db.writer.write(self.file_path, data)
        else:
            self.database.db.writer.sync_write(self.file_path, data)
    def _find_document_index(self, query):
        for i, doc in enumerate(self.documents):
            if apply_query_operators(doc, query):
                return i
        return -1
    def _find_documents(self, query=None):
        if query is None:
            return self.documents.copy()
        indexed_results = query_with_index(self.documents, query, self.indexes)
        if indexed_results is not None:
            return indexed_results
        return [doc for doc in self.documents if apply_query_operators(doc, query or {})]
    def _apply_projection(self, documents, projection):
        if not projection:
            return documents
        result = []
        include_mode = None
        for doc in documents:
            projected_doc = {}
            if include_mode is None:
                include_values = [v for v in projection.values() if v == 1]
                exclude_values = [v for v in projection.values() if v == 0]
                if include_values and exclude_values:
                    non_id_projection = {k: v for k, v in projection.items() if k != '_id'}
                    non_id_include = [v for v in non_id_projection.values() if v == 1]
                    non_id_exclude = [v for v in non_id_projection.values() if v == 0]
                    if non_id_include and non_id_exclude:
                        raise ValueError("Cannot mix inclusive and exclusive projections")
                    include_mode = bool(non_id_include)
                else:
                    include_mode = bool(include_values)
            if include_mode:
                for field, value in projection.items():
                    if value == 1 and field in doc:
                        projected_doc[field] = doc[field]
                if '_id' not in projection or projection['_id'] == 1:
                    projected_doc['_id'] = doc['_id']
            else:
                projected_doc = doc.copy()
                for field, value in projection.items():
                    if value == 0 and field in projected_doc:
                        del projected_doc[field]
            result.append(projected_doc)
        return result
    def create_index(self, keys, **kwargs):
        with self.lock:
            normalized_keys = []
            index_name = None
            if isinstance(keys, list):
                if keys and all(isinstance(item, tuple) and len(item) == 2 for item in keys):
                    normalized_keys = [k for k, _ in keys]
                    index_name = '_'.join([f"{k}_{d}" for k, d in keys])
                else:
                    normalized_keys = list(keys)
                    index_name = '_'.join([f"{k}_1" for k in normalized_keys])
            elif isinstance(keys, str):
                normalized_keys = [keys]
                index_name = f"{keys}_1"
            else:
                raise TypeError("keys must be a list of fields or list of (field, direction) tuples or a string field name")
            self.indexes[index_name] = build_index(self.documents, normalized_keys)
            self._save_data()
            return index_name
    def drop_index(self, index_name):
        with self.lock:
            if index_name in self.indexes:
                del self.indexes[index_name]
                self._save_data()
    def drop_indexes(self):
        with self.lock:
            self.indexes = {}
            self._save_data()
    def insert_one(self, document):
        if not isinstance(document, dict):
            raise TypeError("document must be a dict")
        with self.lock:
            doc_copy = document.copy()
            if '_id' not in doc_copy:
                doc_copy['_id'] = ObjectId()
            for key, value in doc_copy.items():
                if is_media_type(value):
                    doc_copy[key] = encode_media(value)
            self.documents.append(doc_copy)
            for index_name, index_data in self.indexes.items():
                index_data = build_index([doc_copy], index_data.keys(), existing_index=index_data)
                self.indexes[index_name] = index_data
            self._save_data()
            return {'inserted_id': doc_copy['_id']}
    def insert_many(self, documents, ordered=True):
        if not isinstance(documents, list):
            raise TypeError("documents must be a list")
        inserted_ids = []
        with self.lock:
            for doc in documents:
                doc_copy = doc.copy()
                if '_id' not in doc_copy:
                    doc_copy['_id'] = ObjectId()
                for key, value in doc_copy.items():
                    if is_media_type(value):
                        doc_copy[key] = encode_media(value)
                self.documents.append(doc_copy)
                inserted_ids.append(doc_copy['_id'])
            for index_name in self.indexes:
                self.indexes[index_name] = build_index(self.documents, self.indexes[index_name].keys())
            self._save_data()
            return {'inserted_ids': inserted_ids}
    def find(self, query=None, projection=None):
        with self.lock:
            documents = self._find_documents(query)
            if projection:
                documents = self._apply_projection(documents, projection)
            for doc in documents:
                for key, value in doc.items():
                    if isinstance(value, dict) and value.get('__media_type__'):
                        doc[key] = lambda k=key, v=value: decode_media(v, self.database.db.media_cache)
            return Cursor(documents)
    def find_one(self, query=None, projection=None):
        with self.lock:
            documents = self._find_documents(query)
            if not documents:
                return None
            result = documents[0]
            if projection:
                result = self._apply_projection([result], projection)[0]
            for key, value in result.items():
                if isinstance(value, dict) and value.get('__media_type__'):
                    result[key] = decode_media(value, self.database.db.media_cache)
            return result
    def update_one(self, filter, update, upsert=False):
        with self.lock:
            doc_index = self._find_document_index(filter)
            if doc_index == -1:
                if upsert:
                    new_doc = filter.copy()
                    new_doc = apply_update_operators({}, update)
                    return self.insert_one(new_doc)
                return {'matched_count': 0, 'modified_count': 0}
            self.documents[doc_index] = apply_update_operators(self.documents[doc_index], update)
            for index_name in self.indexes:
                self.indexes[index_name] = build_index(self.documents, self.indexes[index_name].keys())
            self._save_data()
            return {'matched_count': 1, 'modified_count': 1}
    def update_many(self, filter, update, upsert=False):
        with self.lock:
            matching_docs = [i for i, doc in enumerate(self.documents) if apply_query_operators(doc, filter)]
            if not matching_docs and upsert:
                new_doc = filter.copy()
                new_doc = apply_update_operators({}, update)
                return self.insert_one(new_doc)
            for idx in matching_docs:
                self.documents[idx] = apply_update_operators(self.documents[idx], update)
            for index_name in self.indexes:
                self.indexes[index_name] = build_index(self.documents, self.indexes[index_name].keys())
            self._save_data()
            return {'matched_count': len(matching_docs), 'modified_count': len(matching_docs)}
    def replace_one(self, filter, replacement, upsert=False):
        with self.lock:
            doc_index = self._find_document_index(filter)
            if doc_index == -1:
                if upsert:
                    return self.insert_one(replacement)
                return {'matched_count': 0, 'modified_count': 0}
            replacement_copy = replacement.copy()
            replacement_copy['_id'] = self.documents[doc_index]['_id']
            for key, value in replacement_copy.items():
                if is_media_type(value):
                    replacement_copy[key] = encode_media(value)
            self.documents[doc_index] = replacement_copy
            for index_name in self.indexes:
                self.indexes[index_name] = build_index(self.documents, self.indexes[index_name].keys())
            self._save_data()
            return {'matched_count': 1, 'modified_count': 1}
    def delete_one(self, filter):
        with self.lock:
            doc_index = self._find_document_index(filter)
            if doc_index == -1:
                return {'deleted_count': 0}
            del self.documents[doc_index]
            for index_name in self.indexes:
                self.indexes[index_name] = build_index(self.documents, self.indexes[index_name].keys())
            self._save_data()
            return {'deleted_count': 1}
    def delete_many(self, filter):
        with self.lock:
            original_count = len(self.documents)
            self.documents = [doc for doc in self.documents if not apply_query_operators(doc, filter)]
            deleted_count = original_count - len(self.documents)
            for index_name in self.indexes:
                self.indexes[index_name] = build_index(self.documents, self.indexes[index_name].keys())
            self._save_data()
            return {'deleted_count': deleted_count}
    def count_documents(self, query=None):
        with self.lock:
            return len(self._find_documents(query))
    def distinct(self, field, query=None):
        with self.lock:
            documents = self._find_documents(query)
            values = set()
            for doc in documents:
                if field in doc:
                    if '.' in field:
                        parts = field.split('.')
                        value = doc
                        for part in parts:
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                value = None
                                break
                        if value is not None:
                            values.add(value if not isinstance(value, (list, dict)) else str(value))
                    else:
                        value = doc[field]
                        values.add(value if not isinstance(value, (list, dict)) else str(value))
            return list(values)
    def aggregate(self, pipeline):
        with self.lock:
            return Cursor(apply_aggregation_pipeline(self.documents, pipeline))
    def bulk_write(self, operations, ordered=True):
        with self.lock:
            result = {
                'inserted_count': 0,
                'matched_count': 0,
                'modified_count': 0,
                'deleted_count': 0,
                'upserted_count': 0,
                'upserted_ids': []
            }
            for op in operations:
                op_type = list(op.keys())[0]
                op_data = op[op_type]
                if op_type == 'insert_one':
                    res = self.insert_one(op_data['document'])
                    result['inserted_count'] += 1
                elif op_type == 'update_one':
                    res = self.update_one(
                        op_data['filter'],
                        op_data['update'],
                        op_data.get('upsert', False)
                    )
                    result['matched_count'] += res.get('matched_count', 0)
                    result['modified_count'] += res.get('modified_count', 0)
                    if res.get('upserted_id'):
                        result['upserted_count'] += 1
                        result['upserted_ids'].append(res['upserted_id'])
                elif op_type == 'update_many':
                    res = self.update_many(
                        op_data['filter'],
                        op_data['update'],
                        op_data.get('upsert', False)
                    )
                    result['matched_count'] += res.get('matched_count', 0)
                    result['modified_count'] += res.get('modified_count', 0)
                    if res.get('upserted_id'):
                        result['upserted_count'] += 1
                        result['upserted_ids'].append(res['upserted_id'])
                elif op_type == 'replace_one':
                    res = self.replace_one(
                        op_data['filter'],
                        op_data['replacement'],
                        op_data.get('upsert', False)
                    )
                    result['matched_count'] += res.get('matched_count', 0)
                    result['modified_count'] += res.get('modified_count', 0)
                    if res.get('upserted_id'):
                        result['upserted_count'] += 1
                        result['upserted_ids'].append(res['upserted_id'])
                elif op_type == 'delete_one':
                    res = self.delete_one(op_data['filter'])
                    result['deleted_count'] += res.get('deleted_count', 0)
                elif op_type == 'delete_many':
                    res = self.delete_many(op_data['filter'])
                    result['deleted_count'] += res.get('deleted_count', 0)
            self._save_data()
            return result
    def drop(self):
        with self.lock:
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
            self.documents = []
            self.indexes = {}
            return True
    def rename(self, new_name):
        with self.lock:
            old_path = self.file_path
            new_path = os.path.join(os.path.dirname(old_path), f"{new_name}.collection")
            if os.path.exists(old_path):
                self.file_path = new_path
                self._save_data(False)
                os.remove(old_path)
            self.database.collections[new_name] = self.database.collections.pop(self.name)
            self.name = new_name
            return True
    def stats(self):
        with self.lock:
            storage_size = 0
            if os.path.exists(self.file_path):
                storage_size = os.path.getsize(self.file_path)
            return {
                'ns': f"{self.database.name}.{self.name}",
                'count': len(self.documents),
                'size': storage_size,
                'avgObjSize': storage_size / len(self.documents) if self.documents else 0,
                'storageSize': storage_size,
                'nindexes': len(self.indexes),
                'indexNames': list(self.indexes.keys()),
                'ok': 1.0
            }
class Cursor:
    def __init__(self, documents):
        self.documents = documents
        self.position = 0
    def __iter__(self):
        return self
    def __next__(self):
        if self.position >= len(self.documents):
            raise StopIteration
        document = self.documents[self.position]
        self.position += 1
        return document
    def next(self):
        return self.__next__()
    def sort(self, key_or_list, direction=None):
        if direction is not None:
            key = key_or_list
            reverse = direction == -1
            self.documents.sort(key=lambda x: x.get(key) if key in x else None, reverse=reverse)
        else:
            for key, direction in reversed(key_or_list):
                reverse = direction == -1
                self.documents.sort(key=lambda x: x.get(key) if key in x else None, reverse=reverse)
        return self
    def skip(self, count):
        self.documents = self.documents[count:]
        return self
    def limit(self, count):
        self.documents = self.documents[:count]
        return self
    def count(self):
        return len(self.documents)
    def distinct(self, key):
        values = set()
        for doc in self.documents:
            if key in doc:
                value = doc[key]
                if not isinstance(value, (list, dict)):
                    values.add(value)
        return list(values)
    def to_list(self):
        return self.documents.copy()
class Database:
    def __init__(self, mainydb, name):
        self.db = mainydb
        self.name = name
        self.collections = {}
        self.path = os.path.join(self.db.path, self.name)
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        self._load_collections()
    def _load_collections(self):
        if os.path.exists(self.path):
            for filename in os.listdir(self.path):
                if filename.endswith('.collection'):
                    collection_name = filename[:-11]
                    file_path = os.path.join(self.path, filename)
                    self.collections[collection_name] = Collection(self, collection_name, file_path)
    def create_collection(self, name, options=None):
        if name in self.collections:
            return self.collections[name]
        file_path = os.path.join(self.path, f"{name}.collection")
        collection = Collection(self, name, file_path, options)
        self.collections[name] = collection
        return collection
    def drop_collection(self, name):
        if name in self.collections:
            self.collections[name].drop()
            del self.collections[name]
            return True
        return False
    def list_collection_names(self):
        return list(self.collections.keys())
    def get_collection(self, name):
        if name not in self.collections:
            return self.create_collection(name)
        return self.collections[name]
    def __getitem__(self, name):
        return self.get_collection(name)
    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return self.get_collection(name)
class MainyDB:
    def __init__(self, path=None, pymongo_compatible=False):
        if path is None:
            path = os.path.join(os.getcwd(), 'mainydb.mdb')
        if os.path.isfile(path) or not os.path.exists(path) and not path.endswith('/'):
            self.single_file_mode = True
            self.path = os.path.dirname(path)
            self.db_file = path
        else:
            self.single_file_mode = False
            self.path = path
            self.db_file = None
        if not os.path.exists(self.path) and self.path:
            os.makedirs(self.path)
        self.pymongo_compatible = pymongo_compatible
        self.databases = {}
        self.writer = AsyncFileWriter()
        self.media_cache = MediaCache()
        if self.single_file_mode:
            self._load_single_file()
        else:
            self._load_databases()
    def _load_single_file(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'rb') as f:
                    encrypted_data = f.read()
                    decrypted_data = self.fernet.decrypt(encrypted_data)
                    data = pickle.loads(decrypted_data)
                    for db_name, collections in data.items():
                        db = Database(self, db_name)
                        for coll_name, coll_data in collections.items():
                            file_path = os.path.join(self.path, db_name, f"{coll_name}.collection")
                            coll = Collection(db, coll_name, file_path)
                            coll.documents = coll_data.get('documents', [])
                            coll.indexes = coll_data.get('indexes', {})
                            db.collections[coll_name] = coll
                        self.databases[db_name] = db
            except Exception as e:
                print(f"Error loading database file: {e}")
    def _save_single_file(self):
        if not self.single_file_mode:
            return
        data = {}
        for db_name, db in self.databases.items():
            data[db_name] = {}
            for coll_name, coll in db.collections.items():
                data[db_name][coll_name] = {
                    'documents': coll.documents,
                    'indexes': coll.indexes
                }
        self.writer.sync_write(self.db_file, data)
    def _load_databases(self):
        if os.path.exists(self.path):
            for dirname in os.listdir(self.path):
                db_path = os.path.join(self.path, dirname)
                if os.path.isdir(db_path):
                    self.databases[dirname] = Database(self, dirname)
    def list_database_names(self):
        return list(self.databases.keys())
    def get_database(self, name):
        if name not in self.databases:
            db = Database(self, name)
            self.databases[name] = db
            return db
        return self.databases[name]
    def drop_database(self, name):
        if name in self.databases:
            db_path = os.path.join(self.path, name)
            if os.path.exists(db_path):
                for filename in os.listdir(db_path):
                    file_path = os.path.join(db_path, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                os.rmdir(db_path)
            del self.databases[name]
            if self.single_file_mode:
                self._save_single_file()
            return True
        return False
    def __getitem__(self, name):
        return self.get_database(name)
    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return self.get_database(name)
    def close(self):
        if self.single_file_mode:
            self._save_single_file()
        self.writer.shutdown()
class MongoClient:
    def __init__(self, host=None, port=None, **kwargs):
        self.mainydb = MainyDB(pymongo_compatible=True)
        self.host = host or 'localhost'
        self.port = port or 27017
    def __getitem__(self, name):
        return self.mainydb.get_database(name)
    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return self.mainydb.get_database(name)
    def list_database_names(self):
        return self.mainydb.list_database_names()
    def drop_database(self, name):
        return self.mainydb.drop_database(name)
    def close(self):
        self.mainydb.close()