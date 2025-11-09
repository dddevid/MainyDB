import os
from cryptography.fernet import Fernet
def generate_key():
    """Generates a new Fernet key."""
    return Fernet.generate_key()
def load_key(key_path):
    """Loads the key from the specified file path."""
    try:
        with open(key_path, "rb") as key_file:
            return key_file.read()
    except FileNotFoundError:
        return None
def save_key(key, key_path):
    """Saves the key to the specified file path."""
    with open(key_path, "wb") as key_file:
        key_file.write(key)
def get_or_create_key(key_path):
    """Loads an existing key or generates a new one if it doesn't exist."""
    key = load_key(key_path)
    if key is None:
        key = generate_key()
        save_key(key, key_path)
    return key