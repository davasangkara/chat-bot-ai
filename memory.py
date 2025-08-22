# memory.py
import os, json
from typing import List, Dict

DATA_DIR = os.getenv("DATA_DIR", "./data")
MEM_PATH = os.path.join(DATA_DIR, "memory.json")

os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(MEM_PATH):
    with open(MEM_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

MAX_MESSAGES = 30  # simpan 30 pesan terakhir per kontak

def _read_store() -> Dict:
    with open(MEM_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_store(store: Dict):
    with open(MEM_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)

def get_history(contact: str) -> List[Dict]:
    store = _read_store()
    conv = store.get(contact) or []
    return conv[-MAX_MESSAGES:]

def append_message(contact: str, role: str, content: str):
    store = _read_store()
    conv = store.get(contact) or []
    conv.append({"role": role, "content": content})
    store[contact] = conv[-MAX_MESSAGES:]
    _write_store(store)

def reset_history(contact: str):
    store = _read_store()
    store[contact] = []
    _write_store(store)
