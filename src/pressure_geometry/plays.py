"""Play-level PFF scouting transformations."""

from __future__ import annotations

import polars as pl

SUCCESS_COLUMNS = ("pff_hurry", "pff_hit", "pff_sack")
EDGE_ALIGNMENTS = {"LE", "RE", "LEO", "REO", "LOLB", "ROLB", "LLB", "RLB"}
INTERIOR_ALIGNMENTS = {"DLT", "DRT", "NLT", "NRT", "NT"}


def successful_rusher_events(scouting: pl.DataFrame) -> pl.DataFrame:
    """Return one row per PFF-labeled successful pass-rush event.

    A successful event is a player assigned the ``Pass Rush`` role and credited
    with at least one hurry, hit, or sack. ``pressure_label`` retains every
    positive label, so combinations such as ``hurry|hit`` remain visible.
    """
    return (
        pass_rusher_events(scouting)
        .filter(pl.col("pff_pressure"))
        .select(
            "gameId",
            "playId",
            "rusherId",
            "pff_positionLinedUp",
            "rush_alignment_group",
            "pressure_label",
        )
    )


def pass_rusher_events(scouting: pl.DataFrame) -> pl.DataFrame:
    """Return every PFF pass rusher with its PFF pressure outcome label."""
    required = {
        "gameId",
        "playId",
        "nflId",
        "pff_role",
        "pff_positionLinedUp",
        *SUCCESS_COLUMNS,
    }
    missing = required.difference(scouting.columns)
    if missing:
        raise ValueError(f"Scouting data missing columns: {sorted(missing)}")

    labels = pl.concat_str(
        [
            pl.when(pl.col(column).cast(pl.Utf8) == "1")
            .then(pl.lit(column.removeprefix("pff_")))
            .otherwise(pl.lit(""))
            for column in SUCCESS_COLUMNS
        ],
        separator="|",
    ).str.strip_chars("|")
    alignment_group = (
        pl.when(pl.col("pff_positionLinedUp").is_in(EDGE_ALIGNMENTS))
        .then(pl.lit("edge"))
        .when(pl.col("pff_positionLinedUp").is_in(INTERIOR_ALIGNMENTS))
        .then(pl.lit("interior"))
        .otherwise(pl.lit("other"))
    )
    return (
        scouting.filter(pl.col("pff_role") == "Pass Rush")
        .with_columns(pressure_label=labels)
        .with_columns(pff_pressure=pl.col("pressure_label") != "")
        .with_columns(rush_alignment_group=alignment_group)
        .select(
            "gameId",
            "playId",
            pl.col("nflId").alias("rusherId"),
            "pff_positionLinedUp",
            "rush_alignment_group",
            "pressure_label",
            "pff_pressure",
        )
        .unique()
    )


def quarterbacks_by_play(scouting: pl.DataFrame) -> pl.DataFrame:
    """Return the quarterback identified by PFF for each passing play."""
    required = {"gameId", "playId", "nflId", "pff_role", "pff_positionLinedUp"}
    missing = required.difference(scouting.columns)
    if missing:
        raise ValueError(f"Scouting data missing columns: {sorted(missing)}")

    qbs = (
        scouting.filter(
            (pl.col("pff_role") == "Pass") & (pl.col("pff_positionLinedUp") == "QB")
        )
        .select("gameId", "playId", pl.col("nflId").alias("qbId"))
        .unique()
    )
    duplicate_plays = qbs.group_by("gameId", "playId").len().filter(pl.col("len") > 1)
    if duplicate_plays.height:
        raise ValueError("PFF scouting data identifies more than one quarterback on a play")
    return qbs


def candidate_pressure_events(scouting: pl.DataFrame) -> pl.DataFrame:
    """Attach each successful rusher to the QB and play-level rush count."""
    rush_counts = (
        scouting.filter(pl.col("pff_role") == "Pass Rush")
        .group_by("gameId", "playId")
        .agg(pl.col("nflId").n_unique().alias("num_pass_rushers"))
    )
    return (
        successful_rusher_events(scouting)
        .join(quarterbacks_by_play(scouting), on=["gameId", "playId"], how="inner")
        .join(rush_counts, on=["gameId", "playId"], how="left")
        .filter(pl.col("rusherId") != pl.col("qbId"))
    )


def candidate_events_for_tracking_week(
    scouting: pl.DataFrame, tracking: pl.DataFrame
) -> pl.DataFrame:
    """Limit successful-rusher events to plays present in one tracking file."""
    required = {"gameId", "playId"}
    missing = required.difference(tracking.columns)
    if missing:
        raise ValueError(f"Tracking data missing columns: {sorted(missing)}")

    tracked_plays = tracking.select("gameId", "playId").unique()
    return candidate_pressure_events(scouting).join(
        tracked_plays, on=["gameId", "playId"], how="inner"
    )


def pass_rushers_for_tracking_week(scouting: pl.DataFrame, tracking: pl.DataFrame) -> pl.DataFrame:
    """Attach every tracked pass rusher to the QB and play-level rush count."""
    required = {"gameId", "playId"}
    missing = required.difference(tracking.columns)
    if missing:
        raise ValueError(f"Tracking data missing columns: {sorted(missing)}")

    rush_counts = (
        scouting.filter(pl.col("pff_role") == "Pass Rush")
        .group_by("gameId", "playId")
        .agg(pl.col("nflId").n_unique().alias("num_pass_rushers"))
    )
    tracked_plays = tracking.select("gameId", "playId").unique()
    return (
        pass_rusher_events(scouting)
        .join(quarterbacks_by_play(scouting), on=["gameId", "playId"], how="inner")
        .join(rush_counts, on=["gameId", "playId"], how="left")
        .join(tracked_plays, on=["gameId", "playId"], how="inner")
        .filter(pl.col("rusherId") != pl.col("qbId"))
    )


def traditional_dropback_events(events: pl.DataFrame, plays: pl.DataFrame) -> pl.DataFrame:
    """Restrict event rows to conventional (non-scramble, non-rollout) dropbacks."""
    required_events = {"gameId", "playId"}
    required_plays = {"gameId", "playId", "dropBackType"}
    missing_events = required_events.difference(events.columns)
    missing_plays = required_plays.difference(plays.columns)
    if missing_events or missing_plays:
        raise ValueError(
            f"Missing event columns: {sorted(missing_events)}; "
            f"missing play columns: {sorted(missing_plays)}"
        )
    return events.join(
        plays.select("gameId", "playId", "dropBackType"),
        on=["gameId", "playId"],
        how="inner",
    ).filter(pl.col("dropBackType") == "TRADITIONAL")
