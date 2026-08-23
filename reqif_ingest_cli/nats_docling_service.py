"""NATS Micro Service exposing this repo's Docling-backed extraction over
the network, so it is a genuinely *shared*, discoverable capability (via
`nats service list`) rather than only a local stdio subprocess.

Connection target is configurable so this works equally against a local
test NATS server (podman) or the real b00t-hive vultr1 NATS hub (reached
via an SSH tunnel to 127.0.0.1:<local-forwarded-port>, matching the b00t
firewall convention that NATS itself is never publicly exposed).

Endpoint: "extract" on service "ledgrrr-docling". Request payload:
    {"path": "<file path readable by this process>", "profile": "auto"}
Reply payload: the same JSON shape `reqif_ingest_cli extract` prints, or
    {"error": "..."} on failure.

Run:
    NATS_URL=nats://127.0.0.1:14222 NATS_USER=... NATS_PASSWORD=... \\
        uv run python -m reqif_ingest_cli.nats_docling_service

On-demand lifecycle: this process is meant to be started by systemd
(a Podman Quadlet, see ../deploy/quadlet/docling-nats-service.container)
only when needed, not run perpetually — vultr1's NATS server is the only
thing meant to stay always-on (per the b00t hive's "small standing
coordination layer, everything else on-demand" design). To make that
enforceable rather than just a convention, this process tracks the time
of its last handled request and exits cleanly (code 0) after
IDLE_TIMEOUT_SECONDS (default 300) with none — systemd (Restart=no) then
leaves it stopped until the next on-demand start rather than restarting
it into another idle loop.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import asdict

import nats
import nats.micro as micro

from reqif_ingest_cli.docling_adapter import extract_docling_document
from reqif_ingest_cli.xlsx_extractor import extract_xlsx_document

SERVICE_NAME = "ledgrrr-docling"
SERVICE_VERSION = "0.1.0"
DEFAULT_IDLE_TIMEOUT_SECONDS = 300.0


def _run_extract(path: str, profile: str) -> dict:
    suffix = path.lower().rsplit(".", 1)[-1] if "." in path else ""
    if suffix == "xlsx":
        result = extract_xlsx_document(path)
    else:
        result = extract_docling_document(path, profile=profile)

    if hasattr(result, "unwrap"):
        # returns.result.Result: Success/Failure
        from returns.result import Failure

        if isinstance(result, Failure):
            return {"error": str(result.failure())}
        graph = result.unwrap()
    else:
        graph = result

    return json.loads(json.dumps(asdict(graph), default=str))


async def _extract_handler(request: micro.Request, last_activity: list[float]) -> None:
    last_activity[0] = time.monotonic()
    try:
        payload = json.loads(request.data or b"{}")
        path = payload["path"]
        profile = payload.get("profile", "auto")
        reply = await asyncio.get_running_loop().run_in_executor(
            None, _run_extract, path, profile
        )
        await request.respond(json.dumps(reply).encode())
    except Exception as exc:  # noqa: BLE001 - reply with the error, don't crash the service
        await request.respond_error("500", str(exc))
    finally:
        last_activity[0] = time.monotonic()


async def _idle_watchdog(last_activity: list[float], idle_timeout: float) -> None:
    while True:
        await asyncio.sleep(5)
        if time.monotonic() - last_activity[0] >= idle_timeout:
            return


async def main() -> None:
    url = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")
    user = os.environ.get("NATS_USER")
    password = os.environ.get("NATS_PASSWORD")
    idle_timeout = float(
        os.environ.get("IDLE_TIMEOUT_SECONDS", DEFAULT_IDLE_TIMEOUT_SECONDS)
    )

    nc = await nats.connect(url, user=user, password=password)
    svc = await micro.add_service(
        nc,
        config=micro.ServiceConfig(
            name=SERVICE_NAME,
            version=SERVICE_VERSION,
            description="Docling-backed document extraction (PDF/DOCX/MD/XLSX), "
            "shared over NATS by reqif-opa-mcp — see its README for the "
            "ingestion pipeline this front-ends.",
        ),
    )
    group = svc.add_group(name="ledgrrr")
    last_activity = [time.monotonic()]
    await group.add_endpoint(
        name="extract",
        handler=lambda request: _extract_handler(request, last_activity),
    )

    print(f"[{SERVICE_NAME}] listening on '{url}' as subject 'ledgrrr.extract'", flush=True)
    print(
        f"[{SERVICE_NAME}] on-demand mode: exiting after {idle_timeout:.0f}s idle",
        flush=True,
    )
    try:
        await _idle_watchdog(last_activity, idle_timeout)
        print(f"[{SERVICE_NAME}] idle timeout reached, shutting down", flush=True)
    finally:
        await svc.stop()
        await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
