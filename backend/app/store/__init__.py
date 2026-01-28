from pathlib import Path

from app.store.session_store import SessionStore

BASE_DIR = Path(__file__).resolve().parent / "data"
store = SessionStore(BASE_DIR)
