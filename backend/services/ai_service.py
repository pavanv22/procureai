"""
services/ai_service.py
======================
Single point of contact for all Anthropic API calls.
Every public function accepts typed Python arguments, calls Claude,
parses the JSON response, and returns a plain dict.

Other modules must NOT import httpx or call Anthropic directly.
"""
from __future__ import annotations
import json
import re
import httpx
from core.config import get_settings
from google.generativeai import GenerativeModel
import asyncio
import google.generativeai as genai

_settings = get_settings()


genai.configure(api_key=_settings.gemini_api_key)



# ── Internal helpers ──────────────────────────────────────────────────────────

async def call_gemini_adk(system: str, user: str, max_tokens: int = 1024):
    """
    Make a single synchronous-style Gemini call using ADK inside async context.
    Raises exceptions on failure similar to httpx.raise_for_status().
    """

    model = GenerativeModel(
        model_name=_settings.gemini_model,
        system_instruction=system
    )

    # ADK is sync → wrap in thread for async compatibility
    def _call():
        response = model.generate_content(
            user,
            generation_config={
                "max_output_tokens": max_tokens
            }
        )
        return response

    response = await asyncio.to_thread(_call)

    # Extract text safely (Gemini can return multiple parts)
    try:
        return response.text
    except Exception:
        return response.candidates[0].content.parts[0].text

def _parse_json(raw: str) -> dict | list:
    """
    Strip optional markdown code fences and parse JSON.
    Raises json.JSONDecodeError if the model returned invalid JSON.
    """
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return json.loads(cleaned)


# ── Public service functions ──────────────────────────────────────────────────

async def generate_questionnaires(
    rfq_subject: str,
    scope_of_work: str,
    line_items: list[dict],
) -> dict:
    """
    Generate a technical and commercial vendor questionnaire
    tailored to the supplied RFQ metadata.
    Returns: {"technical": [...], "commercial": [...]}
    """
    items_text = "\n".join(
        f"  {item['id']}. {item['name']}: {item.get('description', '')}"
        for item in line_items
    )
    system = (
        "You are a senior procurement specialist. "
        "Return ONLY valid JSON — no markdown, no commentary."
    )
    user = f"""Create two vendor questionnaires for this RFQ.

RFQ SUBJECT: {rfq_subject}

LINE ITEMS:
{items_text}

SCOPE SUMMARY: {scope_of_work[:1000]}

OUTPUT FORMAT (JSON only):
{{
  "technical": [
    {{"id": "T1", "question": "...", "type": "Open text | File upload | Yes/No | Matrix", "rationale": "..."}}
  ],
  "commercial": [
    {{"id": "C1", "question": "...", "type": "...", "rationale": "..."}}
  ]
}}

Rules:
- Generate exactly 8 technical questions (capability, compliance, team, process, kids-advertising experience)
- Generate exactly 6 commercial questions (pricing structure, payment, assumptions, validity, media spend separation)
- Technical questions must probe CARU / COPPA / BCAP compliance specifically
- Commercial questions must prevent hidden costs and open-ended fees
"""
    raw = await _call_gemini(system, user, max_tokens=1800)
    return _parse_json(raw)


async def extract_vendor_data(
    vendors: list[dict],
    line_items: list[dict],
) -> dict:
    """
    Read messy multi-format vendor documents and return normalised
    line-item pricing for all vendors.

    Currency normalisation: 1 GBP = 1.26 USD, 1 EUR = 1.08 USD.

    Returns: {"vendors": [ExtractedVendor-shaped dicts, ...]}
    """
    items_text = "\n".join(f"  {i['id']}. {i['name']}" for i in line_items)
    vendors_text = "\n\n".join(
        f"=== {v['vendor_name']} ({v['file_type']}) ===\n{v['raw_content']}"
        for v in vendors
    )
    system = (
        "You are a procurement data extraction specialist. "
        "Return ONLY valid JSON. "
        "Normalise all currencies to USD (1 GBP = 1.26 USD, 1 EUR = 1.08 USD). "
        "If a price is genuinely absent return null for amount."
    )
    user = f"""Extract and normalise vendor pricing from the documents below.

MAP ALL PRICING TO THESE LINE ITEMS (use the numeric id as the key):
{items_text}

VENDOR DOCUMENTS:
{vendors_text}

OUTPUT FORMAT (JSON only):
{{
  "vendors": [
    {{
      "name": "vendor name",
      "line_item_pricing": {{
        "1": {{"amount": 285000, "note": "explanation", "covered": true}},
        "2": {{"amount": null,   "note": "not quoted",  "covered": false}}
      }},
      "total_bid": 1259000,
      "delivery_weeks": 14,
      "payment_terms": "Net 45, 30% upfront",
      "compliance_level": "High",
      "scope_coverage": 100,
      "currency_original": "USD",
      "anomalies": ["Anomaly description ..."],
      "missing_items": ["Item name if not quoted"],
      "strengths": ["Strength 1", "Strength 2"],
      "risks": ["Risk 1", "Risk 2"]
    }}
  ]
}}

Rules:
- One entry per vendor in the order they appear above
- Fill all 8 line-item keys (1-8) for every vendor
- Flag pricing hidden in images, bundled totals, or currency conflicts as anomalies
- scope_coverage is an integer 0-100 representing % of line items with a real price
"""
    raw = await _call_gemini(system, user, max_tokens=4000)
    return _parse_json(raw)


async def run_technical_analysis(vendors: list[dict]) -> dict:
    """
    Score vendor capabilities, compliance evidence, and scope gaps.

    Returns: TechnicalAnalysis-shaped dict
    """
    vendor_summary = "\n".join(
        f"  {v['name']}: "
        f"scope={v.get('scope_coverage')}%, "
        f"compliance={v.get('compliance_level')}, "
        f"delivery={v.get('delivery_weeks')} wks, "
        f"strengths={v.get('strengths')}, "
        f"risks={v.get('risks')}, "
        f"missing={v.get('missing_items')}"
        for v in vendors
    )
    system = (
        "You are a senior procurement analyst. "
        "Return ONLY valid JSON."
    )
    user = f"""Run a technical analysis of these vendor responses for a kids health drink global marketing launch.

VENDOR SUMMARY:
{vendor_summary}

OUTPUT FORMAT (JSON only):
{{
  "requirements_met": [
    {{
      "vendor": "Vendor Name",
      "meets_all": true,
      "gaps": [],
      "highlights": ["Full scope", "ISO certified child safety"]
    }}
  ],
  "compliance_scores": [
    {{
      "vendor": "Vendor Name",
      "score": 88,
      "evidence": "Evidence text from document",
      "certifications": ["CARU", "COPPA"]
    }}
  ],
  "key_differentiators": "Paragraph describing what sets vendors apart.",
  "missing_response_summary": "Paragraph summarising what is missing or incomplete."
}}

Rules:
- compliance score is 0-100; weight certifications (CARU, COPPA, BCAP, ASA, ISO) heavily
- meets_all is false if ANY of the 8 line items is not covered or if compliance evidence is absent
- Key differentiators must be grounded in the data provided — no speculation
"""
    raw = await _call_gemini(system, user, max_tokens=2000)
    return _parse_json(raw)


async def run_commercial_analysis(
    vendors: list[dict],
    line_items: list[dict],
) -> dict:
    """
    Cross-vendor cost comparison, anomaly detection, and value-for-money ranking.

    Returns: CommercialAnalysis-shaped dict
    """
    vendor_data = [
        {
            "name": v["name"],
            "total_bid": v.get("total_bid"),
            "scope_coverage": v.get("scope_coverage"),
            "delivery_weeks": v.get("delivery_weeks"),
            "currency_original": v.get("currency_original"),
            "line_item_pricing": v.get("line_item_pricing", {}),
            "anomalies": v.get("anomalies", []),
            "payment_terms": v.get("payment_terms", ""),
        }
        for v in vendors
    ]
    item_names = {str(i["id"]): i["name"] for i in line_items}
    system = (
        "You are a commercial procurement analyst. "
        "Return ONLY valid JSON."
    )
    user = f"""Perform a cross-vendor commercial comparison.

VENDOR BIDS:
{json.dumps(vendor_data, indent=2)}

LINE ITEM NAMES (id → name):
{json.dumps(item_names, indent=2)}

OUTPUT FORMAT (JSON only):
{{
  "line_item_comparison": [
    {{
      "item": "Strategy & Creative Development",
      "item_id": 1,
      "vendors": {{
        "Vendor A": 285000,
        "Vendor B": null
      }}
    }}
  ],
  "anomalies": [
    {{
      "type": "too_high | too_low | missing | currency_risk | open_ended",
      "vendor": "Vendor Name",
      "item": "Line item name or Total",
      "detail": "Explanation of why this is flagged"
    }}
  ],
  "cost_insights": "Paragraph summarising key cost findings, hidden cost risks, and comparable ranges.",
  "value_for_money_ranking": [
    {{"rank": 1, "vendor": "Vendor Name", "rationale": "..."}}
  ]
}}

Rules:
- line_item_comparison must have one entry per line item (all 8)
- value is the USD amount or null if not quoted
- Flag: prices >40% above average (too_high), prices suspiciously low (too_low), missing workstreams (missing), currency conflicts (currency_risk), percentage-only pricing (open_ended)
- value_for_money_ranking covers ALL vendors (rank all {len(vendors)})
- Do NOT rank on cost alone — scope coverage and compliance matter more for a kids brand
"""
    raw = await _call_gemini(system, user, max_tokens=2500)
    return _parse_json(raw)


async def generate_award_recommendation(vendors: list[dict]) -> dict:
    """
    Produce 3 award scenarios (best value, lowest cost, split award)
    and identify the recommended winner.

    Returns: AwardRecommendation-shaped dict
    """
    vendor_summary = "\n".join(
        f"  {v['name']}: "
        f"total_bid=${v.get('total_bid', '?')}, "
        f"scope={v.get('scope_coverage')}%, "
        f"compliance={v.get('compliance_level')}, "
        f"delivery={v.get('delivery_weeks')} wks, "
        f"payment='{v.get('payment_terms', '')}', "
        f"strengths={v.get('strengths')}, "
        f"risks={v.get('risks')}"
        for v in vendors
    )
    system = (
        "You are a senior procurement strategist advising on a kids health drink global launch. "
        "Return ONLY valid JSON. "
        "NEVER recommend based on cost alone — compliance and full scope coverage are paramount."
    )
    user = f"""Generate a structured award recommendation.

VENDOR DATA:
{vendor_summary}

SCORING WEIGHTS:
  compliance = 30 pts   (child advertising regulations, CARU/COPPA/BCAP)
  scope      = 25 pts   (% of 8 line items fully covered)
  cost       = 20 pts   (value vs market and vs peers)
  timeline   = 15 pts   (delivery speed vs award date of June 2, 2026)
  risk       = 10 pts   (commercial, operational, regulatory risk)
  TOTAL      = 100 pts

OUTPUT FORMAT (JSON only):
{{
  "scenarios": [
    {{
      "title": "Best Value Full Award",
      "subtitle": "Single vendor, optimised for overall value",
      "primary_vendor": "...",
      "secondary_vendor": null,
      "scoring": {{
        "compliance": 27,
        "scope": 25,
        "cost": 15,
        "timeline": 13,
        "risk": 8,
        "total": 88
      }},
      "recommendation": "Detailed recommendation paragraph.",
      "tradeoffs": "What the buyer gives up or should watch.",
      "confidence": "High",
      "risk_level": "Low"
    }},
    {{
      "title": "Lowest Cost Award",
      "subtitle": "Optimise for budget — accept trade-offs",
      ...
    }},
    {{
      "title": "Split Award",
      "subtitle": "Best-in-class per workstream",
      "primary_vendor": "...",
      "secondary_vendor": "...",
      ...
    }}
  ],
  "overall_recommendation_summary": "Executive summary paragraph for the recommended scenario.",
  "winner_name": "Recommended vendor name",
  "winner_scenario": 0,
  "key_rationale": "3-4 sentence rationale grounded in data.",
  "tradeoffs": "What the buyer must negotiate or monitor post-award.",
  "confidence_statement": "One sentence stating confidence level and primary reason."
}}

Rules:
- Exactly 3 scenarios in the order: best-value, lowest-cost, split
- winner_scenario is 0, 1, or 2 (index into scenarios array)
- risk_level must be one of: Low, Medium, High
- Scoring totals must be the arithmetic sum of the five components
"""
    raw = await _call_gemini(system, user, max_tokens=3000)
    return _parse_json(raw)
