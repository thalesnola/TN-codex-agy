from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from .service import Service

def build(cfg):
    service = Service(cfg)
    server = FastMCP("codex-argon", instructions="Codex commands; only configured Gemini models execute. Submit bounded tasks, inspect results, and explicitly accept dependencies after verification. This bridge never applies patches to the source.")
    @server.tool()
    def argon_status() -> dict:
        """Inspect local bridge status without an inference call."""
        return service.status()
    @server.tool()
    def argon_models(refresh: bool = False) -> dict:
        """Discover allowed Gemini models; does not run inference."""
        return service.models(refresh)
    @server.tool()
    def argon_submit(task: dict) -> dict:
        """Queue a bounded task and start the detached worker; returns immediately."""
        return service.submit(task)
    @server.tool()
    def argon_jobs() -> list[dict]:
        """List recent jobs and their observed state."""
        return service.jobs()
    @server.tool()
    def argon_result(job_id: str, artifact: str | None = None, offset: int = 0, limit: int = 4000) -> dict:
        """Read compact results or a bounded artifact page (byte offsets)."""
        return service.result(job_id, artifact, offset, limit)
    @server.tool()
    def argon_cancel(job_id: str) -> dict:
        """Request cancellation; worker terminates the AGY process tree."""
        return service.cancel(job_id)
    @server.tool()
    def argon_accept(job_id: str) -> dict:
        """Record Codex acceptance of a successful result, unlocking dependent tasks."""
        return service.accept(job_id)
    return server

def run(cfg):
    build(cfg).run(transport="stdio")
