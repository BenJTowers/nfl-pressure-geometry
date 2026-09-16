import polars as pl

from pressure_geometry.analysis import (
    add_pressure_outcome_severity,
    add_pressure_sector,
    pressure_sector_summary,
)


def test_pressure_sectors_wrap_cleanly_around_zero_degrees() -> None:
    geometry = pl.DataFrame({"pressure_angle": [0.0, 44.9, 45.0, 134.9, 135.0, 224.9, 225.0, 314.9, 315.0]})

    result = add_pressure_sector(geometry)

    assert result["pressure_sector"].to_list() == [
        "front",
        "front",
        "offensive_left",
        "offensive_left",
        "backfield",
        "backfield",
        "offensive_right",
        "offensive_right",
        "front",
    ]


def test_sector_summary_calculates_within_outcome_proportions() -> None:
    geometry = pl.DataFrame(
        {
            "pressure_label": ["hurry", "hurry", "hit"],
            "pressure_angle": [0.0, 90.0, 180.0],
        }
    )

    result = pressure_sector_summary(geometry)

    assert result.to_dicts() == [
        {"pressure_label": "hit", "pressure_sector": "backfield", "events": 1, "total_events": 1, "proportion": 1.0},
        {"pressure_label": "hurry", "pressure_sector": "front", "events": 1, "total_events": 2, "proportion": 0.5},
        {"pressure_label": "hurry", "pressure_sector": "offensive_left", "events": 1, "total_events": 2, "proportion": 0.5},
    ]


def test_pressure_outcome_severity_uses_descriptive_pff_ordering() -> None:
    geometry = pl.DataFrame({"pressure_label": ["hurry", "hit", "sack", "other"]})

    result = add_pressure_outcome_severity(geometry)

    assert result["pressure_outcome_severity"].to_list() == [0, 1, 2, None]
