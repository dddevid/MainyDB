"""
MainyDB Encryption Module

Provides automatic encryption support for MainyDB using:
- SHA256: One-way hashing (ideal for passwords)
- AES256: Reversible encryption (ideal for sensitive data like emails, SSN, etc.)
"""

import base64
import hashlib
import os
import secrets
import threading
from typing import Any, Dict, List, Optional, Union

try:
    from Crypto.Cipher import AES
    from Crypto.Protocol.KDF import PBKDF2
    from Crypto.Random import get_random_bytes
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class SHA256Hasher:
    """
    SHA256 one-way hashing for strings.
    Used for data that should not be reversible (e.g., passwords).
    """

    @staticmethod
    def hash(data: str, salt: Optional[bytes] = None) -> Dict[str, str]:
        """
        Hash a string using SHA256 with salt.

        Args:
            data: String to hash
            salt: Optional salt bytes. If not provided, generates random salt.

        Returns:
            Dict containing 'hash' and 'salt' (both base64 encoded)
        """
        if salt is None:
            salt = secrets.token_bytes(32)

        hasher = hashlib.sha256()
        hasher.update(salt)
        hasher.update(data.encode('utf-8'))
        hash_bytes = hasher.digest()

        return {
            'hash': base64.b64encode(hash_bytes).decode('utf-8'),
            'salt': base64.b64encode(salt).decode('utf-8'),
            'algorithm': 'sha256'
        }

    @staticmethod
    def verify(data: str, stored_hash: Dict[str, str]) -> bool:
        """
        Verify a string against a stored hash.

        Args:
            data: String to verify
            stored_hash: Dict containing 'hash' and 'salt'

        Returns:
            True if data matches the hash, False otherwise
        """
        salt = base64.b64decode(stored_hash['salt'])
        new_hash = SHA256Hasher.hash(data, salt)
        return new_hash['hash'] == stored_hash['hash']


class AES256Cipher:
    """
    AES256 encryption/decryption for strings.
    Used for data that needs to be reversible (e.g., emails, SSN, credit cards).
    """

    def __init__(self, key: Union[str, bytes]):
        """
        Initialize AES256 cipher with a key.

        Args:
            key: Encryption key (string or bytes). If string, will be derived using PBKDF2.
        """
        if not CRYPTO_AVAILABLE:
            raise ImportError(
                "pycryptodome is required for AES256 encryption. "
                "Install it with: pip install pycryptodome"
            )

        if isinstance(key, str):

            salt = b'MainyDB-AES256-Salt'
            self.key = PBKDF2(key, salt, dkLen=32, count=100000)
        else:
            self.key = key

        self.lock = threading.RLock()

    def encrypt(self, data: str) -> Dict[str, str]:
        """
        Encrypt a string using AES256.

        Args:
            data: String to encrypt

        Returns:
            Dict containing 'ciphertext', 'iv', and 'algorithm'
        """
        with self.lock:

            iv = get_random_bytes(16)

            cipher = AES.new(self.key, AES.MODE_CBC, iv)

            data_bytes = data.encode('utf-8')
            padding_length = 16 - (len(data_bytes) % 16)
            padded_data = data_bytes + (bytes([padding_length]) * padding_length)

            ciphertext = cipher.encrypt(padded_data)

            return {
                'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
                'iv': base64.b64encode(iv).decode('utf-8'),
                'algorithm': 'aes256'
            }

    def decrypt(self, encrypted_data: Dict[str, str]) -> str:
        """
        Decrypt AES256 encrypted data.

        Args:
            encrypted_data: Dict containing 'ciphertext' and 'iv'

        Returns:
            Decrypted string
        """
        with self.lock:

            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
            iv = base64.b64decode(encrypted_data['iv'])

            cipher = AES.new(self.key, AES.MODE_CBC, iv)

            padded_data = cipher.decrypt(ciphertext)

            padding_length = padded_data[-1]
            data_bytes = padded_data[:-padding_length]

            return data_bytes.decode('utf-8')


class EncryptionConfig:
    """
    Configuration for field encryption.
    """

    def __init__(self):
        self.sha256_fields: List[str] = []
        self.aes256_fields: List[str] = []

    def add_sha256_field(self, field_name: str):
        """Add a field to be hashed with SHA256."""
        if field_name not in self.sha256_fields:
            self.sha256_fields.append(field_name)

    def add_aes256_field(self, field_name: str):
        """Add a field to be encrypted with AES256."""
        if field_name not in self.aes256_fields:
            self.aes256_fields.append(field_name)

    def is_sha256_field(self, field_name: str) -> bool:
        """Check if a field should be hashed with SHA256."""
        return field_name in self.sha256_fields

    def is_aes256_field(self, field_name: str) -> bool:
        """Check if a field should be encrypted with AES256."""
        return field_name in self.aes256_fields

    def is_encrypted_field(self, field_name: str) -> bool:
        """Check if a field should be encrypted (SHA256 or AES256)."""
        return self.is_sha256_field(field_name) or self.is_aes256_field(field_name)


class EncryptionManager:
    """
    Manages encryption operations for MainyDB collections.
    """

    def __init__(
        self,
        config: EncryptionConfig,
        aes_key: Optional[Union[str, bytes]] = None
    ):
        """
        Initialize encryption manager.

        Args:
            config: Encryption configuration
            aes_key: AES256 encryption key. Priority order:
                     1. Explicit parameter
                     2. MAINYDB_ENCRYPTION_KEY environment variable
                     3. Auto-generated key (with warning)
        """
        self.config = config
        self.sha256_hasher = SHA256Hasher()

        if self.config.aes256_fields:
            if aes_key is None:

                aes_key = os.environ.get('MAINYDB_ENCRYPTION_KEY')

                if aes_key is None:

                    aes_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
                    print(
                        f"WARNING: Auto-generated encryption key. "
                        f"Store this securely: {aes_key}\n"
                        f"Set MAINYDB_ENCRYPTION_KEY environment variable or pass explicit key "
                        f"to avoid this warning."
                    )

            self.aes_cipher = AES256Cipher(aes_key)
        else:
            self.aes_cipher = None

    def encrypt_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt specified fields in a document.

        Args:
            document: Document to encrypt

        Returns:
            Document with encrypted fields
        """
        encrypted_doc = document.copy()

        for field in self.config.sha256_fields:
            if field in encrypted_doc and isinstance(encrypted_doc[field], str):
                encrypted_doc[field] = self.sha256_hasher.hash(encrypted_doc[field])

        if self.aes_cipher:
            for field in self.config.aes256_fields:
                if field in encrypted_doc and isinstance(encrypted_doc[field], str):
                    encrypted_doc[field] = self.aes_cipher.encrypt(encrypted_doc[field])

        return encrypted_doc

    def decrypt_document(
        self,
        document: Dict[str, Any],
        decrypt_aes: bool = True
    ) -> Dict[str, Any]:
        """
        Decrypt AES256 fields in a document. SHA256 fields cannot be decrypted.

        Args:
            document: Document to decrypt
            decrypt_aes: Whether to decrypt AES256 fields

        Returns:
            Document with decrypted AES256 fields
        """
        if not decrypt_aes or not self.aes_cipher:
            return document

        decrypted_doc = document.copy()

        for field in self.config.aes256_fields:
            if field in decrypted_doc and isinstance(decrypted_doc[field], dict):
                if decrypted_doc[field].get('algorithm') == 'aes256':
                    try:
                        decrypted_doc[field] = self.aes_cipher.decrypt(decrypted_doc[field])
                    except Exception as e:
                        print(f"Warning: Failed to decrypt field '{field}': {e}")

        return decrypted_doc

    def verify_sha256_field(self, field_name: str, value: str, hashed_data: Dict[str, str]) -> bool:
        """
        Verify a value against a SHA256 hashed field.

        Args:
            field_name: Name of the field
            value: Value to verify
            hashed_data: Stored hash data

        Returns:
            True if value matches the hash, False otherwise
        """
        if not self.config.is_sha256_field(field_name):
            raise ValueError(f"Field '{field_name}' is not configured for SHA256 hashing")

        return self.sha256_hasher.verify(value, hashed_data)


def create_encryption_config(
    sha256_fields: Optional[List[str]] = None,
    aes256_fields: Optional[List[str]] = None
) -> EncryptionConfig:
    """
    Helper function to create an encryption configuration.

    Args:
        sha256_fields: List of field names to hash with SHA256
        aes256_fields: List of field names to encrypt with AES256

    Returns:
        EncryptionConfig instance
    """
    config = EncryptionConfig()

    if sha256_fields:
        for field in sha256_fields:
            config.add_sha256_field(field)

    if aes256_fields:
        for field in aes256_fields:
            config.add_aes256_field(field)

    return config
