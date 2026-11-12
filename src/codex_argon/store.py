from __future__ import annotations
import json
import sqlite3
import time
import uuid
import os
from pathlib import Path
from contextlib import contextmanager
from .contracts import fingerprint, overlap

class Store:
    def __init__(self, state):
        self.state = state
        state.mkdir(parents=True, exist_ok=True)
        self.path = state / "jobs.sqlite3"
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, task TEXT NOT NULL, fingerprint TEXT NOT NULL,
              idem TEXT UNIQUE, state TEXT NOT NULL, accepted INTEGER NOT NULL DEFAULT 0,
              cancel INTEGER NOT NULL DEFAULT 0, pid INTEGER, result TEXT, created REAL NOT NULL, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS worker(id INTEGER PRIMARY KEY CHECK(id=1), token TEXT, pid INTEGER, heartbeat REAL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, job TEXT, at REAL, kind TEXT, detail TEXT);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA journal_mode=WAL")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _row(self, r):
        if not r:
            raise KeyError("Unknown job")
        d = dict(r)
        d["task"] = json.loads(d["task"])
        d["result"] = json.loads(d["result"]) if d["result"] else None
        return d

    def get(self, job):
        with self.connect() as db:
            return self._row(db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone())

    def jobs(self):
        with self.connect() as db:
            return [self._row(r) for r in db.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT 100")]

    def submit(self, task):
        fp = fingerprint(task)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if task.get("idempotency_key"):
                row = db.execute("SELECT * FROM jobs WHERE idem=?", (task["idempotency_key"],)).fetchone()
                if row:
                    if row["fingerprint"] != fp:
                        raise ValueError("Idempotency key already used for a different task")
                    return row["id"]
            deps = list(task["dependencies"])
            if task.get("review_of"):
                deps.append(task["review_of"])
            for dep in deps:
                if not db.execute("SELECT 1 FROM jobs WHERE id=?", (dep,)).fetchone():
                    raise ValueError(f"Unknown dependency: {dep}")
            job = uuid.uuid4().hex
            now = time.time()
            db.execute("INSERT INTO jobs(id,task,fingerprint,idem,state,created,updated) VALUES(?,?,?,?,?,?,?)",
                       (job, json.dumps(task), fp, task.get("idempotency_key"), "queued", now, now))
            return job

    def update(self, job, **fields):
        if set(fields) - {"state", "accepted", "cancel", "pid", "result"}:
            raise ValueError("Invalid update")
        if "result" in fields:
            fields["result"] = json.dumps(fields["result"], ensure_ascii=False)
        fields["updated"] = time.time()
        with self.connect() as db:
            db.execute(f"UPDATE jobs SET {','.join(k+'=?' for k in fields)} WHERE id=?", (*fields.values(), job))

    def cancel(self, job):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state FROM jobs WHERE id=?", (job,)).fetchone()
            if not row:
                raise KeyError("Unknown job")
            if row["state"] in ("queued", "running"):
                db.execute("UPDATE jobs SET cancel=1,state=CASE WHEN state='queued' THEN 'cancelled' ELSE state END,updated=? WHERE id=?", (time.time(), job))
        return self.get(job)

    def accept(self, job):
        with self.connect() as db:
            row = db.execute("SELECT state FROM jobs WHERE id=?", (job,)).fetchone()
            if not row or row["state"] != "succeeded":
                raise ValueError("Only successful jobs can be accepted by Codex")
            db.execute("UPDATE jobs SET accepted=1,updated=? WHERE id=?", (time.time(), job))

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            active = [self._row(r) for r in db.execute("SELECT * FROM jobs WHERE state='running'")]
            for row in db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY created").fetchall():
                item = self._row(row)
                task = item["task"]
                deps = task["dependencies"] + ([task["review_of"]] if task.get("review_of") else [])
                ready = True
                for dep in deps:
                    d = db.execute("SELECT state,accepted FROM jobs WHERE id=?", (dep,)).fetchone()
                    if d["state"] in ("failed", "cancelled", "interrupted"):
                        db.execute("UPDATE jobs SET state='failed',result=?,updated=? WHERE id=?", (json.dumps({"error": "dependency failed", "dependency": dep}), time.time(), item["id"]))
                    if d["state"] != "succeeded" or not d["accepted"]:
                        ready = False
                if not ready:
                    continue
                owned = [os.path.normcase(str((Path(task["source"])/p).resolve())).replace("\\", "/") for p in task["owns"]]
                if any(overlap([os.path.normcase(str((Path(a["task"]["source"])/p).resolve())).replace("\\", "/") for p in a["task"]["owns"]], owned) for a in active):
                    continue
                db.execute("UPDATE jobs SET state='running',updated=? WHERE id=?", (time.time(), item["id"]))
                return item["id"]
        return None

    def event(self, job, kind, detail):
        with self.connect() as db:
            db.execute("INSERT INTO events(job,at,kind,detail) VALUES(?,?,?,?)", (job, time.time(), kind, json.dumps(detail)))
