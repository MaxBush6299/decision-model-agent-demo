"""Deliberately limited recognition of sourced calendar and quantity claims."""

import re
from contextvars import ContextVar
from datetime import date, datetime

from .contracts import DemoError, ProseWarning
from .fixtures import WEEKDAYS, calendar_label, grounded_fixture_payload

PROSE_SINK = ContextVar("prose_sink", default=None)


DAY = re.compile(r"\b(" + "|".join(WEEKDAYS) + r")\b", re.I)
ISO_DATE = r"\d{4}-\d{2}-\d{2}"
TIME = r"\d{1,2}:\d{2}(?:\s*[-\u2013\u2014]\s*\d{1,2}:\d{2})?"
NUMBER = r"\d+(?:,\d{3})*(?:\.\d+)?"
EVENT = re.compile(
    r"cell (?:occupancy|work|end)|cell_occupancy_(?:start|end)|"
    r"factory (?:ready|readiness)|ready_at|packing(?:_end)?|"
    r"booking(?: cutoff)?|booked by|cutoffs?|pickups?|arrivals?|arriv\w*|"
    r"deliver\w*|windows?|reservation", re.I,
)

# Named patterns intentionally exclude general numbers, order IDs and objective weights.
QUANTITIES = (
    ("required_cell_minutes", rf"\b(?:requires?|needs?)\s+({NUMBER})\s+cell[- ]minutes\b"),
    ("required_cell_minutes", rf"\b(?:requires?|needs?)\s+({NUMBER})\s+minutes of cell work\b"),
    ("required_cell_minutes", rf"\brequired[_ ]cell[_ ]minutes\s*[:=]?\s*({NUMBER})\b"),
    ("available_cell_minutes", rf"\b({NUMBER})\s+(?:staffed\s+)?available\s+(?:staffed\s+)?(?:cell\s+)?minutes\b"),
    ("available_cell_minutes", rf"\bavailable_cell_minutes\s*[:=]?\s*({NUMBER})\b"),
    ("packing_minutes", rf"\b({NUMBER})[- ](?:separate[- ])?packing[- ]minutes\b"),
    ("packing_minutes", rf"\bpacking(?:_minutes|\s+(?:takes|requires|lasts|is)|(?=\s*[:=]))\s*[:=]?\s*({NUMBER})\b"),
    ("freight_total_usd", rf"\$\s*({NUMBER})\s+(?:incremental\s+)?freight\b"),
    ("freight_total_usd", rf"\bfreight(?:\s+(?:total|cost))?\s*(?:(?:is|of|totals|costs)\s+|[:=]\s*)\$\s*({NUMBER})"),
    ("available_material_units", rf"\b({NUMBER})\s+(?:(?:released|unreserved)\s+)?available\s+(?:released\s+)?material(?:s|\s+units)\b"),
    ("available_material_units", rf"\bavailable[_ ]material[_ ]units\s*[:=]?\s*({NUMBER})\b"),
    ("new_units", rf"\b(?:requires?|needs?)\s+({NUMBER})\s+(?:new\s+units|material\s+units)\b"),
    ("new_units", rf"\b({NUMBER})\s+new\s+units\s+(?:are\s+)?required\b"),
)
QUANTITIES = tuple((key, re.compile(pattern, re.I)) for key, pattern in QUANTITIES)
CELL_PAIR = re.compile(
    rf"\b({NUMBER})\s*(?:of|/)\s*({NUMBER})\s+(?:available\s+)?(?:staffed\s+)?cell[- ]minutes\b", re.I)
MATERIAL_RESIDUAL = re.compile(
    r"\bremain\w*|\bremainder\b|\bleft\b|"
    r"\bafter\b[^;.!?]*\b(?:requirements?|consum\w*|us(?:e|ing)|build|production|allocation)\b|"
    r"\b(?:post[- ]build|post[- ]consumption)\b", re.I)


def option_scope(text, position, option_ids, explicit):
    if explicit:
        return [explicit]
    matches = []
    for option in option_ids:
        pattern = re.escape(option).replace(r"\-", r"[- ]?")
        matches.extend((m.end(), option) for m in re.finditer(pattern, text[:position], re.I))
    return [max(matches)[1]] if matches else list(option_ids)


def source_figures(records, executed):
    figures, events = {}, {}
    build = records["read_build"]
    if "read_build" in executed:
        derived = grounded_fixture_payload("read_build", records, executed)["derived_evidence"]
        for option_id, values in derived["options"].items():
            for key in ("required_cell_minutes", "available_cell_minutes", "packing_minutes", "new_units"):
                figures.setdefault(key, {})[option_id] = (values[key], build.evidence_id)
            events[option_id] = {
                "cell": [(values["cell_occupancy_end"], build.evidence_id)],
                "ready": [(values["ready_at"], build.evidence_id)],
                "packing": [(values["packing_end"], build.evidence_id)],
                "reservation": [(o.production_from, build.evidence_id) for o in build.other_orders],
            }
    if "read_shipment" in executed:
        shipment = records["read_shipment"]
        derived = grounded_fixture_payload("read_shipment", records, executed)["derived_evidence"]
        for option in shipment.options:
            values = derived["options"][option.option_id]
            figures.setdefault("freight_total_usd", {})[option.option_id] = (
                values["freight_total_usd"], shipment.evidence_id)
            events.setdefault(option.option_id, {}).update({
                "booking": [(leg.booking_cutoff, shipment.evidence_id) for leg in option.legs],
                "pickup": [(leg.pickup_at, shipment.evidence_id) for leg in option.legs],
                "arrival": [(arrival, shipment.evidence_id) for arrival in values["arrivals"]],
                "delivery": [(leg.window_start, shipment.evidence_id) for leg in option.legs],
            })
    if "read_inventory" in executed:
        stock = records["read_inventory"]
        available = stock.released_material_units - stock.materials_reserved_other_orders
        figures["available_material_units"] = {
            option.option_id: (available, stock.evidence_id) for option in build.options
        }
    return figures, events


def fail(actor, field, claim, key, expected):
    sources = "; ".join(f"{value} ({source})" for value, source in expected)
    sink = PROSE_SINK.get()
    if sink is not None:
        sink.append(ProseWarning(actor, field, str(claim), f"prose.{key}", f"{key}={sources}"))
        return
    raise DemoError(f"Prose mismatch: actor={actor}; field={field}; claim={claim!r}; "
                    f"source {key}={sources}. No rewrite or repair was made.")


def event_kind(cue):
    cue = cue.lower()
    if cue.startswith("cell"):
        return "cell"
    if cue.startswith(("factory", "ready")):
        return "ready"
    if cue.startswith("packing"):
        return "packing"
    if cue.startswith(("book", "cutoff")):
        return "booking"
    if cue.startswith("pickup"):
        return "pickup"
    if cue.startswith("arriv"):
        return "arrival"
    if cue.startswith(("deliver", "window")):
        return "delivery"
    return "reservation"


def expected_event(sentence, start, events, explicit):
    cues = list(EVENT.finditer(sentence))
    preceding = [cue for cue in cues if cue.end() <= start]
    cue = preceding[-1] if preceding else None
    if cue is None or start - cue.end() > 100:
        return None, []
    kind = event_kind(cue.group())
    options = option_scope(sentence, start, events, explicit)
    expected = [item for option in options for item in events.get(option, {}).get(kind, [])
                if item[0] is not None]
    return kind, sorted(set(expected))


def check_calendar(text, actor, field, events, explicit):
    for sentence in re.split(r"[.;!?]\s*", text):
        for match in DAY.finditer(sentence):
            suffix = sentence[match.end():]
            eve = re.match(r"\s+eve\b", suffix, re.I)
            day = WEEKDAYS.index(match.group().capitalize())
            if eve:
                day = (day - 1) % 7
                suffix = suffix[eve.end():]
            dated = re.match(rf"\s*\(?({ISO_DATE})\)?", suffix)
            date_value = None
            if dated:
                try:
                    date_value = date.fromisoformat(dated.group(1))
                except ValueError:
                    fail(actor, field, match.group() + dated.group(), "valid ISO date", [])
                if date_value.weekday() != day:
                    fail(actor, field, match.group() + dated.group(), "calendar weekday",
                         [(f"{WEEKDAYS[date_value.weekday()]} {date_value}", "ISO calendar")])
            timed = re.match(rf"\s*(?:at\s+)?(?:{ISO_DATE}\s+)?{TIME}", suffix)
            prior_time = re.search(rf"{TIME}\s*$", sentence[:match.start()])
            if not (dated or timed or prior_time):
                continue
            kind, expected = expected_event(sentence, match.start(), events, explicit)
            # More than one possible calendar day is ambiguous; do not infer a leg/event.
            dates = {datetime.fromisoformat(value).date() for value, _ in expected}
            if len(dates) != 1:
                continue
            canonical = next(iter(dates))
            if canonical.weekday() != day or (date_value is not None and date_value != canonical):
                fail(actor, field, sentence[match.start():].strip(), kind,
                     [(calendar_label(value), source) for value, source in expected])
        for match in re.finditer(rf"\b{ISO_DATE}\b", sentence):
            kind, expected = expected_event(sentence, match.start(), events, explicit)
            dates = {datetime.fromisoformat(value).date().isoformat() for value, _ in expected}
            if len(dates) == 1 and match.group() not in dates:
                fail(actor, field, match.group(), kind,
                     [(calendar_label(value), source) for value, source in expected])


def check_quantities(text, actor, field, figures, explicit):
    for sentence in re.split(r"[;!?]\s*|(?<!\d)\.(?:\s+|$)", text):
        claims = [(key, m.group(1), m.start(), m.group()) for key, pattern in QUANTITIES
                  for m in pattern.finditer(sentence)]
        for match in CELL_PAIR.finditer(sentence):
            claims.extend((key, match.group(index), match.start(), match.group())
                          for key, index in (("required_cell_minutes", 1), ("available_cell_minutes", 2)))
        for key, amount, position, claim in claims:
            # A residual is not the sourced pre-build balance; ambiguous phase claims are unverified.
            if key == "available_material_units" and MATERIAL_RESIDUAL.search(sentence):
                continue
            available = figures.get(key, {})
            options = option_scope(sentence, position, available, explicit)
            expected = [available[option] for option in options if option in available]
            if expected and float(amount.replace(",", "")) not in {value for value, _ in expected}:
                fail(actor, field, claim, key, expected)


def validate_scoped_prose(value, actor, records, executed, *, warn=False):
    """Prose-only checks. Default raises (legacy); warn=True returns host ProseWarnings instead."""
    if len(getattr(records["read_build"], "options", ())) < 2:
        return ()
    figures, events = source_figures(records, executed)
    texts = ([("brief", value.brief, None)] if actor == "coordinator" else [
        ("assessment", value.assessment, None), ("implication", value.implication, None),
        *[(f"option_assessments[{item.option_id}].assessment", item.assessment, item.option_id)
          for item in value.option_assessments],
    ])
    found = []
    token = PROSE_SINK.set(found) if warn else None
    try:
        for field, text, explicit in texts:
            check_calendar(text, actor, field, events, explicit)
            check_quantities(text, actor, field, figures, explicit)
    finally:
        if token is not None:
            PROSE_SINK.reset(token)
    return tuple(dict.fromkeys(found))
