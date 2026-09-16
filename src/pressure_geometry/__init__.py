"""Tools for analyzing the geometry of NFL quarterback pressure."""

from .analysis import (
    add_pressure_outcome_severity,
    add_pressure_sector,
    fixed_horizon_pressure_geometry,
    fixed_horizon_sensitivity,
    pressure_sector_summary,
)
from .coordinates import add_normalized_pressure_geometry
from .epa import add_nflverse_epa, add_outcome_adjusted_epa
from .load import WeekInputs, load_week_inputs
from .plays import (
    candidate_events_for_tracking_week,
    candidate_pressure_events,
    pass_rushers_for_tracking_week,
    traditional_dropback_events,
)
from .plotting import (
    plot_defensive_epa_heatmap,
    plot_offensive_epa_heatmap,
    plot_pressure_angle_distribution,
    plot_pressure_outcome_heatmap,
    plot_threat_timeline,
    save_validation_sample,
)
from .pressure import (
    PeakOnsetRule,
    ThreatRule,
    add_threat_metrics,
    calibrate_threat_rules,
    calibrate_threat_rules_by_group,
    first_relative_peak_onset,
    first_sustained_onset,
    fixed_horizon_frames,
    qb_rusher_post_snap_frames,
)
from .summaries import angular_offensive_epa_summary

__all__ = [
    "PeakOnsetRule",
    "ThreatRule",
    "WeekInputs",
    "add_nflverse_epa",
    "add_normalized_pressure_geometry",
    "add_outcome_adjusted_epa",
    "add_pressure_outcome_severity",
    "add_pressure_sector",
    "add_threat_metrics",
    "angular_offensive_epa_summary",
    "calibrate_threat_rules",
    "calibrate_threat_rules_by_group",
    "candidate_events_for_tracking_week",
    "candidate_pressure_events",
    "first_relative_peak_onset",
    "first_sustained_onset",
    "fixed_horizon_frames",
    "fixed_horizon_pressure_geometry",
    "fixed_horizon_sensitivity",
    "load_week_inputs",
    "pass_rushers_for_tracking_week",
    "plot_defensive_epa_heatmap",
    "plot_offensive_epa_heatmap",
    "plot_pressure_angle_distribution",
    "plot_pressure_outcome_heatmap",
    "plot_threat_timeline",
    "pressure_sector_summary",
    "qb_rusher_post_snap_frames",
    "save_validation_sample",
    "traditional_dropback_events",
]
