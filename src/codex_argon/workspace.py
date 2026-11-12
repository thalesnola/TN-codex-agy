from __future__ import annotations
import hashlib
import json
import os
import shutil
import subprocess
import string
from pathlib import Path
from .contracts import relative

IGNORE = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}

def git(root, *args):
    env = {k:v for k,v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    executable = shutil.which("git")
    if not executable and os.name == "nt":
        candidates = [Path(os.environ.get("ProgramFiles", "C:/Program Files"))/"Git/cmd/git.exe",
                      Path.home()/"AppData/Local/Programs/Git/cmd/git.exe"]
        executable = next((str(p) for p in candidates if p.is_file()), None)
    if not executable:
        raise ValueError("Git executable unavailable; install Git or add it to PATH")
    r = subprocess.run([executable, "-c", f"core.hooksPath={os.devnull}", "-C", str(root), *args], capture_output=True, stdin=subprocess.DEVNULL, env=env)
    if r.returncode:
        raise ValueError(f"git {args[0]} failed")
    return r.stdout

def safe_files(root):
    root = Path(root).resolve()
    found = []
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in IGNORE and not (Path(base)/d).is_symlink() and not (hasattr(Path(base)/d, "is_junction") and (Path(base)/d).is_junction())]
        for name in files:
            p = Path(base)/name
            if p.is_symlink() or not p.resolve().is_relative_to(root):
                raise ValueError("Snapshot contains links or external paths")
            found.append(p.relative_to(root).as_posix())
    return sorted(found)

def manifest(root):
    return {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in safe_files(root)}

def snapshot(source, destination, inputs):
    if destination.exists():
        raise ValueError("Snapshot already exists")
    destination.mkdir(parents=True)
    candidates = safe_files(source)
    # Git ignore applies to untracked files; tracked files remain part of snapshot.
    try:
        listed = git(source, "ls-files", "-z", "-co", "--exclude-standard").decode("utf-8").split("\0")
        candidates = [p for p in candidates if p in set(listed)]
    except ValueError:
        pass
    if inputs:
        for selected in inputs:
            if not any(p == selected or p.startswith(selected+"/") for p in candidates):
                raise ValueError(f"Selected input is missing or ignored: {selected}")
        candidates = [p for p in candidates if any(p == x or p.startswith(x+"/") for x in inputs)]
    total = 0
    for name in candidates:
        relative(name)
        p = source/name
        total += p.stat().st_size
        if len(candidates) > 20000 or total > 200*1024*1024:
            raise ValueError("Snapshot limit exceeded; select a smaller input set")
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    base = manifest(destination)
    git(destination, "init", "-q")
    git(destination, "add", "-A")
    git(destination, "-c", "user.name=codex-argon", "-c", "user.email=codex-argon@local", "-c", "core.autocrlf=false", "commit", "-qm", "snapshot", "--allow-empty")
    return base

def patch_result(work, base, owns):
    current = manifest(work)
    changed = sorted(p for p in set(base)|set(current) if base.get(p) != current.get(p))
    if any(not any(p == o or p.startswith(o+"/") for o in owns) for p in changed):
        raise ValueError("Executor changed files outside declared ownership")
    git(work, "add", "-A")
    patch = git(work, "diff", "--cached", "--binary", "--no-renames")
    return changed, patch

def prepare_profile(profile, work):
    cfg = profile/".gemini/config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg/"config.json").write_text(json.dumps({"plugins":{"googlecloudtools.datacloud_telemetry":{"enabled":False}}}), encoding="utf-8")
    settings = profile/"settings.json"
    work = work.resolve()
    denied = []
    current = Path(work.anchor)
    for part in work.parts[1:]:
        for entry in current.iterdir():
            if entry.name.casefold() != part.casefold():
                denied.extend(f"{tool}({entry.as_posix()})" for tool in ("read_file", "write_file"))
        current = current/part
    if os.name == "nt":
        for drive in string.ascii_uppercase:
            if drive != work.drive[0].upper() and Path(f"{drive}:/").exists():
                denied.extend(f"{tool}({drive}:/)" for tool in ("read_file", "write_file"))
    denied += [f"write_file({(work/'.git').as_posix()})", "command(*)", "mcp(*)"]
    settings.write_text(json.dumps({"permissions":{"deny":denied}}), encoding="utf-8")
    keep = {"SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "COMSPEC", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "LANG"}
    env = {k:v for k,v in os.environ.items() if k.upper() in keep}
    env.update(HOME=str(profile), USERPROFILE=str(profile), PYTHONIOENCODING="utf-8")
    return env, settings
