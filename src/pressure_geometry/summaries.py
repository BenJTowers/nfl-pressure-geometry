"""Uncertainty-aware summaries for circular pressure-geometry analysis."""

from __future__ import annotations

import numpy as np
import polars as pl


def angular_offensive_epa_summary(
    geometry: pl.DataFrame,
    bins: int = 18,
    bootstrap_iterations: int = 1_000,
    seed: int = 2021,
    value_column: str = "epa",
    value_name: str = "offensive_epa",
) -> pl.DataFrame:
    """Summarize 18-bin offensive EPA with play-level bootstrap intervals.

    The input has one row per PFF-positive rusher. ``play_equal_weight``
    distributes multi-rusher plays across those rows, while resampling occurs
    at the play level so correlations within a play are retained.
    """
    required = {"gameId", "playId", "pressure_angle", value_column, "play_equal_weight"}
    missing = required.difference(geometry.columns)
    if missing:
        raise ValueError(f"Geometry table missing columns: {sorted(missing)}")
    if bins < 4:
        raise ValueError("bins must be at least 4")
    if bootstrap_iterations < 1:
        raise ValueError("bootstrap_iterations must be at least 1")

    subset = geometry.select(*required).drop_nulls(
        ["pressure_angle", value_column, "play_equal_weight"]
    )
    if subset.is_empty():
        raise ValueError("No non-null EPA geometry rows are available")

    angles = subset["pressure_angle"].to_numpy()
    bin_index = np.floor((angles % 360) / (360 / bins)).astype(int)
    bin_index = np.clip(bin_index, 0, bins - 1)
    values = subset[value_column].to_numpy()
    weights = subset["play_equal_weight"].to_numpy()
    play_keys = list(subset.select("gameId", "playId").iter_rows())
    play_lookup: dict[tuple[object, object], int] = {}
    play_index = np.empty(len(play_keys), dtype=int)
    for row_index, key in enumerate(play_keys):
        play_index[row_index] = play_lookup.setdefault(key, len(play_lookup))

    raw_events = np.bincount(bin_index, minlength=bins)
    effective_plays = np.bincount(bin_index, weights=weights, minlength=bins)
    total_value = np.bincount(bin_index, weights=weights * values, minlength=bins)
    mean_value = np.divide(
        total_value, effective_plays, out=np.full(bins, np.nan), where=effective_plays > 0
    )

    generator = np.random.default_rng(seed)
    bootstrap_means = np.full((bootstrap_iterations, bins), np.nan)
    number_of_plays = len(play_lookup)
    for iteration in range(bootstrap_iterations):
        sampled_plays = generator.integers(0, number_of_plays, size=number_of_plays)
        multiplicity = np.bincount(sampled_plays, minlength=number_of_plays)[play_index]
        resampled_weights = weights * multiplicity
        resampled_volume = np.bincount(bin_index, weights=resampled_weights, minlength=bins)
        resampled_value = np.bincount(
            bin_index, weights=resampled_weights * values, minlength=bins
        )
        bootstrap_means[iteration] = np.divide(
            resampled_value,
            resampled_volume,
            out=np.full(bins, np.nan),
            where=resampled_volume > 0,
        )

    lower_ci = np.full(bins, np.nan)
    upper_ci = np.full(bins, np.nan)
    populated_bins = effective_plays > 0
    lower_ci[populated_bins] = np.nanquantile(
        bootstrap_means[:, populated_bins], 0.025, axis=0
    )
    upper_ci[populated_bins] = np.nanquantile(
        bootstrap_means[:, populated_bins], 0.975, axis=0
    )
    bin_width = 360 / bins
    return pl.DataFrame(
        {
            "angle_bin": np.arange(bins),
            "bin_start_degrees": np.arange(bins) * bin_width,
            "bin_end_degrees": (np.arange(bins) + 1) * bin_width,
            "bin_center_degrees": (np.arange(bins) + 0.5) * bin_width,
            "raw_rusher_events": raw_events,
            "effective_plays": effective_plays,
            f"mean_{value_name}": mean_value,
            f"{value_name}_ci_lower": lower_ci,
            f"{value_name}_ci_upper": upper_ci,
        }
    )
