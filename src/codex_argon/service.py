from __future__ import annotations
import json
from pathlib import Path
from .contracts import validate_task
from .store import Store
from .worker import start_worker, worker_alive
from .agy import catalog

class Service:
    def __init__(self, cfg):
        self.cfg = cfg
        self.store = Store(cfg.state_dir)

    def status(self):
        return {"version":"0.1.0", "agy_exists":Path(self.cfg.agy_bin).is_file(),
                "worker_alive":worker_alive(self.store), "state_dir":str(self.cfg.state_dir),
                "allowed_models":list(self.cfg.allowed_models), "concurrency":self.cfg.concurrency,
                "capabilities":{"web":"unverified", "profile":"application-level; not an OS sandbox"}}

    def submit(self, task, auto_worker=True):
        task = validate_task(task, self.cfg)
        job = self.store.submit(task)
        if auto_worker:
            start_worker(self.cfg)
        return {"job_id":job, "state":self.store.get(job)["state"]}

    def jobs(self):
        return [{"job_id":x["id"], "state":x["state"], "accepted":bool(x["accepted"]),
                 "role":x["task"]["role"], "created":x["created"]} for x in self.store.jobs()]

    def result(self, job, artifact=None, offset=0, limit=4000):
        item = self.store.get(job)
        if artifact is None:
            return {"job_id":job, "state":item["state"], "accepted":bool(item["accepted"]), "result":item["result"]}
        if artifact not in ("response", "patch") or not 0 <= offset or not 1 <= limit <= 16000:
            raise ValueError("Invalid artifact or pagination")
        path = self.cfg.state_dir/"artifacts"/item["id"]/("response.txt" if artifact == "response" else "changes.patch")
        if not path.is_file():
            raise ValueError("Artifact unavailable")
        # Read bounded byte range; UTF-8 boundaries use replacement characters.
        with open(path, "rb") as f:
            f.seek(offset)
            data = f.read(limit)
        return {"artifact":artifact, "offset":offset, "next_offset":offset+len(data), "total_bytes":path.stat().st_size,
                "content":data.decode("utf-8", errors="replace"), "path":str(path)}

    def cancel(self, job):
        self.store.cancel(job)
        return self.result(job)

    def accept(self, job):
        self.store.accept(job)
        return self.result(job)

    def models(self, refresh=False):
        return {**catalog(self.cfg, refresh), "routes":self.cfg.routes}
