from .core import Collection, Database, MainyDB, MongoClient, ObjectId
from .encryption import (
    EncryptionManager,
    SHA256Hasher,
    AES256Cipher,
    EncryptionConfig,
    create_encryption_config
)

__version__ = '1.0.4'
__author__ = 'devid'
__easter_egg__ = "You've found the secret message! MainyDB is watching you... always."