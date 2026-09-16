import polars as pl

from pressure_geometry.plays import (
    candidate_events_for_tracking_week,
    candidate_pressure_events,
    successful_rusher_events,
    traditional_dropback_events,
)


def test_successful_rusher_events_only_keeps_positive_pass_rushers() -> None:
    scouting = pl.DataFrame(
        {
            "gameId": [1, 1, 1],
            "playId": [10, 10, 10],
            "nflId": [20, 21, 30],
            "pff_role": ["Pass Rush", "Pass Rush", "Pass"],
            "pff_positionLinedUp": ["DE", "DT", "QB"],
            "pff_hurry": ["1", "0", None],
            "pff_hit": ["0", "1", None],
            "pff_sack": ["0", "0", None],
        }
    )

    result = successful_rusher_events(scouting).sort("rusherId")

    assert result.to_dicts() == [
        {
            "gameId": 1,
            "playId": 10,
            "rusherId": 20,
            "pff_positionLinedUp": "DE",
            "rush_alignment_group": "other",
            "pressure_label": "hurry",
        },
        {
            "gameId": 1,
            "playId": 10,
            "rusherId": 21,
            "pff_positionLinedUp": "DT",
            "rush_alignment_group": "other",
            "pressure_label": "hit",
        },
    ]


def test_pass_rushers_include_alignment_groups() -> None:
    from pressure_geometry.plays import pass_rusher_events

    scouting = pl.DataFrame(
        {
            "gameId": [1, 1, 1],
            "playId": [1, 2, 3],
            "nflId": [10, 11, 12],
            "pff_role": ["Pass Rush", "Pass Rush", "Pass Rush"],
            "pff_positionLinedUp": ["LEO", "NT", "SCBL"],
            "pff_hurry": ["0", "0", "0"],
            "pff_hit": ["0", "0", "0"],
            "pff_sack": ["0", "0", "0"],
        }
    )

    result = pass_rusher_events(scouting).sort("rusherId")

    assert result["rush_alignment_group"].to_list() == ["edge", "interior", "other"]


def test_traditional_dropback_events_excludes_scrambles_and_rollouts() -> None:
    events = pl.DataFrame(
        {"gameId": [1, 1, 1], "playId": [10, 11, 12], "rusherId": [20, 21, 22]}
    )
    plays = pl.DataFrame(
        {
            "gameId": [1, 1, 1],
            "playId": [10, 11, 12],
            "dropBackType": ["TRADITIONAL", "SCRAMBLE", "DESIGNED_ROLLOUT_RIGHT"],
        }
    )

    result = traditional_dropback_events(events, plays)

    assert result.select("playId", "rusherId", "dropBackType").to_dicts() == [
        {"playId": 10, "rusherId": 20, "dropBackType": "TRADITIONAL"}
    ]


def test_candidate_events_attach_qb_and_rush_count() -> None:
    scouting = pl.DataFrame(
        {
            "gameId": [1, 1, 1],
            "playId": [10, 10, 10],
            "nflId": [20, 21, 30],
            "pff_role": ["Pass Rush", "Pass Rush", "Pass"],
            "pff_positionLinedUp": ["DE", "DT", "QB"],
            "pff_hurry": ["1", "0", None],
            "pff_hit": ["0", "0", None],
            "pff_sack": ["0", "0", None],
        }
    )

    result = candidate_pressure_events(scouting)

    assert result.to_dicts() == [
        {
            "gameId": 1,
            "playId": 10,
                "rusherId": 20,
                "pff_positionLinedUp": "DE",
                "rush_alignment_group": "other",
                "pressure_label": "hurry",
            "qbId": 30,
            "num_pass_rushers": 2,
        }
    ]


def test_candidate_events_for_tracking_week_filters_to_tracked_plays() -> None:
    scouting = pl.DataFrame(
        {
            "gameId": [1, 1, 2, 2],
            "playId": [10, 10, 20, 20],
            "nflId": [20, 30, 40, 50],
            "pff_role": ["Pass Rush", "Pass", "Pass Rush", "Pass"],
            "pff_positionLinedUp": ["DE", "QB", "DE", "QB"],
            "pff_hurry": ["1", None, "1", None],
            "pff_hit": ["0", None, "0", None],
            "pff_sack": ["0", None, "0", None],
        }
    )
    tracking = pl.DataFrame({"gameId": [1], "playId": [10]})

    result = candidate_events_for_tracking_week(scouting, tracking)

    assert result.select("gameId", "playId", "rusherId").to_dicts() == [
        {"gameId": 1, "playId": 10, "rusherId": 20}
    ]
