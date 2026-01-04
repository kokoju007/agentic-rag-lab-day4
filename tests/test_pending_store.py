from app.pending_store import PendingActionStore


def test_pending_store_persists_sqlite(tmp_path) -> None:
    db_path = tmp_path / "pending_actions.db"
    store = PendingActionStore(db_path=str(db_path))
    action = {
        "action_id": "action-1",
        "tool": "notify",
        "args": {"channel": "ops", "message": "test"},
        "risk": "high",
        "rationale": "test",
    }
    store.save_pending("trace-1", [action])

    new_store = PendingActionStore(db_path=str(db_path))
    entry = new_store.get_entry("trace-1")

    assert entry is not None
    assert entry.pending_actions[0]["action_id"] == "action-1"
