"""Read-only adapters. Every calculation below delegates to legacy helpers."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from astrology.calculations.varga import SUPPORTED_VARGAS, build_varga_facts
from charts.vedic_utils import PLANET_NAMES, SIGN_NAMES, aspected_houses, house_from_sign, transit_context_for_lord
from chat.prediction_context import CATEGORY_RULES
from chat.timing_windows import _transit_segments_for_lord
from astrology.calculations import jaimini as jaimini_calc
from astrology.calculations.counted_signs import REFERENCES, CountedSignError, counted_sign, house_from_moon

from .contracts import (
    AshtakavargaData, ChartFactsData, DashaData, MAX_SAMPLES, RuleData,
    TimingData, ToolFailure, TransitData, date_range, parse_date, supported,
    AshtakavargaRequest, ChartFactsRequest, DashaRequest, RuleRequest, TimingRequest, TransitRequest,
    AspectsData, AspectsRequest, CountedSignData, CountedSignRequest, JaiminiData, JaiminiRequest,
)

CLASSICAL = ("Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa")
CATEGORIES = frozenset(CATEGORY_RULES) | {"business", "general"}


def category_spec(category):
    supported(category in CATEGORIES, "Unknown category/topic.")
    houses = [2, 7, 10, 11] if category == "business" else CATEGORY_RULES.get(category, {}).get("houses", [])
    charts = CATEGORY_RULES.get(category, {}).get("divisional_charts", ["d1"])
    return houses, charts


def get_chart_facts(request: ChartFactsRequest, chart):
    keys = list(dict.fromkeys(key.lower() for key in request.charts))
    supported(all(key in SUPPORTED_VARGAS for key in keys), "Requested chart division is not implemented.")
    facts = build_varga_facts(chart.chart_data, chart_keys=keys)
    missing = [key for key in keys if not facts["charts"].get(key, {}).get("lagna") or
               {p.get("code") for p in facts["charts"].get(key, {}).get("planets", [])} != set(PLANET_NAMES) or
               any(p.get("longitude") is None for p in chart.chart_data.get(key, {}).get("planets", []))]
    longitudes = {key: {p["code"]: p.get("longitude") for p in chart.chart_data.get(key, {}).get("planets", []) if p.get("code")}
                  for key in keys if chart.chart_data.get(key)}
    yogas = None
    warnings = [f"Missing or incomplete stored chart: {key}." for key in missing]
    if request.include_yogas:
        stored = chart.chart_data.get("yogas")
        if type(stored) is list:
            # Stored detections from charts/yogas.py; "meaning" is stored reference text, not a prediction.
            yogas = [{k: deepcopy(y.get(k)) for k in ("name", "category", "strength", "evidence", "meaning")}
                     for y in stored if type(y) is dict and type(y.get("name")) is str]
        else:
            yogas = []
            warnings.append("No stored yoga detections exist for this chart; none were calculated or inferred.")
    return ChartFactsData(chart.chart_data.get("system"), chart.chart_data.get("ayanamsa"),
                          facts["charts"], longitudes, missing,
                          {"longitude": "degrees", "degree": "DD-MM-SS formatted", "sign": "1..12", "house": "1..12"},
                          yogas), warnings, "stored natal placements; whole-sign houses", "not applicable"


def _coverage(intervals, start, end):
    """Describe coverage without rewriting the source's dates or durations."""
    cursor = start
    gaps = []
    for left, right in sorted(intervals):
        left, right = max(start, left), min(end + timedelta(days=1), right)
        if right <= left:
            continue
        if cursor < left:
            gaps.append({"start": cursor.isoformat(), "end": (left - timedelta(days=1)).isoformat()})
        cursor = max(cursor, right)
    if cursor <= end:
        gaps.append({"start": cursor.isoformat(), "end": end.isoformat()})
    return {"start": start.isoformat(), "end": end.isoformat(), "complete": not gaps, "gaps": gaps}


def get_dasha_periods(request: DashaRequest, chart):
    start, end = date_range(request.start_date, request.end_date)
    supported(request.system in ("vimshottari", "yogini", "chara"), "Supported systems: vimshottari, yogini, chara.")
    supported(request.granularity in ("mahadasha", "antardasha"), "Only Mahadasha and Antardasha schedules exist; deeper levels are unsupported.")
    source = (chart.chart_data.get("jaimini", {}).get("chara_dasha", {}) if request.system == "chara"
              else chart.chart_data.get("dashas", {}).get(request.system, {}))
    rows, intervals = [], []
    for major in source.get("periods", []):
        candidates = ([major] if request.granularity == "mahadasha" else
                      major.get("antardashas" if request.system == "vimshottari" else "subperiods", []))
        for period in candidates:
            left, right = parse_date(period["start"]), parse_date(period["end"])
            if left <= end and right > start:
                # Preserve the complete native period, not a clipped synthetic one.
                row = {k: deepcopy(v) for k, v in period.items() if k not in ("antardashas", "subperiods")}
                row["mahadasha"] = {k: deepcopy(v) for k, v in major.items() if k not in ("antardashas", "subperiods")}
                rows.append(row)
                intervals.append((left, right))
    coverage = _coverage(intervals, start, end)
    warnings = [] if coverage["complete"] else ["Stored dasha schedule does not fully cover the requested range."]
    instants = all(row.get("start_utc") and row.get("end_utc") for row in rows)
    if rows and not instants:
        warnings.append("Stored chart predates exact dasha instants; boundaries are calendar dates only. Recalculate the chart for exact instants.")
    precision = ("exact transition instants (start_utc/end_utc); start/end are calendar dates in the chart timezone"
                 if instants else "ISO calendar dates, not transition instants")
    return DashaData(request.system, request.granularity, rows, coverage, deepcopy(source.get("method", {}))), warnings, precision, "source periods [start,end); requested range inclusive; full intersecting periods retained"


def _sanitize_sav(row, chart_data):
    values = {item.get("house"): item.get("sarva") for item in chart_data.get("ashtakavarga", {}).get("rows", [])}
    house = row.get("transit_house_from_lagna")
    if house not in values or values[house] is None:
        row["sarvashtakavarga_points"] = None
        row["can_deliver_owned_or_placed_house_results"] = None


def get_transits(request: TransitRequest, chart):
    start, end = date_range(request.start_date, request.end_date)
    supported(request.resolution == "daily", "Only daily sampling at 12:00 UTC is supported; not exact ingresses or muhurta.")
    supported(request.output in ("positions", "segments"), "Output must be positions or segments.")
    supported(all(code in PLANET_NAMES for code in request.planets), "Use implemented planet codes Su/Mo/Ma/Me/Ju/Ve/Sa/Ra/Ke.")
    planets = list(dict.fromkeys(request.planets))
    if len(planets) * ((end - start).days + 1) > MAX_SAMPLES:
        raise ToolFailure("sample_limit", f"Request exceeds {MAX_SAMPLES} planet-day samples.")
    rows = []
    for planet in planets:
        if request.output == "segments":
            samples = _transit_segments_for_lord(chart.chart_data, planet, start, end, [])
        else:
            samples = []
            day = start
            while day <= end:
                instant = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).replace(hour=12)
                samples.append({**transit_context_for_lord(chart.chart_data, planet, instant), "date": day.isoformat()})
                day += timedelta(days=1)
        for row in samples:
            _sanitize_sav(row, chart.chart_data)
            # OD-33: the same transit sign counted from the natal Moon, alongside the Lagna count.
            row["transit_house_from_moon"] = house_from_moon(chart.chart_data, row.get("transit_sign_number"))
            # Transit graha drishti: the houses (from the natal Lagna) the planet aspects from its transit
            # sign, by the same Parashari offsets used for natal aspects. A count from the Moon is a
            # position, never an aspect.
            row["transit_aspected_houses_from_lagna"] = aspected_houses(planet, row.get("transit_house_from_lagna"))
        rows.extend(samples)
    missing = any(row.get("sarvashtakavarga_points") is None for row in rows)
    warnings = ["SAV is unavailable for some sampled houses; missing values are not zero."] if missing else []
    return TransitData(planets, request.output, rows,
                       {"start": start.isoformat(), "end": end.isoformat(), "complete": True, "gaps": []},
                       {"longitude": "degrees", "sign": "1..12", "house": "natal Lagna whole-sign", "SAV": "bindu"}), warnings, "daily sample at 12:00 UTC; sign segments from daily samples", "inclusive calendar dates; no exact ingress time inferred"


def get_ashtakavarga(request: AshtakavargaRequest, chart):
    supported(request.kind in ("sav", "bav", "both"), "Kind must be sav, bav or both.")
    supported(request.planet in (*CLASSICAL, "all", "Ra", "Ke"), "Unknown Ashtakavarga planet code.")
    if request.kind != "sav":
        supported(request.planet not in ("Ra", "Ke"), "Planet-specific Rahu/Ketu BAV is not implemented; request kind=sav instead.")
    for value in (request.sign, request.house):
        if value is not None and not 1 <= value <= 12:
            raise ToolFailure("invalid_arguments", "Sign and house must be integers from 1 to 12.")
    if request.sign is not None and request.house is not None and house_from_sign(chart.chart_data, request.sign) != request.house:
        raise ToolFailure("invalid_arguments", "Sign and house filters refer to different natal houses.")
    stored = chart.chart_data.get("ashtakavarga", {}).get("rows", [])
    rows = []
    planets = CLASSICAL if request.planet == "all" else (request.planet,)
    for sign in range(1, 13):
        house = house_from_sign(chart.chart_data, sign)
        if request.sign is not None and sign != request.sign or request.house is not None and house != request.house:
            continue
        source = next((item for item in stored if item.get("sign") == SIGN_NAMES[sign]), {})
        rows.append({"sign_number": sign, "sign": SIGN_NAMES[sign], "house": house,
                     "sav": source.get("sarva") if request.kind != "bav" else None,
                     "bav": {p: source.get("scores", {}).get(p) for p in planets} if request.kind != "sav" else {}})
    missing = any((request.kind != "bav" and row["sav"] is None) or any(v is None for v in row["bav"].values()) for row in rows)
    return AshtakavargaData(request.kind, request.planet, rows, "integer bindu; stored natal scores"), [
        "Some requested BAV/SAV cells are unavailable; no zero substitution."
    ] if missing else [], "stored per-rashi integer scores mapped to natal Lagna houses", "not applicable"


def evaluate_astrology_rules(request: RuleRequest, chart):
    # Reuse the legacy evaluator set and formulas without asking an LLM or
    # letting free text expand the one-day evidence scope.
    from astrology.services import prediction_service as legacy
    from astrology.structures import PredictionEvidence, QuestionContext
    day, _ = date_range(request.as_of, request.as_of)
    houses, charts = category_spec(request.category)
    if not 1 <= request.max_rules <= 100:
        raise ToolFailure("invalid_arguments", "max_rules must be 1..100.")
    facts = legacy.build_chart_facts(chart.chart_data, request.category, houses, charts)
    dashas = legacy.build_dasha_facts(chart.chart_data, request.category, houses, day)
    evidence = PredictionEvidence(
        question=QuestionContext(text="", category=request.category, time_scope={"start": request.as_of, "end": request.as_of}),
        chart_facts=facts, parashari=legacy.build_parashari_facts(chart.chart_data, request.category, houses, dashas["parashari_vimshottari"]),
        parashari_vimshottari=dashas["parashari_vimshottari"], jaimini=dashas["jaimini"], yogini=dashas["yogini"],
        varga=legacy.build_varga_assessment(facts, request.category, charts[1] if len(charts) > 1 else charts[0], charts[2] if len(charts) > 2 else None),
        transits=legacy.build_transit_facts(chart.chart_data, houses, dashas, "", request.category, day, end_date=day),
    ).to_dict()
    evidence["event_confirmation"] = dashas["event_confirmation"]
    evidence["reference_frames"] = dashas["reference_frames"]
    evidence["natural_karakas_assessment"] = legacy.build_natural_karaka_assessment(chart.chart_data, request.category)
    result = legacy.run_rule_engine(evidence, request.category)
    rules = list(result["triggered_rules"])
    rules.extend(legacy.evaluate_generic_varga_rules(facts, request.category))
    rules.extend(legacy.evaluate_d1_lagna_roles(facts, evidence, request.category))
    for evaluator in (legacy.evaluate_d2_hora_rules, legacy.evaluate_d3_drekkana_rules, legacy.evaluate_d4_chaturthamsha_rules,
                      legacy.evaluate_d7_saptamsha_rules, legacy.evaluate_d9_navamsha_rules, legacy.evaluate_d10_dashamsha_rules,
                      legacy.evaluate_d12_dwadashamsha_rules, legacy.evaluate_d16_shodashamsha_rules):
        rules.extend(evaluator(facts, request.category))
    evidence["triggered_rules"] = rules
    evidence["summary_scores"] = legacy.aggregate_scores(rules, request.category)
    evidence["evidence_ledger"] = legacy.build_evidence_ledger(evidence)
    conflicts = legacy.resolve_contradictions(evidence)
    omitted = max(0, len(rules) - request.max_rules)
    warnings = list(result["load_errors"])
    if omitted:
        warnings.append("Returned rules are capped; summary scores and conflicts use all triggered rules.")
    if evidence["transits"]["future_timing"]["dasha_transit_timeline"]["status"] != "complete":
        warnings.append("Dasha/transit/SAV evidence is incomplete; rule conclusions are preliminary.")
    for key in charts:
        if not facts["varga"]["charts"].get(key):
            warnings.append(f"Category chart {key} is unavailable.")
    return RuleData(request.category, request.as_of, rules[:request.max_rules], len(rules), omitted,
                    evidence["summary_scores"], conflicts, "heuristic outcome scores, not probabilities"), warnings, "legacy YAML plus invoked Python evaluators, explicit single-date evidence", "legacy base dasha selectors retain inclusive ends; scoped transits use half-open source periods"


def get_timing_candidates(request: TimingRequest, chart):
    from astrology.services.timing_window_service import build_timing_window_selection
    start, end = date_range(request.start_date, request.end_date)
    category_spec(request.topic)
    supported(request.topic != "general", "Timing requires a classified topic.")
    supported(request.evidence_policy == "legacy_intersections", "Only legacy_intersections is implemented.")
    if not 1 <= request.max_candidates <= 5:
        raise ToolFailure("invalid_arguments", "max_candidates must be 1..5.")
    result = build_timing_window_selection(chart.chart_data, "", request.topic, start, months=max(1, round((end-start).days/30)), end_date=end)
    candidates = ([result["best_window"]] if result["best_window"] else []) + result["secondary_windows"]
    warnings = ["Ranked hypotheses preserve legacy heuristic ranking, candidate caps and representative-period metadata."]
    # A partial chart must never be presented as full four-system confirmation.
    required = ("vimshottari", "yogini")
    missing = any(not chart.chart_data.get("dashas", {}).get(key, {}).get("periods") for key in required)
    missing = missing or not chart.chart_data.get("jaimini", {}).get("chara_dasha", {}).get("periods")
    if missing:
        warnings.append("One or more dasha systems are unavailable; candidates are preliminary.")
    if not chart.chart_data.get("ashtakavarga", {}).get("rows"):
        warnings.append("SAV is unavailable; legacy ranking may use zero for missing scores. Do not interpret this as measured zero.")
    complete = not missing and bool(chart.chart_data.get("ashtakavarga", {}).get("rows"))
    for system in ("vimshottari", "yogini", "chara"):
        source = (chart.chart_data.get("jaimini", {}).get("chara_dasha", {}) if system == "chara" else chart.chart_data.get("dashas", {}).get(system, {}))
        covered = _coverage([(parse_date(p["start"]), parse_date(p["end"])) for p in source.get("periods", [])], start, end)
        if not covered["complete"]:
            complete = False
            warnings.append(f"Stored {system} periods do not cover the requested range.")
    for key in category_spec(request.topic)[1]:
        if not chart.chart_data.get(key, {}).get("planets"):
            complete = False
            warnings.append(f"Category chart {key} is unavailable.")
    # Preserve the legacy ranking, but do not label its missing SAV fallback as
    # a measured zero in the returned transit evidence.
    for candidate in candidates:
        for row in candidate.get("transit_segments", []):
            _sanitize_sav(row, chart.chart_data)
            if row.get("sarvashtakavarga_points") is None:
                complete = False
        for trigger in candidate.get("transit_convergence", {}).get("triggers", []):
            _sanitize_sav(trigger, chart.chart_data)
            if trigger.get("sarvashtakavarga_points") is None:
                complete = False
    if not complete:
        warnings.append("Requested timing evidence is incomplete; missing scores are not measured zeros.")
    omitted = max(0, len(candidates) - request.max_candidates)
    if omitted:
        warnings.append("Additional selected candidates omitted by requested cap; legacy preselection itself is limited to eight windows.")
    return TimingData(request.topic, candidates[:request.max_candidates],
                      {"start": start.isoformat(), "end": end.isoformat(), "candidate_count": len(candidates), "complete": complete},
                      result["selection_rule"], omitted, "heuristic support scores, not probabilities"), warnings, "legacy deterministic intersection ranking and daily-noon transit evidence", "inclusive requested dates; transit source MD/AD periods [start,end)"


JAIMINI_PARTS = ("karakas", "karakamsha", "padas", "jaimini_yogas", "ak_amk")
JAIMINI_CONVENTIONS = {
    "karakas": "7 Chara karakas (Sun to Saturn; Rahu and Ketu excluded), ranked by degrees within sign",
    "padas": "All 12 house padas by direct counting (house to lord, same distance again); a result in the house itself or the 7th from it is replaced by the 10th sign from it (classical exception, applied); AL = A1, A7 = Darapada, UL = A12",
    "karakamsha": "Navamsha (D9) sign of the Atmakaraka; derived signs read in D1",
    "rasi_drishti": "Movable aspect fixed except adjacent; fixed aspect movable except adjacent; dual aspect other duals",
    "source": "astrology/calculations/jaimini.py and charts/astro_engine.py (existing; unchanged)",
}


def get_jaimini_facts(request: JaiminiRequest, chart):
    parts = list(dict.fromkeys(request.include))
    supported(all(p in JAIMINI_PARTS for p in parts), "Supported parts: " + ", ".join(JAIMINI_PARTS) + ".")
    data = chart.chart_data
    supported(any(p.get("jaimini_karaka") for p in data.get("d1", {}).get("planets", [])),
              "Stored chart has no Chara karaka assignment; nothing is calculated or inferred.")

    def pick(name, build):
        return deepcopy(build(data)) if name in parts else None

    padas = pick("padas", jaimini_calc.build_padas)
    unavailable = ["planetary_padas: deferred in code (no sufficiently explicit formula in the reviewed source)"]
    warnings = []
    if padas is not None and any(v.get("pada_sign_number") is None for v in padas.get("all_padas", {}).values()):
        warnings.append("Some house padas could not be determined from stored data; none were inferred.")
    return (JaiminiData(pick("karakas", jaimini_calc.build_karakas), pick("karakamsha", jaimini_calc.build_karakamsha),
                        padas, pick("jaimini_yogas", jaimini_calc.build_jaimini_yogas),
                        pick("ak_amk", jaimini_calc.build_ak_amk_relation), dict(JAIMINI_CONVENTIONS), unavailable),
            warnings, "stored D1/D9 placements; sign-based Jaimini counting", "not applicable")


def get_counted_sign(request: CountedSignRequest, chart):
    supported(request.reference in REFERENCES, "Reference must be one of: " + ", ".join(REFERENCES) + ".")
    supported(1 <= request.count <= 12, "Count must be 1 to 12 (inclusive counting).")
    try:
        result = counted_sign(chart.chart_data, request.reference, request.count)
    except CountedSignError as exc:
        raise ToolFailure("unsupported", "The reference point cannot be determined from stored data; nothing was inferred.", "unsupported") from exc
    conventions = {k: JAIMINI_CONVENTIONS[k] for k in ("padas", "karakamsha", "rasi_drishti")}
    return (CountedSignData(result, conventions), [], "sign counting from stored D1/D9 placements",
            "inclusive count; the reference sign is the 1st")


def get_natal_aspects(request: AspectsRequest, chart):
    from charts.vedic_utils import PLANET_ASPECTS, aspected_houses, get_planets, natal_mutual_aspects
    supported(request.house is None or 1 <= request.house <= 12, "House must be 1 to 12.")
    supported(request.planet is None or request.planet in PLANET_NAMES, "Use planet codes Su/Mo/Ma/Me/Ju/Ve/Sa/Ra/Ke.")
    planets = []
    for p in get_planets(chart.chart_data, "d1"):
        code = p.get("code")
        if code not in PLANET_NAMES or not p.get("house") or (request.planet and code != request.planet):
            continue
        houses = aspected_houses(code, p["house"])
        if request.house and request.house not in houses:
            continue
        planets.append({"code": code, "name": PLANET_NAMES[code], "natal_house": p["house"],
                        "aspect_offsets": list(PLANET_ASPECTS.get(code, [7])), "aspected_houses": houses})
    on_houses = {}
    for row in planets:
        for house in row["aspected_houses"]:
            if request.house is None or house == request.house:
                on_houses.setdefault(str(house), []).append(row["code"])
    mutual = [deepcopy(m) for m in natal_mutual_aspects(chart.chart_data)
              if not request.planet or request.planet in (m.get("planet_a"), m.get("planet_b"))]
    convention = {
        "rule": "All planets 7th; Mars 4th and 8th; Jupiter 5th and 9th; Saturn 3rd and 10th; Rahu and Ketu 7th only",
        "houses": "whole-sign houses from the natal Lagna; aspects are cast on houses (signs)",
        "not": "Jaimini rasi drishti (use get_jaimini_facts)",
        "source": "charts/vedic_utils.py (existing; unchanged)",
    }
    return (AspectsData("parashari_graha_drishti", planets, on_houses, mutual, convention), [],
            "natal D1 whole-sign aspects", "not applicable")
