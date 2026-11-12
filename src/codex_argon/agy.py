from __future__ import annotations
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from .workspace import prepare_profile
from .processes import ProcessGroup

def kill_tree(proc):
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, timeout=15)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        proc.kill()
    except OSError:
        pass

def parse_output(text, returncode=0):
    if returncode:
        return {"status":"error", "error":"AGY returned a nonzero exit code"}
    decoder = json.JSONDecoder()
    obj = None
    for i,c in enumerate(text):
        if c == "{":
            try:
                value, end = decoder.raw_decode(text[i:])
                if isinstance(value, dict) and "response" in value and not text[i+end:].strip():
                    obj = value
                    break
            except ValueError:
                continue
    if obj is None:
        short = text[:300].lower()
        status = "model-unavailable" if "not recognized" in short or "unknown model" in short else "invalid-output"
        return {"status":status, "error":"No valid AGY response object"}
    if not isinstance(obj.get("response"), str) or not obj["response"].strip():
        return {"status":"empty", "error":"Empty or invalid response"}
    if not isinstance(obj.get("usage", {}), dict):
        return {"status":"invalid-output", "error":"Invalid usage type"}
    return {"status":"ok", "response":obj["response"], "usage":obj.get("usage", {}), "structured":obj.get("structured_output")}

def invoke(cfg, model, prompt, work, profile, timeout, writing=False, cancelled=lambda:False, on_pid=lambda pid:None):
    if model not in cfg.allowed_models:
        raise ValueError("Model is not on the Gemini allowlist")
    env, settings = prepare_profile(profile, work)
    cmd = [*cfg.command, "-p", prompt, "--model", model, "--mode", "accept-edits" if writing else "plan",
           "--print-timeout", f"{timeout}s", "--output-format", "json", "--disable-slash-commands", "--settings", str(settings)]
    flags = {"creationflags":subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session":True}
    started = time.monotonic()
    # Disk-backed output prevents pipe deadlocks and unbounded memory during generation.
    with open(profile/"stdout.txt", "wb") as out, open(profile/"stderr.txt", "wb") as err:
        proc = subprocess.Popen(cmd, cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, **flags)
        group = None
        try:
            group = ProcessGroup(proc)
            on_pid(proc.pid)
            state = None
            while proc.poll() is None:
                if cancelled():
                    state = "cancelled"
                    break
                if time.monotonic()-started > timeout+5:
                    state = "timeout"
                    break
                if (profile/"stdout.txt").stat().st_size + (profile/"stderr.txt").stat().st_size > 16*1024*1024:
                    state = "output-limit"
                    break
                time.sleep(.1)
            if state:
                kill_tree(proc)
            proc.wait(timeout=15)
        finally:
            if group:
                group.close()
            if proc.poll() is None:
                kill_tree(proc)
                proc.wait(timeout=15)
            on_pid(None)
    if state:
        result = {"status":state, "error":state}
    else:
        result = parse_output((profile/"stdout.txt").read_text(encoding="utf-8", errors="replace"), proc.returncode)
    result.update(model=model, seconds=round(time.monotonic()-started, 3))
    return result

def catalog(cfg, refresh=False):
    cache = cfg.state_dir/"models.json"
    if not refresh and cache.exists():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            if time.time()-data["at"] < 86400 and data["binary"] == cfg.agy_bin:
                return data
        except (ValueError, KeyError):
            pass
    profile = cfg.state_dir/"catalog-profile"
    profile.mkdir(parents=True, exist_ok=True)
    env, _ = prepare_profile(profile, cfg.state_dir)
    try:
        r = subprocess.run([*cfg.command, "models"], env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=60, text=True, encoding="utf-8", errors="replace")
        values = [line.split("\t")[0].strip() for line in r.stdout.splitlines() if "\t" in line]
        models = [m for m in cfg.allowed_models if m in values]
        data = {"at":time.time(), "binary":cfg.agy_bin, "models":models, "status":"ok" if r.returncode == 0 and values else "unavailable"}
    except (OSError, subprocess.TimeoutExpired):
        data = {"at":time.time(), "binary":cfg.agy_bin, "models":[], "status":"unavailable"}
    if data["status"] == "ok":
        cache.write_text(json.dumps(data), encoding="utf-8")
    return data
