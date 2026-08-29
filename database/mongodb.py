from __future__ import annotations

import json
import os
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv(override=True)

LOCAL_DATA_PATH = Path(__file__).resolve().parents[1] / ".local_data.json"


def _local_store() -> dict:
    if not LOCAL_DATA_PATH.exists():
        default = {"users": [], "sessions": [], "transactions": [], "notifications": []}
        LOCAL_DATA_PATH.write_text(json.dumps(default, default=str), encoding="utf-8")
        return default
    try:
        data = json.loads(LOCAL_DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {"users": [], "sessions": [], "transactions": [], "notifications": []}
        LOCAL_DATA_PATH.write_text(json.dumps(data, default=str), encoding="utf-8")
    return data


def _save_local_store(data: dict) -> None:
    LOCAL_DATA_PATH.write_text(json.dumps(data, default=str), encoding="utf-8")


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
    normalized_email = email.strip().lower()
    try:
        users = get_database().users
        if users.find_one({"email": normalized_email}):
            raise ValueError("An account with this email already exists.")
        result = users.insert_one({
            "name": name.strip(),
            "email": normalized_email,
            "password_hash": _hash_password(password),
            "created_at": datetime.now(timezone.utc),
        })
        return str(result.inserted_id)
    except Exception:
        store = _local_store()
        if any(user["email"] == normalized_email for user in store["users"]):
            raise ValueError("An account with this email already exists.")
        user_id = str(uuid.uuid4())
        new_user = {
            "_id": user_id,
            "name": name.strip(),
            "email": normalized_email,
            "password_hash": _hash_password(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        store["users"].append(new_user)
        _save_local_store(store)
        return user_id


def authenticate_user(email: str, password: str):
    try:
        user = get_database().users.find_one({"email": email.strip().lower()})
        if not user or not _verify_password(password, user["password_hash"]):
            return None
        return {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}
    except Exception:
        store = _local_store()
        user = next((item for item in store["users"] if item["email"] == email.strip().lower()), None)
        if not user or not _verify_password(password, user["password_hash"]):
            return None
        return {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}


def create_session(user_id: str, days: int = 30) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    try:
        get_database().sessions.create_index("expires_at", expireAfterSeconds=0)
        get_database().sessions.insert_one({
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "user_id": user_id,
            "expires_at": expires_at,
        })
        return token
    except Exception:
        store = _local_store()
        store["sessions"].append({
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "user_id": user_id,
            "expires_at": expires_at.isoformat(),
        })
        _save_local_store(store)
        return token


def authenticate_session(token: str):
    if not token:
        return None
    try:
        session = get_database().sessions.find_one({
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        })
        if not session:
            return None
        user = get_database().users.find_one({"_id": ObjectId(session["user_id"])})
        if not user:
            return None
        return {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}
    except Exception:
        store = _local_store()
        now = datetime.now(timezone.utc)
        session = next(
            (
                item for item in store["sessions"]
                if item["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
                and datetime.fromisoformat(item["expires_at"]) > now
            ),
            None,
        )
        if not session:
            return None
        user = next((item for item in store["users"] if item["_id"] == session["user_id"]), None)
        if not user:
            return None
        return {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}


def revoke_session(token: str) -> None:
    if token:
        try:
            get_database().sessions.delete_one({
                "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            })
        except Exception:
            store = _local_store()
            store["sessions"] = [
                item for item in store["sessions"]
                if item["token_hash"] != hashlib.sha256(token.encode()).hexdigest()
            ]
            _save_local_store(store)


def load_transactions(user_id: str = "demo-user"):
    try:
        documents = list(get_database().transactions.find({"user_id": user_id}, {"_id": 0}))
        if not documents:
            return None
        return documents
    except Exception:
        store = _local_store()
        documents = [item for item in store["transactions"] if item.get("user_id") == user_id]
        if not documents:
            return None
        return documents


def save_transaction(transaction: dict, user_id: str = "demo-user") -> None:
    document = {**transaction, "user_id": user_id}
    try:
        get_database().transactions.insert_one(document)
    except Exception:
        store = _local_store()
        store["transactions"].append(document)
        _save_local_store(store)


def delete_transaction(transaction: dict, user_id: str = "demo-user") -> None:
    filter_query = {**transaction, "user_id": user_id}
    try:
        get_database().transactions.delete_one(filter_query)
    except Exception:
        store = _local_store()
        store["transactions"] = [
            item for item in store["transactions"]
            if not (
                item.get("user_id") == user_id
                and item.get("date") == transaction.get("date")
                and item.get("type") == transaction.get("type")
                and item.get("category") == transaction.get("category")
                and item.get("amount") == transaction.get("amount")
                and item.get("description") == transaction.get("description")
            )
        ]
        _save_local_store(store)


def save_notifications(items: list[dict], user_id: str = "demo-user") -> None:
    if items:
        try:
            get_database().notifications.insert_many([{**item, "user_id": user_id, "read": False, "created_at": datetime.now(timezone.utc)} for item in items])
        except Exception:
            store = _local_store()
            for item in items:
                store["notifications"].append({**item, "user_id": user_id, "read": False, "created_at": datetime.now(timezone.utc).isoformat()})
            _save_local_store(store)


def load_notifications(user_id: str = "demo-user") -> list[dict]:
    try:
        return list(get_database().notifications.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(20))
    except Exception:
        store = _local_store()
        records = [item for item in store["notifications"] if item.get("user_id") == user_id]
        return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)[:20]