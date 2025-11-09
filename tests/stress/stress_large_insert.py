import os
import time
import random
import tempfile
from MainyDB.core import MainyDB
def run_large_insert(num_docs: int = 20000, batch_size: int = 1000):
    """
    Inserisce una grande quantità di documenti e misura throughput e correttezza.
    - num_docs: numero totale di documenti da inserire
    - batch_size: dimensione dei batch per insert_many
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MainyDB(path=tmpdir)["stress_large"]
        coll = db["items"]
        start = time.perf_counter()
        remaining = num_docs
        inserted = 0
        while remaining > 0:
            n = min(batch_size, remaining)
            batch = [
                {
                    "user_id": random.randint(1, 10000),
                    "value": random.random(),
                    "tags": ["t" + str(random.randint(1, 50)) for _ in range(random.randint(1, 5))],
                }
                for _ in range(n)
            ]
            res = coll.insert_many(batch)
            inserted += len(res.get("inserted_ids", []))
            remaining -= n
        dur = time.perf_counter() - start
        count = coll.count_documents()
        print(f"[large_insert] inserted={inserted} count={count} duration={dur:.2f}s ops/s={inserted/dur:.0f}")
        assert count == num_docs, f"Conteggio errato: atteso {num_docs}, ottenuto {count}"
        assert inserted == num_docs, f"Insert errato: atteso {num_docs}, ottenuto {inserted}"
if __name__ == "__main__":
    run_large_insert()