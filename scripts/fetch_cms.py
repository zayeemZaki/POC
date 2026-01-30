"""
Fetch Local Coverage Determinations (LCDs) from the public CMS Coverage API.

API Docs: https://api.coverage.cms.gov/docs/
Endpoint:  GET /v1/data/lcd?lcdid={numeric_id}

The API requires a session token obtained by accepting the license agreement
at /v1/metadata/license-agreement. No API key is needed — the token is
returned automatically and expires in 1 hour.

Output matches the MOCK_POLICIES structure used in ingest.py:
    { "policy_id": "LCD-33722", "title": "...", "text": "..." }
"""

import re
import html
import requests

CMS_BASE = "https://api.coverage.cms.gov"
LICENSE_URL = f"{CMS_BASE}/v1/metadata/license-agreement"
LCD_URL = f"{CMS_BASE}/v1/data/lcd"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def clean_policy_id(policy_id: str) -> str:
    """
    Convert an internal policy ID to the numeric ID the CMS API expects.

    Examples:
        "LCD-33722" -> "33722"
        "L33722"    -> "33722"
        "33722"     -> "33722"
    """
    cleaned = re.sub(r"^(LCD-?|L)", "", policy_id.strip(), flags=re.IGNORECASE)
    return cleaned


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities from CMS response fields."""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse excessive whitespace but preserve paragraph breaks
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_cms_token() -> str | None:
    """
    Accept the CMS license agreement and return a Bearer token.
    The token is valid for 1 hour and requires no API key.
    """
    try:
        resp = requests.get(LICENSE_URL, headers={"Accept": "application/json"}, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        token = body["data"][0]["Token"]
        return token
    except Exception as e:
        print(f"[ERROR] Failed to obtain CMS license token: {e}")
        return None


# ------------------------------------------------------------------
# Main Fetch Function
# ------------------------------------------------------------------

def fetch_medicare_policy(policy_id: str) -> dict | None:
    """
    Fetch a Local Coverage Determination from the CMS Coverage API.

    Args:
        policy_id: Internal policy ID (e.g. "LCD-33722").

    Returns:
        A dict matching the MOCK_POLICIES structure:
            { "policy_id": str, "title": str, "text": str }
        or None on failure.
    """
    numeric_id = clean_policy_id(policy_id)
    if not numeric_id.isdigit():
        print(f"[ERROR] Invalid policy ID after cleaning: '{numeric_id}' (from '{policy_id}')")
        return None

    # Step 1: Get auth token
    token = get_cms_token()
    if not token:
        return None

    # Step 2: Fetch the LCD
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    params = {"lcdid": numeric_id}

    try:
        resp = requests.get(LCD_URL, headers=headers, params=params, timeout=30)
    except requests.RequestException as e:
        print(f"[ERROR] Network error fetching LCD {policy_id}: {e}")
        return None

    if resp.status_code == 401:
        print(f"[ERROR] Unauthorized — CMS token may have expired.")
        return None

    if resp.status_code != 200:
        print(f"[ERROR] CMS API returned HTTP {resp.status_code} for LCD {policy_id}")
        return None

    body = resp.json()
    records = body.get("data", [])

    if not records:
        print(f"[WARN] No data returned for LCD {policy_id} (numeric: {numeric_id}). "
              "The policy may be retired or not in the CMS database.")
        return None

    record = records[0]

    # Step 3: Build the policy text from the richest available fields
    title = record.get("title") or "Untitled LCD"

    sections = []
    sections.append(f"POLICY LCD-{numeric_id}: {title.upper()}")

    field_map = [
        ("indication",        "Indications / Coverage"),
        ("coding_guidelines", "Coding Guidelines"),
        ("doc_reqs",          "Documentation Requirements"),
        ("summary_of_evidence", "Summary of Evidence"),
        ("analysis_of_evidence", "Analysis of Evidence"),
        ("util_guide",        "Utilization Guidelines"),
        ("appendices",        "Appendices"),
    ]

    for field, heading in field_map:
        raw = record.get(field)
        if raw:
            cleaned = strip_html(raw)
            if cleaned:
                sections.append(f"\n{heading}:\n{cleaned}")

    text = "\n".join(sections)

    return {
        "policy_id": policy_id,
        "title": title,
        "text": text,
    }


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    import json

    test_id = "LCD-33722"
    print(f"Fetching policy: {test_id}\n")
    result = fetch_medicare_policy(test_id)

    if result:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nPolicy {test_id} was not found in the CMS API.")
        print("Trying a known active LCD (35000) as a demo...\n")
        demo = fetch_medicare_policy("LCD-35000")
        if demo:
            # Truncate text for readability
            demo_display = {**demo, "text": demo["text"][:1000] + "..."}
            print(json.dumps(demo_display, indent=2))
        else:
            print("Demo fetch also failed. Check your network connectivity.")
