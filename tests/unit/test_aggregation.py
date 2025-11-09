import unittest
import tempfile
from MainyDB.core import MainyDB


class TestAggregation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mainy = MainyDB(path=self.tmp.name)
        self.db = self.mainy["test_agg"]
        self.coll = self.db["items"]
        self.coll.insert_many([
            {"group": "A", "val": 10},
            {"group": "A", "val": 5},
            {"group": "B", "val": 3},
        ])

    def tearDown(self):
        try:
            self.mainy.close()
        finally:
            self.tmp.cleanup()

    def test_group_sum(self):
        res = self.coll.aggregate([
            {"$match": {}},
            {"$group": {"_id": "$group", "total": {"$sum": "$val"}}},
            {"$sort": {"_id": 1}},
        ])
        results = list(res)
        as_dict = {r["_id"]: r["total"] for r in results}
        self.assertEqual(as_dict.get("A"), 15)
        self.assertEqual(as_dict.get("B"), 3)


if __name__ == "__main__":
    unittest.main()