from __future__ import annotations

import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from bson import ObjectId
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


def create_session(user_id: str, days: int = 30) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    get_database().sessions.create_index("expires_at", expireAfterSeconds=0)
    get_database().sessions.insert_one({
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "user_id": user_id,
        "expires_at": expires_at,
    })
    return token


def authenticate_session(token: str):
    if not token:
        return None
    session = get_database().sessions.find_one({
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "expires_at": {"$gt": datetime.now(timezone.utc)},
    })
    if not session:
        return None
    try:
        user = get_database().users.find_one({"_id": ObjectId(session["user_id"])})
    except Exception:
        user = None
    if not user:
        return None
    return {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}


def revoke_session(token: str) -> None:
    if token:
        get_database().sessions.delete_one({
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        })


def load_transactions(user_id: str = "demo-user"):
    documents = list(get_database().transactions.find({"user_id": user_id}, {"_id": 0}))
    if not documents:
        return None
    return documents


def save_transaction(transaction: dict, user_id: str = "demo-user") -> None:
    document = {**transaction, "user_id": user_id}
    get_database().transactions.insert_one(document)


def delete_transaction(transaction: dict, user_id: str = "demo-user") -> None:
    filter_query = {**transaction, "user_id": user_id}
    get_database().transactions.delete_one(filter_query)


def save_notifications(items: list[dict], user_id: str = "demo-user") -> None:
    if items:
        get_database().notifications.insert_many([{**item, "user_id": user_id, "read": False, "created_at": datetime.now(timezone.utc)} for item in items])


def load_notifications(user_id: str = "demo-user") -> list[dict]:
    return list(get_database().notifications.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(20))