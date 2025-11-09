import time
import random
import tempfile
from MainyDB.core import MainyDB
def run_index_stress(num_docs: int = 15000):
    """
    Crea indici e lancia molte query mirate per verificare correttezza e performance.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MainyDB(path=tmpdir)["stress_index"]
        coll = db["items"]
        payload = [
            {
                "country": random.choice(["IT", "FR", "DE", "ES", "US"]),
                "age": random.randint(18, 80),
                "score": random.randint(0, 1000),
            }
            for _ in range(num_docs)
        ]
        coll.insert_many(payload)
        idx1 = coll.create_index(["country"])
        idx2 = coll.create_index(["country", "age"])
        start = time.perf_counter()
        match_count = 0
        for _ in range(10000):
            q = {"country": random.choice(["IT", "FR", "DE", "ES", "US"]), "age": random.randint(18, 80)}
            docs = coll.find(q).limit(100).to_list()
            match_count += len(docs)
        dur = time.perf_counter() - start
        print(f"[index_stress] queries=10000 matches={match_count} duration={dur:.2f}s")
        assert idx1 in coll.indexes and idx2 in coll.indexes
if __name__ == "__main__":
    run_index_stress()