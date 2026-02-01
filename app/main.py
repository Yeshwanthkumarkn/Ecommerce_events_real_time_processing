"""FastAPI service that receives Pub/Sub push messages and writes to BigQuery.

Key behavior:
- Always store the incoming event in the RAW table.
- Validate/normalize into a PROCESSED table.
- If the payload is invalid, return 2xx to Pub/Sub (ack) and record details in RAW/ERROR.
- If a transient/server failure occurs, return 5xx so Pub/Sub retries (and eventually DLQs).
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from app.bq_client import BigQueryWriter
from app.processor import load_config, process_event

app = FastAPI(title="Ecommerce Streaming Processor")

_log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    force=True,
)

logger = logging.getLogger("ecommerce-processor")


@app.on_event("startup")
def _startup_log() -> None:
    """Emit a startup log so we can confirm which revision is running."""
    logger.info(
        "Starting service",
        extra={
            "k_revision": os.getenv("K_REVISION"),
            "k_service": os.getenv("K_SERVICE"),
            "k_configuration": os.getenv("K_CONFIGURATION"),
        },
    )


@app.middleware("http")
async def _log_unhandled_exceptions(request: Request, call_next):
    """Log unhandled exceptions with stack traces.

    This catches failures that occur before/around the route handler (e.g., JSON parsing).
    """
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled exception", extra={"path": str(request.url.path)})
        raise


@app.get("/health")
def health() -> dict[str, str]:
    """Lightweight health check for Cloud Run / uptime probes."""
    return {
        "status": "ok",
        "revision": os.getenv("K_REVISION", ""),
    }


@app.post("/pubsub/push")
async def pubsub_push(request: Request) -> dict[str, str]:
    """Pub/Sub push endpoint.

    Expects the standard Pub/Sub push envelope:
    {
      "message": {"data": "<base64>", "messageId": "...", "publishTime": "...", "attributes": {...}},
      "subscription": "..."
    }

    Returns:
    - 2xx when successfully handled OR when the event is invalid (to avoid infinite retries on bad data)
    - 5xx when processing/storage fails (to trigger Pub/Sub retry)
    """
    envelope: dict[str, Any] = await request.json()

    message = envelope.get("message")
    if not isinstance(message, dict):
        raise HTTPException(status_code=400, detail="Invalid Pub/Sub envelope: missing message")

    data_b64 = message.get("data")
    if not isinstance(data_b64, str):
        raise HTTPException(status_code=400, detail="Invalid Pub/Sub envelope: missing data")

    try:
        # Pub/Sub push encodes the original message bytes into base64.
        payload_bytes = base64.b64decode(data_b64)
        payload_text = payload_bytes.decode("utf-8")
        event = json.loads(payload_text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    message_id = message.get("messageId")
    publish_time = message.get("publishTime")
    attributes = message.get("attributes")

    project_id = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    writer = BigQueryWriter(project_id=project_id)
    config = load_config()

    try:
        process_event(
            event=event,
            message_id=message_id if isinstance(message_id, str) else None,
            publish_time=publish_time if isinstance(publish_time, str) else None,
            attributes=attributes if isinstance(attributes, dict) else None,
            writer=writer,
            config=config,
        )
    except Exception as exc:  # noqa: BLE001
        # Pub/Sub retries on 5xx; use that to handle transient failures.
        logger.exception("Failed to process Pub/Sub message")
        # Fallback: ensure something hits stderr even if logging is misconfigured.
        print(f"ERROR: Failed to process Pub/Sub message: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return {"status": "accepted"}
