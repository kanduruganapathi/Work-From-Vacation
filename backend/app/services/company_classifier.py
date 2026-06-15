"""Classify a company into a type (product / startup / mnc / service) and a tier.

Backed by curated sets of well-known global and Indian companies plus light
heuristics. Extend the sets below, or swap in a company-intelligence dataset,
as your coverage needs grow.

Returned values:
- ``company_type``: ``product`` | ``startup`` | ``mnc`` | ``service`` | ``other``
- ``company_tier``: ``tier1`` | ``tier2`` | ``tier3`` | ``None``
"""

from __future__ import annotations

# ── Product companies (build their own products) ────────────────────────────
_PRODUCT_TIER1 = {
    # Global elite (FAANG+ and peers)
    "google", "alphabet", "meta", "facebook", "instagram", "amazon", "aws",
    "apple", "microsoft", "netflix", "nvidia", "adobe", "salesforce", "oracle",
    "sap", "intel", "qualcomm", "cisco", "vmware", "linkedin", "paypal",
    "uber", "airbnb", "atlassian", "stripe", "spotify", "x", "twitter",
    "openai", "anthropic", "databricks", "snowflake", "tesla", "intuit",
    "servicenow", "workday", "dropbox", "pinterest", "block", "square",
    "coinbase", "palantir", "samsung", "google cloud", "meta platforms",
    "walmart", "walmart labs", "walmart global tech", "goldman sachs",
}
_PRODUCT_TIER2 = {
    # Global strong product / scale-ups
    "shopify", "gitlab", "github", "hashicorp", "datadog", "cloudflare",
    "notion", "figma", "canva", "intercom", "segment", "asana", "miro",
    "postman", "browserstack", "mongodb", "elastic", "confluent", "okta",
    "zendesk", "twilio", "grab", "gojek", "sea", "shopee", "doordash",
    "instacart", "robinhood", "plaid", "brex", "ramp", "vercel", "supabase",
    # Indian product unicorns / soonicorns
    "flipkart", "swiggy", "zomato", "razorpay", "freshworks", "zoho", "cred",
    "phonepe", "paytm", "meesho", "sharechat", "dream11", "dreamsports",
    "unacademy", "byjus", "byju's", "ola", "olacabs", "oyo", "nykaa",
    "policybazaar", "zerodha", "groww", "upstox", "hasura", "chargebee",
    "druva", "icertis", "innovaccer", "gupshup", "mamaearth", "urban company",
    "urbancompany", "delhivery", "zepto", "blinkit", "cult.fit", "curefit",
    "pine labs", "pinelabs", "slice", "navi", "khatabook", "vedantu",
    "physicswallah", "licious", "bigbasket", "udaan", "spinny", "cars24",
    "lenskart", "boat", "mobikwik", "acko", "digit", "postman labs",
    "rapido", "porter", "dunzo", "groww", "jupiter", "fi money", "open",
    "mindtickle", "darwinbox", "angel one", "angelone", "tata elxsi",
}

# ── IT-services multinationals (classic "MNC" service companies) ─────────────
_MNC_TIER1 = {
    "tcs", "tata consultancy services", "infosys", "wipro", "hcl", "hcltech",
    "hcl technologies", "tech mahindra", "accenture", "cognizant", "capgemini",
    "ibm", "deloitte", "dxc", "dxc technology", "pwc", "ey", "ernst & young",
    "kpmg", "atos", "ntt data", "fujitsu",
}
_MNC_TIER2 = {
    "mindtree", "mphasis", "ltimindtree", "lti", "l&t infotech", "persistent",
    "persistent systems", "birlasoft", "hexaware", "coforge", "nagarro",
    "zensar", "cybage", "sonata software", "happiest minds", "mastek",
    "newgen", "ramco systems", "kpit", "cyient", "sasken",
}

# ── Curated startups (incl. demo/sample companies for UI variety) ───────────
_STARTUPS = {
    "lumen labs", "brightside studio", "vela ai", "harbor metrics", "docflow",
    "tidal apps", "sproutly", "cadence health",
}
_SAMPLE_PRODUCT_TIER2 = {
    "northwind cloud", "solstice systems", "aurora commerce", "meridian",
}


def classify(company: str | None) -> tuple[str, str | None]:
    """Return ``(company_type, company_tier)`` for a company name."""
    if not company:
        return "other", None
    name = company.strip().lower()

    if name in _PRODUCT_TIER1:
        return "product", "tier1"
    if name in _PRODUCT_TIER2 or name in _SAMPLE_PRODUCT_TIER2:
        return "product", "tier2"
    if name in _MNC_TIER1:
        return "mnc", "tier1"
    if name in _MNC_TIER2:
        return "mnc", "tier2"
    if name in _STARTUPS:
        return "startup", "tier3"

    # Heuristics for unlisted companies.
    if any(k in name for k in ("labs", " ai", "studio", "startup")):
        return "startup", "tier3"
    if any(k in name for k in ("technologies", "consulting", "solutions", "services", "infotech")):
        return "service", "tier3"
    return "other", None
