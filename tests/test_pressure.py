import polars as pl

from pressure_geometry.pressure import (
    PeakOnsetRule,
    ThreatRule,
    add_threat_metrics,
    calibrate_threat_rules,
    first_relative_peak_onset,
    first_sustained_onset,
    fixed_horizon_frames,
)


def _frames() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "gameId": [1] * 5 + [1] * 5,
            "playId": [1] * 5 + [2] * 5,
            "rusherId": [11] * 5 + [12] * 5,
            "frameId": list(range(5)) + list(range(5)),
            "frame_from_snap": list(range(5)) + list(range(5)),
            "distance_to_qb": [5.0, 4.0, 3.0, 2.0, 1.0] + [5.0] * 5,
            "pff_pressure": [True] * 5 + [False] * 5,
        }
    )


def test_threat_metrics_calculate_closing_speed_strain_and_ttc() -> None:
    result = add_threat_metrics(_frames(), smoothing_frames=1)
    second_frame = result.filter((pl.col("playId") == 1) & (pl.col("frameId") == 1)).row(0, named=True)

    assert second_frame["closing_speed"] == 10.0
    assert second_frame["strain"] == 2.5
    assert second_frame["implied_ttc_seconds"] == 0.4


def test_sustained_onset_uses_the_first_of_two_consecutive_eligible_frames() -> None:
    metrics = add_threat_metrics(_frames(), smoothing_frames=1)
    onset = first_sustained_onset(
        metrics, ThreatRule(max_ttc_seconds=0.5, max_distance_yards=5.0, persistence_frames=2)
    )

    assert onset.to_dicts() == [
        {
            "gameId": 1,
            "playId": 1,
            "rusherId": 11,
            "onset_frame": 1,
            "onset_frame_from_snap": 1,
            "onset_distance_to_qb": 4.0,
            "onset_strain": 2.5,
            "onset_ttc_seconds": 0.4,
        }
    ]


def test_calibration_compares_tracking_detection_to_pff_labels() -> None:
    metrics = add_threat_metrics(_frames(), smoothing_frames=1)
    result = calibrate_threat_rules(
        metrics, [ThreatRule(max_ttc_seconds=0.5, max_distance_yards=5.0, persistence_frames=2)]
    )

    assert result.select("true_positive", "false_positive", "false_negative", "true_negative").to_dicts() == [
        {"true_positive": 1, "false_positive": 0, "false_negative": 0, "true_negative": 1}
    ]


def test_relative_peak_onset_uses_the_start_of_a_rushers_threat_ramp() -> None:
    frames = _frames().with_columns(
        event=pl.when(pl.col("frameId") == 4).then(pl.lit("pass_forward")).otherwise(pl.lit("None"))
    )
    metrics = add_threat_metrics(frames, smoothing_frames=1)

    onset = first_relative_peak_onset(
        metrics,
        PeakOnsetRule(peak_fraction=0.5, max_distance_yards=5.0, min_strain=0.1, persistence_frames=2),
    )

    assert onset.select("gameId", "playId", "rusherId", "onset_frame", "peak_frame").to_dicts() == [
        {"gameId": 1, "playId": 1, "rusherId": 11, "onset_frame": 3, "peak_frame": 4}
    ]


def test_fixed_horizon_selects_the_frame_half_a_second_before_terminal_event() -> None:
    frames = _frames().with_columns(
        event=pl.when(pl.col("frameId") == 4).then(pl.lit("pass_forward")).otherwise(pl.lit("None"))
    )

    result = fixed_horizon_frames(frames, seconds_before_terminal=0.2)

    assert result.select("gameId", "playId", "rusherId", "frameId", "terminal_frame").to_dicts() == [
        {"gameId": 1, "playId": 1, "rusherId": 11, "frameId": 2, "terminal_frame": 4},
        {"gameId": 1, "playId": 2, "rusherId": 12, "frameId": 2, "terminal_frame": 4},
    ]
