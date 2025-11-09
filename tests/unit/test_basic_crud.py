import unittest
import tempfile
from MainyDB.core import MainyDB


class TestBasicCRUD(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mainy = MainyDB(path=self.tmp.name)
        self.db = self.mainy["test_basic"]
        self.coll = self.db["items"]

    def tearDown(self):
        try:
            self.mainy.close()
        finally:
            self.tmp.cleanup()

    def test_insert_find_update_delete(self):
        # insert_one
        res = self.coll.insert_one({"name": "alpha", "age": 30})
        self.assertIn("inserted_id", res)

        # find_one
        doc = self.coll.find_one({"name": "alpha"})
        self.assertIsNotNone(doc)
        self.assertEqual(doc["age"], 30)

        # insert_many
        many = [{"name": f"n{i}", "val": i} for i in range(10)]
        res_many = self.coll.insert_many(many)
        self.assertEqual(len(res_many.get("inserted_ids", [])), 10)

        # count_documents
        total = self.coll.count_documents()
        self.assertEqual(total, 11)

        # update_one
        upd = self.coll.update_one({"name": "alpha"}, {"$set": {"age": 31}})
        self.assertEqual(upd["matched_count"], 1)
        self.assertEqual(upd["modified_count"], 1)
        doc = self.coll.find_one({"name": "alpha"})
        self.assertEqual(doc["age"], 31)

        # replace_one (mantiene _id)
        old = self.coll.find_one({"name": "alpha"})
        rid = old["_id"]
        rep = self.coll.replace_one({"name": "alpha"}, {"name": "beta", "age": 40})
        self.assertEqual(rep["matched_count"], 1)
        newdoc = self.coll.find_one({"name": "beta"})
        self.assertIsNotNone(newdoc)
        self.assertEqual(newdoc["_id"], rid)

        # delete_one
        del_res = self.coll.delete_one({"name": "beta"})
        self.assertEqual(del_res["deleted_count"], 1)

        # delete_many
        dm = self.coll.delete_many({"val": {"$gte": 5}})
        self.assertTrue(dm["deleted_count"] >= 5)

    def test_distinct_and_projection(self):
        self.coll.insert_many([
            {"category": "A", "x": 1},
            {"category": "B", "x": 2},
            {"category": "A", "x": 3},
        ])
        vals = self.coll.distinct("category")
        self.assertTrue(set(vals).issuperset({"A", "B"}))

        # projection include
        docs = self.coll.find({}, projection={"category": 1, "_id": 0}).to_list()
        self.assertTrue(all("category" in d and "_id" not in d for d in docs))


if __name__ == "__main__":
    unittest.main()