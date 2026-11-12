from __future__ import annotations
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path
from codex_argon.agy import parse_output
from codex_argon.config import Config
from codex_argon.contracts import validate_task
from codex_argon.service import Service
from codex_argon.worker import run
from codex_argon.workspace import snapshot

class Core(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows Git installation discovery')
    def test_snapshot_without_git_on_path(self):
        with patch.dict(os.environ, {'PATH': ''}):
            result = snapshot(self.source, self.root/'no-path-snapshot', ['a.txt'])
        self.assertIn('a.txt', result)
        self.assertEqual((self.root/'no-path-snapshot'/'a.txt').read_text(), 'before\n')

    def setUp(self):
        temp_root=Path(__file__).resolve().parents[3]/"work"/"argon-tests"
        temp_root.mkdir(parents=True,exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_root)
        self.addCleanup(self.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/"source"
        self.source.mkdir()
        (self.source/"a.txt").write_text("before\n")
        self.cfg = Config(state_dir=self.root/"state", agy_bin=str(Path(__file__).with_name("fake_agy.py")))
        self.service = Service(self.cfg)

    def cleanup(self):
        for index in range(20):
            try:
                self.tmp.cleanup()
                return
            except PermissionError:
                if index == 19: raise
                time.sleep(.1)

    def task(self, **kw):
        return {"source":str(self.source), "role":"ask", "objective":"read file", **kw}

    def submit(self, **kw):
        return self.service.submit(self.task(**kw), False)["job_id"]

    def test_allowlist_every_entry(self):
        for bad in ("claude-opus-5-5-high", "gemini-unknown", "gemini-4-argon-high --other"):
            with self.assertRaises(ValueError): self.submit(model=bad)
        with self.assertRaises(ValueError): Config(allowed_models=("claude",))
        with self.assertRaises(ValueError): Config(routes={"ask":["claude"]})

    def test_parser(self):
        self.assertEqual(parse_output('notice\n{"response":"hello"}')["status"], "ok")
        for raw in ('{"response":[]}', '{"response":""}', '{"response":"x","usage":[]}', 'jetski: no output produced', '{broken'):
            self.assertNotEqual(parse_output(raw)["status"], "ok")
        self.assertEqual(parse_output('{"response":"valid"}', 1)["status"], "error")

    def test_idempotence(self):
        a=self.submit(idempotency_key="one")
        self.assertEqual(a,self.submit(idempotency_key="one"))
        with self.assertRaises(ValueError): self.submit(idempotency_key="one", objective="different")

    def test_snapshot_patch_source_preserved(self):
        job=self.submit(role="implement", objective="EDIT", owns=["new file.txt"])
        run(self.cfg, once=True)
        result=self.service.result(job)
        self.assertEqual(result["state"],"succeeded",result)
        self.assertFalse((self.source/"new file.txt").exists())
        self.assertIn("new file.txt",result["result"]["changed_files"])
        self.assertIn("+changed",self.service.result(job,"patch")["content"])
        self.assertFalse(result["result"]["confirmed_by_codex"])

    def test_out_of_scope_rejected(self):
        job=self.submit(role="implement",objective="OUTSIDE",owns=["a.txt"])
        run(self.cfg,once=True)
        self.assertEqual(self.service.result(job)["state"],"failed")

    def test_dependencies_need_acceptance(self):
        first=self.submit()
        second=self.submit(dependencies=[first])
        run(self.cfg,once=True)
        self.assertEqual(self.service.result(second)["state"],"queued")
        self.service.accept(first)
        run(self.cfg,once=True)
        self.assertEqual(self.service.result(second)["state"],"succeeded")

    def test_review_uses_executor_snapshot(self):
        first=self.submit(role="implement", objective="EDIT", owns=["new file.txt"])
        run(self.cfg,once=True);self.service.accept(first)
        second=self.submit(role="review", review_of=first)
        run(self.cfg,once=True)
        item=self.service.result(second)
        self.assertEqual(item["state"],"succeeded",item)
        self.assertTrue((Path(item["result"]["snapshot"])/"new file.txt").exists())

    def test_cancel_queued(self):
        job=self.submit();self.service.cancel(job);run(self.cfg,once=True)
        self.assertEqual(self.service.result(job)["state"],"cancelled")

    def test_cancel_running(self):
        job=self.submit(objective="SLEEP", timeout=10)
        t=threading.Thread(target=run,args=(self.cfg,True));t.start()
        try:
            deadline=time.time()+8
            while not self.service.store.get(job)["pid"] and time.time()<deadline:time.sleep(.05)
            self.service.cancel(job);t.join(8)
            self.assertFalse(t.is_alive())
            self.assertEqual(self.service.result(job)["state"],"cancelled")
        finally:
            self.service.cancel(job);t.join(10)

    def test_overlap_nested_sources(self):
        (self.source/"sub").mkdir()
        first=self.submit(role="implement",owns=["sub/a.txt"])
        second=self.service.submit(self.task(source=str(self.source/"sub"),role="implement",owns=["a.txt"]),False)["job_id"]
        self.assertEqual(self.service.store.claim(),first)
        self.assertIsNone(self.service.store.claim())

    def test_restart_marks_interrupted(self):
        job=self.submit();self.service.store.claim();run(self.cfg,once=True)
        self.assertEqual(self.service.result(job)["state"],"interrupted")

    def test_artifact_validation(self):
        job=self.submit();run(self.cfg,once=True)
        with self.assertRaises(ValueError):self.service.result(job,"../secret")
        part=self.service.result(job,"response",0,4)
        self.assertEqual(part["content"],"Veri")

    @unittest.skipUnless(os.name == "nt", "Windows Job Object")
    def test_descendant_killed_after_parent_exit(self):
        job=self.submit(objective="GRANDCHILD")
        run(self.cfg,once=True)
        time.sleep(2.2)
        folder=self.cfg.state_dir/"artifacts"/job/"work"
        self.assertFalse((folder/"grandchild-marker.txt").exists())
        self.assertEqual(self.service.result(job)["state"],"succeeded")

    def test_missing_input_rejected(self):
        job=self.submit(inputs=["missing.txt"])
        run(self.cfg,once=True)
        self.assertEqual(self.service.result(job)["state"],"failed")

    def test_paths(self):
        for path in ("../a","/a","a/../b","C:/a",".git/config"):
            with self.assertRaises(ValueError):self.submit(role="implement",owns=[path])

    def test_mcp_surface(self):
        from codex_argon.mcp_server import build
        server=build(self.cfg)
        tools=server._tool_manager.list_tools()
        self.assertEqual({x.name for x in tools},{"argon_status","argon_models","argon_submit","argon_jobs","argon_result","argon_cancel","argon_accept"})

if __name__ == "__main__":unittest.main()
