from __future__ import annotations
import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

MODELS = ("gemini-4-argon-high", "gemini-4-argon-medium", "gemini-4-argon-low",
          "gemini-3.8-flash-high", "gemini-3.8-flash-medium", "gemini-3.8-flash-low")
ROUTES = {"ask": MODELS[:2], "explore": (MODELS[1], MODELS[3], MODELS[4]),
          "research": MODELS[:2], "challenge": MODELS[:2], "implement": MODELS[:2],
          "document": (MODELS[3], MODELS[1]), "review": MODELS[:2]}

@dataclass
class Config:
    state_dir: Path = field(default_factory=lambda: Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/state")) / "codex-argon")
    agy_bin: str = field(default_factory=lambda: str(Path.home() / ".gemini/bin" / ("agy.exe" if os.name == "nt" else "agy")))
    concurrency: int = 2
    allowed_models: tuple[str, ...] = MODELS
    routes: dict = field(default_factory=lambda: dict(ROUTES))
    config_path: str | None = None

    def __post_init__(self):
        self.state_dir = Path(self.state_dir).resolve()
        if not 1 <= self.concurrency <= 8:
            raise ValueError("concurrency must be between 1 and 8")
        if not self.allowed_models or any(m not in MODELS for m in self.allowed_models):
            raise ValueError("Only explicitly supported Gemini models may be allowed")
        if any(not route or any(m not in self.allowed_models for m in route) for route in self.routes.values()):
            raise ValueError("Every route must use only allowed Gemini models")

    @property
    def command(self):
        return [sys.executable, self.agy_bin] if self.agy_bin.endswith(".py") else [self.agy_bin]

def load(config_path=None, state=None):
    path = Path(config_path).resolve() if config_path else None
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path else {}
    unknown = set(data) - {"state_dir", "agy_bin", "concurrency", "allowed_models", "routes"}
    if unknown:
        raise ValueError(f"Unknown configuration keys: {sorted(unknown)}")
    if state:
        data["state_dir"] = state
    if "allowed_models" in data:
        data["allowed_models"] = tuple(data["allowed_models"])
    if "routes" in data:
        data["routes"] = {**ROUTES, **data["routes"]}
    return Config(**data, config_path=str(path) if path else None)
