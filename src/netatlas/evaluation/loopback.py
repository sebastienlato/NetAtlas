"""Four local authored services; standalone capture-to-durable-search timing."""

import asyncio
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from netatlas.config import Settings
from netatlas.derivations.engine import canonical, derive, digest
from netatlas.derivations.offline import load_pack
from netatlas.discovery.engine import run_campaign
from netatlas.discovery.scope import Scope
from netatlas.observation import Observation
from netatlas.search.models import Query
from netatlas.search.service import search
from netatlas.storage.pipeline import Pipeline

PAYLOADS = (
    b"HTTP/1.1 200 OK\r\nServer: nginx\r\nContent-Length: 0\r\n\r\n",
    b"SSH-2.0-OpenSSH_9.0\r\n",
    b"220 fixture.example ESMTP Postfix\r\n",
    b"unrecognized authored greeting\r\n",
)


def settings() -> Settings:
    return Settings.model_validate(
        {
            "measurement": {
                "enabled": True,
                "operator_name": "NetAtlas authored fixture evaluation",
                "operator_contact": "research@example.org",
                "user_agent": "NetAtlas/0.14 (research; loopback fixture)",
                "protocol_evidence": True,
                "max_concurrency": 2,
            }
        }
    )


async def trial(pipeline: Pipeline, root: Path) -> dict[str, Any]:
    servers = []
    handlers: set[asyncio.Task[None]] = set()
    connections = 0

    def handler(payload: bytes) -> Any:
        async def serve(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            nonlocal connections
            task = asyncio.current_task()
            if task is not None:
                handlers.add(task)
            connections += 1
            try:
                writer.write(payload)
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()
                if task is not None:
                    handlers.discard(task)

        return serve

    config = settings()
    try:
        for payload in PAYLOADS:
            servers.append(await asyncio.start_server(handler(payload), "127.0.0.1", 0))
        ports = tuple(server.sockets[0].getsockname()[1] for server in servers)
        scope = Scope(targets=("127.0.0.1",), ports=ports, lab_loopback=True, seed=13)
        start = perf_counter()
        manifest = await run_campaign(config, scope, root=root)
        captured = perf_counter()
        directory = next(p for p in root.iterdir() if p.is_dir())
        payload = (directory / "observations.jsonl").read_bytes()
        if digest(payload) != manifest["observations_sha256"]:
            raise ValueError("loopback spool digest mismatch")
        rows = [Observation.model_validate_json(line) for line in payload.splitlines()]
        for row in rows:
            pipeline.ingest(canonical(row), synthetic=True)
            pipeline.derive(row.observation_id, load_pack())
        persisted = perf_counter()
        # Exact newly measured identities: no prior warm-up fallback.
        q = Query(network="127.0.0.1/32", after=min(r.finished_at for r in rows), mode="history")
        result = search(pipeline.engine, q)
        json.dumps(result, ensure_ascii=True)
        finished = perf_counter()
        if (
            manifest["attempted"],
            manifest["completed"],
            manifest["incomplete"],
            manifest["connection_attempted"],
            connections,
        ) != (4, 4, 0, 4, 4):
            raise ValueError("loopback connection/source count mismatch")
        if {r["id"] for r in result["hits"]} != {str(r.observation_id) for r in rows} or result[
            "candidates"
        ] != 3:
            raise ValueError("loopback read oracle mismatch")
        actual = {
            row.endpoint.port: {c.product for c in derive(row, load_pack()).candidates}
            for row in rows
        }
        if [actual[p] for p in ports] != [{"nginx"}, {"OpenSSH"}, {"Postfix"}, set()]:
            raise ValueError("loopback assertion oracle mismatch")
        return {
            "capture_spool_seconds": captured - start,
            "durable_ingest_derive_seconds": persisted - captured,
            "search_seconds": finished - persisted,
            "total_seconds": finished - start,
            "sources_per_second": 4 / (finished - start),
            "attempted": 4,
            "completed": 4,
            "incomplete": 0,
            "connections": connections,
            "candidates": 3,
            "unknown_sources": 1,
            "config_sha256": config.sha256,
            "manifest_sha256": digest((directory / "manifest.json").read_bytes()),
            "source_sha256": [digest(canonical(r)) for r in rows],
            "policy_sha256": manifest["policy_sha256"],
            "failures": 0,
        }
    finally:
        for server in servers:
            server.close()
            await server.wait_closed()
        if handlers:
            await asyncio.gather(*handlers, return_exceptions=True)
