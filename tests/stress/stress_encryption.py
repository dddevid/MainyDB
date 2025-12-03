"""
Stress test per encryption: concorrenza, performance, e thread safety
"""

from MainyDB import create_encryption_config, EncryptionManager
from MainyDB.core import MainyDB, Database
import os
import sys
import time
import random
import string
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def random_string(length=10):
    """Generate a random string"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def random_email():
    """Generate a random email"""
    return f"{random_string(8)}@{random_string(5)}.com"


def random_ssn():
    """Generate a random SSN"""
    return f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"


def _writer_encrypted(coll, encryption_manager, stop_event, counters):
    """
    Writer thread that inserts and updates encrypted documents
    """
    try:
        while not stop_event.is_set():
            if random.random() < 0.6:

                doc = {
                    "username": random_string(12),
                    "password": random_string(16),
                    "email": random_email(),
                    "ssn": random_ssn(),
                    "age": random.randint(18, 80),
                    "active": random.choice([True, False]),
                }
                coll.insert_one(doc)
                counters["insert"] += 1
            else:

                username = random_string(12)
                updates = {}
                if random.random() < 0.5:
                    updates["password"] = random_string(16)
                if random.random() < 0.5:
                    updates["email"] = random_email()

                if updates:
                    coll.update_many(
                        {"active": True},
                        {"$set": updates}
                    )
                    counters["update"] += 1
    except Exception as e:
        counters["errors"].append(("writer_encrypted", str(e)))


def _reader_encrypted(coll, encryption_manager, stop_event, counters):
    """
    Reader thread that queries and verifies encrypted data
    """
    try:
        while not stop_event.is_set():

            docs = coll.find({"active": True}).limit(10).to_list()
            counters["read"] += 1

            for doc in docs:

                if "email" in doc and isinstance(doc["email"], str):
                    counters["decrypt_success"] += 1

                if "password" in doc and isinstance(doc["password"], dict):
                    if doc["password"].get("algorithm") == "sha256":
                        counters["hash_verify"] += 1
    except Exception as e:
        counters["errors"].append(("reader_encrypted", str(e)))


def _password_verifier(coll, encryption_manager, stop_event, counters):
    """
    Thread that verifies SHA256 passwords
    """
    try:
        thread_id = threading.current_thread().ident
        idx = 0

        while not stop_event.is_set():

            password = random_string(16)
            username = f"verify_user_{thread_id}_{idx}"

            coll.insert_one({
                "username": username,
                "password": password,
                "email": random_email(),
                "active": False,
            })

            time.sleep(0.001)

            user = coll.find_one({"username": username})
            if user and "password" in user:
                try:
                    is_valid = encryption_manager.verify_sha256_field(
                        "password", password, user["password"]
                    )
                    if is_valid:
                        counters["password_verify_success"] += 1
                    else:
                        counters["password_verify_fail"] += 1

                        print(f"  [DEBUG] Password verify failed for {username}")
                except Exception as e:
                    counters["errors"].append(("password_verify", str(e)))

            idx += 1
            if idx >= 50:
                break
    except Exception as e:
        counters["errors"].append(("password_verifier", str(e)))


def run_encryption_stress(
    duration_sec: int = 5,
    writers: int = 4,
    readers: int = 4,
    verifiers: int = 2
):
    """
    Stress test for encryption with concurrent operations

    Tests:
    - Concurrent inserts with encrypted fields
    - Concurrent updates with encrypted fields
    - Concurrent reads with automatic decryption
    - SHA256 password verification under load
    - Thread safety of encryption operations
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        mainy = MainyDB(path=tmpdir)

        config = create_encryption_config(
            sha256_fields=["password", "security_answer"],
            aes256_fields=["email", "ssn", "credit_card"]
        )

        encryption_manager = EncryptionManager(
            config,
            aes_key="stress-test-key-2024-very-secure"
        )

        db = Database(mainy, "stress_encryption", encryption_manager=encryption_manager)
        coll = db.create_collection("users")

        counters = {
            "insert": 0,
            "update": 0,
            "read": 0,
            "decrypt_success": 0,
            "hash_verify": 0,
            "password_verify_success": 0,
            "password_verify_fail": 0,
            "errors": []
        }

        stop_event = threading.Event()

        with ThreadPoolExecutor(max_workers=writers + readers + verifiers) as ex:
            futures = []

            for _ in range(writers):
                futures.append(
                    ex.submit(_writer_encrypted, coll, encryption_manager, stop_event, counters)
                )

            for _ in range(readers):
                futures.append(
                    ex.submit(_reader_encrypted, coll, encryption_manager, stop_event, counters)
                )

            for _ in range(verifiers):
                futures.append(
                    ex.submit(_password_verifier, coll, encryption_manager, stop_event, counters)
                )

            time.sleep(duration_sec)
            stop_event.set()

            for f in futures:
                try:
                    f.result(timeout=3)
                except Exception as e:
                    counters["errors"].append(("future", str(e)))

        total_docs = coll.count_documents()

        print(
            f"[encryption_stress] duration={duration_sec}s "
            f"writers={writers} readers={readers} verifiers={verifiers}"
        )
        print(
            f"  Operations: insert={counters['insert']} update={counters['update']} "
            f"read={counters['read']}"
        )
        print(
            f"  Encryption: decrypt_success={counters['decrypt_success']} "
            f"hash_verify={counters['hash_verify']}"
        )
        print(
            f"  Password Verify: success={counters['password_verify_success']} "
            f"fail={counters['password_verify_fail']}"
        )
        print(f"  Total docs: {total_docs}")

        assert not counters["errors"], f"Errors detected: {counters['errors']}"
        assert total_docs > 0, "No documents inserted"
        assert counters["decrypt_success"] > 0, "No successful decryptions"
        assert counters["hash_verify"] > 0, "No hash verifications"
        assert counters["password_verify_success"] > 0, "No successful password verifications"

        if counters["password_verify_fail"] > 0:
            success_rate = counters["password_verify_success"] / (
                counters["password_verify_success"] + counters["password_verify_fail"]
            )
            print(f"  Password verify success rate: {success_rate:.1%}")
            assert success_rate > 0.9, f"Password verification success rate too low: {success_rate:.1%}"

        sample = coll.find_one({"active": True})
        if sample:
            print("\n  Sample document verification:")
            if "email" in sample:
                assert isinstance(sample["email"], str), "Email not decrypted"
                print(f"    ✓ Email decrypted: {sample['email']}")
            if "password" in sample:
                assert isinstance(sample["password"], dict), "Password not hashed"
                assert sample["password"].get("algorithm") == "sha256", "Wrong hash algorithm"
                print(f"    ✓ Password hashed with {sample['password']['algorithm']}")

        mainy.close()
        print("\n[encryption_stress] ✓ All checks passed!")


if __name__ == "__main__":
    run_encryption_stress()
