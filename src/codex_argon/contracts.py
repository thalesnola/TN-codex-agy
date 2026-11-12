from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
from .config import Config

def relative(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Use nonempty slash-separated relative paths")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ("..", ".git") for x in p.parts) or value != p.as_posix():
        raise ValueError(f"Invalid relative path: {value}")
    return value

def validate_task(raw: dict, cfg: Config):
    if not isinstance(raw, dict):
        raise ValueError("Task must be an object")
    keys = {"objective", "role", "source", "inputs", "owns", "acceptance", "dependencies", "model",
            "timeout", "max_attempts", "idempotency_key", "review_of"}
    if set(raw) - keys:
        raise ValueError(f"Unknown task fields: {sorted(set(raw)-keys)}")
    task = {"inputs": [], "owns": [], "acceptance": [], "dependencies": [], "timeout": 240,
            "max_attempts": 2, **raw}
    if not isinstance(task.get("objective"), str) or not 1 <= len(task["objective"]) <= 16000:
        raise ValueError("objective must contain 1..16000 characters")
    if task.get("role") not in cfg.routes:
        raise ValueError("Unknown role")
    source = Path(task.get("source", "")).resolve()
    if not source.is_dir() or not task.get("source"):
        raise ValueError("source must be an existing directory")
    task["source"] = str(source)
    for name in ("inputs", "owns", "acceptance", "dependencies"):
        if not isinstance(task[name], list) or any(not isinstance(x, str) for x in task[name]):
            raise ValueError(f"{name} must be a string list")
    for name in ("inputs", "owns"):
        task[name] = list(dict.fromkeys(relative(x) for x in task[name]))
    if task["role"] in ("implement", "document") and not task["owns"]:
        raise ValueError("Writing tasks require explicit owns paths")
    if task.get("model") and task["model"] not in cfg.allowed_models:
        raise ValueError("Model is not on the Gemini allowlist")
    if type(task["timeout"]) is not int or not 1 <= task["timeout"] <= 3600:
        raise ValueError("timeout must be 1..3600 seconds per attempt")
    if type(task["max_attempts"]) is not int or not 1 <= task["max_attempts"] <= 6:
        raise ValueError("max_attempts must be 1..6")
    if task.get("idempotency_key") is not None and (not isinstance(task["idempotency_key"], str) or not 1 <= len(task["idempotency_key"]) <= 200):
        raise ValueError("Invalid idempotency key")
    return task

def fingerprint(task):
    return hashlib.sha256(json.dumps(task, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def overlap(a, b):
    return any(x == y or x.startswith(y + "/") or y.startswith(x + "/") for x in a for y in b)
