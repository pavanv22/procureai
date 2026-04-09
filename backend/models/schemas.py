"""
models/schemas.py
=================
Every Pydantic model used across the API lives here.
Organised by domain: RFQ → Vendor → Extraction → Technical → Commercial → Award.
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
# Enumerations
# ══════════════════════════════════════════════════════════════════════════════

class RFQStatus(str, Enum):
    draft      = "Draft"
    active     = "Active"
    evaluation = "Evaluation"
    awarded    = "Awarded"
    cancelled  = "Cancelled"


class ComplianceLevel(str, Enum):
    high   = "High"
    medium = "Medium"
    low    = "Low"


class RiskLevel(str, Enum):
    low    = "Low"
    medium = "Medium"
    high   = "High"


class FileType(str, Enum):
    pdf   = "PDF"
    ppt   = "PPT"
    excel = "Excel"
    word  = "Word"
    other = "Other"


# ══════════════════════════════════════════════════════════════════════════════
# RFQ domain
# ══════════════════════════════════════════════════════════════════════════════

class RFQTimeline(BaseModel):
    clarifications_deadline:  str = "May 12th, 2026"
    technical_bid_deadline:   str = "May 19th, 2026"
    commercial_bid_deadline:  str = "May 21st, 2026"
    evaluation_start_date:    str = "May 22nd, 2026"
    negotiation_start_date:   str = "May 27th, 2026"
    final_award_date:         str = "June 2nd, 2026"


class LineItem(BaseModel):
    id:          int
    name:        str
    category:    str = "Services"
    hsn:         str = "8471XX"
    uom:         str = "Lot"
    description: str = ""


class RFQCreate(BaseModel):
    subject:       str
    rfp_code:      str
    sourcing_type: str       = "RFQ"
    round:         str       = "Round 1"
    status:        RFQStatus = RFQStatus.draft
    owner:         str
    currency:      str       = "USD"
    requestor:     str
    department:    str
    category:      str
    timelines:     RFQTimeline              = Field(default_factory=RFQTimeline)
    line_items:    list[LineItem]           = Field(default_factory=list)
    scope_of_work: str                      = ""


class RFQResponse(RFQCreate):
    id: str


class RFQUpdate(BaseModel):
    """Partial update — all fields optional."""
    subject:       Optional[str]       = None
    rfp_code:      Optional[str]       = None
    sourcing_type: Optional[str]       = None
    round:         Optional[str]       = None
    status:        Optional[RFQStatus] = None
    owner:         Optional[str]       = None
    currency:      Optional[str]       = None
    requestor:     Optional[str]       = None
    department:    Optional[str]       = None
    category:      Optional[str]       = None
    timelines:     Optional[RFQTimeline]    = None
    line_items:    Optional[list[LineItem]] = None
    scope_of_work: Optional[str]            = None


# ══════════════════════════════════════════════════════════════════════════════
# Questionnaire domain
# ══════════════════════════════════════════════════════════════════════════════

class QuestionItem(BaseModel):
    id:         str
    question:   str
    type:       str  # e.g. "Open text", "File upload", "Yes/No"
    rationale:  str


class QuestionnaireResponse(BaseModel):
    rfq_id:     str
    technical:  list[QuestionItem]
    commercial: list[QuestionItem]


# ══════════════════════════════════════════════════════════════════════════════
# Vendor domain
# ══════════════════════════════════════════════════════════════════════════════

class VendorCreate(BaseModel):
    vendor_name:  str
    file_name:    str
    file_type:    str        # PDF | PPT | Excel | Word
    raw_content:  str        # extracted / simulated document text


class VendorResponse(VendorCreate):
    vendor_id: str
    rfq_id:    str
    status:    str = "uploaded"


# ══════════════════════════════════════════════════════════════════════════════
# Extraction domain
# ══════════════════════════════════════════════════════════════════════════════

class LineItemPricing(BaseModel):
    amount:  Optional[float] = None   # None means not quoted
    note:    str             = ""
    covered: bool            = False


class ExtractedVendor(BaseModel):
    vendor_id:         str
    name:              str
    line_item_pricing: dict[str, LineItemPricing] = Field(default_factory=dict)
    total_bid:         Optional[float]             = None
    delivery_weeks:    Optional[int]               = None
    payment_terms:     str                         = ""
    compliance_level:  ComplianceLevel             = ComplianceLevel.medium
    scope_coverage:    int                         = 0    # 0-100 %
    currency_original: str                         = "USD"
    anomalies:         list[str]                   = Field(default_factory=list)
    missing_items:     list[str]                   = Field(default_factory=list)
    strengths:         list[str]                   = Field(default_factory=list)
    risks:             list[str]                   = Field(default_factory=list)


class ExtractionResponse(BaseModel):
    rfq_id:  str
    vendors: list[ExtractedVendor]


# ══════════════════════════════════════════════════════════════════════════════
# Technical analysis domain
# ══════════════════════════════════════════════════════════════════════════════

class RequirementCoverage(BaseModel):
    vendor:     str
    meets_all:  bool
    gaps:       list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class ComplianceScore(BaseModel):
    vendor:         str
    score:          int           # 0-100
    evidence:       str
    certifications: list[str]     = Field(default_factory=list)


class TechnicalAnalysis(BaseModel):
    rfq_id:                   str
    requirements_met:         list[RequirementCoverage]
    compliance_scores:        list[ComplianceScore]
    key_differentiators:      str
    missing_response_summary: str


# ══════════════════════════════════════════════════════════════════════════════
# Commercial analysis domain
# ══════════════════════════════════════════════════════════════════════════════

class CommercialAnomaly(BaseModel):
    type:   str   # too_high | too_low | missing | currency_risk | open_ended
    vendor: str
    item:   str
    detail: str


class ValueRanking(BaseModel):
    rank:      int
    vendor:    str
    rationale: str


class LineItemComparison(BaseModel):
    item:    str
    item_id: int
    vendors: dict[str, Optional[float]]   # vendor name → amount or None


class CommercialAnalysis(BaseModel):
    rfq_id:                  str
    line_item_comparison:    list[LineItemComparison]
    anomalies:               list[CommercialAnomaly]
    cost_insights:           str
    value_for_money_ranking: list[ValueRanking]


# ══════════════════════════════════════════════════════════════════════════════
# Award recommendation domain
# ══════════════════════════════════════════════════════════════════════════════

class ScenarioScoring(BaseModel):
    compliance: int   # /30
    scope:      int   # /25
    cost:       int   # /20
    timeline:   int   # /15
    risk:       int   # /10
    total:      int   # /100


class AwardScenario(BaseModel):
    title:            str
    subtitle:         str
    primary_vendor:   str
    secondary_vendor: Optional[str] = None
    scoring:          ScenarioScoring
    recommendation:   str
    tradeoffs:        str
    confidence:       str       # High | Medium | Low
    risk_level:       RiskLevel


class AwardRecommendation(BaseModel):
    rfq_id:                       str
    scenarios:                    list[AwardScenario]
    overall_recommendation_summary: str
    winner_name:                  str
    winner_scenario:              int   # index into scenarios[]
    key_rationale:                str
    tradeoffs:                    str
    confidence_statement:         str


# ══════════════════════════════════════════════════════════════════════════════
# Summary / generic
# ══════════════════════════════════════════════════════════════════════════════

class AnalysisSummary(BaseModel):
    rfq_id:         str
    questionnaires: Optional[QuestionnaireResponse] = None
    extraction:     Optional[ExtractionResponse]    = None
    technical:      Optional[TechnicalAnalysis]     = None
    commercial:     Optional[CommercialAnalysis]    = None
    recommendation: Optional[AwardRecommendation]  = None


class StatusMessage(BaseModel):
    status:  str
    message: str
    data:    Optional[Any] = None
