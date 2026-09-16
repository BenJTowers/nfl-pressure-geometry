"""Quarterback-relative coordinate normalization and pressure direction."""

from __future__ import annotations

import math

import polars as pl


def add_normalized_pressure_geometry(frames: pl.DataFrame) -> pl.DataFrame:
    """Normalize QB-relative vectors so every offense attacks positive x.

    The angle convention is 0 degrees downfield, 90 degrees toward offensive
    left, 180 degrees toward the offensive backfield, and 270 degrees toward
    offensive right. Individual left- and right-moving plays are visually
    checked before league-wide reporting.
    """
    required = {"playDirection", "rusher_x", "rusher_y", "qb_x", "qb_y"}
    missing = required.difference(frames.columns)
    if missing:
        raise ValueError(f"Frame data missing columns: {sorted(missing)}")

    direction_sign = (
        pl.when(pl.col("playDirection") == "right")
        .then(pl.lit(1.0))
        .when(pl.col("playDirection") == "left")
        .then(pl.lit(-1.0))
        .otherwise(None)
    )
    with_relative = frames.with_columns(
        relative_x=pl.col("rusher_x") - pl.col("qb_x"),
        relative_y=pl.col("rusher_y") - pl.col("qb_y"),
        _direction_sign=direction_sign,
    ).with_columns(
        normalized_relative_x=pl.col("relative_x") * pl.col("_direction_sign"),
        normalized_relative_y=pl.col("relative_y") * pl.col("_direction_sign"),
    )
    return (
        with_relative.with_columns(
            pressure_angle=(
                (pl.arctan2("normalized_relative_y", "normalized_relative_x") * (180 / math.pi))
                + 360
            )
            % 360
        )
        .drop("_direction_sign")
    )
