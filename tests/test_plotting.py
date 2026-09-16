import polars as pl

from pressure_geometry.plotting import validation_events


def test_validation_events_is_balanced_by_label() -> None:
    frames = pl.DataFrame(
        {
            "gameId": [1, 1, 1, 1, 1],
            "playId": [1, 2, 3, 4, 5],
            "rusherId": [11, 12, 13, 14, 15],
            "pressure_label": ["hurry", "hurry", "hit", "hit", "sack"],
        }
    )

    result = validation_events(frames, per_label=1)

    assert result.to_dicts() == [
        {"gameId": 1, "playId": 3, "rusherId": 13, "pressure_label": "hit"},
        {"gameId": 1, "playId": 1, "rusherId": 11, "pressure_label": "hurry"},
        {"gameId": 1, "playId": 5, "rusherId": 15, "pressure_label": "sack"},
    ]
