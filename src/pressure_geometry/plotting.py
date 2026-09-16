"""Plots for manually validating successful pass-rush tracking events."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.colors import TwoSlopeNorm

from .pressure import (
    PeakOnsetRule,
    ThreatRule,
    first_relative_peak_onset,
    first_sustained_onset,
)

EVENT_KEYS = ("gameId", "playId", "rusherId")
KEY_EVENTS = ("pass_forward", "qb_sack", "qb_strip_sack")


def validation_events(frames: pl.DataFrame, per_label: int = 4) -> pl.DataFrame:
    """Select a deterministic, label-balanced set of events for inspection."""
    if per_label < 1:
        raise ValueError("per_label must be at least 1")
    events = frames.select(*EVENT_KEYS, "pressure_label").unique().sort(
        "pressure_label", *EVENT_KEYS
    )
    return (
        events.group_by("pressure_label", maintain_order=True)
        .head(per_label)
        .sort("pressure_label", *EVENT_KEYS)
    )


def plot_validation_event(
    frames: pl.DataFrame,
    game_id: int,
    play_id: int,
    rusher_id: int,
    anchor_frame: int | None = None,
    output_path: Path | str | None = None,
) -> plt.Figure:
    """Plot QB and successful-rusher trajectories for one event.

    The gold marker is the point of closest approach. It is a visual reference
    only, not the project's pressure-onset definition.
    """
    event = (
        frames.filter(
            (pl.col("gameId") == game_id)
            & (pl.col("playId") == play_id)
            & (pl.col("rusherId") == rusher_id)
        )
        .sort("frameId")
    )
    if event.is_empty():
        raise ValueError("No matched post-snap frames found for this event")

    closest = event.sort("distance_to_qb").head(1).to_dicts()[0]
    first = event.head(1).to_dicts()[0]
    event_info = first["pressure_label"].replace("|", ", ")

    figure, axis = plt.subplots(figsize=(10, 6))
    axis.set_facecolor("#eaf4e8")
    axis.axhline(0, color="#ffffff", linewidth=2, alpha=0.8)
    for yard_line in range(0, 121, 10):
        axis.axvline(yard_line, color="#ffffff", linewidth=1, alpha=0.7)

    axis.plot(event["qb_x"], event["qb_y"], color="#1f77b4", linewidth=2.5, label="QB")
    axis.plot(
        event["rusher_x"],
        event["rusher_y"],
        color="#d62728",
        linewidth=2.5,
        label="Successful rusher",
    )
    axis.scatter(first["qb_x"], first["qb_y"], color="#1f77b4", s=50, zorder=3)
    axis.scatter(first["rusher_x"], first["rusher_y"], color="#d62728", s=50, zorder=3)
    axis.plot(
        [closest["qb_x"], closest["rusher_x"]],
        [closest["qb_y"], closest["rusher_y"]],
        color="#c99a00",
        linestyle="--",
        linewidth=2,
        label="Closest approach",
    )
    axis.scatter(
        [closest["qb_x"], closest["rusher_x"]],
        [closest["qb_y"], closest["rusher_y"]],
        color="#c99a00",
        marker="*",
        s=125,
        zorder=4,
    )
    if anchor_frame is not None:
        anchor = event.filter(pl.col("frameId") == anchor_frame)
        if anchor.height != 1:
            raise ValueError("Anchor frame is not present in this event's tracking rows")
        anchor_row = anchor.to_dicts()[0]
        axis.plot(
            [anchor_row["qb_x"], anchor_row["rusher_x"]],
            [anchor_row["qb_y"], anchor_row["rusher_y"]],
            color="#6a3d9a",
            linewidth=2.5,
            label="Fixed-horizon direction",
        )
        axis.scatter(
            [anchor_row["qb_x"], anchor_row["rusher_x"]],
            [anchor_row["qb_y"], anchor_row["rusher_y"]],
            color="#6a3d9a",
            marker="s",
            s=52,
            zorder=5,
        )
    key_events = event.filter(pl.col("event").is_in(KEY_EVENTS)).unique("frameId")
    if key_events.is_empty():
        key_events = event.filter(pl.col("event") == "autoevent_passforward").unique("frameId")
    for index, key_event in enumerate(key_events.iter_rows(named=True)):
        label = "Throw or sack event" if index == 0 else None
        axis.scatter(
            key_event["qb_x"],
            key_event["qb_y"],
            color="#6a3d9a",
            marker="X",
            s=85,
            zorder=5,
            label=label,
        )
        axis.annotate(
            f"{key_event['event']}\nframe {key_event['frame_from_snap']}",
            (key_event["qb_x"], key_event["qb_y"]),
            xytext=(5, 8),
            textcoords="offset points",
            fontsize=8,
        )

    axis.set(xlim=(0, 120), ylim=(0, 53.3), xlabel="Field x (yards)", ylabel="Field y (yards)")
    axis.set_aspect("equal", adjustable="box")
    title = (
        f"Game {game_id}, play {play_id}, rusher {rusher_id} ({event_info})\n"
        f"Closest approach: {closest['distance_to_qb']:.2f} yd at frame "
        f"{closest['frame_from_snap']} after snap"
    )
    if anchor_frame is not None:
        anchor_offset = event.filter(pl.col("frameId") == anchor_frame).item(0, "frame_from_snap")
        title += f" | Fixed geometry frame: {anchor_offset} after snap"
    axis.set_title(title)
    axis.legend(loc="upper right")
    figure.tight_layout()

    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(destination, dpi=160, bbox_inches="tight")
        plt.close(figure)
    return figure


def plot_pressure_outcome_heatmap(
    geometry: pl.DataFrame,
    bins: int = 18,
    minimum_events: int = 5,
    output_path: Path | str | None = None,
) -> plt.Figure:
    """Plot 360-degree pressure volume beside ordinal PFF-outcome severity.

    Severity is an exploratory score: hurry=0, hit=1, sack=2. The second
    panel masks low-volume bins so one or two plays cannot imply a pattern.
    """
    required = {"pressure_angle", "pressure_label"}
    missing = required.difference(geometry.columns)
    if missing:
        raise ValueError(f"Geometry table missing columns: {sorted(missing)}")
    if bins < 4:
        raise ValueError("bins must be at least 4")
    if minimum_events < 1:
        raise ValueError("minimum_events must be at least 1")

    severity_map = {"hurry": 0, "hit": 1, "sack": 2}
    angles = geometry["pressure_angle"].to_numpy()
    labels = geometry["pressure_label"].to_list()
    severity = np.array([severity_map.get(label, np.nan) for label in labels], dtype=float)
    valid = np.isfinite(severity)
    angles = np.deg2rad(angles[valid])
    severity = severity[valid]
    counts, edges = np.histogram(angles, bins=bins, range=(0, 2 * np.pi))
    weighted, _ = np.histogram(angles, bins=edges, weights=severity)
    mean_severity = np.divide(
        weighted, counts, out=np.full(bins, np.nan), where=counts > 0
    )
    masked_severity = np.ma.masked_where(counts < minimum_events, mean_severity)
    width = 2 * np.pi / bins
    centers = np.arange(bins) * width + width / 2

    figure, axes = plt.subplots(
        1, 2, figsize=(15, 7.5), subplot_kw={"projection": "polar"}
    )
    axes[0].bar(centers, counts, width=width, alpha=0.78, color="#3973ac", align="center")
    axes[0].set_title("PFF-positive rusher frequency")

    colormap = plt.get_cmap("magma").copy()
    colormap.set_bad("#d9d9d9")
    colors = colormap(masked_severity / 2)
    axes[1].bar(
        centers, np.ones(bins), bottom=0.8, width=width, color=colors,
        align="center", edgecolor="white", linewidth=0.7,
    )
    axes[1].set_ylim(0, 1.8)
    axes[1].set_yticklabels([])
    axes[1].set_title("Mean PFF outcome severity\n0=hurry · 1=hit · 2=sack")
    colorbar = figure.colorbar(
        plt.cm.ScalarMappable(norm=plt.Normalize(0, 2), cmap=colormap),
        ax=axes[1], pad=0.12, shrink=0.72,
    )
    colorbar.set_label(f"Mean severity (gray: fewer than {minimum_events} rushers)")

    for axis in axes:
        axis.set_theta_zero_location("N")
        axis.set_theta_direction(1)
        axis.set_thetagrids(
            [0, 90, 180, 270],
            ["Front\n0°", "Offensive left\n90°", "Backfield\n180°", "Offensive right\n270°"],
        )
    figure.suptitle(
        "Traditional dropbacks: pressure direction 0.5 seconds before terminal event",
        fontsize=15,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.94))

    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(destination, dpi=160, bbox_inches="tight")
        plt.close(figure)
    return figure


def plot_defensive_epa_heatmap(
    geometry: pl.DataFrame,
    bins: int = 12,
    minimum_effective_plays: float = 8,
    output_path: Path | str | None = None,
) -> plt.Figure:
    """Plot play-equal, defensive EPA by pre-terminal pressure direction.

    ``defense_epa`` must be positive for results favorable to the defense and
    ``play_equal_weight`` must split plays with multiple positive rushers.
    """
    required = {"pressure_angle", "defense_epa", "play_equal_weight"}
    missing = required.difference(geometry.columns)
    if missing:
        raise ValueError(f"Geometry table missing columns: {sorted(missing)}")
    if bins < 4:
        raise ValueError("bins must be at least 4")
    if minimum_effective_plays <= 0:
        raise ValueError("minimum_effective_plays must be positive")

    subset = geometry.filter(pl.col("defense_epa").is_not_null())
    angles = np.deg2rad(subset["pressure_angle"].to_numpy())
    defense_epa = subset["defense_epa"].to_numpy()
    weights = subset["play_equal_weight"].to_numpy()
    volume, edges = np.histogram(angles, bins=bins, range=(0, 2 * np.pi), weights=weights)
    weighted_epa, _ = np.histogram(angles, bins=edges, weights=weights * defense_epa)
    mean_defense_epa = np.divide(
        weighted_epa, volume, out=np.full(bins, np.nan), where=volume > 0
    )
    masked_epa = np.ma.masked_where(volume < minimum_effective_plays, mean_defense_epa)
    limit = max(0.5, float(np.nanmax(np.abs(mean_defense_epa))))
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
    colormap = plt.get_cmap("RdYlGn").copy()
    colormap.set_bad("#d9d9d9")
    width = 2 * np.pi / bins
    centers = np.arange(bins) * width + width / 2

    figure, axis = plt.subplots(figsize=(9, 9), subplot_kw={"projection": "polar"})
    bars = axis.bar(
        centers, np.ones(bins), bottom=0.8, width=width, color=colormap(norm(masked_epa)),
        align="center", edgecolor="white", linewidth=0.9,
    )
    del bars
    axis.set_ylim(0, 1.8)
    axis.set_yticklabels([])
    axis.set_theta_zero_location("N")
    axis.set_theta_direction(1)
    axis.set_thetagrids(
        [0, 90, 180, 270],
        ["Front\n0°", "Offensive left\n90°", "Backfield\n180°", "Offensive right\n270°"],
    )
    axis.set_title(
        "Play-equal defensive EPA by pressure direction\n"
        "Positive = favorable to defense; terminal anchor: 0.5 seconds",
        pad=25,
    )
    colorbar = figure.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=colormap), ax=axis, pad=0.12, shrink=0.74
    )
    colorbar.set_label(
        f"Mean defensive EPA (gray: fewer than {minimum_effective_plays:g} effective plays)"
    )
    figure.tight_layout()

    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(destination, dpi=160, bbox_inches="tight")
        plt.close(figure)
    return figure


def plot_offensive_epa_heatmap(
    geometry: pl.DataFrame,
    bins: int = 18,
    minimum_effective_plays: float = 5,
    value_column: str = "epa",
    value_title: str = "Mean offensive EPA",
    interpretation: str = "negative = worse for offense",
    population_label: str = "PFF-positive pressure",
    output_path: Path | str | None = None,
) -> plt.Figure:
    """Plot play-equal offensive EPA by pre-terminal pressure direction.

    This uses every PFF-positive rusher. Negative values mean the offensive
    result was worse, while multi-rusher plays remain weighted to one total
    play across all direction bins.
    """
    required = {"pressure_angle", value_column, "play_equal_weight"}
    missing = required.difference(geometry.columns)
    if missing:
        raise ValueError(f"Geometry table missing columns: {sorted(missing)}")
    if bins < 4:
        raise ValueError("bins must be at least 4")
    if minimum_effective_plays <= 0:
        raise ValueError("minimum_effective_plays must be positive")

    subset = geometry.filter(pl.col(value_column).is_not_null())
    angles = np.deg2rad(subset["pressure_angle"].to_numpy())
    offensive_epa = subset[value_column].to_numpy()
    weights = subset["play_equal_weight"].to_numpy()
    volume, edges = np.histogram(angles, bins=bins, range=(0, 2 * np.pi), weights=weights)
    weighted_epa, _ = np.histogram(angles, bins=edges, weights=weights * offensive_epa)
    mean_offensive_epa = np.divide(
        weighted_epa, volume, out=np.full(bins, np.nan), where=volume > 0
    )
    masked_epa = np.ma.masked_where(volume < minimum_effective_plays, mean_offensive_epa)
    limit = max(0.5, float(np.nanmax(np.abs(mean_offensive_epa))))
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
    colormap = plt.get_cmap("RdYlGn").copy()
    colormap.set_bad("#d9d9d9")
    width = 2 * np.pi / bins
    centers = np.arange(bins) * width + width / 2

    figure, axes = plt.subplots(
        1, 2, figsize=(15, 7.5), subplot_kw={"projection": "polar"}
    )
    axes[0].bar(centers, volume, width=width, alpha=0.78, color="#3973ac", align="center")
    axes[0].set_title("Effective pressure-play volume")
    axes[1].bar(
        centers, np.ones(bins), bottom=0.8, width=width, color=colormap(norm(masked_epa)),
        align="center", edgecolor="white", linewidth=0.7,
    )
    axes[1].set_ylim(0, 1.8)
    axes[1].set_yticklabels([])
    axes[1].set_title(f"{value_title}\n{interpretation}")
    colorbar = figure.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=colormap),
        ax=axes[1], pad=0.12, shrink=0.72,
    )
    colorbar.set_label(
        f"{value_title} (gray: fewer than {minimum_effective_plays:g} effective plays)"
    )
    for axis in axes:
        axis.set_theta_zero_location("N")
        axis.set_theta_direction(1)
        axis.set_thetagrids(
            [0, 90, 180, 270],
            ["Front\n0°", "Offensive left\n90°", "Backfield\n180°", "Offensive right\n270°"],
        )
    figure.suptitle(
        f"Traditional dropbacks: {value_title.lower()} by {population_label} direction\n"
        "18 sectors; terminal anchor: 0.5 seconds",
        fontsize=15,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.94))

    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(destination, dpi=160, bbox_inches="tight")
        plt.close(figure)
    return figure


def save_validation_sample(
    frames: pl.DataFrame, output_dir: Path | str, per_label: int = 4
) -> list[Path]:
    """Write a label-balanced validation sample and return the created paths."""
    destination = Path(output_dir)
    selected = validation_events(frames, per_label=per_label)
    output_paths: list[Path] = []
    for event in selected.iter_rows(named=True):
        path = destination / (
            f"game_{event['gameId']}_play_{event['playId']}_rusher_{event['rusherId']}.png"
        )
        plot_validation_event(
            frames,
            event["gameId"],
            event["playId"],
            event["rusherId"],
            output_path=path,
        )
        output_paths.append(path)
    return output_paths


def plot_threat_timeline(
    metrics: pl.DataFrame,
    game_id: int,
    play_id: int,
    rusher_id: int,
    rules: list[ThreatRule],
    peak_rules: list[PeakOnsetRule] | None = None,
    output_path: Path | str | None = None,
) -> plt.Figure:
    """Plot distance, STRAIN, and TTC with candidate onsets for one rusher."""
    event = (
        metrics.filter(
            (pl.col("gameId") == game_id)
            & (pl.col("playId") == play_id)
            & (pl.col("rusherId") == rusher_id)
        )
        .sort("frameId")
    )
    if event.is_empty():
        raise ValueError("No threat-metric frames found for this event")

    figure, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    time = event["frame_from_snap"] / 10
    axes[0].plot(time, event["distance_to_qb"], color="#a6a6a6", alpha=0.55, label="Raw distance")
    axes[0].plot(time, event["smoothed_distance_to_qb"], color="#1f77b4", label="Smoothed distance")
    axes[1].plot(time, event["strain"], color="#d62728", label="STRAIN")
    axes[2].plot(time, event["implied_ttc_seconds"], color="#2ca02c", label="Implied TTC")

    colors = ("#6a3d9a", "#ff7f00", "#17becf")
    for index, rule in enumerate(rules):
        onset = first_sustained_onset(event, rule)
        if onset.is_empty():
            continue
        onset_time = onset.item(0, "onset_frame_from_snap") / 10
        label = (
            f"Onset: TTC<={rule.max_ttc_seconds:.1f}, "
            f"d<={rule.max_distance_yards:.0f}, n={rule.persistence_frames}"
        )
        for axis in axes:
            axis.axvline(onset_time, color=colors[index % len(colors)], linestyle="--", label=label)

    for index, rule in enumerate(peak_rules or []):
        onset = first_relative_peak_onset(event, rule)
        if onset.is_empty():
            continue
        onset_time = onset.item(0, "onset_frame_from_snap") / 10
        label = (
            f"Peak onset: {rule.peak_fraction:.0%} peak, "
            f"d<={rule.max_distance_yards:.0f}, n={rule.persistence_frames}"
        )
        for axis in axes:
            axis.axvline(
                onset_time,
                color=colors[(index + len(rules)) % len(colors)],
                linestyle="-.",
                label=label,
            )

    key_events = event.filter(pl.col("event").is_in(KEY_EVENTS)).unique("frameId")
    if key_events.is_empty():
        key_events = event.filter(pl.col("event") == "autoevent_passforward").unique("frameId")
    for key_event in key_events.iter_rows(named=True):
        event_time = key_event["frame_from_snap"] / 10
        for axis in axes:
            axis.axvline(event_time, color="#333333", linestyle=":", alpha=0.8)
        axes[0].annotate(
            key_event["event"],
            (event_time, axes[0].get_ylim()[1]),
            xytext=(3, -13),
            textcoords="offset points",
            fontsize=8,
        )

    axes[0].set_ylabel("Distance (yd)")
    axes[1].set_ylabel("STRAIN (1/s)")
    axes[2].set_ylabel("TTC (s)")
    axes[2].set_xlabel("Seconds after snap")
    axes[2].set_ylim(bottom=0)
    for axis in axes:
        axis.grid(alpha=0.25)
    axes[0].legend(loc="upper right", fontsize=8)
    axes[1].legend(loc="upper right", fontsize=8)
    axes[2].legend(loc="upper right", fontsize=8)
    event_label = event.item(0, "pressure_label") or "PFF non-pressure"
    figure.suptitle(
        f"Threat timeline: game {game_id}, play {play_id}, rusher {rusher_id} ({event_label})"
    )
    figure.tight_layout()

    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(destination, dpi=160, bbox_inches="tight")
        plt.close(figure)
    return figure


def plot_pressure_angle_distribution(
    geometry: pl.DataFrame,
    group_column: str | None = None,
    bins: int = 36,
    output_path: Path | str | None = None,
) -> plt.Figure:
    """Plot a circular pressure-frequency distribution using the project angle convention."""
    if bins < 4:
        raise ValueError("bins must be at least 4")
    required = {"pressure_angle"}
    if group_column is not None:
        required.add(group_column)
    missing = required.difference(geometry.columns)
    if missing:
        raise ValueError(f"Geometry table missing columns: {sorted(missing)}")

    groups = [("All PFF-positive rushers", geometry)]
    if group_column is not None:
        groups = [
            (str(group[0] if isinstance(group, tuple) and len(group) == 1 else group), subset)
            for group, subset in geometry.partition_by(group_column, as_dict=True).items()
        ]
    figure, axes = plt.subplots(
        1,
        len(groups),
        figsize=(8 * len(groups), 8),
        subplot_kw={"projection": "polar"},
        squeeze=False,
    )
    width = 2 * np.pi / bins
    for axis, (label, subset) in zip(axes[0], groups, strict=True):
        angles = np.deg2rad(subset["pressure_angle"].to_numpy())
        counts, _ = np.histogram(angles, bins=bins, range=(0, 2 * np.pi))
        if group_column is not None:
            counts = counts / counts.sum()
        centers = np.arange(bins) * width + width / 2
        axis.bar(centers, counts, width=width, alpha=0.65, align="center")
        axis.set_theta_zero_location("N")
        axis.set_theta_direction(1)
        axis.set_thetagrids(
            [0, 90, 180, 270],
            ["Front\n0°", "Offensive left\n90°", "Backfield\n180°", "Offensive right\n270°"],
        )
        axis.set_title(label)
    title = "PFF-positive pressure direction at fixed pre-terminal horizon"
    if group_column is not None:
        title += "\n(Within-outcome proportions)"
    figure.suptitle(title, fontsize=16)
    figure.tight_layout(rect=(0, 0, 1, 0.94))

    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(destination, dpi=160, bbox_inches="tight")
        plt.close(figure)
    return figure
