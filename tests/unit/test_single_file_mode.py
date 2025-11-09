import unittest
import os
import tempfile
import pickle
from MainyDB.core import MainyDB


class TestSingleFileMode(unittest.TestCase):
    def test_mdb_only_with_directory_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = MainyDB(path=tmpdir)
            coll = db.get_database('testdb').get_collection('items')
            coll.insert_one({'name': 'alpha'})
            db.close()

            mdb_path = os.path.join(tmpdir, 'mainydb.mdb')
            self.assertTrue(os.path.isfile(mdb_path), 'mainydb.mdb should exist')
            # Ensure no .collection files anywhere in tmpdir
            found_collection = []
            for root, dirs, files in os.walk(tmpdir):
                found_collection.extend([f for f in files if f.endswith('.collection')])
            self.assertEqual(found_collection, [], 'No .collection files should exist')
            # Ensure no subdirectories created for databases in single-file mode
            top_level_dirs = [d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))]
            self.assertEqual(top_level_dirs, [], 'No database directories should be created')

    def test_mdb_only_with_file_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mdb_path = os.path.join(tmpdir, 'mydb.mdb')
            db = MainyDB(path=mdb_path)
            coll = db.get_database('foo').get_collection('bar')
            coll.insert_one({'k': 'v'})
            db.close()

            self.assertTrue(os.path.isfile(mdb_path), 'specified .mdb should exist')
            found_collection = []
            for root, dirs, files in os.walk(tmpdir):
                found_collection.extend([f for f in files if f.endswith('.collection')])
            self.assertEqual(found_collection, [], 'No .collection files should exist')

    def test_data_persisted_in_mdb(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = MainyDB(path=tmpdir)
            coll = db.get_database('persist').get_collection('docs')
            coll.insert_many([{'n': i} for i in range(3)])
            db.close()

            mdb_path = os.path.join(tmpdir, 'mainydb.mdb')
            with open(mdb_path, 'rb') as f:
                data = pickle.load(f)
            self.assertIn('persist', data)
            self.assertIn('docs', data['persist'])
            docs = data['persist']['docs']['documents']
            self.assertEqual(len(docs), 3)
            self.assertTrue(any(d.get('n') == 1 for d in docs))


if __name__ == '__main__':
    unittest.main()