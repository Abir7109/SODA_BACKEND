import csv
import io
import json
import logging
import os
import re
import time
from typing import Optional

import requests

logger = logging.getLogger("soda.lead_finder")

PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

FIELD_MASK_BASIC = ",".join([
    "places.id", "places.displayName", "places.formattedAddress",
    "places.location", "places.rating", "places.userRatingCount",
    "places.nationalPhoneNumber", "places.websiteUri",
    "places.businessStatus", "places.types",
    "nextPageToken",
])

FIELD_MASK_DETAIL = ",".join([
    "id", "displayName", "formattedAddress", "location",
    "rating", "userRatingCount", "nationalPhoneNumber",
    "websiteUri", "businessStatus", "types",
    "regularOpeningHours", "priceLevel",
])

_EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')


def _places_request(url: str, payload: dict) -> dict:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": PLACES_API_KEY,
        "X-Goog-FieldMask": FIELD_MASK_BASIC,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def search_businesses(query: str, location: str = "", max_results: int = 20) -> list[dict]:
    if not PLACES_API_KEY:
        return {"success": False, "error": "GOOGLE_PLACES_API_KEY not set"}
    text_query = f"{query} in {location}" if location else query
    payload = {
        "textQuery": text_query,
        "pageSize": min(max_results, 20),
        "languageCode": "en",
    }
    all_places = []
    next_token = None
    while len(all_places) < max_results:
        if next_token:
            payload["pageToken"] = next_token
        try:
            data = _places_request(TEXT_SEARCH_URL, payload)
        except requests.RequestException as e:
            logger.error(f"Places API error: {e}")
            break
        places = data.get("places", [])
        for p in places:
            all_places.append(_normalize_place(p))
        next_token = data.get("nextPageToken")
        if not next_token:
            break
        time.sleep(0.5)
    return all_places[:max_results]


def _normalize_place(p: dict) -> dict:
    return {
        "place_id": p.get("id", ""),
        "name": p.get("displayName", {}).get("text", ""),
        "address": p.get("formattedAddress", ""),
        "phone": p.get("nationalPhoneNumber", ""),
        "website": p.get("websiteUri", ""),
        "rating": p.get("rating"),
        "review_count": p.get("userRatingCount"),
        "status": p.get("businessStatus", ""),
        "types": p.get("types", []),
        "lat": p.get("location", {}).get("latitude"),
        "lng": p.get("location", {}).get("longitude"),
    }


def find_leads(query: str, location: str = "", min_rating: float = 0, max_results: int = 50) -> dict:
    raw = search_businesses(query, location, max_results)
    if isinstance(raw, dict) and not raw.get("success", True):
        return raw
    leads = []
    for b in raw:
        if min_rating and (b.get("rating") or 0) < min_rating:
            continue
        leads.append(b)
    no_site = [l for l in leads if not l.get("website")]
    return {
        "success": True,
        "query": query,
        "location": location,
        "total": len(leads),
        "without_website": len(no_site),
        "leads": leads,
        "no_website_leads": no_site,
    }


def enrich_lead(place_id: str) -> dict:
    if not PLACES_API_KEY:
        return {"success": False, "error": "GOOGLE_PLACES_API_KEY not set"}
    url = PLACE_DETAILS_URL.format(place_id=place_id)
    headers = {
        "X-Goog-Api-Key": PLACES_API_KEY,
        "X-Goog-FieldMask": FIELD_MASK_DETAIL,
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        detail = resp.json()
        return {"success": True, "detail": _normalize_place(detail)}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


def extract_emails_from_site(url: str) -> list[str]:
    try:
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        emails = _EMAIL_REGEX.findall(resp.text)
        valid = [e for e in emails if not e.endswith((".png", ".jpg", ".gif", ".svg")) and "example" not in e]
        return list(set(valid))
    except Exception:
        return []


def export_leads_csv(leads: list[dict]) -> str:
    output = io.StringIO()
    fieldnames = ["name", "phone", "address", "website", "email", "rating", "review_count", "types", "status"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for l in leads:
        row = {k: l.get(k, "") for k in fieldnames}
        if isinstance(row.get("types"), list):
            row["types"] = ", ".join(row["types"])
        writer.writerow(row)
    return output.getvalue()


def export_leads_json(leads: list[dict]) -> str:
    return json.dumps(leads, indent=2, default=str)


if __name__ == "__main__":
    result = find_leads("plumber", "Austin, TX", max_results=5)
    print(json.dumps(result, indent=2, default=str))
