import polars as pl

from pressure_geometry.summaries import angular_offensive_epa_summary


def test_angular_epa_summary_keeps_multi_rusher_play_weight_to_one() -> None:
    geometry = pl.DataFrame(
        {
            "gameId": [1, 1, 1],
            "playId": [10, 10, 11],
            "pressure_angle": [5.0, 15.0, 100.0],
            "epa": [-1.0, -1.0, 0.5],
            "play_equal_weight": [0.5, 0.5, 1.0],
        }
    )

    result = angular_offensive_epa_summary(geometry, bins=4, bootstrap_iterations=10)

    assert result.select("raw_rusher_events").to_series().to_list() == [2, 1, 0, 0]
    assert result.select("effective_plays").to_series().to_list() == [1.0, 1.0, 0.0, 0.0]
    assert result.select("mean_offensive_epa").to_series().to_list()[:2] == [-1.0, 0.5]
