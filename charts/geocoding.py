import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


GEONAMES_SEARCH_URLS = [
    "https://secure.geonames.org/searchJSON",
    "http://api.geonames.org/searchJSON",
]


def search_places(query, max_rows=8):
    username = getattr(settings, "GEONAMES_USERNAME", "")
    if not username:
        return {
            "configured": False,
            "results": [],
            "error": "Set GEONAMES_USERNAME in .env to enable birthplace suggestions.",
        }

    params = {
        "name_startsWith": query,
        "maxRows": max_rows,
        "username": username,
        "featureClass": "P",
        "orderby": "relevance",
        "style": "FULL",
        "type": "json",
    }
    last_error = None
    try:
        for url in GEONAMES_SEARCH_URLS:
            request = Request(
                f"{url}?{urlencode(params)}",
                headers={"User-Agent": "AstrologyGPT/1.0 local development"},
            )
            try:
                with urlopen(request, timeout=8) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    break
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
        else:
            raise last_error or TimeoutError("GeoNames did not respond.")
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "configured": True,
            "results": [],
            "error": f"Place search is temporarily unavailable. Please try again in a moment. Details: {exc}",
        }

    status = payload.get("status")
    if status:
        return {"configured": True, "results": [], "error": status.get("message", "Place search failed.")}

    results = []
    for place in payload.get("geonames", []):
        timezone = place.get("timezone")
        if isinstance(timezone, dict):
            timezone = timezone.get("timeZoneId", "")

        admin = place.get("adminName1") or place.get("adminName2") or ""
        label_parts = [place.get("name"), admin, place.get("countryName")]
        label = ", ".join(part for part in label_parts if part)

        results.append(
            {
                "label": label,
                "name": place.get("name", ""),
                "latitude": place.get("lat", ""),
                "longitude": place.get("lng", ""),
                "timezone": timezone or "",
            }
        )

    return {"configured": True, "results": results, "error": ""}
