from __future__ import annotations

import os
import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv(override=True)


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI is not configured. Copy .env.example to .env and add your URI.")
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def get_database() -> Database:
    return get_client()[os.getenv("MONGODB_DATABASE", "ai_financial_advisor")]


def check_connection() -> bool:
    get_client().admin.command("ping")
    return True


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, digest_hex = stored_hash.split("$", 1)
    expected = _hash_password(password, bytes.fromhex(salt_hex)).split("$", 1)[1]
    return hmac.compare_digest(expected, digest_hex)


def register_user(name: str, email: str, password: str) -> str:
    users = get_database().users
    normalized_email = email.strip().lower()
    if users.find_one({"email": normalized_email}):
        raise ValueError("An account with this email already exists.")
    result = users.insert_one({
        "name": name.strip(),
        "email": normalized_email,
        "password_hash": _hash_password(password),
        "created_at": datetime.now(timezone.utc),
    })
    return str(result.inserted_id)


def authenticate_user(email: str, password: str):
    user = get_database().users.find_one({"email": email.strip().lower()})
    if not user or not _verify_password(password, user["password_hash"]):
        return None
    return {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}


def load_transactions(user_id: str = "demo-user"):
    documents = list(get_database().transactions.find({"user_id": user_id}, {"_id": 0}))
    if not documents:
        return None
    return documents


def save_transaction(transaction: dict, user_id: str = "demo-user") -> None:
    document = {**transaction, "user_id": user_id}
    get_database().transactions.insert_one(document)


def save_notifications(items: list[dict], user_id: str = "demo-user") -> None:
    if items:
        get_database().notifications.insert_many([{**item, "user_id": user_id, "read": False, "created_at": datetime.now(timezone.utc)} for item in items])


def load_notifications(user_id: str = "demo-user") -> list[dict]:
    return list(get_database().notifications.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(20))