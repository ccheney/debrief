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


@pytest.mark.parametrize(
    ("narrative", "expected"),
    [
        (
            "We never got a warning even though had we stopped our turn we would have hit terrain.",
            "Unknown",
        ),
        ("During climbout we stopped our climb due to electrical malfunctions.", "Unknown"),
        (
            "I applied maximum braking to avoid a collision with the vehicle and it swerved into the grass.",
            "Yes",
        ),
        ("The airplane went into the grass beside the runway.", "No"),
        (
            "Remembering the close call another crew had last summer; I elected to land with manual thrust.",
            "Unknown",
        ),
        ("We stopped short of the hold line.", "Yes"),
    ],
)
def test_recovery_review_regressions(narrative, expected):
    assert derive_recoverable(narrative)[0] == expected


def test_recollected_near_miss_is_not_this_incident():
    from src.schema import NEAR_MISS, unnegated_match

    assert (
        unnegated_match(
            NEAR_MISS,
            "Remembering the close call one of our crews had last summer; I elected to land.",
        )
        is None
    )
    assert unnegated_match(NEAR_MISS, "We had a close call with a fuel truck.") is not None


def test_i_should_note_is_narration():
    from src.schema import extract_lesson

    assert (
        extract_lesson(
            ["I should note; at no time did we have any indication of smoke on the flight deck."]
        )
        == "None stated."
    )


def test_abbreviations_do_not_end_sentences():
    from src.schema import sentences

    assert sentences("Revise the restriction to 12000 vs. 10000 feet. Then we landed.") == [
        "Revise the restriction to 12000 vs. 10000 feet.",
        "Then we landed.",
    ]
    assert len(sentences("Avoid crossing restrictions ie. Those with potential for conflict.")) == 1
    assert len(sentences("We stopped. We waited. We went.")) == 3


def test_engine_shutdown_is_not_engine_failure_evidence():
    narrative = "The reverser light came on with a slight engine rollback and we shut the engine down per the QRH."
    assert grounding_flags(narrative, "The crew reported an engine failure.")["events"] == [
        "engine failure"
    ]
    assert not grounding_flags(
        "The engine quit at 500 feet.", "The crew reported an engine failure."
    )["events"]


def test_named_aircraft_and_descriptors_generalized_when_unattested():
    narrative = "We feathered the propellers and the left brake failed during taxi; the prop struck a taxi light."
    row = {
        COLUMNS[
            "synopsis"
        ]: "The pilot of a King Air aircraft reported a left brake failure during taxi.",
        COLUMNS["factor"]: "Aircraft",
    }
    brief = compose_gold(row, narrative)
    assert brief and "King Air" not in brief.what_happened and "an aircraft" in brief.what_happened
    row = {
        COLUMNS["synopsis"]: "Narrow body Airbus flight crew reported a roll upset during climb.",
        COLUMNS["factor"]: "Aircraft",
    }
    brief = compose_gold(
        row,
        "During climb the aircraft rolled sharply and the side stick felt loose; the remainder of the flight was uneventful.",
    )
    assert brief and "Airbus" not in brief.what_happened and "Narrow" not in brief.what_happened


def test_unattested_night_and_cause_are_rejected():
    narrative = "On the visual approach the EGPWS called terrain and we climbed to the MSA before continuing."
    assert grounding_flags(
        narrative, "The crew reported a terrain warning on a night visual approach."
    )["events"] == ["night"]
    narrative = "After about two hours the engine began to die and I made a forced landing in a field; I had planned 19 gallons."
    row = {
        COLUMNS["synopsis"]: "Pilot reported a loss of engine power due to fuel mismanagement.",
        COLUMNS["factor"]: "Human Factors",
    }
    assert compose_gold(row, narrative) is None
    row = {
        COLUMNS[
            "synopsis"
        ]: "Pilot reported a loss of engine power and a forced landing in a field.",
        COLUMNS["factor"]: "Human Factors",
    }
    assert compose_gold(row, narrative) is not None


@pytest.mark.parametrize(
    ("narrative", "expected"),
    [
        ("We overran the runway and the nose wheel was sheared off.", "No"),
        (
            "I was able to recover the aircraft before the wing tip struck the ground. The remainder of the flight was uneventful.",
            "Yes",
        ),
    ],
)
def test_overrun_and_recovered_before_contact(narrative, expected):
    assert derive_recoverable(narrative)[0] == expected


@pytest.mark.parametrize(
    "sentence",
    [
        "By now I should have had 2600 RPM but still had slightly less than 2500.",
        "If the checklist was followed properly; both the fuel switches and the fire switches should have been off.",
    ],
)
def test_expected_state_narration_is_not_a_lesson(sentence):
    from src.schema import extract_lesson

    assert extract_lesson([sentence]) == "None stated."


def test_prescriptive_sentence_is_not_a_near_miss_and_recommends_is_hypothetical():
    narrative = (
        "We crossed STUBL at 320 knots after a misunderstanding with ATC. "
        "Procedures - Don't build crossing restrictions that have potential for conflict ie. speed and altitude together."
    )
    row = {
        COLUMNS[
            "synopsis"
        ]: "Flight crew reported a speed deviation on the arrival after a misunderstanding with ATC.",
        COLUMNS["factor"]: "Procedure",
    }
    brief = compose_gold(row, narrative)
    assert (
        brief
        and brief.what_almost_happened == "None stated"
        and brief.lesson.startswith("Don't build crossing restrictions")
    )
    from src.schema import supported_synopsis

    assert (
        supported_synopsis(
            "A Maintenance Controller recommends that APU compartments be checked after a failed start.",
            "The APU failed to start and the compartment was checked later.",
        )
        == []
    )
