"""Classify a company into a type (product / startup / mnc / service) and a tier.

This uses curated lists of well-known companies plus light heuristics. It's a
pragmatic starting point — extend the dictionaries, or back them with a real
company-intelligence dataset, as needed.

Returned values:
- ``company_type``: ``product`` | ``startup`` | ``mnc`` | ``service`` | ``other``
- ``company_tier``: ``tier1`` | ``tier2`` | ``tier3`` | ``None``
"""

from __future__ import annotations

# Product companies (build their own products), by tier.
_PRODUCT_TIER1 = {
    "google", "alphabet", "meta", "facebook", "amazon", "apple", "microsoft",
    "netflix", "nvidia", "adobe", "salesforce", "atlassian", "stripe", "uber",
    "airbnb", "linkedin", "oracle", "paypal", "spotify", "x", "twitter",
    "openai", "anthropic",
}
_PRODUCT_TIER2 = {
    "flipkart", "swiggy", "zomato", "razorpay", "freshworks", "zoho", "cred",
    "phonepe", "paytm", "postman", "browserstack", "gojek", "grab", "shopify",
    "gitlab", "hashicorp", "datadog", "twilio", "cloudflare", "notion",
    "figma", "canva", "intercom", "segment",
}

# Large IT-services multinationals (the classic "MNC" service companies).
_MNC_TIER1 = {
    "tcs", "tata consultancy services", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "ibm", "hcl", "hcltech", "tech mahindra",
    "deloitte", "dxc", "dxc technology",
}
_MNC_TIER2 = {
    "mindtree", "mphasis", "ltimindtree", "lti", "persistent", "birlasoft",
    "hexaware", "coforge", "nagarro", "zensar",
}

# Curated startups (incl. the demo/sample companies so the UI shows variety).
_STARTUPS = {
    "lumen labs", "brightside studio", "vela ai", "harbor metrics", "docflow",
    "tidal apps", "sproutly", "cadence health",
}
# Sample companies presented as product-tier for demo variety.
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
    if any(k in name for k in ("labs", "ai", "studio", "io")):
        return "startup", "tier3"
    if any(k in name for k in ("technologies", "consulting", "solutions", "services")):
        return "service", "tier3"
    return "other", None
