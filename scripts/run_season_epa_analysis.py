"""Build the season-level fixed-horizon pressure/EPA analysis artifacts."""

from pathlib import Path

import nflreadpy as nfl
import polars as pl

from pressure_geometry.analysis import add_pressure_sector
from pressure_geometry.coordinates import add_normalized_pressure_geometry
from pressure_geometry.epa import add_nflverse_epa, add_outcome_adjusted_epa
from pressure_geometry.load import load_week_inputs
from pressure_geometry.plays import (
    candidate_events_for_tracking_week,
    traditional_dropback_events,
)
from pressure_geometry.plotting import plot_offensive_epa_heatmap
from pressure_geometry.pressure import fixed_horizon_frames, qb_rusher_post_snap_frames
from pressure_geometry.summaries import angular_offensive_epa_summary

ROOT = Path(__file__).resolve().parents[1]
HORIZONS = (0.3, 0.5, 0.7)


def week_geometry(week: int) -> pl.DataFrame:
    """Build all requested anchor horizons from a week's tracking data once."""
    inputs = load_week_inputs(week=week)
    events = traditional_dropback_events(
        candidate_events_for_tracking_week(inputs.scouting, inputs.tracking), inputs.plays
    )
    frames = qb_rusher_post_snap_frames(inputs.tracking, events)
    return pl.concat(
        [
            add_normalized_pressure_geometry(
                fixed_horizon_frames(frames, seconds_before_terminal=horizon)
            ).with_columns(week=week, geometry_horizon_seconds=horizon)
            for horizon in HORIZONS
        ]
    )


def sector_shares(geometry: pl.DataFrame) -> pl.DataFrame:
    """Return outcome-sector shares by week and anchor horizon."""
    sectors = add_pressure_sector(geometry)
    keys = ["week", "geometry_horizon_seconds", "pressure_label", "pressure_sector"]
    counts = sectors.group_by(keys).len().rename({"len": "rusher_events"})
    totals = counts.group_by(keys[:-1]).agg(pl.col("rusher_events").sum().alias("total_events"))
    return (
        counts.join(totals, on=keys[:-1])
        .with_columns(proportion=pl.col("rusher_events") / pl.col("total_events"))
        .sort(keys)
    )


def weekly_sector_epa(geometry: pl.DataFrame) -> pl.DataFrame:
    """Summarize raw and outcome-adjusted EPA by broad sector within week."""
    sectors = add_pressure_sector(geometry)
    keys = ["week", "pressure_sector"]
    return (
        sectors.group_by(keys)
        .agg(
            pl.len().alias("raw_rusher_events"),
            pl.col("play_equal_weight").sum().alias("effective_plays"),
            (pl.col("epa") * pl.col("play_equal_weight")).sum()
            .truediv(pl.col("play_equal_weight").sum())
            .alias("mean_offensive_epa"),
            (pl.col("outcome_adjusted_epa") * pl.col("play_equal_weight")).sum()
            .truediv(pl.col("play_equal_weight").sum())
            .alias("mean_outcome_adjusted_epa"),
        )
        .sort(keys)
    )


def pure_hurry_geometry(geometry: pl.DataFrame) -> pl.DataFrame:
    """Keep hurry plays without a simultaneous PFF hit or sack label."""
    play_keys = ["gameId", "playId"]
    pure_hurry_plays = (
        geometry.group_by(play_keys)
        .agg(pl.col("pressure_label").unique().alias("pressure_labels"))
        .filter(
            (pl.col("pressure_labels").list.len() == 1)
            & pl.col("pressure_labels").list.contains("hurry")
        )
        .select(play_keys)
    )
    return geometry.join(pure_hurry_plays, on=play_keys, how="inner").filter(
        pl.col("pressure_label") == "hurry"
    )


def main() -> None:
    interim = ROOT / "data" / "interim"
    figures = ROOT / "figures" / "final"
    interim.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    sensitivity = pl.concat([week_geometry(week) for week in range(1, 9)])
    sensitivity.write_parquet(interim / "2021_weeks1_8_traditional_horizon_sensitivity.parquet")
    sector_shares(sensitivity).write_csv(interim / "2021_weeks1_8_pressure_sector_week_horizon.csv")

    fixed_half_second = sensitivity.filter(pl.col("geometry_horizon_seconds") == 0.5)
    with_epa = add_nflverse_epa(fixed_half_second, nfl.load_pbp(seasons=2021))
    with_epa = add_outcome_adjusted_epa(with_epa)
    with_epa.write_parquet(interim / "2021_weeks1_8_traditional_fixed_horizon_geometry_epa.parquet")
    weekly_sector_epa(with_epa).write_csv(interim / "2021_weeks1_8_week_sector_offensive_epa.csv")
    plot_offensive_epa_heatmap(
        with_epa,
        bins=18,
        minimum_effective_plays=8,
        output_path=figures / "2021_weeks1_8_pressure_direction_offensive_epa.png",
    )

    summaries = [
        angular_offensive_epa_summary(with_epa).with_columns(pressure_label=pl.lit("all"))
    ]
    for outcome in ("hurry", "hit", "sack"):
        summaries.append(
            angular_offensive_epa_summary(
                with_epa.filter(pl.col("pressure_label") == outcome)
            ).with_columns(pressure_label=pl.lit(outcome))
        )
    pl.concat(summaries).select(
        "pressure_label", pl.exclude("pressure_label")
    ).write_csv(interim / "2021_weeks1_8_directional_offensive_epa_bootstrap.csv")
    adjusted_summary = angular_offensive_epa_summary(
        with_epa,
        value_column="outcome_adjusted_epa",
        value_name="outcome_adjusted_epa",
    )
    adjusted_summary.write_csv(interim / "2021_weeks1_8_directional_outcome_adjusted_epa_bootstrap.csv")
    plot_offensive_epa_heatmap(
        with_epa,
        bins=18,
        minimum_effective_plays=8,
        value_column="outcome_adjusted_epa",
        value_title="Outcome-adjusted offensive EPA",
        interpretation="negative = worse than expected for that PFF outcome",
        output_path=figures / "2021_weeks1_8_pressure_direction_outcome_adjusted_epa.png",
    )

    pure_hurries = pure_hurry_geometry(with_epa)
    plot_offensive_epa_heatmap(
        pure_hurries,
        bins=18,
        minimum_effective_plays=5,
        population_label="PFF hurry-only pressure",
        output_path=figures / "2021_weeks1_8_pure_hurry_direction_offensive_epa.png",
    )
    angular_offensive_epa_summary(pure_hurries).write_csv(
        interim / "2021_weeks1_8_pure_hurry_directional_offensive_epa_bootstrap.csv"
    )


if __name__ == "__main__":
    main()
