"""Join nflverse play value to rusher-level pressure geometry."""

from __future__ import annotations

import polars as pl


def add_nflverse_epa(geometry: pl.DataFrame, play_by_play: pl.DataFrame) -> pl.DataFrame:
    """Attach nflverse EPA and play-equal weights to pressure-geometry rows.

    nflverse reports offensive EPA, so ``defense_epa`` is its negation: a
    positive value is favorable for the defense.  A play with multiple
    PFF-positive rushers is split equally among them, preventing it from
    counting more than once in an angle-level EPA average.
    """
    geometry_keys = {"gameId", "playId"}
    missing_geometry = geometry_keys.difference(geometry.columns)
    if missing_geometry:
        raise ValueError(f"Geometry table missing columns: {sorted(missing_geometry)}")
    required_pbp = {"old_game_id", "play_id", "epa"}
    missing_pbp = required_pbp.difference(play_by_play.columns)
    if missing_pbp:
        raise ValueError(f"Play-by-play table missing columns: {sorted(missing_pbp)}")

    epa_by_play = (
        play_by_play.select(
            pl.col("old_game_id").cast(pl.Int64).alias("gameId"),
            pl.col("play_id").cast(pl.Int64).alias("playId"),
            pl.col("epa").cast(pl.Float64),
        )
        .unique(["gameId", "playId"])
    )
    play_keys = ["gameId", "playId"]
    return (
        geometry.join(epa_by_play, on=play_keys, how="left")
        .with_columns(
            defense_epa=-pl.col("epa"),
            positive_rushers_on_play=pl.len().over(play_keys),
        )
        .with_columns(play_equal_weight=1 / pl.col("positive_rushers_on_play"))
    )


def add_outcome_adjusted_epa(geometry: pl.DataFrame) -> pl.DataFrame:
    """Center offensive EPA within each supplied PFF pressure outcome.

    The resulting value answers a narrower descriptive question: was this
    play better or worse for the offense than a typical pressure play with the
    same hurry, hit, or sack label? The PFF-positive-rusher weights are used
    when calculating each outcome's baseline.
    """
    required = {"pressure_label", "epa", "play_equal_weight"}
    missing = required.difference(geometry.columns)
    if missing:
        raise ValueError(f"Geometry table missing columns: {sorted(missing)}")
    baselines = (
        geometry.filter(pl.col("epa").is_not_null())
        .group_by("pressure_label")
        .agg(
            (pl.col("epa") * pl.col("play_equal_weight")).sum()
            .truediv(pl.col("play_equal_weight").sum())
            .alias("outcome_mean_offensive_epa")
        )
    )
    return geometry.join(baselines, on="pressure_label", how="left").with_columns(
        outcome_adjusted_epa=pl.col("epa") - pl.col("outcome_mean_offensive_epa")
    )
