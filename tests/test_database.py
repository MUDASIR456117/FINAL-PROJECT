from database.mongodb import get_client, get_database, load_transactions, delete_transaction, _verify_password, _hash_password
from backend.main import Transaction, add_transaction


def test_database_module_uses_configured_database_name(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGODB_DATABASE", "test_finance")
    get_client.cache_clear()
    database = get_database()
    assert database.name == "test_finance"


def test_load_transactions_returns_none_when_collection_is_empty(monkeypatch):
    class EmptyCollection:
        def find(self, *_args):
            return []

    class FakeDatabase:
        transactions = EmptyCollection()

    monkeypatch.setattr("database.mongodb.get_database", lambda: FakeDatabase())
    assert load_transactions() is None


def test_password_hash_can_be_verified():
    password_hash = _hash_password("correct-password")
    assert _verify_password("correct-password", password_hash)
    assert not _verify_password("wrong-password", password_hash)


def test_api_transaction_is_saved_to_database(monkeypatch):
    saved = {}
    monkeypatch.setattr("backend.main.save_transaction", lambda transaction: saved.update(transaction))
    transaction = Transaction(type="expense", category="Food", amount=25, date="2026-08-24", description="Lunch")
    response = add_transaction(transaction)
    assert response["message"] == "Transaction saved"
    assert saved["category"] == "Food"
    assert saved["amount"] == 25


def test_delete_transaction_removes_matching_record(monkeypatch):
    deleted = {}

    class FakeCollection:
        def delete_one(self, filter_query):
            deleted.update(filter_query)
            return type("Result", (), {"deleted_count": 1})()

    class FakeDatabase:
        transactions = FakeCollection()

    monkeypatch.setattr("database.mongodb.get_database", lambda: FakeDatabase())

    delete_transaction({"date": "2026-08-24", "type": "expense", "category": "Food", "amount": 25, "description": "Lunch"}, "user-123")

    assert deleted["user_id"] == "user-123"
    assert deleted["category"] == "Food"
    assert deleted["amount"] == 25