"""BigQuery client wrapper.

We keep this tiny on purpose:
- Centralizes streaming inserts.
- Supports `insertId` to reduce duplicates when Pub/Sub retries a message.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from google.cloud import bigquery


@dataclass(frozen=True)
class BigQueryTarget:
    """Identifies a BigQuery table by dataset + table id."""

    dataset_id: str
    table_id: str


class BigQueryWriter:
    def __init__(self, project_id: str | None = None) -> None:
        """Create a BigQuery client.

        Args:
            project_id: Optional explicit GCP project; if omitted, uses ADC default.
        """
        self._client = bigquery.Client(project=project_id)

    def insert_row(
        self,
        target: BigQueryTarget,
        row: Mapping[str, Any],
        *,
        insert_id: str | None = None,
    ) -> None:
        """Insert a single row into BigQuery via streaming inserts.

        Args:
            target: Dataset/table target.
            row: JSON-serializable row mapping.
            insert_id: Optional insertId for best-effort de-duplication.
                      Using Pub/Sub messageId or event_id here helps avoid duplicates on retries.
        """
        table_ref = f"{self._client.project}.{target.dataset_id}.{target.table_id}"

        row_ids = [insert_id] if insert_id else None
        errors = self._client.insert_rows_json(table_ref, [dict(row)], row_ids=row_ids)
        if errors:
            raise RuntimeError(f"BigQuery insert failed for {table_ref}: {errors}")
