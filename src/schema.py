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
    text = re.sub(r"(?<=[a-z0-9%)])\.(?=[A-Z])", ". ", text)
    # "vs.", "ie.", "i.e.", "eg.", "e.g." and "approx." end abbreviations, not sentences.
    boundary = (
        r"(?<!\bvs\.)(?<!\bie\.)(?<!\bi\.e\.)(?<!\beg\.)(?<!\be\.g\.)(?<!\bapprox\.)"
        r"(?<!\bpgs\.)(?<!\bpg\.)(?<!\bpara\.)(?<!\bref\.)(?<!\bMr\.)(?<!\bMrs\.)(?<!\bDr\.)"
        r"(?<=[.!?])\s+(?=[A-Z\[\"'])|\n+"
    )
    return [s.strip() for s in re.split(boundary, text, flags=re.I) if s.strip()]


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
    r"\b(?:no|not|never|without|avoid\w*|prevent\w*|potential|possible|near|nearly|almost"
    r"|risk of|could have|would have|didn't|did not|neither|nobody|no one|none|nor|if|whether|any"
    r"|inquir\w*|check\w* for|inspect\w* for|looked for|concern\w*|worr\w*|fear\w*|threat of"
    r"|rather than|instead of|suitable for|even though|had (?:we|I|they|he|she)"
    r"|remember\w*|recall\w*|last (?:year|summer|winter|spring|fall|month|week|time)|years? ago"
    r"|previous\w*|prior (?:event|incident|occasion|experience)|in the past"
    r"|another crew|other crews?|one of our crews|similar (?:situation|event|incident)"
    r"|should have|might have|may have|likely|probably|possibly|apparently|perhaps"
    r"|suggest\w*|recommend\w*|preclude\w*)\b",
    re.I,
)
# v0.2: patterns widened from the v0.1 gold review's recorded false negatives
# (first-person "I stopped", "performed the reject", "went missed", off-field
# landings, injuries). Still deterministic keyword rules, still weak supervision.
# "Exited/departed the runway" and "contacted ground" are normal operations and
# are deliberately not treated as completed events.
COMPLETED = re.compile(
    r"\b(?:collided|collision (?:occurred|with)|(?:landing |nose |main |left |right |tail )?(?:gear|wheel) collapsed"
    r"|(?:aircraft|airplane|plane|wing ?tip|wing|tail|nose|gear|prop\w*|rotor|skid|helicopter|glider|we|I)"
    r" (?:\w+ ){0,3}?(?:struck|hit|contacted) the (?:ground(?! control)|terrain|runway surface)"
    r"|(?:struck|hit|clipped|scraped) (?:a |an |the |our )?(?:vehicle|truck|tug|tractor|light|sign|pole|fence"
    r"|building|jet ?bridge|jetway|tree|power ?line|wire|(?:parked |another |other )?aircraft|airplane|hangar|cone|barrier"
    r"|horizontal stabilizer|stabilizer|elevator|rudder|fuselage|nacelle)"
    r"|(?:cowl\w*|panel|door|fairing|window|windscreen|windshield|wheel pant|spinner|antenna|access door)"
    r" (?:had )?(?:departed|separated|came off|was lost|blew off|flew off|detached|was missing|missing)"
    r"|lost (?:a |the |an )?(?:cowl\w*|panel|fairing|windscreen|windshield|wheel pant|spinner|antenna)"
    r"|wing ?tip (?:struck|hit|contacted|clipped|scraped|dipped into|dragged)|prop(?:eller)? strike|tail strike|ground loop"
    r"|crashed|hull loss|off[- ](?:airport|field) landing|forced landing"
    r"|landed (?:in|on) (?:a |the )?(?:field|grass|pasture|highway|road|water|lake|river|beach|street)|ditched"
    r"|ground contact|runway (?:excursion|overrun)|overr(?:an|un) the (?:runway|end)|ran off the end"
    r"|(?:nose|main|landing|left|right) ?(?:gear|wheel|strut) (?:was )?(?:collapsed|sheared|separated|broke|failed|folded)"
    r"|(?:went|ran|slid|veered|skidded|rolled) off (?:the |of the )?(?:end of the |side of the |edge of the )?(?:runway|taxiway|pavement)"
    r"|departed (?:the )?(?:runway|taxiway|pavement) (?:to the (?:left|right)|into|surface)"
    r"|(?:aircraft|airplane|plane|helicopter|glider|we|I|it|nose|gear|wing|wheel|tire|tyre|main|left|right)"
    r" (?:\w+ ){0,4}?into the (?:grass|dirt|mud|ditch|snow ?bank|weeds|brush)"
    r"|nosed over|flipped over|overturned|rolled over"
    r"|(?:substantial|significant|major|structural|extensive) damage|sustained (?:\w+ )?damage"
    r"|damage to (?:the |our |my |his |her )?(?:aircraft|airplane|plane|wing|propeller|prop|gear|engine|fuselage|tail|nose|helicopter)"
    r"|aircraft was damaged|(?:was|were|got) (?:seriously |severely |badly )?(?:injured|hurt)|injuries|fatalit\w+|(?:was|were) killed)\b",
    re.I,
)
SUCCESS = re.compile(
    r"\b(?:(?:I|we) (?:(?:then|immediately|successfully|safely|quickly|eventually|promptly|both) )?"
    r"(?:stopped(?=[.;!,]|$)|stopped (?:short|immediately|abruptly|in time|before|prior to|to avoid|well before|just short|well short"
    r"|(?:the |our )?(?:aircraft|airplane|plane|push|pushback|tow|taxi) (?:short|immediately|abruptly|in time|before"
    r"|to avoid|well before|just short|well short))|queried ATC|went (?:around|missed)|rejected|aborted"
    r"|(?:discontinued|broke off) (?:the |our )?(?:approach|takeoff|landing|departure)"
    r"|elected to (?:go around|go-around|reject|abort|return|divert|discontinue))"
    r"|(?:I|we) diverted(?! (?:my|our|his|her|their) attention)|diverted (?:to|back to|the (?:flight|aircraft))\b"
    r"|(?:executed|performed|initiated|completed|commenced|flew|made|called for|elected) (?:a |an |the )?"
    r"(?:go[- ]around|missed approach|rejected takeoff|(?:low|slow|high)[- ]speed (?:reject|abort)|reject|abort"
    r"|evasive (?:action|maneuver))"
    r"|(?:rejected|aborted|rejecting|aborting|discontinued|discontinuing) (?:the |our )?(?:takeoff|take-off|landing|approach|departure)"
    r"|(?:followed|complied with|responded to) (?:the )?(?:TCAS )?RA\b"
    r"|took evasive action|(?:able to )?avoid(?:ed)? (?:a |an |the )?(?:collision|conflict)"
    r"|(?:slammed on|applied (?:maximum|max|hard|heavy|full)|got on) (?:the )?brak(?:es|ing)|braked hard|hard braking"
    r"|(?:averted|prevented) (?:a |an |the )?(?:collision|conflict|accident|incursion)|collision was avoided"
    r"|corrected (?:the |our |my |this )?(?:error|deviation|altitude|course|heading|mistake|situation)"
    r"|(?:regained|restored|reestablished|re-established) (?:aircraft |positive |radio |standard )?(?:control|separation|communication|contact)"
    r"|returned (?:to|for) (?:the |our )?(?:departure airport|field|airport|gate|land\w*)"
    r"|landed (?:safely|without (?:further |any )?(?:incident|event|problem)|uneventfully)"
    r"|(?:flight|approach|landing|climb-?out|remainder of the flight) (?:was|were) uneventful"
    r"|went around|go[- ]around was (?:executed|performed|initiated|flown))\b",
    re.I,
)

NEAR_MISS = re.compile(
    r"\b(?:near[- ]miss(?:es)?|near mid[- ]?air|NMAC|near[- ]collision|close call"
    r"|(?:almost|nearly) (?:hit|collid\w*|struck|ran (?:into|off)|taxied into|landed on|took off|lost control|stalled|impacted"
    r"|had an? (?:collision|midair|mid-air|accident|tragic|serious|catastrophic|major|incident))"
    r"|(?:avoided|prevented|averted) (?:a |an |the )?(?:collision|midair|mid-air|accident|incursion|CFIT)"
    r"|potential (?:for )?(?:a |an )?(?:ground |midair |mid-air |wingtip )?(?:collision|conflict|CFIT|loss of separation|accident)"
    r"|(?:could|would|might) have (?:hit|collided|struck"
    r"|resulted in (?:a |an )?(?:collision|midair|mid-air|accident|CFIT|loss of separation|incursion|crash)"
    r"|led to (?:a |an )?(?:collision|midair|mid-air|accident|crash)"
    r"|ended (?:in|with) (?:a |an )?(?:collision|crash|accident)"
    r"|been (?:a |an )?(?:disaster|catastroph\w+|fatal\w*|deadly|tragic|tragedy|worse|bad|ugly"
    r"|(?:much |far |a lot )?(?:bigger|larger|worse) (?:problem|issue|deal|situation)"
    r"|very (?:dangerous|bad|serious|close)|serious (?:incident|accident|collision|conflict)"
    r"|(?:mid-?air|ground) collision|incident|accident|NMAC|near miss))"
    r"|came (?:very |too |extremely |dangerously )?close to"
    r"|narrowly (?:missed|avoided|averted)"
    r"|within \d[\d;,]* ?(?:ft|feet|foot|meters|m|yards) (?:horizontally|vertically|laterally|of|from)"
    r"|evasive (?:action|maneuver))\b",
    re.I,
)

# Lessons are copied verbatim from the narrative. A sentence qualifies only when
# the reporter recommends something; narration of the moment and reported speech
# ("Tower told us we should...") are excluded. Imperatives are accepted only with
# an explicit lead-in because ASRS narration routinely drops its subject.
LESSON_START = re.compile(
    r"^(?:In (?:the future|hindsight|retrospect)|From now on|Next time|Going forward|Lessons? learned"
    r"|My (?:recommendation|suggestion)|Recommendations?|Suggestions?|(?:Don't|Do not|Never|Always)\b"
    r"|(?:I|We) (?:will|would) (?:now |always |never |be )|(?:I|We) (?:now |also |strongly )?(?:recommend|suggest))",
    re.I,
)
LESSON_MODAL = re.compile(
    r"\b(?:I|we|pilots?|crews?|controllers?|operators?|maintenance|dispatch(?:ers)?|everyone|anyone"
    r"|all (?:aircraft|pilots|crews|controllers|operators)"
    r"|the (?:crew|company|controller|pilot|airline|FAA|facility|tower)"
    r"|company|ATC|tower|management|training|airlines?|operations?|procedures?|checklists?|charts?|NOTAMs?)"
    r" (?:\w+ ){0,2}?(?:should(?: not| never| always)?(?: have)?|need(?:s)? to|must(?! have)|ought to)\b"
    r"|\b(?:should|ought to|needs? to) (?:be|have been|not be|never be|always be|also be)\b"
    r"|\bmust (?:be|not be|never be|always be|also be)\b"
    r"|\bI (?:would |strongly |also |personally )?(?:recommend|suggest)\b",
    re.I,
)
# Reported speech or a description of a rule ("Tower said we should", "the form
# states it must"), and comparisons ("higher than we should have been"), are
# narration, not the reporter's recommendation.
NOT_A_LESSON = re.compile(
    r"\b(?:told|said|stated|states|says|advised|instructed|informed|replied|asked|responded|answered"
    r"|agreed|decided|determined|concluded|conclusion|discussed|mentioned|suggested|recommended"
    r"|called out|call out|yelled|shouted|announced|screamed|exclaimed"
    r"|requires?|required|where|than|what|how)\b.*?\b(?:should|must|need|ought|will|recommend|suggest)"
    r"|\b(?:would|could|might) (?:\w+ ){0,2}?(?:should|need to|have to)\b"
    r"|\b(?:do not|don't|did not|didn't) (?:\w+ ){0,1}?(?:feel|think|believe|see)\b"
    r"|\bno (?:suggestions?|recommendations?|lessons?)\b"
    r"|^Never (?:did|was|were|have|had|has)\b"
    r"|\bI should (?:also |just |probably )?(?:note|mention|add|point out|say|state|clarify|explain|emphasize|stress)\b"
    r"|\bshould have (?:had|shown|read|indicated|been (?:at|about|around|approximately|near|reading|showing"
    r"|indicating|off|on|in|out|set|selected|closed|open|armed|engaged|extended|retracted|down|up))\b"
    r"|\bshould (?:not |never )?have (?:received|gotten|seen|heard|been given|done (?:it|that|this|so))\b"
    r"|\bshould be (?:repairable|fixable|fine|ok|okay|noted|able to)\b",
    re.I,
)
# A near-miss statement describes; a sentence that prescribes is a lesson candidate.
PRESCRIPTIVE = re.compile(
    r"\b(?:should|must|need(?:s)? to|don't|do not|never|always|recommend\w*|suggest\w*)\b", re.I
)
ANAPHORA = re.compile(r"(?:If so|This|That|It|He|She|They|Which)\b", re.I)


def extract_lesson(parts, exclude=()):
    """Last explicit recommendation sentence, verbatim, or None stated."""
    for sentence in reversed(parts):
        # Drop list enumerators and section labels ("Procedures - ", "Recommendation: ").
        sentence = re.sub(r"^\d{1,2}[.)]\s+", "", sentence)
        sentence = re.sub(
            r"^(?:Procedures?|Recommendations?|Suggestions?|Lessons?(?: learned)?|Corrective actions?|Comments?)"
            r"\s*[-:\u2013\u2014]\s*",
            "",
            sentence,
            flags=re.I,
        )
        sentence = re.sub(r"\.\s*\d{1,2}\.$", ".", sentence)
        if (
            5 <= len(sentence.split()) <= 35
            and re.match(r"[A-Z0-9\"'\[(]", sentence)
            and sentence.endswith(".")
            and "?" not in sentence
            and sentence not in exclude
            and not ANAPHORA.match(sentence)
            and not NOT_A_LESSON.search(sentence)
            and (LESSON_START.match(sentence) or LESSON_MODAL.search(sentence))
        ):
            return sentence
    return "None stated."


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
        if pattern is COMPLETED and re.search(r"\b(?:before|recover\w*|prior to)\b", prefix, re.I):
            continue  # "recovered before the wing tip struck the ground"
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


# Event classes an analyst-style summary tends to assert. Each output claim needs
# lexical evidence in the narrative; the evidence patterns are deliberately
# permissive so this catches invented classifications, not paraphrase.
EVENT_CLAIMS = (
    (
        "near miss",
        r"\bnear[- ]miss(?:es)?\b|\bnear mid[- ]?air\b|\bNMAC\b|\bnear[- ]collision\b",
        r"near[- ]?miss|mid[- ]?air|nmac|near[- ]collision|close call|almost|nearly|evasive|too close|very close|collision|collid",
    ),
    (
        "loss of separation",
        r"\bloss of separation\b|\bseparation (?:loss|error|was lost)\b",
        r"separation|(?:less|closer) than|within \d|miles? (?:apart|from|of)|feet (?:apart|from|of|vertical|lateral)",
    ),
    (
        "runway incursion",
        r"\brunway incursion\b",
        r"incursion|(?:onto|entered|crossed|across|into) (?:the |an |a )?(?:active |wrong )?runway|hold short|runway without",
    ),
    (
        "runway excursion",
        r"\brunway excursion\b",
        r"excursion|off the (?:runway|side|end)|departed the runway|ran off|left the (?:runway|pavement)|into the grass",
    ),
    (
        "engine failure",
        r"\bengine failure\b",
        r"engine (?:fail|quit|stop|flame|loss|out|problem|trouble)|lost (?:the |an |#?\d )?engine|power loss|loss of power|dead engine",
    ),
    (
        "hard landing",
        r"\bhard landing\b",
        r"hard landing|landed hard|hard touchdown|firm landing|bounced|g[- ]?load|g[- ]?force",
    ),
    ("bird strike", r"\bbird ?strike\b", r"bird|goose|geese|wildlife|hawk|gull|duck|vulture"),
    (
        "tail strike",
        r"\btail ?strike\b",
        r"tail ?strike|tail struck|tail (?:contact|scrap|hit)|struck the tail|tail skid",
    ),
    ("prop strike", r"\bprop(?:eller)? strike\b", r"prop"),
    ("fire", r"\bfire\b", r"fire|flame|burn"),
    ("smoke", r"\bsmoke\b", r"smoke|fume|odor|smell|haze"),
    ("go-around", r"\bgo[- ]around\b", r"go[- ]around|went around|go around|missed approach"),
    ("rejected takeoff", r"\brejected takeoff\b|\bRTO\b", r"reject|abort|RTO"),
    (
        "declared emergency",
        r"\bdeclared an emergency\b",
        r"emergency|declar|mayday|pan[- ]pan|priority",
    ),
    ("diversion", r"\bdivert(?:ed|ion)\b", r"divert|alternate"),
    ("fatigue", r"\bfatigue\b", r"fatigue|tired|exhaust|sleep|rest\b|duty day"),
    ("injury", r"\binjur(?:y|ies|ed)\b", r"injur|hurt|medical|paramedic|wound"),
    ("wake turbulence", r"\bwake turbulence\b", r"wake"),
    ("CFIT", r"\bCFIT\b", r"CFIT|terrain|GPWS|pull up"),
    ("night", r"\bnight(?:time)?\b", r"night|dark|evening|dusk|sunset|hours of darkness"),
    ("icing", r"\bicing\b", r"\bic(?:e|ing|ed)\b|frost|rime|anti-?ice|de-?ice"),
    ("fog", r"\bfog\b", r"fog|mist|visibility"),
    ("thunderstorm", r"\bthunderstorm\w*\b", r"thunderstorm|storm|convective|lightning|cell"),
    ("snow", r"\bsnow\b", r"snow|slush|winter|blizzard"),
    ("crosswind", r"\bcross[- ]?winds?\b", r"cross[- ]?wind|wind"),
    ("wind shear", r"\bwind ?shear\b", r"shear|microburst|gust"),
    ("turbulence", r"\bturbulence\b", r"turbulen|chop|bump|rough air|jolt"),
)
EVENT_CLAIMS = tuple(
    (name, re.compile(claim, re.I), re.compile(evidence, re.I))
    for name, claim, evidence in EVENT_CLAIMS
)


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
    events = [
        name
        for name, claim, evidence in EVENT_CLAIMS
        if claim.search(output) and not evidence.search(narrative)
    ]
    return {
        "numbers": invented_numbers,
        "acronyms": sorted(acronyms - source_words),
        "events": events,
    }


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
    r"\b(?:would have|could have|if we|if I|should have|my question|I wonder|hopefully|will have|should|recommend\w*|suggest\w*)\b",
    re.I,
)


# Named types and descriptors that analyst synopses add from the report header.
# Proper nouns only (case-sensitive) so ordinary words are never rewritten.
AIRCRAFT_NAME = re.compile(
    r"\b(?:King Air|Airbus|Boeing|Cessna|Piper|Cirrus|Mooney|Beech(?:craft)?|Bonanza|Baron|Citation"
    r"|Gulfstream|Lear(?:jet)?|Challenger|Embraer|Pilatus|Caravan|Skyhawk|Skylane|Cherokee|Archer"
    r"|Warrior|Seminole|Seneca|Saratoga|Navajo|Malibu|Meridian|Aztec|Comanche|Tomahawk|Robinson"
    r"|Sikorsky|Eurocopter|Dash ?8|Q400|Saab|Metroliner|Twin Otter|Super Cub|Piper Cub|Husky"
    r"|Decathlon|Citabria|Stearman|Hawker|Premier|Phenom|Sovereign|Kodiak|Islander|Twin Commander"
    r"|Aero Commander|Queen Air|Duke|Travel Air|Twin Bonanza|Lancair|Glasair|Kitfox|Fokker|Dornier"
    r"|Hondajet|Bell \d{3}|Diamond DA-?\d+|TBM-?\d*|PC-?12|DC-?\d+|CJ\d|SR-?2[02]|DA-?\d{2}|RV-?\d{1,2}"
    r"|Aeronca|Champ|Luscombe|Taylorcraft|Ercoupe|Grumman|Maule|Bellanca|Beechjet|Sabreliner|Westwind|Astra"
    r"|Falcon \d+|Cessna \d+|Skyhawk|Skylane|Stationair|Centurion|Cardinal|Cutlass|Conquest|Chancellor"
    r"|Super King Air|Sundowner|Sierra|Musketeer|Skipper|Starship|Premier I)\b"
)
QUALIFIERS = (
    r"Light|Aerobatic|Corporate|Business|Small|Large|Heavy|Narrow[- ]body|Wide[- ]body|Vintage|Military"
    r"|Regional|Single[- ]engine|Twin[- ]engine|Multi[- ]engine|Turboprop|Piston|Commuter|Cargo|Experimental"
    r"|Homebuilt|Amateur[- ]built|Ultralight|Tailwheel|High[- ]performance|Antique|Warbird|Jet|Air taxi"
    r"|Fractional|Charter|Air carrier"
)
ROLES = (
    "Captain",
    "First Officer",
    "Flight Attendant",
    "Dispatcher",
    "Instructor",
    "Student",
    "Mechanic",
    "Technician",
    "Ramp",
    "Load planner",
    "Controller",
)
HEDGE = re.compile(
    r"\b(?:I (?:believe|think|suspect|feel|assume)|possibl[ey]|probabl[ey]|likely|may have|might have"
    r"|apparently|seemed|appeared|perhaps|presumably)\b",
    re.I,
)
CAUSAL = re.compile(
    r"\b(?:due to|because of|as a result of|caused by|resulting from|attributed to|as a consequence of)\b",
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
    if re.search(
        r"\b(?:unsure|not sure|can.t be .*?sure|cannot be .*?sure|not certain|uncertain|surmise"
        r"|unable to determine|could not determine|cannot determine|unknown (?:cause|reason)"
        r"|highly suspect|it is my belief|I am not sure|not positive)\b",
        narrative,
        re.I,
    ):
        return []
    # Content words of every hedged narrative sentence; a synopsis cause that
    # overlaps them is the analyst promoting a guess to a fact.
    hedge_words = set()
    for candidate in sentences(narrative):
        if HEDGE.search(candidate):
            hedge_words |= words(candidate)
    for phrase in ("high altitude airport", "low altitude airport"):
        if phrase in synopsis.lower() and phrase not in narrative.lower():
            return []
    for role in ROLES:
        if not re.search(r"\b" + role + r"\b", narrative, re.I):
            synopsis = re.sub(r"\b" + role + r"\b", "reporter", synopsis, flags=re.I)
        elif re.search(r"\b(?:the|my|our) " + role + r"\b", narrative, re.I) and not re.search(
            r"\b(?:I was|I am|I'm|as|as the|being the|acting) "
            + role
            + r"\b|\b"
            + role
            + r" \(me\)|\bmyself\b",
            narrative,
            re.I,
        ):
            # The narrator refers to this role in the third person, so the analyst's
            # attribution of the report to that role is not supported by the narrative.
            synopsis = re.sub(
                r"\b" + role + r"\b(?=[^.]{0,40}\breport)", "reporter", synopsis, flags=re.I
            )
    synopsis = re.sub(r"\breporter (?:pilot|personnel|crew)\b", "reporter", synopsis, flags=re.I)
    synopsis = AIRCRAFT_TYPE.sub(generalize, synopsis)
    synopsis = AIRCRAFT_NAME.sub(generalize, synopsis)
    for qualifier in QUALIFIERS.split("|"):
        if not re.search(r"\b" + qualifier + r"\b", narrative, re.I):
            synopsis = re.sub(
                r"\b"
                + qualifier
                + r"(?=(?:\s+(?:"
                + QUALIFIERS
                + r"))*\s+(?:aircraft|airplane|plane|helicopter|pilot|jet|turboprop|piston|twin|glider|crew|reporter)\b)",
                "",
                synopsis,
                flags=re.I,
            )
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
        cause = CAUSAL.split(sentence, maxsplit=1)
        cause_words = words(cause[1]) if len(cause) > 1 else set()
        # A stated cause is the claim most often invented; its own words must be attested.
        cause_supported = not cause_words or len(cause_words & source) / len(cause_words) >= 0.6
        cause_terms = cause_words or (
            content
            if re.search(r"\b(?:caus\w*|result\w*|led to|because)\b", sentence, re.I)
            else set()
        )
        if len(cause_terms & hedge_words) >= 2:
            cause_supported = False
        if (
            not any(grounding_flags(narrative, sentence).values())
            and overlap >= 0.50
            and cause_supported
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
            if unnegated_match(NEAR_MISS, sentence)
            and sentence != happened
            and len(sentence.split()) <= 60
            and not PRESCRIPTIVE.search(sentence)
            and not re.search(r"\bfil(?:e|ed|ing)\b", sentence, re.I)
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
    lesson = extract_lesson(parts, exclude=(happened, almost))
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
        "version": 4,
        "multi_phase_policy": "first source code (not chronological)",
        "atc_override": ATC_TRIGGER.pattern,
        "atc_function_map": ATC_FUNCTION_MAP,
        "recoverable_completed": COMPLETED.pattern,
        "recoverable_success": SUCCESS.pattern,
        "negation": NEGATION.pattern,
        "near_miss": NEAR_MISS.pattern,
        "lesson_start": LESSON_START.pattern,
        "lesson_modal": LESSON_MODAL.pattern,
        "not_a_lesson": NOT_A_LESSON.pattern,
        "event_claims": {
            name: [claim.pattern, evidence.pattern] for name, claim, evidence in EVENT_CLAIMS
        },
    }
