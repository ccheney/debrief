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
    assert flags == {"numbers": ["2500"], "acronyms": ["B737", "LAX"]}
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
        ("I was able to avoid a collision using heavy braking.", "Unknown"),
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
