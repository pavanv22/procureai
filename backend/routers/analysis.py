"""
routers/analysis.py
===================
The four-stage AI analysis pipeline:

  POST /extract        — read & normalise vendor documents
  POST /technical      — capability & compliance scoring
  POST /commercial     — cost comparison & anomaly detection
  POST /recommendation — multi-scenario award recommendation

Each stage caches its result in the RFQ bucket.
GET variants return the cached result without re-running AI.

Prefix:  /rfq/{rfq_id}/analysis
Tags:    Analysis
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, status

from core.database import db
from models.schemas import (
    ExtractionResponse,
    TechnicalAnalysis,
    CommercialAnalysis,
    AwardRecommendation,
    AnalysisSummary,
    StatusMessage,
)
from services.ai_service import (
    extract_vendor_data,
    run_technical_analysis,
    run_commercial_analysis,
    generate_award_recommendation,
)

router = APIRouter(prefix="/rfq/{rfq_id}/analysis", tags=["Analysis"])

# Fallback line-item list when an RFQ was created without line_items
_DEFAULT_LINE_ITEMS = [
    {"id": 1, "name": "Strategy & Creative Development"},
    {"id": 2, "name": "TVC Development"},
    {"id": 3, "name": "TVC Production"},
    {"id": 4, "name": "Social Organic Content"},
    {"id": 5, "name": "Social Paid Media Planning"},
    {"id": 6, "name": "Social Paid Media Buying & Optimization"},
    {"id": 7, "name": "Kids Advertising & Claims Compliance Review"},
    {"id": 8, "name": "Launch Program Management"},
]


def _require_rfq(rfq_id: str) -> dict:
    rfq = db.get_rfq(rfq_id)
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ '{rfq_id}' not found.",
        )
    return rfq


def _require_extraction(rfq_id: str) -> dict:
    extraction = db.get_bucket(rfq_id, "extraction")
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No extraction data. Run POST /extract first.",
        )
    return extraction


# ══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Extraction
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/extract",
    summary="Extract & normalise all vendor documents",
)
async def run_extraction(rfq_id: str) -> dict:
    """
    Read every vendor document attached to this RFQ, extract pricing,
    normalise currencies to USD, and map results to the 8 RFQ line items.

    Requires: at least one vendor seeded/uploaded.
    """
    rfq = _require_rfq(rfq_id)
    vendors = db.list_vendors(rfq_id)
    if not vendors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No vendor documents found. Seed or upload vendors first.",
        )

    line_items = rfq.get("line_items") or _DEFAULT_LINE_ITEMS
    raw = await extract_vendor_data(vendors, line_items)
    extracted_vendors = raw.get("vendors", [])

    # Attach the stored vendor_id to each extracted entry (by position)
    for i, ev in enumerate(extracted_vendors):
        ev["vendor_id"] = vendors[i]["vendor_id"] if i < len(vendors) else f"v{i}"

    result = {"rfq_id": rfq_id, "vendors": extracted_vendors}
    db.set_bucket(rfq_id, "extraction", result)
    return result


@router.get(
    "/extract",
    summary="Get cached extraction results",
)
async def get_extraction(rfq_id: str) -> dict:
    _require_rfq(rfq_id)
    data = db.get_bucket(rfq_id, "extraction")
    if not data:
        raise HTTPException(status_code=404, detail="No extraction data. Run POST /extract first.")
    return data


@router.delete(
    "/extract",
    response_model=StatusMessage,
    summary="Clear cached extraction results",
)
async def clear_extraction(rfq_id: str) -> dict:
    _require_rfq(rfq_id)
    db.clear_bucket(rfq_id, "extraction")
    return {"status": "ok", "message": "Extraction cache cleared."}


# ══════════════════════════════════════════════════════════════════════════════
# Stage 2 — Technical Analysis
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/technical",
    summary="Run AI technical analysis",
)
async def technical_analysis(rfq_id: str) -> dict:
    """
    Score vendors on capability, compliance evidence, and scope coverage.
    Requires extraction to have been run first.
    """
    _require_rfq(rfq_id)
    extraction = _require_extraction(rfq_id)

    raw = await run_technical_analysis(extraction["vendors"])
    result = {"rfq_id": rfq_id, **raw}
    db.set_bucket(rfq_id, "technical", result)
    return result


@router.get(
    "/technical",
    summary="Get cached technical analysis",
)
async def get_technical(rfq_id: str) -> dict:
    _require_rfq(rfq_id)
    data = db.get_bucket(rfq_id, "technical")
    if not data:
        raise HTTPException(status_code=404, detail="No technical analysis. Run POST /technical first.")
    return data


@router.delete(
    "/technical",
    response_model=StatusMessage,
    summary="Clear cached technical analysis",
)
async def clear_technical(rfq_id: str) -> dict:
    _require_rfq(rfq_id)
    db.clear_bucket(rfq_id, "technical")
    return {"status": "ok", "message": "Technical analysis cache cleared."}


# ══════════════════════════════════════════════════════════════════════════════
# Stage 3 — Commercial Analysis
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/commercial",
    summary="Run AI commercial analysis",
)
async def commercial_analysis(rfq_id: str) -> dict:
    """
    Cross-vendor cost comparison, anomaly detection, and value-for-money ranking.
    Requires extraction to have been run first.
    """
    rfq = _require_rfq(rfq_id)
    extraction = _require_extraction(rfq_id)

    line_items = rfq.get("line_items") or _DEFAULT_LINE_ITEMS
    raw = await run_commercial_analysis(extraction["vendors"], line_items)
    result = {"rfq_id": rfq_id, **raw}
    db.set_bucket(rfq_id, "commercial", result)
    return result


@router.get(
    "/commercial",
    summary="Get cached commercial analysis",
)
async def get_commercial(rfq_id: str) -> dict:
    _require_rfq(rfq_id)
    data = db.get_bucket(rfq_id, "commercial")
    if not data:
        raise HTTPException(status_code=404, detail="No commercial analysis. Run POST /commercial first.")
    return data


@router.delete(
    "/commercial",
    response_model=StatusMessage,
    summary="Clear cached commercial analysis",
)
async def clear_commercial(rfq_id: str) -> dict:
    _require_rfq(rfq_id)
    db.clear_bucket(rfq_id, "commercial")
    return {"status": "ok", "message": "Commercial analysis cache cleared."}


# ══════════════════════════════════════════════════════════════════════════════
# Stage 4 — Award Recommendation
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/recommendation",
    summary="Generate multi-scenario award recommendation",
)
async def award_recommendation(rfq_id: str) -> dict:
    """
    Produce three award scenarios (best value, lowest cost, split award)
    and identify the recommended winner.
    Requires extraction to have been run first.
    """
    _require_rfq(rfq_id)
    extraction = _require_extraction(rfq_id)

    raw = await generate_award_recommendation(extraction["vendors"])
    result = {"rfq_id": rfq_id, **raw}
    db.set_bucket(rfq_id, "recommendation", result)
    return result


@router.get(
    "/recommendation",
    summary="Get cached award recommendation",
)
async def get_recommendation(rfq_id: str) -> dict:
    _require_rfq(rfq_id)
    data = db.get_bucket(rfq_id, "recommendation")
    if not data:
        raise HTTPException(status_code=404, detail="No recommendation. Run POST /recommendation first.")
    return data


@router.delete(
    "/recommendation",
    response_model=StatusMessage,
    summary="Clear cached award recommendation",
)
async def clear_recommendation(rfq_id: str) -> dict:
    _require_rfq(rfq_id)
    db.clear_bucket(rfq_id, "recommendation")
    return {"status": "ok", "message": "Recommendation cache cleared."}


# ══════════════════════════════════════════════════════════════════════════════
# Summary — all cached results in one call
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/summary",
    summary="Get all cached analysis results",
)
async def get_summary(rfq_id: str) -> dict:
    """
    Returns all cached pipeline results for this RFQ.
    Null fields mean that stage has not been run yet.
    Useful for the frontend to hydrate state on page load.
    """
    _require_rfq(rfq_id)
    return {
        "rfq_id":         rfq_id,
        "questionnaires": db.get_bucket(rfq_id, "questionnaires"),
        "extraction":     db.get_bucket(rfq_id, "extraction"),
        "technical":      db.get_bucket(rfq_id, "technical"),
        "commercial":     db.get_bucket(rfq_id, "commercial"),
        "recommendation": db.get_bucket(rfq_id, "recommendation"),
    }


@router.delete(
    "/all",
    response_model=StatusMessage,
    summary="Clear all cached analysis results",
)
async def clear_all_analysis(rfq_id: str) -> dict:
    """Reset the entire pipeline so all stages can be re-run."""
    _require_rfq(rfq_id)
    for key in ("questionnaires", "extraction", "technical", "commercial", "recommendation"):
        db.clear_bucket(rfq_id, key)
    return {"status": "ok", "message": "All analysis caches cleared."}
