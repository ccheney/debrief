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
    "reporter_function": "Person 1.3_Function",
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
ATC_FUNCTION_MAP = {
    code: "ATC"
    for code in ("Enroute", "Approach", "Departure", "Local", "Ground", "Supervisor / CIC")
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
    text = re.sub(r"(?<=[a-z])\.(?=[A-Z][a-z])", ". ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\[\"'])|\n+", text) if s.strip()]


def parse_brief(text):
    """Strict validation: no prose wrappers, repeats, extra fields or repairs."""
    text = text.strip()
    heading_lines = re.findall(r"^([A-Za-z][A-Za-z -]*):[ \t]*$", text, re.M)
    if heading_lines != list(HEADINGS):
        raise ValueError("Unexpected, duplicated, or missing section heading")
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


def map_factor(value, narrative="", reporter_function=""):
    mapped = FACTOR_MAP.get(str(value or "").strip(), "Unknown")
    controller = any(code in ATC_FUNCTION_MAP for code in split_codes(reporter_function))
    own_error = re.search(
        r"\b(?:I|we) (?:had )?(?:(?:inadvertently|mistakenly|incorrectly|erroneously) (?:cleared|issued|assigned|instructed)"
        r"|(?:forgot|failed) to|misunderstood|missed|assumed|issued (?:a |the )?(?:late|wrong|incorrect))\b",
        narrative,
        re.I,
    )
    return (
        "ATC"
        if mapped == "Human" and (ATC_TRIGGER.search(narrative) or (controller and own_error))
        else mapped
    )


NEGATION = re.compile(
    r"\b(?:no|not|never|without|avoid|avoided|prevented|potential|possible|near|nearly|almost|risk of|could have|would have|didn't|did not)\b",
    re.I,
)
COMPLETED = re.compile(
    r"\b(?:collided|collision (?:occurred|with)|landing gear collapsed|struck (?:the |a )?(?:ground|terrain|aircraft|vehicle)|hit (?:the |a )?(?:ground|terrain|aircraft|vehicle)|crashed|hull loss|off[- ]airport landing|ground contact)\b",
    re.I,
)
SUCCESS = re.compile(
    r"\b(?:we (?:(?:then|immediately|successfully|safely|quickly|eventually) )?(?:stopped|queried ATC|went around)"
    r"|(?:executed|performed|initiated|completed) (?:a |the )?(?:go[- ]around|missed approach)"
    r"|(?:rejected|aborted) (?:the )?takeoff|followed (?:the )?(?:TCAS )?RA"
    r"|took evasive action|avoided (?:a |the )?collision|collision was avoided"
    r"|corrected (?:the |our |my |this )?(?:error|deviation|altitude)"
    r"|(?:regained|restored|reestablished) (?:aircraft |positive |radio )?(?:control|separation|communication))\b",
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


# Only recognized aircraft-family tokens can be generalized. Never erase an
# arbitrary unknown airport, number or callsign to make a target appear grounded.
AIRCRAFT_TYPE = re.compile(
    r"\b(?:B\d{3}(?:-\d+[A-Z]*)?|A\d{3}(?:-\d+)?|MD-?\d+|CRJ-?\d+|ERJ-?\d+|EMB-?\d+|C[AE]?\d{3}|BE-?\d+|PA-?\d+)\b"
)
EVENT_WORDS = re.compile(
    r"\b(?:fail\w*|lost|loss|error|incorrect|wrong|warn\w*|smoke|fire|struck|hit|collid\w*|collision|separat\w*|departed|uncommanded|roll\w*|dislodged|inoperative|shut|shutdown|deviation|miss\w*|conflict|turbulence|injur\w*|damag\w*|incursion|billowing|hurt|blood|brak\w*)\b",
    re.I,
)
HYPOTHETICAL = re.compile(
    r"\b(?:would have|could have|if we|if I|should have|my question|I wonder|hopefully|will have|should|recommend)\b",
    re.I,
)


def supported_synopsis(synopsis, narrative):
    def generalize(match):
        token = match.group(0)
        if re.search(r"\b" + re.escape(token) + r"\b", narrative, re.I):
            return token
        return "aircraft"

    # Preserve uncertainty: do not supervise a confident synopsis from a narrator
    # who explicitly says they cannot establish what happened.
    if re.search(r"\b(?:unsure|not sure|can.t be .*?sure|cannot be .*?sure)\b", narrative, re.I):
        return []
    for phrase in ("high altitude airport", "low altitude airport"):
        if phrase in synopsis.lower() and phrase not in narrative.lower():
            return []
    for role in ("Captain", "First Officer"):
        if not re.search(r"\b" + role + r"\b", narrative, re.I):
            synopsis = re.sub(r"\b" + role + r"\b", "reporter", synopsis, flags=re.I)
    synopsis = AIRCRAFT_TYPE.sub(generalize, synopsis)
    for qualifier in ("Light", "Aerobatic", "Corporate", "Business", "Small", "Large", "Heavy"):
        if qualifier.lower() not in words(narrative):
            synopsis = re.sub(r"\b" + qualifier + r"(?= aircraft\b)", "", synopsis, flags=re.I)
    synopsis = re.sub(r" +", " ", synopsis).strip()
    synopsis = re.sub(r"\ba aircraft\b", "an aircraft", synopsis, flags=re.I)
    synopsis = re.sub(r"\b(?:an? )?aircraft flight crew\b", "The flight crew", synopsis, flags=re.I)
    synopsis = re.sub(r"\baircraft aircraft\b", "aircraft", synopsis, flags=re.I)
    synopsis = re.sub(r"\b(?:an? )?aircraft (captain|reporter)\b", r"The \1", synopsis, flags=re.I)
    selected = []
    source = words(narrative)
    for index, sentence in enumerate(sentences(synopsis)):
        content = words(sentence)
        overlap = len(content & source) / max(1, len(content))
        if (
            not any(grounding_flags(narrative, sentence).values())
            and overlap >= 0.50
            and EVENT_WORDS.search(sentence)
            and not HYPOTHETICAL.search(sentence)
            and not sentence.endswith("?")
            and len(sentence.split()) <= 65
        ):
            selected.append(sentence[0].upper() + sentence[1:])
        elif index == 0:
            return []  # a later sentence must not replace the central incident
    return selected[:2]


def compose_gold(row, narrative):
    """Source-checked deterministic synopsis; reject unsupported prose targets."""
    synopsis = str(row.get(COLUMNS["synopsis"], "") or "")
    parts = sentences(narrative)
    summary = supported_synopsis(synopsis, narrative)
    if not summary:
        return None
    happened = " ".join(summary)
    almost = next(
        (
            sentence
            for sentence in parts
            if NEAR_MISS.search(sentence) and sentence != happened and len(sentence.split()) <= 60
        ),
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
            if re.search(
                r"^(?:(?:We|Pilots|Crews|Controllers|Operators|Maintenance|The crew|Our crew|Flight crews|You) (?:should|need to|must)|I (?:recommend|suggest)|The lesson)",
                s,
                re.I,
            )
            and len(s.split()) <= 35
            and not re.match(r"(?:If so|This|That|It|He|She|They)\b", s, re.I)
            and s.endswith(".")
        ),
        "None stated.",
    )
    brief = Brief(
        happened,
        almost,
        map_phase(row.get(COLUMNS["phase"])),
        map_factor(row.get(COLUMNS["factor"]), narrative, row.get(COLUMNS["reporter_function"])),
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
        "version": 3,
        "multi_phase_policy": "first source code (not chronological)",
        "atc_override": ATC_TRIGGER.pattern,
        "atc_function_map": ATC_FUNCTION_MAP,
        "recoverable_completed": COMPLETED.pattern,
        "recoverable_success": SUCCESS.pattern,
        "negation": NEGATION.pattern,
        "near_miss": NEAR_MISS.pattern,
    }
