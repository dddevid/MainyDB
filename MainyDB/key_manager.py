import os

from cryptography.fernet import Fernet


def generate_key():
    return Fernet.generate_key()


def load_key(key_path):
    try:
        with open(key_path, "rb") as key_file:
            return key_file.read()
    except FileNotFoundError:
        return None


def save_key(key, key_path):
    with open(key_path, "wb") as key_file:
        key_file.write(key)


def get_or_create_key(key_path):
    key = load_key(key_path)
    if key is None:
        key = generate_key()
        save_key(key, key_path)
    return key
