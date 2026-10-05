import json
import os
import tempfile
import threading

_locks = {}
_lock_mutex = threading.Lock()

def get_lock(filename):
    with _lock_mutex:
        if filename not in _locks:
            _locks[filename] = threading.Lock()
        return _locks[filename]

def read_json(filepath, default=None):
    if not os.path.exists(filepath):
        return default if default is not None else {}
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default if default is not None else {}

def write_json_atomic(filepath, data):
    # Atomic write to prevent corruption
    lock = get_lock(filepath)
    with lock:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(filepath), text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, filepath)
