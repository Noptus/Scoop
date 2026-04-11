"""
Scoop Digest Pipeline

Three-pass approach:
  1. Deep research on the seller (product, buyers, triggers, deal killers, urgency drivers).
  2. For each target account, run 8 parallel queries: people moves, business initiatives,
     hiring velocity, partnerships, financial events, risk signals, competitive moves,
     regulatory/compliance.
  3. Rank by urgency and impact, deduplicate, return top signals.

At $3/1000 Perplexity queries, thoroughness is cheap. Bad intel is expensive.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

import httpx

from exceptions import APIError, ConfigError

logger = logging.getLogger(__name__)

PPLX_API_URL = "https://api.perplexity.ai/chat/completions"
PPLX_MODEL = "sonar-pro"

SIGNAL_CATEGORIES: dict[str, dict[str, str]] = {
    # People
    "leadership_change": {"tag": "People Move", "color": "red"},
    # Initiatives
    "tech_initiative": {"tag": "Tech Initiative", "color": "blue"},
    "platform_change": {"tag": "Platform Change", "color": "blue"},
    "digital_transformation": {"tag": "Transformation", "color": "blue"},
    "strategic": {"tag": "Strategic", "color": "blue"},
    # Growth
    "hiring": {"tag": "Hiring Signal", "color": "green"},
    "partnership": {"tag": "Partnership", "color": "green"},
    "expansion": {"tag": "Expansion", "color": "green"},
    "funding": {"tag": "Funding", "color": "green"},
    # Financial
    "financial_event": {"tag": "Financial", "color": "green"},
    "earnings_language": {"tag": "Earnings", "color": "green"},
    # Risk
    "risk_layoffs": {"tag": "Risk: Layoffs", "color": "red"},
    "risk_reorg": {"tag": "Risk: Reorg", "color": "red"},
    "risk_churn": {"tag": "Risk: Churn", "color": "red"},
    "restructuring": {"tag": "Restructuring", "color": "red"},
    # Competitive
    "competitive": {"tag": "Competitive", "color": "amber"},
    "competitor_win": {"tag": "Competitor", "color": "amber"},
    "competitor_launch": {"tag": "Competitor", "color": "amber"},
    "acquisition": {"tag": "M&A", "color": "amber"},
    # Regulatory
    "regulatory": {"tag": "Regulation", "color": "amber"},
    "regulation": {"tag": "Regulation", "color": "amber"},
    "compliance_deadline": {"tag": "Compliance", "color": "red"},
}

ALL_TAGS = ", ".join(SIGNAL_CATEGORIES.keys())

_SELLER_CONTEXT_REQUIRED_KEYS = frozenset({
    "company_summary",
    "industry",
    "buyer_personas",
    "use_cases",
    "buying_triggers",
    "competitors",
    "keywords",
    "product_category",
})


# ── Perplexity helpers ───────────────────────

async def _pplx_query(system: str, prompt: str, max_tokens: int = 700) -> dict:
    api_key = os.getenv("PPLX_KEY")
    if not api_key:
        raise ConfigError("PPLX_KEY not set")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                PPLX_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": PPLX_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise APIError(f"Perplexity API returned {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise APIError(f"Perplexity API request failed: {exc}") from exc
    return resp.json()


def _parse_json(content: str) -> dict | list:
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(content)


def _validate_seller_context(ctx: dict) -> dict:
    """Ensure seller context contains the expected keys, filling defaults for any missing."""
    for key in _SELLER_CONTEXT_REQUIRED_KEYS:
        if key not in ctx or not isinstance(ctx[key], str) or not ctx[key].strip():
            logger.warning("Seller context missing or empty field: %s", key)
            ctx.setdefault(key, "")
    return ctx


# ── Pass 1: Deep seller research ─────────────

async def research_seller(product: str) -> dict:
    data = await _pplx_query(
        system="You are a B2B sales intelligence analyst. Return only valid JSON.",
        prompt=f"""Research "{product}" thoroughly as a B2B product/company.
I need to understand this deeply for sales intelligence purposes.

Respond in this exact JSON format (no markdown, no code fences):
{{
    "company_summary": "<2-3 sentences on what this company/product does>",
    "industry": "<the seller's primary industry>",
    "buyer_personas": "<comma-separated list of 5-8 job titles who evaluate and buy this product>",
    "use_cases": "<the top 5 problems this product solves, comma-separated>",
    "buying_triggers": "<7-10 specific events that would create a sales opportunity, comma-separated>",
    "deal_killers": "<5-7 events or situations that would KILL a deal or indicate the prospect is NOT a buyer. e.g., 'just signed a 3-year contract with competitor X', 'hiring freeze in department', 'recently failed implementation of similar tool'>",
    "urgency_drivers": "<What creates URGENCY to buy NOW vs. next quarter? Compliance deadlines, fiscal year timing, competitive pressure, board mandates, etc.>",
    "competitors": "<top 3-5 competitors, comma-separated>",
    "keywords": "<10 keywords and phrases a prospect would use when they need this product, comma-separated>",
    "product_category": "<one short phrase describing the category, e.g. 'cloud ERP', 'observability platform', 'commercial insurance'>",
    "industries_served": "<top 5 industries where this product is most commonly sold, comma-separated>"
}}""",
        max_tokens=700,
    )
    content = data["choices"][0]["message"]["content"]
    parsed: dict = _parse_json(content)
    return _validate_seller_context(parsed)


# ── Pass 2: 8 query types per company ────────

QUERY_TYPES: list[dict[str, str]] = [
    {
        "name": "people_moves",
        "prompt": """Find role changes, appointments, departures, or promotions
at {company} in the LAST 7 DAYS ONLY. Focus on people in roles relevant to buying {product_category}:
- Roles like: {buyer_personas}
- Any leadership change at the VP, Director, or Head-of level in departments that would buy {product_category}
- New hires into senior roles in relevant departments

Include the person's NAME, their new TITLE, and where they came from if known.
Skip roles that have no connection to buying {product_category}.
IMPORTANT: Only include events from the last 7 days. Skip anything older.
If no relevant people moves found, say so clearly.""",
    },
    {
        "name": "business_initiatives",
        "prompt": """Find initiatives, programs, or strategic projects at {company}
in the LAST 14 DAYS ONLY that would be relevant to someone selling {product_category}.

Look for:
- Programs related to: {use_cases}
- Budget increases or new investment announcements in relevant areas
- RFPs, tenders, or vendor selection processes
- Transformation programs, modernization efforts, or expansion plans
- Anything matching these buying triggers: {buying_triggers}

Include specific details: project scope, budget if mentioned, timeline.
IMPORTANT: Only include events from the last 14 days. Skip anything older.
If nothing found, say so clearly.""",
    },
    {
        "name": "hiring_velocity",
        "prompt": """Analyze the HIRING PATTERNS at {company} over the LAST 14 DAYS. Not just individual job postings, but the VOLUME and VELOCITY of hiring.
Look for:
- Total number of open roles relevant to buying {product_category}
- CLUSTERS of similar roles (e.g., "12 data engineers posted in 2 weeks" = building something big)
- New team formation signals (e.g., first-ever "Head of Platform Engineering" = new department)
- Seniority patterns (hiring a VP before ICs = early stage; hiring 20 ICs = scaling)
- Keywords in job descriptions that match: {keywords}
- Contractor/consultant postings (often precede major projects)

The insight we need is: WHAT IS {company} BUILDING and HOW FAST?

A single job posting is noise. A pattern of 10+ related postings in the same month is a signal.
Also note: hiring freezes or sudden job posting removals are RISK signals.
IMPORTANT: Only include hiring activity from the last 14 days. Skip anything older.
If nothing found beyond normal hiring activity, say so clearly.""",
    },
    {
        "name": "partnerships_vendors",
        "prompt": """Find partnerships, vendor selections, or strategic relationships
at {company} in the LAST 14 DAYS ONLY relevant to someone selling {product_category}. Look for:
- New vendor announcements in areas where {product_category} competes
- Strategic partnerships that change how {company} operates
- Competitor deployments (competitors include: {competitors})
- Industry events or conferences where {company} presented as a buyer

Include specific names and details.
IMPORTANT: Only include events from the last 14 days. Skip anything older.
If nothing relevant found, say so clearly.""",
    },
    {
        "name": "financial_events",
        "prompt": """Find financial events and earnings information for {company} in the LAST 14 DAYS ONLY.
Look for:
- Funding rounds (any stage: seed, Series A-F, PE, debt)
- Revenue growth or decline announcements
- Earnings call highlights. QUOTE specific language from executives about spending priorities, growth plans, or cost cuts
- Budget allocation announcements ("investing in X", "doubling down on Y")
- IPO filings or secondary offerings
- Analyst upgrades/downgrades with reasoning

CRITICAL: If you find earnings call language, QUOTE THE EXACT WORDS.
A CEO saying "we are investing heavily in sales enablement" is 100x more
valuable than "company had good earnings."
IMPORTANT: Only include events from the last 14 days. Skip anything older.
If nothing found, say so clearly.""",
    },
    {
        "name": "risk_signals",
        "prompt": """Find NEGATIVE or WARNING signals at {company} in the LAST 14 DAYS ONLY.
This is about protecting existing deals and spotting churn risk.
Look for:
- Layoffs, hiring freezes, or headcount reductions
- Restructuring, department mergers, or org chart changes
- Key executive departures (especially in the department that buys {product_category})
- Budget cuts or "cost optimization" language in public statements
- Office closures or lease reductions
- Declining stock price with analyst commentary on WHY
- Customer complaints about THEIR product (a company in trouble buys less)

Be specific about the SCOPE of the negative signal. "Laid off 50 in marketing"
is very different from "laid off 500 company-wide."

IMPORTANT: Only include events from the last 14 days. Skip anything older.
If nothing concerning found, explicitly state "No risk signals detected" --
that itself is useful information for a sales rep.""",
    },
    {
        "name": "competitive_moves",
        "prompt": """Find competitive intelligence from the LAST 14 DAYS ONLY relevant to selling {product_category} to {company}.
Look for:
- Has {company} recently adopted, evaluated, or mentioned any of these competitors: {competitors}?
- Job postings at {company} that mention competitor product names or related technologies
- Conference talks or blog posts by {company} employees about tools/platforms they use
- Case studies or testimonials where {company} is featured as a customer of a competitor
- RFP or vendor selection processes {company} is running
- Any public statements about switching, replacing, or consolidating vendors in the {product_category} space

IMPORTANT: Also look for signals that {company} is UNHAPPY with their current
solution. Migration projects, "replacing legacy systems", hiring for skills
associated with switching platforms -- all gold.
IMPORTANT: Only include events from the last 14 days. Skip anything older.
If nothing found, say so clearly.""",
    },
    {
        "name": "regulatory_compliance",
        "prompt": """Find regulatory, compliance, or industry mandate changes from the LAST 14 DAYS ONLY that would affect {company} and create urgency to buy {product_category}.
Look for:
- New regulations in {company}'s industry
- Compliance deadlines approaching in the next 6 months
- Fines, penalties, or enforcement actions against {company} or their PEERS in the same industry
- Industry standards updates (ISO, SOC2, GDPR, AI Act, etc.)
- Government contract requirements that mandate specific capabilities
- ESG/sustainability reporting requirements affecting their operations
- Insurance or audit requirements driving changes

For each regulation found, note the DEADLINE (when must they comply?)
and the PENALTY for non-compliance.
IMPORTANT: Only include events from the last 14 days. Skip anything older.
If nothing relevant found, say so clearly.""",
    },
]


# ── Enhanced signal output schema ────────────

SIGNAL_OUTPUT_INSTRUCTION = """Based on what you found, return a JSON array of signals (0 to 3 items).
Each signal must contain concrete, verified information.

Return this exact format (no markdown, no code fences):
[
  {{
    "company": "{company}",
    "tag": "<one of: {all_tags}>",
    "headline": "<one specific sentence with names, dates, and concrete details>",
    "date": "<the date of the event if known, e.g. 'Apr 7' or 'Apr 3, 2026'. Leave empty if unknown>",
    "why": "<one sentence connecting this to selling {product}, referencing which buyer persona would care and why this changes the deal dynamic>",
    "urgency": "<one of: IMMEDIATE, THIS_WEEK, THIS_MONTH, THIS_QUARTER>",
    "window": "<Why this timing matters. e.g., 'New CTO has 90 days to audit the stack.' or 'Compliance deadline is June 30.'>",
    "opening_line": "<A natural, non-salesy sentence the rep can use to start a conversation referencing this signal. e.g., 'I saw [name] just joined as CTO. Congrats on the hire.'>",
    "risk_or_opportunity": "<one of: opportunity, risk, both>",
    "suggested_action": "<Specific next step. Include: who to contact (title), what channel (email/LinkedIn/phone), and what to say.>",
    "confidence": "<HIGH if based on named sources and dates, MEDIUM if inferred from patterns, LOW if speculative>"
  }}
]

RULES:
- Every signal MUST have a specific name, date, or number. No vague statements.
- The "opening_line" must sound like a human, not a salesperson. No jargon.
- The "window" must explain WHY timing matters and WHEN it closes.
- If a signal is a RISK (layoffs, reorg, competitor adoption), mark it clearly.
- Confidence HIGH = you found a named source. MEDIUM = pattern inference. LOW = speculation.
- Return an empty array [] if nothing concrete was found. Never invent signals.
- NEVER use em dashes in any field. Use periods or commas instead."""


async def _run_company_query(
    query_type: dict[str, str],
    company: str,
    product: str,
    seller_context: dict,
) -> list[dict]:
    """Run one query type for one company, return 0-3 signal items."""
    ctx = {
        "company": company,
        "product": product,
        "product_category": seller_context.get("product_category", product),
        "keywords": seller_context.get("keywords", ""),
        "competitors": seller_context.get("competitors", ""),
        "buyer_personas": seller_context.get("buyer_personas", "decision-makers"),
        "use_cases": seller_context.get("use_cases", ""),
        "buying_triggers": seller_context.get("buying_triggers", ""),
    }

    prompt = query_type["prompt"].format(**ctx)

    output_instruction = SIGNAL_OUTPUT_INSTRUCTION.format(
        company=company,
        product=product,
        all_tags=ALL_TAGS,
    )

    data = await _pplx_query(
        system=f"""You are a B2B sales intelligence analyst.
The salesperson sells: {product} ({ctx['product_category']})
Their product solves: {ctx['use_cases']}
Their buyers are: {ctx['buyer_personas']}

Extract concrete, specific facts. Include names, titles, dates, and numbers.
Do not speculate or invent information. If you can't find anything, say so.
Return only valid JSON.""",

        prompt=f"""{prompt}

{output_instruction}""",
        max_tokens=700,
    )

    content = data["choices"][0]["message"]["content"]
    try:
        items = _parse_json(content)
    except (json.JSONDecodeError, ValueError):
        return []

    if not isinstance(items, list):
        items = [items] if isinstance(items, dict) and items.get("headline") else []

    sources: list = data.get("citations", [])
    for item in items:
        item["sources"] = sources

    return [i for i in items if i.get("headline")]


async def _research_company(
    company: str,
    product: str,
    seller_context: dict,
) -> list[dict]:
    """Run all 8 query types for a single company in parallel."""
    tasks = [
        _run_company_query(qt, company, product, seller_context)
        for qt in QUERY_TYPES
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items: list[dict] = []
    for query_type, result in zip(QUERY_TYPES, results):
        if isinstance(result, Exception):
            logger.error("    [%s] Error: %s", query_type["name"], result)
            continue
        if result:
            logger.info("    [%s] %d signal(s)", query_type["name"], len(result))
            all_items.extend(result)
        else:
            logger.info("    [%s] nothing found", query_type["name"])

    return all_items


# ── Pass 3: Rank by urgency and impact ───────

async def _rank_signals(
    items: list[dict],
    product: str,
    seller_context: dict,
) -> list[dict]:
    if len(items) <= 5:
        return items

    buyer_personas = seller_context.get("buyer_personas", "decision-makers")
    signals_json = json.dumps(
        [
            {
                "i": i,
                "company": item["company"],
                "tag": item["tag"],
                "headline": item["headline"],
                "urgency": item.get("urgency", "THIS_QUARTER"),
                "risk_or_opportunity": item.get("risk_or_opportunity", "opportunity"),
                "confidence": item.get("confidence", "MEDIUM"),
            }
            for i, item in enumerate(items)
        ],
        indent=2,
    )

    data = await _pplx_query(
        system="You are a B2B sales prioritization expert. Return only valid JSON.",
        prompt=f"""You are ranking sales intelligence signals for a salesperson who sells {product}.
Their buyers are: {buyer_personas}

CRITICAL FILTER — remove signals that are:
- Generic industry news with NO connection to buying {product} (e.g. "Apple released a new iPhone" is useless to someone selling enterprise middleware)
- Older than 2 weeks
- Vague or unverifiable (no names, dates, or sources)
- About the target company's consumer products/services unless it directly creates a buying trigger for {product}

Only keep signals that create a CONCRETE sales opportunity or RISK to an existing deal.

{signals_json}

Ranking criteria (in order):
1. RISK signals (protecting existing revenue) always rank above opportunities
2. IMMEDIATE urgency ranks above THIS_WEEK, etc.
3. Signals with HIGH confidence rank above MEDIUM and LOW
4. Signals that affect the PRIMARY buyer persona rank above secondary
5. Signals where the "window" is closing soonest rank highest

Return a JSON array of the indices (the "i" field) of the top 10 signals, in priority order:
[0, 3, 7, ...]""",
        max_tokens=200,
    )

    content = data["choices"][0]["message"]["content"]
    try:
        indices = _parse_json(content)
        if isinstance(indices, list):
            ranked: list[dict] = []
            seen: set[str] = set()
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(items):
                    key = items[idx]["headline"][:60]
                    if key not in seen:
                        seen.add(key)
                        ranked.append(items[idx])
            return ranked[:10] if ranked else items[:10]
    except (json.JSONDecodeError, ValueError):
        pass

    return items[:10]


# ── Dedup via LiteLLM ───────────────────────

LITELLM_URL = os.getenv("LITELLM_URL", "")
LITELLM_KEY = os.getenv("LITELLM_KEY", "")
LITELLM_MODEL = os.getenv("LITELLM_MODEL", "azure-gpt-4o-mini")


async def _dedup_signals(
    items: list[dict],
    user_id: str,
) -> list[dict]:
    """Remove signals that cover the same story as last week's digest."""
    if not LITELLM_URL or not LITELLM_KEY or not items:
        return items

    from db import get_last_digest

    previous = await get_last_digest(user_id)
    if not previous:
        return items

    prev_headlines = [
        f"{p.get('company', '')}: {p.get('headline', '')}" for p in previous
    ]
    new_headlines = [
        {"i": i, "company": item["company"], "headline": item["headline"]}
        for i, item in enumerate(items)
    ]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{LITELLM_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {LITELLM_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": LITELLM_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You deduplicate news signals. Return only valid JSON.",
                        },
                        {
                            "role": "user",
                            "content": f"""PREVIOUS WEEK's headlines (already sent):
{json.dumps(prev_headlines, indent=2)}

THIS WEEK's new signals:
{json.dumps(new_headlines, indent=2)}

Remove any new signal that covers the SAME story or event as a previous headline.
Same event reported by different sources = duplicate. Remove it.
A follow-up development on the same story = NOT a duplicate. Keep it.

Return a JSON array of the "i" indices to KEEP:
[0, 2, 5, ...]""",
                        },
                    ],
                    "max_tokens": 200,
                    "temperature": 0,
                },
            )
            resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"]
        keep_indices = _parse_json(content)
        if isinstance(keep_indices, list):
            kept = [items[i] for i in keep_indices if isinstance(i, int) and 0 <= i < len(items)]
            if kept:
                logger.info("  [dedup] %d → %d signals (removed %d duplicates)", len(items), len(kept), len(items) - len(kept))
                return kept
    except Exception:
        logger.warning("  [dedup] LiteLLM call failed, skipping dedup", exc_info=True)

    return items


# ── Public API ───────────────────────────────

async def generate_digest_preview(
    companies: list[str],
    product: str,
    user_id: str | None = None,
) -> list[dict]:
    """Generate digest items with deep multi-query research."""
    # Pass 1: understand the seller
    logger.info("  [seller research]")
    seller_context = await research_seller(product)
    logger.info("    Summary: %s", seller_context.get("company_summary", "")[:120])
    logger.info("    Category: %s", seller_context.get("product_category", ""))
    logger.info("    Buyers: %s", seller_context.get("buyer_personas", "")[:120])
    logger.info("    Triggers: %s", seller_context.get("buying_triggers", "")[:120])
    logger.info("    Deal killers: %s", seller_context.get("deal_killers", "")[:120])
    logger.info("    Urgency: %s", seller_context.get("urgency_drivers", "")[:120])
    logger.info("    Competitors: %s", seller_context.get("competitors", "")[:120])

    # Pass 2: 8 queries per company in parallel
    all_items: list[dict] = []
    for company in companies:
        logger.info("  [%s] (8 queries)", company)
        company_items = await _research_company(company, product, seller_context)
        for item in company_items:
            tag_key = item.get("tag", "strategic")
            category = SIGNAL_CATEGORIES.get(tag_key, SIGNAL_CATEGORIES["strategic"])
            item["tag"] = category["tag"]
            item["tag_color"] = category["color"]
        all_items.extend(company_items)

    if not all_items:
        logger.info("  No signals found across any account.")
        return []

    logger.info("  [ranking] %d raw signals", len(all_items))

    # Pass 3: rank and filter by relevance
    ranked = await _rank_signals(all_items, product, seller_context)
    logger.info("  [ranked] %d signals after ranking", len(ranked))

    # Pass 4: dedup against last week's digest
    if user_id:
        ranked = await _dedup_signals(ranked, user_id)

    logger.info("  [done] %d final signals", len(ranked))
    return ranked


async def generate_digest_for_user(user: dict) -> list[dict]:
    """Generate a full digest for a single user."""
    companies = [c["name"] for c in user.get("companies", [])]
    if not companies:
        return []
    product = user.get("product", "our product")
    return await generate_digest_preview(companies, product, user_id=user.get("id"))
