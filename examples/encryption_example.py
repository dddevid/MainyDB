"""
MainyDB Encryption Example

This example demonstrates how to use the encryption features in MainyDB
to automatically encrypt sensitive data using SHA256 (one-way) and AES256 (reversible).
"""

from MainyDB.core import Database
from MainyDB import MainyDB, create_encryption_config, EncryptionManager
import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def main():

    db = MainyDB("encrypted_app.mdb")

    config = create_encryption_config(
        sha256_fields=["password", "security_answer"],
        aes256_fields=["email", "ssn", "credit_card"]
    )

    encryption_manager = EncryptionManager(config, aes_key="my-secret-encryption-key-2024")

    users_db = Database(db, "my_app", encryption_manager=encryption_manager)
    users = users_db.create_collection("users")

    print("=== MainyDB Encryption Example ===\n")

    print("1. Inserting user with encrypted fields...")
    users.insert_one({
        "username": "alice_wonder",
        "password": "mySecretPassword123!",
        "email": "alice@example.com",
        "ssn": "123-45-6789",
        "security_answer": "blue",
        "age": 28,
        "country": "USA"
    })
    print("✓ User inserted successfully\n")

    print("2. Finding user (AES256 fields auto-decrypt)...")
    user = users.find_one({"username": "alice_wonder"})
    print(f"   Username: {user['username']}")
    print(f"   Email: {user['email']}")
    print(f"   SSN: {user['ssn']}")
    print(f"   Age: {user['age']}")
    print(f"   Password (SHA256 hash): {user['password']['algorithm']} - cannot be decrypted")
    print()

    print("3. Verifying password...")
    correct_password = "mySecretPassword123!"
    wrong_password = "wrongPassword"

    is_valid_correct = encryption_manager.verify_sha256_field(
        "password", correct_password, user["password"]
    )
    is_valid_wrong = encryption_manager.verify_sha256_field(
        "password", wrong_password, user["password"]
    )

    print(f"   Correct password verification: {is_valid_correct}")
    print(f"   Wrong password verification: {is_valid_wrong}")
    print()

    print("4. Updating encrypted fields...")
    users.update_one(
        {"username": "alice_wonder"},
        {"$set": {
            "email": "alice.new@example.com",
            "password": "newSecurePassword456!"
        }}
    )
    print("✓ Fields updated successfully\n")

    print("5. Verifying updated fields...")
    updated_user = users.find_one({"username": "alice_wonder"})
    print(f"   New email: {updated_user['email']}")

    is_new_password_valid = encryption_manager.verify_sha256_field(
        "password", "newSecurePassword456!", updated_user["password"]
    )
    print(f"   New password verification: {is_new_password_valid}")
    print()

    print("6. Inserting multiple users...")
    users.insert_many([
        {
            "username": "bob_builder",
            "password": "bobPass123",
            "email": "bob@example.com",
            "age": 35
        },
        {
            "username": "charlie_brown",
            "password": "charlieSecure",
            "email": "charlie@example.com",
            "ssn": "987-65-4321",
            "age": 42
        }
    ])
    print("✓ Multiple users inserted successfully\n")

    print("7. Finding all users...")
    all_users = users.find()
    count = 0
    for user in all_users:
        count += 1
        print(f"   User {count}: {user['username']} - {user['email']}")
    print()

    print("8. Security Best Practices:")
    print("   ✓ SHA256 for passwords (one-way, cannot be reversed)")
    print("   ✓ AES256 for sensitive data that needs to be retrieved")
    print("   ✓ Use environment variables for encryption keys")
    print("   ✓ Never commit encryption keys to version control")
    print("   ✓ Implement key rotation policies")
    print("   ✓ Limit access to encryption keys")
    print()

    print("=== Example completed successfully! ===")
    print("\nNote: The database file 'encrypted_app.mdb' now contains encrypted data.")
    print("SHA256 hashed fields cannot be decrypted.")
    print("AES256 encrypted fields can only be decrypted with the correct key.")

    db.close()


if __name__ == "__main__":
    main()
