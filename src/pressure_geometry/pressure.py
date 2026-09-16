"""Frame-level quarterback and successful-rusher tracking transformations."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

SNAP_EVENTS = ("ball_snap", "autoevent_ballsnap")
EVENT_KEYS = ("gameId", "playId", "rusherId")


@dataclass(frozen=True)
class ThreatRule:
    """A candidate definition for a sustained, imminent QB threat."""

    max_ttc_seconds: float
    max_distance_yards: float
    persistence_frames: int

    def __post_init__(self) -> None:
        if self.max_ttc_seconds <= 0 or self.max_distance_yards <= 0:
            raise ValueError("TTC and distance thresholds must be positive")
        if self.persistence_frames < 1:
            raise ValueError("persistence_frames must be at least 1")


@dataclass(frozen=True)
class PeakOnsetRule:
    """A within-event rule locating the start of a rusher's threat ramp."""

    peak_fraction: float
    max_distance_yards: float
    min_strain: float = 0.15
    persistence_frames: int = 2

    def __post_init__(self) -> None:
        if not 0 < self.peak_fraction <= 1:
            raise ValueError("peak_fraction must be in (0, 1]")
        if self.max_distance_yards <= 0 or self.min_strain < 0:
            raise ValueError("distance must be positive and min_strain non-negative")
        if self.persistence_frames < 1:
            raise ValueError("persistence_frames must be at least 1")


def qb_rusher_post_snap_frames(
    tracking: pl.DataFrame, candidate_events: pl.DataFrame
) -> pl.DataFrame:
    """Pair each successful rusher with the QB at every shared post-snap frame.

    This is the validation dataset used to inspect distance and trajectories
    before selecting a pressure-onset definition.
    """
    tracking_required = {
        "gameId", "playId", "nflId", "frameId", "time", "playDirection",
        "x", "y", "s", "a", "o", "dir", "event",
    }
    candidate_required = {"gameId", "playId", "rusherId", "qbId", "pressure_label", "num_pass_rushers"}
    missing_tracking = tracking_required.difference(tracking.columns)
    missing_candidates = candidate_required.difference(candidate_events.columns)
    if missing_tracking or missing_candidates:
        raise ValueError(
            f"Missing tracking columns: {sorted(missing_tracking)}; "
            f"missing candidate columns: {sorted(missing_candidates)}"
        )

    pff_outcome = ["pff_pressure"] if "pff_pressure" in candidate_events.columns else []
    rusher_position = (
        ["pff_positionLinedUp"] if "pff_positionLinedUp" in candidate_events.columns else []
    )
    rusher_alignment = (
        ["rush_alignment_group"]
        if "rush_alignment_group" in candidate_events.columns
        else []
    )

    keys = ["gameId", "playId"]
    snap_frames = (
        tracking.filter(pl.col("event").is_in(SNAP_EVENTS))
        .group_by(keys)
        .agg(pl.col("frameId").min().alias("snap_frame"))
    )
    rusher = (
        candidate_events.join(
            tracking,
            left_on=[*keys, "rusherId"],
            right_on=[*keys, "nflId"],
            how="inner",
        )
        .select(
            *keys,
            "rusherId",
            "qbId",
            "pressure_label",
            *pff_outcome,
            *rusher_position,
            *rusher_alignment,
            "num_pass_rushers",
            "frameId",
            "time",
            "event",
            "playDirection",
            pl.col("x").alias("rusher_x"),
            pl.col("y").alias("rusher_y"),
            pl.col("s").alias("rusher_speed"),
            pl.col("a").alias("rusher_acceleration"),
            pl.col("o").alias("rusher_orientation"),
            pl.col("dir").alias("rusher_direction"),
        )
    )
    qb = tracking.select(
        *keys,
        pl.col("nflId").alias("qbId"),
        "frameId",
        pl.col("x").alias("qb_x"),
        pl.col("y").alias("qb_y"),
        pl.col("s").alias("qb_speed"),
    )
    return (
        rusher.join(qb, on=[*keys, "qbId", "frameId"], how="inner")
        .join(snap_frames, on=keys, how="inner")
        .filter(pl.col("frameId") >= pl.col("snap_frame"))
        .with_columns(
            frame_from_snap=pl.col("frameId") - pl.col("snap_frame"),
            relative_x=pl.col("rusher_x") - pl.col("qb_x"),
            relative_y=pl.col("rusher_y") - pl.col("qb_y"),
        )
        .with_columns(
            distance_to_qb=(pl.col("relative_x").pow(2) + pl.col("relative_y").pow(2)).sqrt()
        )
        .sort("gameId", "playId", "rusherId", "frameId")
    )


def add_threat_metrics(frames: pl.DataFrame, smoothing_frames: int = 3) -> pl.DataFrame:
    """Add smoothed distance, radial closing speed, STRAIN, and implied TTC.

    STRAIN is the relative rate at which rusher-QB distance contracts:
    ``closing_speed / smoothed_distance``. TTC is populated only when the
    rusher is closing on the QB. Centered smoothing is for retrospective
    calibration and visual validation, not a real-time model.
    """
    if smoothing_frames < 1 or smoothing_frames % 2 == 0:
        raise ValueError("smoothing_frames must be a positive odd integer")
    required = {*EVENT_KEYS, "frameId", "distance_to_qb"}
    missing = required.difference(frames.columns)
    if missing:
        raise ValueError(f"Frame data missing columns: {sorted(missing)}")

    ordered = frames.sort(*EVENT_KEYS, "frameId")
    smoothed = pl.col("distance_to_qb").rolling_mean(
        window_size=smoothing_frames, center=True, min_samples=1
    ).over(EVENT_KEYS)
    prior_frame = pl.col("frameId").shift(1).over(EVENT_KEYS)
    prior_distance = pl.col("smoothed_distance_to_qb").shift(1).over(EVENT_KEYS)
    frame_delta = pl.col("frameId") - prior_frame
    closing_speed = pl.when(frame_delta == 1).then(
        (prior_distance - pl.col("smoothed_distance_to_qb")) / 0.1
    )

    return (
        ordered.with_columns(smoothed_distance_to_qb=smoothed)
        .with_columns(
            frame_delta=frame_delta,
            closing_speed=closing_speed,
        )
        .with_columns(
            strain=pl.col("closing_speed") / pl.col("smoothed_distance_to_qb"),
            implied_ttc_seconds=pl.when(pl.col("closing_speed") > 0)
            .then(pl.col("smoothed_distance_to_qb") / pl.col("closing_speed"))
            .otherwise(None),
        )
    )


def first_sustained_onset(frames: pl.DataFrame, rule: ThreatRule) -> pl.DataFrame:
    """Return the first frame meeting a sustained tracking-based threat rule."""
    required = {
        *EVENT_KEYS,
        "frameId",
        "frame_from_snap",
        "distance_to_qb",
        "smoothed_distance_to_qb",
        "strain",
        "implied_ttc_seconds",
    }
    missing = required.difference(frames.columns)
    if missing:
        raise ValueError(f"Threat-metric data missing columns: {sorted(missing)}")

    condition = (
        (pl.col("implied_ttc_seconds") <= rule.max_ttc_seconds)
        & (pl.col("smoothed_distance_to_qb") <= rule.max_distance_yards)
    ).fill_null(False)
    sustained_parts = []
    for offset in range(rule.persistence_frames):
        future_condition = condition.shift(-offset).over(EVENT_KEYS).fill_null(False)
        contiguous = (
            pl.col("frameId").shift(-offset).over(EVENT_KEYS) == pl.col("frameId") + offset
        ).fill_null(False)
        sustained_parts.append(future_condition & contiguous)

    sustained = pl.all_horizontal(sustained_parts)
    return (
        frames.with_columns(_sustained=sustained)
        .filter(pl.col("_sustained"))
        .sort(*EVENT_KEYS, "frameId")
        .group_by(*EVENT_KEYS, maintain_order=True)
        .first()
        .select(
            *EVENT_KEYS,
            pl.col("frameId").alias("onset_frame"),
            pl.col("frame_from_snap").alias("onset_frame_from_snap"),
            pl.col("distance_to_qb").alias("onset_distance_to_qb"),
            pl.col("strain").alias("onset_strain"),
            pl.col("implied_ttc_seconds").alias("onset_ttc_seconds"),
        )
    )


def _terminal_frames(frames: pl.DataFrame) -> pl.DataFrame:
    """Find the first actual pass or sack event, with automated pass as fallback."""
    actual = (
        frames.filter(pl.col("event").is_in(["pass_forward", "qb_sack", "qb_strip_sack"]))
        .group_by(*EVENT_KEYS)
        .agg(pl.col("frameId").min().alias("terminal_frame"))
    )
    automated = (
        frames.filter(pl.col("event") == "autoevent_passforward")
        .group_by(*EVENT_KEYS)
        .agg(pl.col("frameId").min().alias("terminal_frame"))
        .join(actual.select(*EVENT_KEYS), on=EVENT_KEYS, how="anti")
    )
    return pl.concat([actual, automated])


def fixed_horizon_frames(frames: pl.DataFrame, seconds_before_terminal: float = 0.5) -> pl.DataFrame:
    """Select the final tracking frame at a fixed horizon before pass or sack.

    This is the primary geometry anchor. It estimates pressure direction at a
    common moment before the terminal event; it does not attempt to infer the
    exact onset of pressure.
    """
    if seconds_before_terminal <= 0:
        raise ValueError("seconds_before_terminal must be positive")
    required = {*EVENT_KEYS, "frameId", "event"}
    missing = required.difference(frames.columns)
    if missing:
        raise ValueError(f"Frame data missing columns: {sorted(missing)}")

    horizon_frames = round(seconds_before_terminal * 10)
    if horizon_frames < 1:
        raise ValueError("seconds_before_terminal must cover at least one tracking frame")

    anchored = (
        frames.join(_terminal_frames(frames), on=EVENT_KEYS, how="inner")
        .with_columns(target_frame=pl.col("terminal_frame") - horizon_frames)
        .filter(pl.col("frameId") <= pl.col("target_frame"))
        .sort(*EVENT_KEYS, "frameId", descending=[False, False, False, True])
        .group_by(*EVENT_KEYS, maintain_order=True)
        .first()
        .with_columns(
            frames_before_terminal=pl.col("terminal_frame") - pl.col("frameId"),
            seconds_before_terminal_actual=(pl.col("terminal_frame") - pl.col("frameId")) / 10,
        )
        .drop("target_frame")
    )
    return anchored


def first_relative_peak_onset(frames: pl.DataFrame, rule: PeakOnsetRule) -> pl.DataFrame:
    """Locate the first sustained rise into a PFF rusher's own threat ramp.

    This is an onset *timing* estimator, intended for known PFF-positive
    rushers. It uses only frames at or before the terminal pass/sack event.
    """
    required = {
        *EVENT_KEYS,
        "frameId",
        "frame_from_snap",
        "event",
        "smoothed_distance_to_qb",
        "distance_to_qb",
        "closing_speed",
        "strain",
    }
    missing = required.difference(frames.columns)
    if missing:
        raise ValueError(f"Threat-metric data missing columns: {sorted(missing)}")

    preterminal = (
        frames.join(_terminal_frames(frames), on=EVENT_KEYS, how="left")
        .filter(pl.col("terminal_frame").is_null() | (pl.col("frameId") <= pl.col("terminal_frame")))
        .sort(*EVENT_KEYS, "frameId")
        .with_columns(
            peak_strain=pl.col("strain").clip(lower_bound=0).max().over(EVENT_KEYS)
        )
    )
    threshold = pl.max_horizontal(
        pl.lit(rule.min_strain), pl.col("peak_strain") * rule.peak_fraction
    )
    condition = (
        (pl.col("strain") >= threshold)
        & (pl.col("closing_speed") > 0)
        & (pl.col("smoothed_distance_to_qb") <= rule.max_distance_yards)
    ).fill_null(False)
    sustained_parts = []
    for offset in range(rule.persistence_frames):
        future_condition = condition.shift(-offset).over(EVENT_KEYS).fill_null(False)
        contiguous = (
            pl.col("frameId").shift(-offset).over(EVENT_KEYS) == pl.col("frameId") + offset
        ).fill_null(False)
        sustained_parts.append(future_condition & contiguous)

    onset = (
        preterminal.with_columns(_sustained=pl.all_horizontal(sustained_parts))
        .filter(pl.col("_sustained"))
        .sort(*EVENT_KEYS, "frameId")
        .group_by(*EVENT_KEYS, maintain_order=True)
        .first()
        .select(
            *EVENT_KEYS,
            pl.col("frameId").alias("onset_frame"),
            pl.col("frame_from_snap").alias("onset_frame_from_snap"),
            pl.col("distance_to_qb").alias("onset_distance_to_qb"),
            pl.col("strain").alias("onset_strain"),
            "peak_strain",
        )
    )
    peaks = (
        preterminal.sort(
            *EVENT_KEYS,
            "strain",
            descending=[False, False, False, True],
            nulls_last=True,
        )
        .group_by(*EVENT_KEYS, maintain_order=True)
        .first()
        .select(*EVENT_KEYS, pl.col("frameId").alias("peak_frame"))
    )
    return onset.join(peaks, on=EVENT_KEYS, how="left")


def calibrate_threat_rules(frames: pl.DataFrame, rules: list[ThreatRule]) -> pl.DataFrame:
    """Evaluate event-level tracking rules against PFF pressure labels."""
    if not rules:
        raise ValueError("at least one threat rule is required")
    if "pff_pressure" not in frames.columns:
        raise ValueError("Frame data must include the PFF pressure outcome")

    truth = frames.select(*EVENT_KEYS, "pff_pressure").unique()
    rows: list[dict[str, float | int]] = []
    for rule in rules:
        detected = first_sustained_onset(frames, rule).select(*EVENT_KEYS).with_columns(
            detected=True
        )
        outcomes = truth.join(detected, on=EVENT_KEYS, how="left").with_columns(
            detected=pl.col("detected").fill_null(False)
        )
        counts = outcomes.select(
            true_positive=((pl.col("pff_pressure")) & pl.col("detected")).sum(),
            false_positive=((~pl.col("pff_pressure")) & pl.col("detected")).sum(),
            false_negative=((pl.col("pff_pressure")) & (~pl.col("detected"))).sum(),
            true_negative=((~pl.col("pff_pressure")) & (~pl.col("detected"))).sum(),
        ).to_dicts()[0]
        tp, fp = counts["true_positive"], counts["false_positive"]
        fn, tn = counts["false_negative"], counts["true_negative"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        specificity = tn / (tn + fp) if tn + fp else 0.0
        rows.append(
            {
                "max_ttc_seconds": rule.max_ttc_seconds,
                "max_distance_yards": rule.max_distance_yards,
                "persistence_frames": rule.persistence_frames,
                **counts,
                "precision": precision,
                "recall": recall,
                "specificity": specificity,
                "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
                "balanced_accuracy": (recall + specificity) / 2,
            }
        )
    return pl.DataFrame(rows).sort("balanced_accuracy", descending=True)


def calibrate_threat_rules_by_group(
    frames: pl.DataFrame, rules: list[ThreatRule], group_column: str = "rush_alignment_group"
) -> pl.DataFrame:
    """Calibrate each candidate rule separately within an event-level stratum."""
    if group_column not in frames.columns:
        raise ValueError(f"Frame data must include grouping column: {group_column}")

    results = []
    for group in frames.select(group_column).unique().drop_nulls().to_series().to_list():
        group_results = calibrate_threat_rules(
            frames.filter(pl.col(group_column) == group), rules
        ).with_columns(pl.lit(group).alias(group_column))
        results.append(group_results)
    return pl.concat(results).sort(group_column, "balanced_accuracy", descending=[False, True])
