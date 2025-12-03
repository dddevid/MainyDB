"""
MainyDB Encryption Example

This example demonstrates how to use the encryption features in MainyDB
to automatically encrypt sensitive data using SHA256 (one-way) and AES256 (reversible).
"""

import os
import sys

# Add parent directory to path to import MainyDB
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from MainyDB import MainyDB, create_encryption_config, EncryptionManager
from MainyDB.core import Database


def main():
    # Create/open database
    db = MainyDB("encrypted_app.mdb")
    
    # Create encryption configuration
    # SHA256 for passwords (one-way, can't be decrypted)
    # AES256 for emails and SSNs (reversible, can be decrypted)
    config = create_encryption_config(
        sha256_fields=["password", "security_answer"],
        aes256_fields=["email", "ssn", "credit_card"]
    )
    
    # Create encryption manager with encryption key
    # In production, use environment variable or secure key management
    encryption_manager = EncryptionManager(config, aes_key="my-secret-encryption-key-2024")
    
    # Create database with encryption
    users_db = Database(db, "my_app", encryption_manager=encryption_manager)
    users = users_db.create_collection("users")
    
    print("=== MainyDB Encryption Example ===\n")
    
    # Example 1: Insert user with encrypted fields
    print("1. Inserting user with encrypted fields...")
    users.insert_one({
        "username": "alice_wonder",
        "password": "mySecretPassword123!",  # Will be hashed with SHA256
        "email": "alice@example.com",  # Will be encrypted with AES256
        "ssn": "123-45-6789",  # Will be encrypted with AES256
        "security_answer": "blue",  # Will be hashed with SHA256
        "age": 28,  # Not encrypted
        "country": "USA"  # Not encrypted
    })
    print("✓ User inserted successfully\n")
    
    # Example 2: Find user - AES256 fields are automatically decrypted
    print("2. Finding user (AES256 fields auto-decrypt)...")
    user = users.find_one({"username": "alice_wonder"})
    print(f"   Username: {user['username']}")
    print(f"   Email: {user['email']}")  # Automatically decrypted
    print(f"   SSN: {user['ssn']}")  # Automatically decrypted
    print(f"   Age: {user['age']}")
    print(f"   Password (SHA256 hash): {user['password']['algorithm']} - cannot be decrypted")
    print()
    
    # Example 3: Verify SHA256 password
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
    
    # Example 4: Update encrypted fields
    print("4. Updating encrypted fields...")
    users.update_one(
        {"username": "alice_wonder"},
        {"$set": {
            "email": "alice.new@example.com",  # Will be re-encrypted
            "password": "newSecurePassword456!"  # Will be re-hashed
        }}
    )
    print("✓ Fields updated successfully\n")
    
    # Example 5: Verify updated fields
    print("5. Verifying updated fields...")
    updated_user = users.find_one({"username": "alice_wonder"})
    print(f"   New email: {updated_user['email']}")  # Automatically decrypted
    
    # Verify new password
    is_new_password_valid = encryption_manager.verify_sha256_field(
        "password", "newSecurePassword456!", updated_user["password"]
    )
    print(f"   New password verification: {is_new_password_valid}")
    print()
    
    # Example 6: Insert multiple users
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
    
    # Example 7: Find all users
    print("7. Finding all users...")
    all_users = users.find()
    count = 0
    for user in all_users:
        count += 1
        print(f"   User {count}: {user['username']} - {user['email']}")
    print()
    
    # Example 8: Security best practices demonstration
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
    
    # Clean up
    db.close()


if __name__ == "__main__":
    main()
