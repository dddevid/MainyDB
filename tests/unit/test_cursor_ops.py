import unittest
import tempfile
import random
from MainyDB.core import MainyDB


class TestCursorOps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mainy = MainyDB(path=self.tmp.name)
        self.db = self.mainy["test_cursor"]
        self.coll = self.db["items"]
        payload = [{"value": random.random()} for _ in range(100)]
        self.coll.insert_many(payload)

    def tearDown(self):
        try:
            self.mainy.close()
        finally:
            self.tmp.cleanup()

    def test_sort_skip_limit(self):
        docs = self.coll.find({}).sort("value", 1).skip(10).limit(20).to_list()
        self.assertEqual(len(docs), 20)
        vals = [d["value"] for d in docs]
        self.assertTrue(all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1)))


if __name__ == "__main__":
    unittest.main()
