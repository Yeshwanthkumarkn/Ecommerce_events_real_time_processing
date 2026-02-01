"""Event processing logic.

This module holds the core "business" behavior:
- Parse/validate incoming events (schema validation).
- Always write RAW rows.
- Write PROCESSED only for valid rows.
- Write ERROR rows for invalid events or downstream failures.

Design note:
Pub/Sub push retries on non-2xx responses. We intentionally return 2xx for
invalid events (bad data is not recoverable) and return 5xx for transient
storage/processing failures.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.bq_client import BigQueryTarget, BigQueryWriter


@dataclass(frozen=True)
class PipelineConfig:
    """Runtime configuration for dataset/table targets."""

    dataset_id: str
    raw_table_id: str
    processed_table_id: str
    error_table_id: str
    source: str


class EventType(str, Enum):
    """Enterprise-ish canonical event types."""

    view = "view"
    add_to_cart = "add_to_cart"
    remove_from_cart = "remove_from_cart"
    checkout = "checkout"
    purchase = "purchase"
    search = "search"


class DeviceType(str, Enum):
    """Allowed device types (normalized)."""

    mobile = "mobile"
    desktop = "desktop"
    tablet = "tablet"


class EcommerceEvent(BaseModel):
    """Validated event schema for the PROCESSED table.

    We allow extra fields to keep the schema evolvable; extra fields are kept in RAW.
    """

    model_config = ConfigDict(extra="allow")

    event_id: UUID
    user_id: str = Field(min_length=1, max_length=128)
    event_type: EventType
    product_id: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=128)
    price: float = Field(ge=0)
    device: DeviceType
    city: str = Field(min_length=1, max_length=128)
    event_time: datetime


def _utc_now() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(tz=UTC)


def _to_rfc3339(dt: datetime | None) -> str | None:
    """Convert datetime to RFC3339 string accepted by BigQuery TIMESTAMP.

    BigQuery streaming inserts expect JSON-serializable values. We store timestamps
    as RFC3339 strings to avoid serialization issues.
    """
    if dt is None:
        return None
    normalized = dt
    if normalized.tzinfo is None:
        normalized = normalized.replace(tzinfo=UTC)
    normalized = normalized.astimezone(UTC)
    return normalized.isoformat().replace("+00:00", "Z")


def _parse_rfc3339_timestamp(value: str | None) -> datetime | None:
    """Parse RFC3339-ish timestamps into UTC.

    Returns None if parsing fails.
    """
    if not value:
        return None

    # Pub/Sub publishTime and many event_time values are RFC3339, often ending with 'Z'.
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _coerce_float(value: Any) -> float | None:
    """Best-effort float conversion for messy inputs."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_config() -> PipelineConfig:
    """Load config from environment variables with sensible defaults."""
    return PipelineConfig(
        dataset_id=os.getenv("BQ_DATASET", "ecommerce_streaming"),
        raw_table_id=os.getenv("BQ_RAW_TABLE", "ecommerce_raw_events"),
        processed_table_id=os.getenv("BQ_PROCESSED_TABLE", "ecommerce_processed_events"),
        error_table_id=os.getenv("BQ_ERROR_TABLE", "ecommerce_error_events"),
        source=os.getenv("EVENT_SOURCE", "pubsub"),
    )


def _insert_error_event(
    *,
    writer: BigQueryWriter,
    config: PipelineConfig,
    message_id: str | None,
    publish_time: datetime | None,
    ingestion_time: datetime,
    event_id: str | None,
    stage: str,
    error_message: str,
    error_details: Any | None,
    raw_event: Mapping[str, Any],
    attributes: Mapping[str, Any] | None,
) -> None:
    """Write a row to the ERROR table (best-effort operational logging)."""
    target = BigQueryTarget(dataset_id=config.dataset_id, table_id=config.error_table_id)
    row = {
        "message_id": message_id,
        "event_id": event_id,
        "publish_time": _to_rfc3339(publish_time),
        "ingestion_time": _to_rfc3339(ingestion_time),
        "stage": stage,
        "error_message": error_message,
        "error_details": json.dumps(error_details) if error_details is not None else None,
        "raw_payload": json.dumps(raw_event),
        "attributes": json.dumps(attributes or {}),
        "source": config.source,
    }
    # Use event_id for idempotency when available.
    writer.insert_row(target, row, insert_id=event_id or message_id)


def process_event(
    *,
    event: Mapping[str, Any],
    message_id: str | None,
    publish_time: str | None,
    attributes: Mapping[str, Any] | None = None,
    writer: BigQueryWriter,
    config: PipelineConfig,
) -> None:
    """Process a single event.

    Args:
        event: Parsed JSON payload.
        message_id: Pub/Sub messageId (used for dedupe when event_id missing).
        publish_time: Pub/Sub publishTime (RFC3339 string).
        attributes: Pub/Sub message attributes.
        writer: BigQuery writer.
        config: Dataset/table config.

    Raises:
        Exception: For transient failures (e.g., BigQuery insert errors) so caller can return 5xx.
    """
    ingestion_time = _utc_now()

    publish_dt = _parse_rfc3339_timestamp(publish_time)
    validation_errors: list[dict[str, Any]] | None = None
    is_valid = True

    validated: EcommerceEvent | None = None
    try:
        validated = EcommerceEvent.model_validate(event)
    except ValidationError as exc:
        is_valid = False
        validation_errors = exc.errors(include_url=False)

    event_id_str: str | None = str(validated.event_id) if validated is not None else None

    event_time_dt: datetime | None
    if validated is not None:
        event_time_dt = validated.event_time.astimezone(UTC) if validated.event_time.tzinfo else validated.event_time.replace(tzinfo=UTC)
    else:
        event_time_dt = _parse_rfc3339_timestamp(
            str(event.get("event_time")) if event.get("event_time") is not None else None
        )

    raw_target = BigQueryTarget(dataset_id=config.dataset_id, table_id=config.raw_table_id)
    processed_target = BigQueryTarget(dataset_id=config.dataset_id, table_id=config.processed_table_id)

    raw_row = {
        "message_id": message_id,
        "event_id": event_id_str,
        "publish_time": _to_rfc3339(publish_dt),
        "ingestion_time": _to_rfc3339(ingestion_time),
        "raw_payload": json.dumps(event),
        "source": config.source,
        "attributes": json.dumps(attributes or {}),
        "is_valid": is_valid,
        "validation_errors": json.dumps(validation_errors) if validation_errors else None,
    }

    # insertId is used for best-effort de-duplication on streaming inserts.
    # Prefer event_id (stable business key) over message_id (transport-level key).
    insert_id = event_id_str or message_id
    writer.insert_row(raw_target, raw_row, insert_id=insert_id)

    if not is_valid or validated is None:
        # Store invalid events to error table for operational visibility.
        _insert_error_event(
            writer=writer,
            config=config,
            message_id=message_id,
            event_id=event_id_str,
            publish_time=publish_dt,
            ingestion_time=ingestion_time,
            stage="validation",
            error_message="Schema validation failed",
            error_details=validation_errors,
            raw_event=event,
            attributes=attributes,
        )
        return

    processed_row = {
        "event_id": event_id_str,
        "user_id": validated.user_id,
        "event_type": validated.event_type.value,
        "product_id": validated.product_id,
        "category": validated.category,
        "price": float(validated.price),
        "device": validated.device.value,
        "city": validated.city,
        "event_time": _to_rfc3339(event_time_dt),
        "ingestion_time": _to_rfc3339(ingestion_time),
    }

    try:
        writer.insert_row(processed_target, processed_row, insert_id=insert_id)
    except Exception as exc:  # noqa: BLE001
        # Best-effort: capture processing failure details for debugging/ops.
        try:
            _insert_error_event(
                writer=writer,
                config=config,
                message_id=message_id,
                event_id=event_id_str,
                publish_time=publish_dt,
                ingestion_time=ingestion_time,
                stage="processed_insert",
                error_message=str(exc),
                error_details=None,
                raw_event=event,
                attributes=attributes,
            )
        finally:
            raise
