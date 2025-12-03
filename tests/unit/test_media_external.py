import unittest
import tempfile
import os
import io
import shutil
import subprocess
import urllib.request
import urllib.error
from typing import Dict, List

from MainyDB.core import MainyDB


def download(url: str, dest: str, timeout: int = 15) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()
        with open(dest, 'wb') as f:
            f.write(data)
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False


def ffmpeg_available() -> bool:
    return shutil.which('ffmpeg') is not None


def convert_ffmpeg(src: str, dest: str) -> bool:
    if not ffmpeg_available():
        return False
    try:
        subprocess.run(['ffmpeg', '-y', '-i', src, dest], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


class TestExternalImageAPIs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = self.tmp.name
        self.dbfile = os.path.join(self.tmpdir, 'ext_media.mdb')
        self.mainy = MainyDB(path=self.dbfile)
        self.db = self.mainy["ext_media"]
        self.images = self.db["images"]

        self.targets = ['jpg', 'png', 'gif', 'webp', 'tiff', 'heic']

        base_map: Dict[str, List[str]] = {
            'jpg': [
                'https://picsum.photos/800/600.jpg',
                'https://placehold.co/800x600.jpg',
            ],
            'png': [
                'https://placehold.co/600x400.png',
            ],
            'gif': [
                'https://placehold.co/320x200.gif',
                'https://images.weserv.nl/?url=placehold.co/600x400.jpg&output=gif',
            ],
            'webp': [
                'https://picsum.photos/800/600.webp',
                'https://placehold.co/600x400.webp',
                'https://cdn.statically.io/img/placehold.co/f=webp/600x400.jpg',
                'https://images.weserv.nl/?url=placehold.co/600x400.jpg&output=webp',
            ],
            'tiff': [
            ],
            'heic': [
            ],
        }

        self.downloaded: Dict[str, str] = {}
        for fmt, urls in base_map.items():
            dest = os.path.join(self.tmpdir, f'sample.{fmt}')
            for url in urls:
                if download(url, dest):
                    self.downloaded[fmt] = dest
                    break

        src_for_conv = self.downloaded.get('jpg') or self.downloaded.get('png')
        for fmt in self.targets:
            if fmt in self.downloaded:
                continue
            if not src_for_conv:
                continue
            dest = os.path.join(self.tmpdir, f'sample.{fmt}')
            if convert_ffmpeg(src_for_conv, dest):
                self.downloaded[fmt] = dest

    def tearDown(self):
        try:
            self.mainy.close()
        finally:
            self.tmp.cleanup()

    def test_insert_and_read_bytes_and_path(self):
        if not self.downloaded:
            self.skipTest('Nessuna immagine scaricata dalle API esterne (nessuna rete o servizi down)')

        for fmt, path in self.downloaded.items():
            name = f'path_{fmt}'
            self.images.insert_one({'name': name, 'image': path})

        for fmt, path in self.downloaded.items():
            name = f'bytes_{fmt}'
            with open(path, 'rb') as f:
                raw = f.read()
            self.images.insert_one({'name': name, 'image': raw})

        for fmt in self.downloaded.keys():
            doc_path = self.images.find_one({'name': f'path_{fmt}'})
            self.assertIsNotNone(doc_path)
            self.assertIn('image', doc_path)
            self.assertIsInstance(doc_path['image'], (bytes, bytearray))
            self.assertGreater(len(doc_path['image']), 0)

            docs_bytes = self.images.find({'name': f'bytes_{fmt}'}).to_list()
            self.assertEqual(len(docs_bytes), 1)
            self.assertTrue(callable(docs_bytes[0]['image']))
            decoded = docs_bytes[0]['image']()
            self.assertIsInstance(decoded, (bytes, bytearray))
            self.assertGreater(len(decoded), 0)

    def test_update_with_path_and_bytes(self):
        if not self.downloaded:
            self.skipTest('Nessuna immagine scaricata, salto test update')
        base = self.downloaded.get('png') or self.downloaded.get('jpg')
        if not base:
            base = list(self.downloaded.values())[0]
        self.images.insert_one({'name': 'upd', 'image': base})

        alt_path = None
        for fmt, p in self.downloaded.items():
            if p != base:
                alt_path = p
                break
        if alt_path:
            self.images.update_one({'name': 'upd'}, {'$set': {'image': alt_path}})
            doc = self.images.find_one({'name': 'upd'})
            self.assertIsInstance(doc['image'], (bytes, bytearray))
            self.assertGreater(len(doc['image']), 0)

        with open(base, 'rb') as f:
            raw = f.read()
        self.images.update_one({'name': 'upd'}, {'$set': {'image': raw}})
        doc2 = self.images.find_one({'name': 'upd'})
        self.assertIsInstance(doc2['image'], (bytes, bytearray))
        self.assertGreater(len(doc2['image']), 0)


if __name__ == '__main__':
    unittest.main()
