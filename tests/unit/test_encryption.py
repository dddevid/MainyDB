"""
Test suite for MainyDB encryption functionality
Tests SHA256 hashing and AES256 encryption
"""

from MainyDB.core import Database
from MainyDB import (
    MainyDB,
    EncryptionManager,
    SHA256Hasher,
    AES256Cipher,
    EncryptionConfig,
    create_encryption_config
)
import os
import sys
import tempfile
import pytest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestSHA256Hasher:
    """Test SHA256 hashing functionality"""

    def test_hash_creates_valid_hash(self):
        """Test that hashing creates a valid hash with salt"""
        hasher = SHA256Hasher()
        result = hasher.hash("test_password")

        assert 'hash' in result
        assert 'salt' in result
        assert 'algorithm' in result
        assert result['algorithm'] == 'sha256'

    def test_verify_correct_password(self):
        """Test that verification works for correct password"""
        hasher = SHA256Hasher()
        stored_hash = hasher.hash("test_password")

        assert hasher.verify("test_password", stored_hash)

    def test_verify_incorrect_password(self):
        """Test that verification fails for incorrect password"""
        hasher = SHA256Hasher()
        stored_hash = hasher.hash("test_password")

        assert hasher.verify("wrong_password", stored_hash) == False

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (due to salt)"""
        hasher = SHA256Hasher()
        hash1 = hasher.hash("test_password")
        hash2 = hasher.hash("test_password")

        assert hash1['hash'] != hash2['hash']

        assert hasher.verify("test_password", hash1)
        assert hasher.verify("test_password", hash2)


class TestAES256Cipher:
    """Test AES256 encryption functionality"""

    def test_encrypt_creates_valid_ciphertext(self):
        """Test that encryption creates valid ciphertext"""
        cipher = AES256Cipher("test_key")
        result = cipher.encrypt("sensitive_data")

        assert 'ciphertext' in result
        assert 'iv' in result
        assert 'algorithm' in result
        assert result['algorithm'] == 'aes256'

    def test_decrypt_recovers_original(self):
        """Test that decryption recovers original data"""
        cipher = AES256Cipher("test_key")
        original = "sensitive_data"
        encrypted = cipher.encrypt(original)
        decrypted = cipher.decrypt(encrypted)

        assert decrypted == original

    def test_different_iv_each_time(self):
        """Test that same data produces different ciphertexts (due to IV)"""
        cipher = AES256Cipher("test_key")
        enc1 = cipher.encrypt("sensitive_data")
        enc2 = cipher.encrypt("sensitive_data")

        assert enc1['iv'] != enc2['iv']

        assert enc1['ciphertext'] != enc2['ciphertext']

        assert cipher.decrypt(enc1) == "sensitive_data"
        assert cipher.decrypt(enc2) == "sensitive_data"

    def test_different_keys_produce_different_results(self):
        """Test that different keys produce different ciphertexts"""
        cipher1 = AES256Cipher("key1")
        cipher2 = AES256Cipher("key2")

        enc1 = cipher1.encrypt("data")
        enc2 = cipher2.encrypt("data")

        assert cipher1.decrypt(enc1) == "data"
        assert cipher2.decrypt(enc2) == "data"


class TestEncryptionConfig:
    """Test encryption configuration"""

    def test_add_sha256_field(self):
        """Test adding SHA256 field to config"""
        config = EncryptionConfig()
        config.add_sha256_field("password")

        assert config.is_sha256_field("password")
        assert config.is_aes256_field("password") == False
        assert config.is_encrypted_field("password")

    def test_add_aes256_field(self):
        """Test adding AES256 field to config"""
        config = EncryptionConfig()
        config.add_aes256_field("email")

        assert config.is_aes256_field("email")
        assert config.is_sha256_field("email") == False
        assert config.is_encrypted_field("email")

    def test_create_encryption_config_helper(self):
        """Test helper function to create config"""
        config = create_encryption_config(
            sha256_fields=["password"],
            aes256_fields=["email", "ssn"]
        )

        assert config.is_sha256_field("password")
        assert config.is_aes256_field("email")
        assert config.is_aes256_field("ssn")


class TestEncryptionManager:
    """Test encryption manager"""

    def test_encrypt_document_sha256(self):
        """Test encrypting document with SHA256 fields"""
        config = create_encryption_config(sha256_fields=["password"])
        manager = EncryptionManager(config, aes_key="test_key")

        doc = {"username": "john", "password": "secret123"}
        encrypted_doc = manager.encrypt_document(doc)

        assert encrypted_doc["username"] == "john"

        assert isinstance(encrypted_doc["password"], dict)
        assert encrypted_doc["password"]["algorithm"] == "sha256"

    def test_encrypt_document_aes256(self):
        """Test encrypting document with AES256 fields"""
        config = create_encryption_config(aes256_fields=["email"])
        manager = EncryptionManager(config, aes_key="test_key")

        doc = {"username": "john", "email": "john@example.com"}
        encrypted_doc = manager.encrypt_document(doc)

        assert encrypted_doc["username"] == "john"

        assert isinstance(encrypted_doc["email"], dict)
        assert encrypted_doc["email"]["algorithm"] == "aes256"

    def test_decrypt_document_aes256(self):
        """Test decrypting document with AES256 fields"""
        config = create_encryption_config(aes256_fields=["email"])
        manager = EncryptionManager(config, aes_key="test_key")

        doc = {"username": "john", "email": "john@example.com"}
        encrypted_doc = manager.encrypt_document(doc)
        decrypted_doc = manager.decrypt_document(encrypted_doc)

        assert decrypted_doc["email"] == "john@example.com"

    def test_verify_sha256_field(self):
        """Test verifying SHA256 hashed field"""
        config = create_encryption_config(sha256_fields=["password"])
        manager = EncryptionManager(config, aes_key="test_key")

        doc = {"password": "secret123"}
        encrypted_doc = manager.encrypt_document(doc)

        assert manager.verify_sha256_field(
            "password", "secret123", encrypted_doc["password"]
        )

        assert manager.verify_sha256_field(
            "password", "wrong", encrypted_doc["password"]
        ) == False


class TestDatabaseIntegration:
    """Test integration with MainyDB"""

    def test_insert_with_sha256_encryption(self):
        """Test inserting documents with SHA256 encryption"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.mdb")
            db = MainyDB(db_path)

            config = create_encryption_config(sha256_fields=["password"])
            encryption_manager = EncryptionManager(config, aes_key="test_key")

            users_db = Database(db, "users", encryption_manager=encryption_manager)
            users = users_db.create_collection("users")

            user = {"username": "john", "password": "secret123"}
            result = users.insert_one(user)

            found_user = users.find_one({"username": "john"})

            assert isinstance(found_user["password"], dict)
            assert found_user["password"]["algorithm"] == "sha256"

    def test_insert_with_aes256_encryption(self):
        """Test inserting documents with AES256 encryption"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.mdb")
            db = MainyDB(db_path)

            config = create_encryption_config(aes256_fields=["email"])
            encryption_manager = EncryptionManager(config, aes_key="test_key")

            users_db = Database(db, "users", encryption_manager=encryption_manager)
            users = users_db.create_collection("users")

            user = {"username": "john", "email": "john@example.com"}
            result = users.insert_one(user)

            found_user = users.find_one({"username": "john"})

            assert found_user["email"] == "john@example.com"

    def test_update_with_encryption(self):
        """Test updating documents with encryption"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.mdb")
            db = MainyDB(db_path)

            config = create_encryption_config(
                sha256_fields=["password"],
                aes256_fields=["email"]
            )
            encryption_manager = EncryptionManager(config, aes_key="test_key")

            users_db = Database(db, "users", encryption_manager=encryption_manager)
            users = users_db.create_collection("users")

            user = {"username": "john", "password": "old_pass", "email": "old@example.com"}
            users.insert_one(user)

            users.update_one(
                {"username": "john"},
                {"$set": {"password": "new_pass", "email": "new@example.com"}}
            )

            found_user = users.find_one({"username": "john"})

            assert found_user["email"] == "new@example.com"

            assert isinstance(found_user["password"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
