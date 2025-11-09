import time
import random
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from MainyDB.core import MainyDB
def _writer(coll, stop_event, counters):
    try:
        while not stop_event.is_set():
            if random.random() < 0.7:
                doc = {
                    "user_id": random.randint(1, 1000),
                    "score": random.randint(0, 1000),
                    "active": random.choice([True, False]),
                }
                coll.insert_one(doc)
                counters["insert"] += 1
            else:
                uid = random.randint(1, 1000)
                coll.update_many({"user_id": uid}, {"$inc": {"score": 1}})
                counters["update"] += 1
    except Exception as e:
        counters["errors"].append(("writer", str(e)))
def _reader(coll, stop_event, counters):
    try:
        while not stop_event.is_set():
            q = {"active": True, "score": {"$gt": random.randint(0, 1000)}}
            _ = coll.find(q).limit(50).to_list()
            _ = coll.count_documents(q)
            counters["read"] += 1
    except Exception as e:
        counters["errors"].append(("reader", str(e)))
def run_concurrent_rw(duration_sec: int = 5, writers: int = 8, readers: int = 8):
    """
    Stress test di concorrenza R/W su una singola collection per N secondi.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        mainy = MainyDB(path=tmpdir)
        db = mainy["stress_concurrent"]
        coll = db["items"]
        counters = {"insert": 0, "update": 0, "read": 0, "errors": []}
        stop_event = threading.Event()
        with ThreadPoolExecutor(max_workers=writers + readers) as ex:
            futures = []
            for _ in range(writers):
                futures.append(ex.submit(_writer, coll, stop_event, counters))
            for _ in range(readers):
                futures.append(ex.submit(_reader, coll, stop_event, counters))
            time.sleep(duration_sec)
            stop_event.set()
            for f in futures:
                try:
                    f.result(timeout=2)
                except Exception as e:
                    counters["errors"].append(("future", str(e)))
        total_docs = coll.count_documents()
        print(
            f"[concurrent_rw] duration={duration_sec}s writers={writers} readers={readers} "
            f"insert={counters['insert']} update={counters['update']} read={counters['read']} total_docs={total_docs}"
        )
        assert not counters["errors"], f"Errori riscontrati: {counters['errors']}"
        assert total_docs >= counters["insert"], "Conteggio documenti inferiore agli insert registrati"
        mainy.close()
if __name__ == "__main__":
    run_concurrent_rw()