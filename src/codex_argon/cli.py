from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .config import load
from .service import Service

def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="codex-argon")
    ap.add_argument("--state")
    ap.add_argument("--config")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    models = sub.add_parser("models"); models.add_argument("--refresh", action="store_true")
    submit = sub.add_parser("submit"); submit.add_argument("task"); submit.add_argument("--no-worker", action="store_true")
    sub.add_parser("jobs")
    result = sub.add_parser("result"); result.add_argument("job"); result.add_argument("--artifact", choices=["response", "patch"]); result.add_argument("--offset", type=int, default=0); result.add_argument("--limit", type=int, default=4000)
    for name in ("cancel", "accept"):
        sub.add_parser(name).add_argument("job")
    worker = sub.add_parser("worker"); worker.add_argument("--once", action="store_true")
    sub.add_parser("mcp")
    args = ap.parse_args(argv)
    try:
        cfg = load(args.config, args.state)
        if args.command == "worker":
            from .worker import run
            run(cfg, args.once)
            return 0
        if args.command == "mcp":
            from .mcp_server import run
            run(cfg)
            return 0
        service = Service(cfg)
        if args.command == "submit":
            output = service.submit(json.loads(Path(args.task).read_text(encoding="utf-8-sig")), not args.no_worker)
        elif args.command == "models":
            output = service.models(args.refresh)
        elif args.command == "result":
            output = service.result(args.job, args.artifact, args.offset, args.limit)
        elif args.command in ("cancel", "accept"):
            output = getattr(service, args.command)(args.job)
        else:
            output = getattr(service, args.command)()
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(json.dumps({"error":str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
