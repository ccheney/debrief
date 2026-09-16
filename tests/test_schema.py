import pytest
from src.schema import (
    Brief,
    COLUMNS,
    derive_recoverable,
    FACTOR_MAP,
    grounding_flags,
    map_factor,
    map_phase,
    parse_brief,
    compose_gold,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Human Factors", "Human"),
        ("Aircraft", "Equipment"),
        ("Weather", "Weather"),
        ("Procedure", "Procedure"),
        ("Ambiguous", "Unknown"),
        ("Company Policy", "Procedure"),
        ("Environment - Non Weather Related", "Other"),
        ("Airport", "Equipment"),
        ("ATC Equipment / Nav Facility / Buildings", "Equipment"),
        ("Chart Or Publication", "Procedure"),
        ("Staffing", "Human"),
        ("Manuals", "Procedure"),
        ("MEL", "Procedure"),
        ("Software and Automation", "Equipment"),
        ("", "Unknown"),
        (None, "Unknown"),
        ("unexpected new source code", "Unknown"),
    ],
)
def test_factor_maps(source, expected):
    assert map_factor(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Parked", "Parked / ramp"),
        ("Initial Climb", "Climb"),
        ("Final Approach", "Approach"),
        ("Takeoff / Launch", "Takeoff"),
        ("Other Go Around", "Go-around"),
        ("Other Rejected Takeoff", "Takeoff"),
        ("Cruise; Descent", "Cruise"),
        ("", "Unknown"),
        (None, "Unknown"),
        ("Experimental", "Other"),
    ],
)
def test_phase_maps(source, expected):
    assert map_phase(source) == expected


def test_atc_equipment_is_not_controller_action():
    assert map_factor("ATC Equipment / Nav Facility / Buildings") == "Equipment"
    assert map_factor("Human Factors", "The controller issued an incorrect clearance.") == "ATC"
    assert map_factor("Human Factors", "I misunderstood the ATC clearance.") == "Human"


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("We stopped before entering the runway.", "Yes"),
        ("We went around and landed safely.", "Yes"),
        ("We did not take evasive action.", "Unknown"),
        ("No collision occurred. We stopped.", "Yes"),
        ("We stopped, but the aircraft collided with a truck.", "No"),
        ("We almost collided with a truck.", "Unknown"),
        ("A collision was avoided.", "Yes"),
        ("We avoided a collision.", "Yes"),
        ("We would have collided if we had not stopped.", "Unknown"),
        ("We queried ATC.", "Yes"),
        ("No information was recorded.", "Unknown"),
    ],
)
def test_recovery(text, label):
    assert derive_recoverable(text)[0] == label


def test_schema_roundtrip():
    brief = Brief(
        "We stopped.",
        contributing_factors=["fatigue"],
        recoverable="Yes",
        lesson="Stop when the route is unclear.",
    )
    assert parse_brief(brief.render()) == brief


@pytest.mark.parametrize(
    "mutator",
    [
        lambda x: "Here is the brief:\n" + x,
        lambda x: x.replace("Primary factor:", "Cause:"),
        lambda x: x.replace("Unknown", "Probably", 1),
        lambda x: x.replace("\n\n", "\n", 1),
        lambda x: x + "\n\nLesson:\nAnother lesson.",
        lambda x: x.replace("None stated.", "One lesson. Another lesson."),
        lambda x: x.replace("What happened:\nWe stopped.", "What happened:\n"),
    ],
)
def test_invalid_schema(mutator):
    with pytest.raises(ValueError):
        parse_brief(mutator(Brief("We stopped.").render()))


def test_grounding():
    flags = grounding_flags("SNA at 1,000 feet.", "SNA at 1000 feet; B737 at 2500 feet near LAX.")
    assert flags == {"numbers": ["2500"], "acronyms": ["B737", "LAX"], "events": []}
    assert not any(
        grounding_flags(
            "Tower gave a clearance.",
            Brief("Tower gave a clearance.", primary_factor="ATC").render(),
        ).values()
    )


def test_synopsis_specifics_never_enter_gold():
    narrative = "We were approaching the airport when the aircraft failed to descend. We selected vertical speed and landed safely."
    row = {
        COLUMNS["synopsis"]: "B737 crew at SNA missed a 5000 foot restriction.",
        COLUMNS["factor"]: "Human Factors",
    }
    brief = compose_gold(row, narrative)
    assert brief is None  # unsupported airport/altitude cannot be laundered into gold


def test_all_factor_labels_controlled():
    assert set(FACTOR_MAP.values()) <= {
        "Human",
        "Procedure",
        "ATC",
        "Weather",
        "Equipment",
        "Other",
        "Unknown",
    }


def test_all_fixture_gold_cards_parse():
    from pathlib import Path

    paths = sorted(Path("fixtures").glob("*.gold.txt"))
    assert len(paths) == 10
    for path in paths:
        parse_brief(path.read_text())


def test_unsupported_aircraft_model_generalized_only_when_rest_is_grounded():
    narrative = "The engine failed during cruise and we returned for a safe landing."
    row = {
        COLUMNS[
            "synopsis"
        ]: "B737 flight crew reported an engine failure during cruise and returned for a safe landing."
    }
    brief = compose_gold(row, narrative)
    assert brief and "B737" not in brief.what_happened
    assert "returned" in brief.what_happened


@pytest.mark.parametrize(
    ("narrative", "expected"),
    [
        ("We then stopped before entering the runway.", "Yes"),
        ("We corrected the deviation and continued.", "Yes"),
        ("We did not execute a missed approach.", "Unknown"),
        ("We discussed the possibility of a TCAS RA.", "Unknown"),
        ("We restored positive separation.", "Yes"),
    ],
)
def test_recovery_intervention_variants(narrative, expected):
    assert derive_recoverable(narrative)[0] == expected


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("The tractor was on a collision course with the aircraft.", "Unknown"),
        ("I was able to avoid a collision using heavy braking.", "Yes"),
        ("The landing gear collapsed during the landing roll.", "No"),
    ],
)
def test_completed_event_not_collision_risk(text, label):
    assert derive_recoverable(text)[0] == label


def test_controller_human_factors_map_to_atc_not_pilot_error():
    assert map_factor("Human Factors", "I issued a late turn.", "Enroute") == "ATC"
    assert (
        map_factor("Human Factors", "I read back the clearance incorrectly.", "First Officer")
        == "Human"
    )
    assert (
        map_factor("ATC Equipment / Nav Facility / Buildings", "The radio failed.", "Ground")
        == "Equipment"
    )


def test_controller_reporting_pilot_mistake_keeps_human_label():
    assert (
        map_factor(
            "Human Factors",
            "The pilot took the wrong runway. I immediately cancelled their takeoff clearance.",
            "Local",
        )
        == "Human"
    )


def test_unknown_heading_cannot_hide_inside_an_expected_section():
    text = Brief("We stopped.\nUnrequested heading:\nA second statement.").render()
    with pytest.raises(ValueError):
        parse_brief(text)


@pytest.mark.parametrize(
    ("narrative", "expected"),
    [
        ("I stopped before the hold short line.", "Yes"),
        ("I performed a low speed reject and taxied clear.", "Yes"),
        ("We were rejecting the takeoff when Tower called.", "Yes"),
        ("We went missed and later flew a successful approach.", "Yes"),
        ("We returned to the departure airport and landed uneventfully.", "Yes"),
        ("The flight attendant was injured when we braked.", "No"),
        ("There were no injuries and no damage to the aircraft.", "Unknown"),
        ("The aircraft departed the runway into the grass.", "No"),
        ("We made an off-field landing in a pasture.", "No"),
        ("The wingtip struck the jet bridge during pushback.", "No"),
        ("I contacted ground control and we taxied to the gate.", "Unknown"),
        ("I must have missed the call.", "Unknown"),
    ],
)
def test_recovery_v02_patterns(narrative, expected):
    assert derive_recoverable(narrative)[0] == expected


def test_completed_event_still_wins_over_later_recovery():
    label, evidence = derive_recoverable(
        "We went around. On the second approach the gear collapsed on touchdown."
    )
    assert label == "No" and "collapsed" in evidence


@pytest.mark.parametrize(
    ("sentence", "is_lesson"),
    [
        ("All aircraft should comply promptly to ATC instructions and advise if unable.", True),
        (
            "I should have delayed the after landing checklist until confirming the taxi route.",
            True,
        ),
        ("Controllers should work to clarify the terminology used for PIREPs.", True),
        ("In the future I will brief the hot spots before every taxi.", True),
        ("Don't allow flight attendants to serve while waiting on a runway.", True),
        ("The taxiway closures should be depicted graphically on the chart.", True),
        ("Tower told us we should hold short of the runway.", False),
        ("I must have missed the frequency change during the descent.", False),
        ("This should never have happened to an experienced crew.", False),
        ("We landed and taxied to the gate without further incident.", False),
        ("Should we have gone around at that point?", False),
        ("Lesson learned.", False),
    ],
)
def test_lesson_extraction(sentence, is_lesson):
    from src.schema import extract_lesson

    parts = ["We were cleared for takeoff on runway one.", sentence]
    assert (extract_lesson(parts) == sentence) is is_lesson


def test_lesson_prefers_last_recommendation_and_skips_reported_speech():
    from src.schema import extract_lesson

    parts = [
        "We should have stopped earlier.",
        "The controller said we should call the tower.",
        "Crews must confirm the taxi route before moving.",
    ]
    assert extract_lesson(parts) == "Crews must confirm the taxi route before moving."


@pytest.mark.parametrize(
    ("sentence", "is_near_miss"),
    [
        ("We came very close to the departing traffic.", True),
        ("It could have resulted in a midair.", True),
        ("This was a close call with a fuel truck.", True),
        ("We took evasive action to stay clear of the helicopter.", True),
        ("We could have hit the tug.", True),
        ("We almost forgot the checklist.", False),
        ("The weather was nearly VFR by the time we landed.", False),
        ("We landed without incident.", False),
    ],
)
def test_near_miss_patterns(sentence, is_near_miss):
    from src.schema import NEAR_MISS

    assert bool(NEAR_MISS.search(sentence)) is is_near_miss


def test_event_class_claims_need_narrative_evidence():
    narrative = "We turned the wrong way on taxiway Alpha and Tower had us continue to the ramp."
    flags = grounding_flags(narrative, "The crew reported a runway incursion and a near miss.")
    assert flags["events"] == ["near miss", "runway incursion"]
    assert not grounding_flags(
        "We entered the runway without a clearance; the other aircraft was very close.",
        "The crew reported a runway incursion and a near miss.",
    )["events"]


def test_unsupported_event_class_in_synopsis_is_rejected():
    narrative = "We turned the wrong way on the taxiway and Tower directed us back to the ramp."
    row = {
        COLUMNS[
            "synopsis"
        ]: "Flight crew reported a runway incursion after a wrong turn on the taxiway.",
        COLUMNS["factor"]: "Human Factors",
    }
    assert compose_gold(row, narrative) is None
