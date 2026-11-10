"""Internal, fixed-source provenance; no caller-controlled paths or settings."""
import hashlib
from importlib.metadata import version
from pathlib import Path

from django.conf import settings

from .contracts import SCHEMA_VERSION, json_bytes

ROOT = Path(__file__).resolve().parents[2]


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def engine_fingerprint():
    sha = hashlib.sha256()
    # These repository-owned roots are fixed, never taken from tool arguments.
    for directory in ("astrology", "charts", "chat"):
        paths = sorted((ROOT / directory).rglob("*.py"))
        if directory == "astrology":
            paths += sorted((ROOT / directory / "rules").glob("*.yaml"))
        for path in paths:
            if path.name.startswith("test") or "migrations" in path.parts:
                continue
            sha.update(str(path.relative_to(ROOT)).replace("\\", "/").encode())
            sha.update(path.read_bytes())
    return digest({
        "source_sha256": sha.hexdigest(), "schema": SCHEMA_VERSION,
        "time_zone": settings.TIME_ZONE, "use_tz": settings.USE_TZ,
        "libraries": {name: version(name) for name in ("Django", "pyswisseph", "PyYAML")},
        "calculation": "legacy_Lahiri_true_node_whole_sign_noon_UTC",
    })


def chart_fingerprint(chart):
    return digest({
        "data": chart.chart_data, "owner": chart.user_id,
        "birth_date": chart.birth_date.isoformat(), "birth_time": chart.birth_time.isoformat(),
        "latitude": str(chart.latitude), "longitude": str(chart.longitude), "timezone": chart.timezone,
        "gender": chart.gender, "marital_status": chart.marital_status,
    })
