import unittest
import tempfile
import random
from MainyDB.core import MainyDB


class TestIndexing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mainy = MainyDB(path=self.tmp.name)
        self.db = self.mainy["test_index"]
        self.coll = self.db["items"]
        payload = [
            {"country": random.choice(["IT", "FR", "DE"]), "age": random.randint(18, 80)}
            for _ in range(500)
        ]
        self.coll.insert_many(payload)

    def tearDown(self):
        try:
            self.mainy.close()
        finally:
            self.tmp.cleanup()

    def test_create_index_and_query(self):
        name = self.coll.create_index(["country", "age"])
        self.assertIn(name, self.coll.indexes)

        q = {"country": "IT", "age": {"$gte": 30}}
        docs = self.coll.find(q).limit(50).to_list()
        self.assertTrue(all(d["country"] == "IT" and d["age"] >= 30 for d in docs))


if __name__ == "__main__":
    unittest.main()