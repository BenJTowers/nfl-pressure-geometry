"""Analysis-ready fixed-horizon pressure geometry tables."""

from __future__ import annotations

import polars as pl

from .coordinates import add_normalized_pressure_geometry
from .plays import candidate_events_for_tracking_week, traditional_dropback_events
from .pressure import fixed_horizon_frames, qb_rusher_post_snap_frames


def fixed_horizon_pressure_geometry(
    scouting: pl.DataFrame,
    plays: pl.DataFrame,
    tracking: pl.DataFrame,
    seconds_before_terminal: float = 0.5,
) -> pl.DataFrame:
    """Build one geometry row per PFF-positive traditional-dropback rusher."""
    events = traditional_dropback_events(
        candidate_events_for_tracking_week(scouting, tracking), plays
    )
    frames = qb_rusher_post_snap_frames(tracking, events)
    return add_normalized_pressure_geometry(
        fixed_horizon_frames(frames, seconds_before_terminal=seconds_before_terminal)
    ).with_columns(geometry_horizon_seconds=seconds_before_terminal)


def fixed_horizon_sensitivity(
    scouting: pl.DataFrame,
    plays: pl.DataFrame,
    tracking: pl.DataFrame,
    horizons: tuple[float, ...] = (0.3, 0.5, 0.7),
) -> pl.DataFrame:
    """Build a stacked geometry table for multiple pre-terminal horizons."""
    if not horizons:
        raise ValueError("at least one horizon is required")
    return pl.concat(
        [
            fixed_horizon_pressure_geometry(scouting, plays, tracking, horizon)
            for horizon in horizons
        ]
    )


def add_pressure_sector(geometry: pl.DataFrame) -> pl.DataFrame:
    """Assign broad 90-degree sectors without prematurely naming field sides."""
    if "pressure_angle" not in geometry.columns:
        raise ValueError("Geometry table must include pressure_angle")
    angle = pl.col("pressure_angle")
    sector = (
        pl.when((angle >= 315) | (angle < 45))
        .then(pl.lit("front"))
        .when(angle < 135)
        .then(pl.lit("offensive_left"))
        .when(angle < 225)
        .then(pl.lit("backfield"))
        .otherwise(pl.lit("offensive_right"))
    )
    return geometry.with_columns(pressure_sector=sector)


def pressure_sector_summary(
    geometry: pl.DataFrame, group_column: str = "pressure_label"
) -> pl.DataFrame:
    """Return event counts and within-group shares for broad pressure sectors."""
    with_sector = add_pressure_sector(geometry)
    if group_column not in with_sector.columns:
        raise ValueError(f"Geometry table missing grouping column: {group_column}")
    counts = with_sector.group_by(group_column, "pressure_sector").len().rename({"len": "events"})
    totals = counts.group_by(group_column).agg(pl.col("events").sum().alias("total_events"))
    sector_order = (
        pl.when(pl.col("pressure_sector") == "front")
        .then(0)
        .when(pl.col("pressure_sector") == "offensive_left")
        .then(1)
        .when(pl.col("pressure_sector") == "backfield")
        .then(2)
        .otherwise(3)
    )
    return (
        counts.join(totals, on=group_column, how="left")
        .with_columns(proportion=pl.col("events") / pl.col("total_events"))
        .with_columns(_sector_order=sector_order)
        .sort(group_column, "_sector_order")
        .drop("_sector_order")
    )


def add_pressure_outcome_severity(geometry: pl.DataFrame) -> pl.DataFrame:
    """Add a simple ordinal PFF outcome score for exploratory visualizations.

    The score ranks the supplied PFF outcomes as hurry=0, hit=1, and sack=2.
    It is deliberately descriptive rather than a value metric; EPA is the
    appropriate next layer when measuring play value.
    """
    if "pressure_label" not in geometry.columns:
        raise ValueError("Geometry table must include pressure_label")
    severity = (
        pl.when(pl.col("pressure_label") == "hurry")
        .then(0)
        .when(pl.col("pressure_label") == "hit")
        .then(1)
        .when(pl.col("pressure_label") == "sack")
        .then(2)
        .otherwise(None)
        .cast(pl.Int8)
    )
    return geometry.with_columns(pressure_outcome_severity=severity)
