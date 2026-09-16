"""Loading and schema validation for NFL Big Data Bowl 2023 data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

REQUIRED_FILES = ("games.csv", "plays.csv", "players.csv", "pffScoutingData.csv")


def default_data_dir() -> Path:
    """Return the downloaded Big Data Bowl 2023 directory used by this project."""
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "raw"
        / "nfl-big-data-bowl-2023"
    )


@dataclass(frozen=True)
class WeekInputs:
    """The raw tables required for a single week of analysis."""

    games: pl.DataFrame
    plays: pl.DataFrame
    players: pl.DataFrame
    scouting: pl.DataFrame
    tracking: pl.DataFrame


def _read_csv(path: Path) -> pl.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required Big Data Bowl file not found: {path}")
    return pl.read_csv(path, null_values="NA")


def load_week_inputs(data_dir: Path | str | None = None, week: int = 1) -> WeekInputs:
    """Load raw Big Data Bowl 2023 tables for one tracking week.

    The downloaded dataset names tracking files ``week1.csv`` through
    ``week8.csv``. PFF's ``NA`` placeholders are converted to null values.
    """
    if week < 1:
        raise ValueError("week must be a positive integer")

    root = Path(data_dir) if data_dir is not None else default_data_dir()
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(f"Missing required files under {root}: {joined}")

    return WeekInputs(
        games=_read_csv(root / "games.csv"),
        plays=_read_csv(root / "plays.csv"),
        players=_read_csv(root / "players.csv"),
        scouting=_read_csv(root / "pffScoutingData.csv"),
        tracking=_read_csv(root / f"week{week}.csv"),
    )
