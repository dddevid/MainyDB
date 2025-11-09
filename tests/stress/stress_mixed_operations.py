import time
import random
import tempfile
from MainyDB.core import MainyDB


def run_mixed_ops(iterations: int = 5000):
    """
    Esegue un mix di CRUD, proiezioni, skip/limit e aggregate su dataset casuale.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MainyDB(path=tmpdir)["stress_mixed"]
        coll = db["items"]

        # Seed iniziale
        for _ in range(2000):
            coll.insert_one({
                "user_id": random.randint(1, 2000),
                "value": random.random(),
                "active": random.choice([True, False]),
                "category": random.choice(["A", "B", "C", "D"]),
            })

        start = time.perf_counter()
        for i in range(iterations):
            r = random.random()
            if r < 0.45:
                coll.insert_one({"user_id": random.randint(1, 2000), "value": random.random()})
            elif r < 0.7:
                uid = random.randint(1, 2000)
                coll.update_one({"user_id": uid}, {"$inc": {"value": 0.1}}, upsert=True)
            elif r < 0.85:
                coll.delete_many({"category": random.choice(["A", "B"])})
            else:
                # Operazioni di lettura con proiezione, sort, skip/limit
                docs = coll.find({"active": True}, projection={"_id": 1, "value": 1}).sort("value").skip(10).limit(20).to_list()
                if docs and random.random() < 0.1:
                    # Piccola aggregazione: group by category simulato via pipeline
                    _ = coll.aggregate([
                        {"$match": {"active": True}},
                        {"$project": {"category": 1}},
                        {"$limit": 100},
                    ])

        dur = time.perf_counter() - start
        total = coll.count_documents()
        print(f"[mixed_ops] iterations={iterations} duration={dur:.2f}s total_docs={total}")

        # Controlli di base
        assert total >= 0


if __name__ == "__main__":
    run_mixed_ops()