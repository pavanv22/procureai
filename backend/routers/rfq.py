"""
routers/rfq.py
==============
CRUD operations for RFQ documents plus AI questionnaire generation.

Prefix:  /rfq
Tags:    RFQ
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, status

from core.database import db
from models.schemas import (
    RFQCreate,
    RFQResponse,
    RFQUpdate,
    QuestionnaireResponse,
    StatusMessage,
)
from services.ai_service import generate_questionnaires
from services.seed_data import DEFAULT_RFQ

router = APIRouter(prefix="/rfq", tags=["RFQ"])


# ── List ──────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[RFQResponse],
    summary="List all RFQs",
)
async def list_rfqs() -> list[dict]:
    """Return every RFQ currently stored."""
    return db.list_rfqs()


# ── Create ────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=RFQResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new RFQ",
)
async def create_rfq(payload: RFQCreate) -> dict:
    """Persist a new RFQ from the supplied payload and return it with its generated id."""
    return db.create_rfq(payload.model_dump(mode="json"))


@router.post(
    "/seed",
    response_model=RFQResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Seed the demo RFQ",
)
async def seed_rfq() -> dict:
    """
    Create the pre-built kids health drink demo RFQ.
    Useful for quick prototyping without filling a form.
    """
    return db.create_rfq(DEFAULT_RFQ)


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get(
    "/{rfq_id}",
    response_model=RFQResponse,
    summary="Get a single RFQ",
)
async def get_rfq(rfq_id: str) -> dict:
    rfq = db.get_rfq(rfq_id)
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ '{rfq_id}' not found.",
        )
    return rfq


# ── Update ────────────────────────────────────────────────────────────────────

@router.put(
    "/{rfq_id}",
    response_model=RFQResponse,
    summary="Full update of an RFQ",
)
async def update_rfq(rfq_id: str, payload: RFQCreate) -> dict:
    """Replace all mutable fields of an existing RFQ."""
    updated = db.update_rfq(rfq_id, payload.model_dump())
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ '{rfq_id}' not found.",
        )
    return updated


@router.patch(
    "/{rfq_id}",
    response_model=RFQResponse,
    summary="Partial update of an RFQ",
)
async def patch_rfq(rfq_id: str, payload: RFQUpdate) -> dict:
    """Update only the supplied fields; leave the rest unchanged."""
    rfq = db.get_rfq(rfq_id)
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ '{rfq_id}' not found.",
        )
    patch_data = payload.model_dump(exclude_none=True)
    updated = db.update_rfq(rfq_id, patch_data)
    return updated


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete(
    "/{rfq_id}",
    response_model=StatusMessage,
    summary="Delete an RFQ",
)
async def delete_rfq(rfq_id: str) -> dict:
    if not db.delete_rfq(rfq_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ '{rfq_id}' not found.",
        )
    return {"status": "ok", "message": f"RFQ '{rfq_id}' deleted."}


# ── Questionnaire generation ──────────────────────────────────────────────────

@router.post(
    "/{rfq_id}/questionnaires",
    response_model=QuestionnaireResponse,
    summary="AI-generate vendor questionnaires",
)
async def generate_rfq_questionnaires(rfq_id: str) -> dict:
    """
    Use Claude to generate tailored technical and commercial questionnaires
    based on the RFQ's subject, line items, and scope of work.

    Results are cached in the RFQ bucket; call again to regenerate.
    """
    rfq = db.get_rfq(rfq_id)
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ '{rfq_id}' not found.",
        )

    result = await generate_questionnaires(
        rfq_subject=rfq["subject"],
        scope_of_work=rfq.get("scope_of_work", ""),
        line_items=rfq.get("line_items", []),
    )

    response = {
        "rfq_id": rfq_id,
        "technical": result.get("technical", []),
        "commercial": result.get("commercial", []),
    }
    db.set_bucket(rfq_id, "questionnaires", response)
    return response


@router.get(
    "/{rfq_id}/questionnaires",
    response_model=QuestionnaireResponse,
    summary="Get cached questionnaires",
)
async def get_questionnaires(rfq_id: str) -> dict:
    """Return previously generated questionnaires without re-calling Claude."""
    rfq = db.get_rfq(rfq_id)
    if not rfq:
        raise HTTPException(status_code=404, detail=f"RFQ '{rfq_id}' not found.")
    cached = db.get_bucket(rfq_id, "questionnaires")
    if not cached:
        raise HTTPException(
            status_code=404,
            detail="No questionnaires generated yet. POST /questionnaires first.",
        )
    return cached
