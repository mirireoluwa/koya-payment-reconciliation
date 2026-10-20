#!/usr/bin/env python3
"""Payment reconciliation.

Reads payments.jsonl and works out how much money we actually collected.
Run:  python3 reconcile.py

Rules (see README):
- Lines that can't be read are ignored, and so are events without a txn_id.
- A payment can be attempted more than once under the same txn_id. Only the
  latest attempt (by ts, not by position in the file) counts.
- A payment is collected only if its latest attempt is `success`.
- Amounts can arrive as numbers or as strings with thousands separators
  ("4,804.15"), so they are normalised before summing. Decimal is used so the
  total isn't skewed by floating point drift.
"""
import json
from decimal import Decimal, InvalidOperation


def parse_amount(value):
    """Return the amount as a Decimal, or None if it can't be read."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value.replace(",", "").strip())
        except InvalidOperation:
            return None
    return None


def load_latest_attempts(path):
    """Map each txn_id to its latest attempt, judged by ts."""
    latest = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
            except ValueError:
                continue  # unreadable line
            if not isinstance(event, dict):
                continue
            txn_id = event.get("txn_id")
            if not txn_id:
                continue  # no txn_id, can't be tied to a payment
            ts = event.get("ts")
            if not isinstance(ts, str):
                continue
            current = latest.get(txn_id)
            if current is None or ts > current["ts"]:
                latest[txn_id] = event
    return latest


latest = load_latest_attempts("payments.jsonl")

total = Decimal("0")
count = 0
for event in latest.values():
    if event.get("status") != "success":
        continue
    amount = parse_amount(event.get("amount"))
    if amount is None:
        continue
    total += amount
    count += 1

with open("expected.txt") as f:
    expected = int(f.read().strip())

if count != expected:
    print(f"Check failed: counted {count} successful payments, expected {expected}.")
    print("Something in the data isn't being handled the way the README describes.")
else:
    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{round(total)}")
