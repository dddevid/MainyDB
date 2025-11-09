import unittest
import tempfile
from MainyDB.core import MainyDB


class TestMediaHandling(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mainy = MainyDB(path=self.tmp.name)
        self.db = self.mainy["test_media"]
        self.coll = self.db["items"]

    def tearDown(self):
        try:
            self.mainy.close()
        finally:
            self.tmp.cleanup()

    def test_binary_media_storage_and_retrieval(self):
        payload1 = b"hello-binary-1"
        payload2 = b"hello-binary-2"
        self.coll.insert_many([
            {"name": "file1", "data": payload1},
            {"name": "file2", "data": payload2},
        ])

        # Verifica lazy decode con find() su file1
        docs1 = self.coll.find({"name": "file1"}).to_list()
        self.assertEqual(len(docs1), 1)
        self.assertTrue(callable(docs1[0]["data"]))
        decoded1 = docs1[0]["data"]()
        self.assertEqual(decoded1, payload1)

        # Verifica eager decode con find_one() su file2
        doc2 = self.coll.find_one({"name": "file2"})
        self.assertIsInstance(doc2["data"], (bytes, bytearray))
        self.assertEqual(doc2["data"], payload2)


if __name__ == "__main__":
    unittest.main()