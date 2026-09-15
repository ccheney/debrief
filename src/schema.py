"""Normative seven-section schema and explicit ASRS mappings.

Metadata is weak supervision, never source text. Free-text targets are copied
from narrative evidence selected by synopsis overlap, not invented from codes.
"""

from dataclasses import asdict, dataclass, field
import re

SYSTEM_PROMPT = """You convert an incident narrative into an investigator brief.
Use only information present in the narrative.
Do not invent facts, numbers, or causes.
If the narrative does not support a field, write Unknown or None stated.
Follow the required headings exactly."""

HEADINGS = (
    "What happened",
    "What almost happened",
    "Phase of flight",
    "Primary factor",
    "Contributing factors",
    "Recoverable",
    "Lesson",
)
PHASES = (
    "Parked / ramp",
    "Taxi",
    "Takeoff",
    "Climb",
    "Cruise",
    "Descent",
    "Approach",
    "Landing",
    "Go-around",
    "Other",
    "Unknown",
)
FACTORS = ("Human", "Procedure", "ATC", "Weather", "Equipment", "Other", "Unknown")
RECOVERABLE = ("Yes", "No", "Unknown")
COLUMNS = {
    "id": "acn_num_ACN",
    "narrative": "Report 1_Narrative",
    "synopsis": "Report 1.2_Synopsis",
    "phase": "Aircraft 1.9_Flight Phase",
    "factor": "Assessments.1_Primary Problem",
    "contributors": "Assessments_Contributing Factors / Situations",
    "human_factors": "Person 1.7_Human Factors",
    "anomalies": "Events_Anomaly",
    "result": "Events.5_Result",
    "related_id": "Person 2.10_ASRS Report Number.Accession Number",
}
PHASE_MAP = {
    "Parked": "Parked / ramp",
    "Taxi": "Taxi",
    "Takeoff / Launch": "Takeoff",
    "Initial Climb": "Climb",
    "Climb": "Climb",
    "Cruise": "Cruise",
    "Descent": "Descent",
    "Initial Approach": "Approach",
    "Final Approach": "Approach",
    "Landing": "Landing",
    "Other Go Around": "Go-around",
    "Go Around": "Go-around",
    "Go-around": "Go-around",
    "Other Rejected Takeoff": "Takeoff",
    "Other Non-Flight": "Other",
    "Other All": "Other",
    "Other Unspecified": "Other",
    "": "Unknown",
}
FACTOR_MAP = {
    "Human Factors": "Human",
    "Aircraft": "Equipment",
    "Procedure": "Procedure",
    "Ambiguous": "Unknown",
    "Weather": "Weather",
    "Company Policy": "Procedure",
    "Environment - Non Weather Related": "Other",
    "Airport": "Equipment",
    "ATC Equipment / Nav Facility / Buildings": "Equipment",
    "Chart Or Publication": "Procedure",
    "Airspace Structure": "Procedure",
    "Equipment / Tooling": "Equipment",
    "Staffing": "Human",
    "Manuals": "Procedure",
    "MEL": "Procedure",
    "Incorrect / Not Installed / Unavailable Part": "Equipment",
    "Software and Automation": "Equipment",
    "Logbook Entry": "Procedure",
    "ATC": "ATC",
    "": "Unknown",
}
# A human-factors primary code may describe controllers or pilots. Override only
# with explicit narrator attribution, never just the presence of an ATC anomaly.
ATC_TRIGGER = re.compile(
    r"\b(?:ATC|controller|tower|ground control)\s+(?:had\s+)?(?:gave|issued|provided)\s+(?:us\s+)?(?:an?\s+|the\s+)?(?:incorrect|wrong|conflicting)\b",
    re.I,
)
# Contributors must have both a coded label and a matching narrative phrase.
CONTRIBUTOR_EVIDENCE = {
    "Fatigue": r"\b(?:fatigue[d]?|exhausted|lack of sleep|tired)\b",
    "Distraction": r"\b(?:distract\w*|interrupted|interruption)\b",
    "Confusion": r"\b(?:confus\w*|unclear)\b",
    "Workload": r"\b(?:workload|task saturat\w*|overloaded)\b",
    "Time Pressure": r"\b(?:rushed|rushing|time pressure|hurry|hurried)\b",
    "Communication Breakdown": r"\b(?:miscommunicat\w*|misheard|misunderstood|blocked transmission|communication breakdown)\b",
    "Training / Qualification": r"\b(?:untrained|inadequate training|lack of training|not trained)\b",
    "Situational Awareness": r"\b(?:lost situational awareness|unaware|did not notice|failed to notice)\b",
    "Human-Machine Interface": r"\b(?:display|interface)\b",
    "Weather": r"\b(?:turbulence|icing|thunderstorm\w*|fog|crosswind\w*|wind shear)\b",
}


@dataclass
class Brief:
    what_happened: str
    what_almost_happened: str = "None stated"
    phase_of_flight: str = "Unknown"
    primary_factor: str = "Unknown"
    contributing_factors: list[str] = field(default_factory=list)
    recoverable: str = "Unknown"
    recoverable_note: str = ""
    lesson: str = "None stated."

    def to_dict(self):
        return asdict(self)

    def render(self):
        values = [
            self.what_happened,
            self.what_almost_happened,
            self.phase_of_flight,
            self.primary_factor,
            "\n".join(f"- {x}" for x in self.contributing_factors) or "None stated",
            self.recoverable + ("\n" + self.recoverable_note if self.recoverable_note else ""),
            self.lesson,
        ]
        return "\n\n".join(f"{h}:\n{v}" for h, v in zip(HEADINGS, values))


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\[\"'])|\n+", text) if s.strip()]


def parse_brief(text):
    """Strict validation: no prose wrappers, repeats, extra fields or repairs."""
    text = text.strip()
    pattern = re.compile(r"^(" + "|".join(re.escape(h) for h in HEADINGS) + r"):[ \t]*\n", re.M)
    matches = list(pattern.finditer(text))
    if [m.group(1) for m in matches] != list(HEADINGS) or not matches or matches[0].start() != 0:
        raise ValueError("Expected exactly seven headings in the required order")
    values = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw = text[match.end() : end]
        if i + 1 < len(matches) and not raw.endswith("\n\n"):
            raise ValueError("Sections must have a blank line between them")
        if not raw.strip():
            raise ValueError(f"Empty section: {HEADINGS[i]}")
        values.append(raw.strip())
    happened, almost, phase, factor, contributors, recovery, lesson = values
    if phase not in PHASES or factor not in FACTORS:
        raise ValueError("Invalid phase or primary factor")
    recovery_lines = recovery.splitlines()
    if recovery_lines[0] not in RECOVERABLE or len(recovery_lines) > 2:
        raise ValueError("Invalid recoverable flag or justification")
    if contributors == "None stated":
        bullets = []
    else:
        lines = contributors.splitlines()
        if not all(line.startswith("- ") and line[2:].strip() for line in lines) or len(lines) > 5:
            raise ValueError("Contributing factors must be at most five bullets")
        bullets = [line[2:].strip() for line in lines]
    if not 1 <= len(sentences(happened)) <= 3:
        raise ValueError("What happened must be one to three sentences")
    if len(sentences(lesson)) != 1 or "\n" in lesson or not lesson.endswith((".", "!", "?")):
        raise ValueError("Lesson must be exactly one sentence")
    return Brief(
        happened,
        almost,
        phase,
        factor,
        bullets,
        recovery_lines[0],
        recovery_lines[1] if len(recovery_lines) > 1 else "",
        lesson,
    )


def split_codes(value):
    return [x.strip() for x in str(value or "").split(";") if x.strip()]


def map_phase(value):
    # ASRS multiple phases have no event-time ordering. Preserve first listed;
    # this is documented weak supervision, not a chronological inference.
    codes = split_codes(value)
    return PHASE_MAP.get(codes[0], "Other") if codes else "Unknown"


def map_factor(value, narrative=""):
    mapped = FACTOR_MAP.get(str(value or "").strip(), "Unknown")
    return "ATC" if mapped == "Human" and ATC_TRIGGER.search(narrative) else mapped


NEGATION = re.compile(
    r"\b(?:no|not|never|without|avoided|prevented|potential|possible|nearly|almost|risk of|could have|would have|didn't|did not)\b",
    re.I,
)
COMPLETED = re.compile(
    r"\b(?:collided|collision|struck (?:the |a )?(?:ground|terrain|aircraft|vehicle)|hit (?:the |a )?(?:ground|terrain|aircraft|vehicle)|crashed|hull loss|off[- ]airport landing|ground contact)\b",
    re.I,
)
SUCCESS = re.compile(
    r"\b(?:we (?:stopped|queried ATC|went around)|(?:executed|performed|initiated) (?:a )?go[- ]around|rejected (?:the )?takeoff|aborted (?:the )?takeoff|followed (?:the )?(?:TCAS )?RA|took evasive action|avoided (?:a |the )?collision|collision was avoided)\b",
    re.I,
)
NEAR_MISS = re.compile(
    r"\b(?:near[- ]miss|near mid[- ]air|NMAC|almost (?:hit|collided)|nearly (?:hit|collided)|(?:avoided|prevented) (?:a |the )?collision|potential (?:ground |midair |mid-air )?collision|could have (?:hit|collided))\b",
    re.I,
)


def unnegated_match(pattern, sentence):
    for match in pattern.finditer(sentence):
        # Only local negation; 'no injuries after we collided' still counts.
        prefix = sentence[max(0, match.start() - 70) : match.start()]
        prefix = re.split(r"[;,]|\bbut\b|\bafter\b", prefix, flags=re.I)[-1]
        suffix = sentence[match.end() : match.end() + 45]
        if pattern is COMPLETED and re.match(
            r"\s+(?:was |were |had been )?(?:avoided|prevented|averted|did not occur)\b",
            suffix,
            re.I,
        ):
            continue
        if not NEGATION.search(prefix):
            return match
    return None


def derive_recoverable(narrative, synopsis=""):
    # Synopsis is deliberately excluded when it adds facts absent from input.
    for sentence in sentences(narrative):
        if unnegated_match(COMPLETED, sentence):
            return "No", sentence
    for sentence in sentences(narrative):
        if unnegated_match(SUCCESS, sentence):
            return "Yes", sentence
    return "Unknown", ""


def grounding_flags(narrative, output):
    """Cheap specifics check, not a semantic hallucination judge."""

    def numbers(value):
        return set(re.findall(r"(?<!\w)\d+(?:[.,;]\d+)*(?!\w)", value))

    def normalize(x):
        return x.replace(",", "").replace(";", "")

    source_numbers = {normalize(x) for x in numbers(narrative)}
    invented_numbers = sorted(x for x in numbers(output) if normalize(x) not in source_numbers)
    # The controlled class ATC is allowed even when the narrator says controller.
    acronyms = set(re.findall(r"\b[A-Z][A-Z0-9-]{1,}\b", output)) - {"ATC"}
    source_words = set(re.findall(r"\b[A-Z0-9-]+\b", narrative.upper()))
    return {"numbers": invented_numbers, "acronyms": sorted(acronyms - source_words)}


def words(text):
    stop = {
        "the",
        "and",
        "that",
        "was",
        "were",
        "with",
        "for",
        "from",
        "this",
        "they",
        "reported",
        "flight",
        "crew",
    }
    return {w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in stop}


def compose_gold(row, narrative):
    """Synopsis-guided extractive targets: every free-text claim has input evidence."""
    synopsis = str(row.get(COLUMNS["synopsis"], "") or "")
    parts = sentences(narrative)
    summary_words = words(synopsis)
    ranked = sorted(enumerate(parts), key=lambda p: (-len(words(p[1]) & summary_words), p[0]))
    # Prefer short complete evidence. Never cut a sentence into a new claim.
    candidates = [(i, s) for i, s in ranked if 6 <= len(s.split()) <= 65 and len(s) < 460]
    if not candidates:
        return None
    selected = sorted(candidates[:2])
    happened = " ".join(s for _, s in selected)
    almost = next(
        (s for s in parts if NEAR_MISS.search(s) and s not in happened and len(s.split()) <= 60),
        "None stated",
    )
    recoverable, evidence = derive_recoverable(narrative)
    contributors = []
    for code in split_codes(row.get(COLUMNS["human_factors"])) + split_codes(
        row.get(COLUMNS["contributors"])
    ):
        pattern = CONTRIBUTOR_EVIDENCE.get(code)
        match = re.search(pattern, narrative, re.I) if pattern else None
        if match and not NEGATION.search(narrative[max(0, match.start() - 25) : match.start()]):
            # Quote the attested phrase instead of asserting an analyst's label.
            phrase = match.group(0)
            if phrase.lower() not in {p.lower() for p in contributors}:
                contributors.append(phrase)
    lesson = next(
        (
            s
            for s in reversed(parts)
            if re.search(r"\b(?:should|need to|lesson|recommend)\b", s, re.I)
            and len(s.split()) <= 35
            and s.endswith(".")
        ),
        "None stated.",
    )
    brief = Brief(
        happened,
        almost,
        map_phase(row.get(COLUMNS["phase"])),
        map_factor(row.get(COLUMNS["factor"]), narrative),
        contributors[:5],
        recoverable,
        evidence if len(evidence.split()) <= 40 and evidence not in happened else "",
        lesson,
    )
    try:
        parse_brief(brief.render())
    except ValueError:
        return None
    return brief


def label_map():
    return {
        "columns": COLUMNS,
        "phases": PHASE_MAP,
        "factors": FACTOR_MAP,
        "contributor_evidence": CONTRIBUTOR_EVIDENCE,
        "version": 1,
        "multi_phase_policy": "first source code (not chronological)",
        "atc_override": ATC_TRIGGER.pattern,
        "recoverable_completed": COMPLETED.pattern,
        "recoverable_success": SUCCESS.pattern,
        "negation": NEGATION.pattern,
        "near_miss": NEAR_MISS.pattern,
    }
