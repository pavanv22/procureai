"""
routers/vendors.py
==================
Upload and manage vendor response documents for a given RFQ.

Prefix:  /rfq/{rfq_id}/vendors
Tags:    Vendors
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, status

from core.database import db
from models.schemas import VendorCreate, VendorResponse, StatusMessage
from services.seed_data import SAMPLE_VENDORS

router = APIRouter(prefix="/rfq/{rfq_id}/vendors", tags=["Vendors"])


def _require_rfq(rfq_id: str) -> dict:
    rfq = db.get_rfq(rfq_id)
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ '{rfq_id}' not found.",
        )
    return rfq


# ── List ──────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[VendorResponse],
    summary="List all vendors for an RFQ",
)
async def list_vendors(rfq_id: str) -> list[dict]:
    _require_rfq(rfq_id)
    return [{"rfq_id": rfq_id, **v} for v in db.list_vendors(rfq_id)]


# ── Create ────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a single vendor document",
)
async def add_vendor(rfq_id: str, payload: VendorCreate) -> dict:
    """Add one vendor document to the RFQ."""
    _require_rfq(rfq_id)
    vendor = db.add_vendor(rfq_id, {**payload.model_dump(), "status": "uploaded"})
    return {"rfq_id": rfq_id, **vendor}


@router.post(
    "/seed",
    status_code=status.HTTP_201_CREATED,
    summary="Seed 5 sample vendor documents",
)
async def seed_vendors(rfq_id: str) -> dict:
    """
    Load all 5 pre-built vendor documents (PDF, PPT, Excel, Word, Docx).
    Existing vendors are cleared first so seeding is idempotent.
    """
    _require_rfq(rfq_id)
    db.clear_vendors(rfq_id)

    added = []
    for v in SAMPLE_VENDORS:
        vendor = db.add_vendor(rfq_id, {**v, "status": "uploaded"})
        added.append({"rfq_id": rfq_id, **vendor})

    return {
        "status": "ok",
        "added": len(added),
        "vendors": added,
    }


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get(
    "/{vendor_id}",
    response_model=VendorResponse,
    summary="Get a single vendor document",
)
async def get_vendor(rfq_id: str, vendor_id: str) -> dict:
    _require_rfq(rfq_id)
    vendor = db.get_vendor(rfq_id, vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor '{vendor_id}' not found in RFQ '{rfq_id}'.",
        )
    return {"rfq_id": rfq_id, **vendor}


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete(
    "/{vendor_id}",
    response_model=StatusMessage,
    summary="Remove a vendor document",
)
async def delete_vendor(rfq_id: str, vendor_id: str) -> dict:
    _require_rfq(rfq_id)
    if not db.delete_vendor(rfq_id, vendor_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor '{vendor_id}' not found.",
        )
    return {"status": "ok", "message": f"Vendor '{vendor_id}' removed."}


@router.delete(
    "/",
    response_model=StatusMessage,
    summary="Remove all vendor documents for an RFQ",
)
async def clear_vendors(rfq_id: str) -> dict:
    _require_rfq(rfq_id)
    count = db.clear_vendors(rfq_id)
    return {"status": "ok", "message": f"{count} vendor(s) removed."}
