"""
core/database.py
================
In-memory key-value repository.  Every RFQ owns a bucket that stores
vendors and all intermediate analysis results.

Swap the InMemoryDB class for a SQLAlchemy session to move to Postgres
without changing any router code.
"""
from __future__ import annotations
import uuid
from typing import Any


class InMemoryDB:
    """Thread-safe-enough for a single-process FastAPI dev server."""

    def __init__(self) -> None:
        # Top-level store: rfq_id → bucket dict
        self._store: dict[str, dict[str, Any]] = {}

    # ── private helpers ───────────────────────────────────────────────────────

    def _bucket(self, rfq_id: str) -> dict | None:
        return self._store.get(rfq_id)

    def _require_bucket(self, rfq_id: str) -> dict:
        b = self._bucket(rfq_id)
        if b is None:
            raise KeyError(f"RFQ '{rfq_id}' not found")
        return b

    # ── RFQ ──────────────────────────────────────────────────────────────────

    def create_rfq(self, data: dict) -> dict:
        """Persist a new RFQ and return it with its generated id."""
        rfq_id = uuid.uuid4().hex[:8].upper()
        record = {"id": rfq_id, **data}
        self._store[rfq_id] = {
            "rfq": record,
            "vendors": {},          # vendor_id → vendor dict
            "questionnaires": None,
            "extraction": None,
            "technical": None,
            "commercial": None,
            "recommendation": None,
        }
        return record

    def get_rfq(self, rfq_id: str) -> dict | None:
        b = self._bucket(rfq_id)
        return b["rfq"] if b else None

    def list_rfqs(self) -> list[dict]:
        return [b["rfq"] for b in self._store.values()]

    def update_rfq(self, rfq_id: str, data: dict) -> dict | None:
        b = self._bucket(rfq_id)
        if not b:
            return None
        b["rfq"].update(data)
        return b["rfq"]

    def delete_rfq(self, rfq_id: str) -> bool:
        if rfq_id in self._store:
            del self._store[rfq_id]
            return True
        return False

    # ── Vendors ───────────────────────────────────────────────────────────────

    def add_vendor(self, rfq_id: str, vendor_data: dict) -> dict | None:
        b = self._bucket(rfq_id)
        if not b:
            return None
        vendor_id = uuid.uuid4().hex[:8]
        vendor = {"vendor_id": vendor_id, **vendor_data}
        b["vendors"][vendor_id] = vendor
        return vendor

    def list_vendors(self, rfq_id: str) -> list[dict]:
        b = self._bucket(rfq_id)
        return list(b["vendors"].values()) if b else []

    def get_vendor(self, rfq_id: str, vendor_id: str) -> dict | None:
        b = self._bucket(rfq_id)
        return b["vendors"].get(vendor_id) if b else None

    def delete_vendor(self, rfq_id: str, vendor_id: str) -> bool:
        b = self._bucket(rfq_id)
        if b and vendor_id in b["vendors"]:
            del b["vendors"][vendor_id]
            return True
        return False

    def clear_vendors(self, rfq_id: str) -> int:
        b = self._bucket(rfq_id)
        if not b:
            return 0
        count = len(b["vendors"])
        b["vendors"] = {}
        return count

    # ── Analysis buckets ─────────────────────────────────────────────────────
    # key is one of: "questionnaires", "extraction", "technical",
    #                "commercial", "recommendation"

    def set_bucket(self, rfq_id: str, key: str, data: Any) -> bool:
        b = self._bucket(rfq_id)
        if not b:
            return False
        b[key] = data
        return True

    def get_bucket(self, rfq_id: str, key: str) -> Any:
        b = self._bucket(rfq_id)
        return b.get(key) if b else None

    def clear_bucket(self, rfq_id: str, key: str) -> bool:
        b = self._bucket(rfq_id)
        if b and key in b:
            b[key] = None
            return True
        return False


# ── Module-level singleton ────────────────────────────────────────────────────
db = InMemoryDB()
