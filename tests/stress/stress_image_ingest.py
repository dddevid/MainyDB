import os
import sys
import time
import tempfile
import shutil
import subprocess
import urllib.request
import urllib.error
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


def main():
    tmp = tempfile.TemporaryDirectory()
    tmpdir = tmp.name
    dbfile = os.path.join(tmpdir, 'stress_images.mdb')
    mainy = MainyDB(path=dbfile)
    db = mainy['stress_images']
    coll = db['images']

    try:
        targets = ['jpg', 'png', 'gif', 'webp']
        downloaded = {}
        url_map = {
            'jpg': ['https://placehold.co/640x360.jpg'],
            'png': ['https://placehold.co/320x200.png'],
            'gif': [
                'https://placehold.co/200x120.gif',
                'https://images.weserv.nl/?url=placehold.co/640x360.jpg&output=gif'],
            'webp': [
                'https://placehold.co/640x360.webp',
                'https://images.weserv.nl/?url=placehold.co/640x360.jpg&output=webp'],
        }
        for fmt, urls in url_map.items():
            dest = os.path.join(tmpdir, f'stress.{fmt}')
            for u in urls:
                if download(u, dest):
                    downloaded[fmt] = dest
                    break
        base = downloaded.get('jpg') or downloaded.get('png')
        for fmt in targets:
            if fmt in downloaded:
                continue
            if base and convert_ffmpeg(base, os.path.join(tmpdir, f'stress.{fmt}')):
                downloaded[fmt] = os.path.join(tmpdir, f'stress.{fmt}')

        if not downloaded:
            print('Nessuna immagine scaricata: salto stress test.')
            sys.exit(0)

        to_insert = []
        for i in range(250):
            fmt = targets[i % len(targets)]
            path = downloaded.get(fmt)
            if not path:
                continue
            if i % 2 == 0:
                to_insert.append({'name': f'img_{i}_{fmt}_path', 'image': path})
            else:
                with open(path, 'rb') as f:
                    raw = f.read()
                to_insert.append({'name': f'img_{i}_{fmt}_bytes', 'image': raw})

        t0 = time.time()
        coll.insert_many(to_insert)
        t1 = time.time()

        samples = [doc for doc in coll.find({'name': {'$regex': r'^img_\d+_.*'}}).to_list()[:20]]
        decoded_count = 0
        for doc in samples:
            img_val = doc['image']
            if callable(img_val):
                img_val = img_val()
            if isinstance(img_val, (bytes, bytearray)) and len(img_val) > 0:
                decoded_count += 1

        t2 = time.time()
        print(
            f'Inseriti: {len(to_insert)} in {t1 - t0:.3f}s; lettura {len(samples)} in {t2 - t1:.3f}s; decodificati: {decoded_count}')
        sys.exit(0 if decoded_count == len(samples) else 1)
    finally:
        try:
            mainy.close()
        finally:
            tmp.cleanup()


if __name__ == '__main__':
    main()
