import polars as pl

from pressure_geometry.epa import add_nflverse_epa, add_outcome_adjusted_epa


def test_nflverse_epa_is_joined_with_play_equal_rusher_weights() -> None:
    geometry = pl.DataFrame(
        {"gameId": [1, 1, 1], "playId": [10, 10, 11], "rusherId": [5, 6, 7]}
    )
    pbp = pl.DataFrame(
        {"old_game_id": [1, 1], "play_id": [10, 11], "epa": [-1.2, 0.4]}
    )

    result = add_nflverse_epa(geometry, pbp)

    assert result.select("defense_epa").to_series().to_list() == [1.2, 1.2, -0.4]
    assert result.select("positive_rushers_on_play").to_series().to_list() == [2, 2, 1]
    assert result.select("play_equal_weight").to_series().to_list() == [0.5, 0.5, 1.0]


def test_outcome_adjusted_epa_centers_each_pff_outcome() -> None:
    geometry = pl.DataFrame(
        {
            "pressure_label": ["hurry", "hurry", "sack"],
            "epa": [-1.0, 1.0, -2.0],
            "play_equal_weight": [0.5, 0.5, 1.0],
        }
    )

    result = add_outcome_adjusted_epa(geometry)

    assert result["outcome_adjusted_epa"].to_list() == [-1.0, 1.0, 0.0]
