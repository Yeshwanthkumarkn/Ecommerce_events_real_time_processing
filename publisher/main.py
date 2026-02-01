from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import UTC, datetime
from random import choice, random

from faker import Faker
from google.cloud import pubsub_v1


EVENT_TYPES = [
    "view",
    "add_to_cart",
    "remove_from_cart",
    "checkout",
    "purchase",
    "search",
]

DEVICES = ["mobile", "desktop", "tablet"]

CATEGORIES = [
    "electronics",
    "fashion",
    "home",
    "beauty",
    "sports",
    "books",
]


def utc_now_iso() -> str:
    """UTC timestamp formatted as RFC3339 with trailing 'Z'."""
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def generate_event(fake: Faker) -> dict:
    """Generate a single ecommerce event payload.

    Args:
        fake: Faker instance.

    Returns:
        JSON-serializable event dict that matches the processor schema.
    """
    event_type = choice(EVENT_TYPES)

    # Make the data feel more realistic: purchases/checkouts skew higher than views.
    base_price = fake.pyfloat(left_digits=4, right_digits=2, positive=True, min_value=1, max_value=3000)
    if event_type in {"purchase", "checkout"}:
        price = float(base_price)
    elif event_type in {"add_to_cart", "remove_from_cart"}:
        price = float(base_price * 0.7)
    else:
        price = float(base_price * 0.4)

    return {
        "event_id": str(uuid.uuid4()),
        "user_id": f"U{fake.random_int(min=1000, max=999999)}",
        "event_type": event_type,
        "product_id": f"P{fake.random_int(min=1000, max=999999)}",
        "category": choice(CATEGORIES),
        "price": round(price, 2),
        "device": choice(DEVICES),
        "city": fake.city(),
        "event_time": utc_now_iso(),
        "session_id": str(uuid.uuid4()),
        "ip": fake.ipv4_public(),
    }


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Publish fake e-commerce events to Pub/Sub")
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"), help="GCP project id")
    parser.add_argument("--topic", default=os.getenv("PUBSUB_TOPIC", "ecommerce_events"), help="Pub/Sub topic name")
    parser.add_argument("--rate", type=float, default=5.0, help="events per second")
    parser.add_argument("--count", type=int, default=0, help="number of events to publish (0 = infinite)")
    args = parser.parse_args()

    if not args.project:
        raise SystemExit("Missing --project (or GOOGLE_CLOUD_PROJECT env var)")

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(args.project, args.topic)

    # One Faker instance is enough; it is relatively expensive to construct repeatedly.
    fake = Faker()
    interval = 1.0 / args.rate if args.rate > 0 else 0

    sent = 0
    while True:
        if args.count and sent >= args.count:
            break

        event = generate_event(fake)
        data = json.dumps(event).encode("utf-8")

        attributes = {
            "schema_version": "1",
            "producer": "faker",
        }

        future = publisher.publish(topic_path, data=data, **attributes)
        future.result(timeout=30)

        sent += 1
        if sent % 100 == 0:
            print(f"published={sent}")

        if interval:
            time.sleep(max(0.0, interval * (0.8 + random() * 0.4)))


if __name__ == "__main__":
    main()
