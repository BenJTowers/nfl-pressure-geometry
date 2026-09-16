# Data

This directory contains local data used by the NFL Pressure Geometry project.

Raw NFL Big Data Bowl data is **not included in this repository** and should never be committed to Git.

## Data Source

The primary dataset is the **NFL Big Data Bowl 2023** dataset distributed through Kaggle. It contains tracking data from the 2021 NFL season.

The project uses NFL player-tracking data together with play-level metadata and PFF scouting labels to investigate the geometry of quarterback pressure.

## Required Files

Place the downloaded Big Data Bowl files in:

```text
data/raw/nfl-big-data-bowl-2023/
```

The published eight-week analysis requires:

```text
games.csv
plays.csv
players.csv
pffScoutingData.csv
week1.csv through week8.csv
```

## Directory Structure

```text
data/
├── raw/
│   └── nfl-big-data-bowl-2023/
│       ├── games.csv
│       ├── plays.csv
│       ├── players.csv
│       ├── pffScoutingData.csv
│       └── week*.csv
│
├── interim/
│
├── processed/
│
└── README.md
```

### `raw/`

Original downloaded data.

These files should never be modified manually.

### `interim/`

Intermediate outputs generated while processing the tracking data.

Examples may include:

* filtered passing plays
* detected pressure events
* normalized player coordinates
* validation samples

These files can always be regenerated from the raw data.

### `processed/`

Analysis-ready datasets.

The schemas below are future-facing design notes. The current MVP writes
fixed-horizon geometry and EPA tables to the local `interim/` directory; see
the top-level README for the published analysis scope.

The project is expected to eventually produce two main processed tables:

#### Pressure-event table

One row per PFF-labeled successful pass-rush event (hurry, hit, or sack).

Expected fields include:

```text
game_id
play_id
qb_id
rusher_id

pressure_time
pressure_frame
pressure_label

qb_x
qb_y
rusher_x
rusher_y

relative_x
relative_y

pressure_angle
pressure_distance

rusher_speed
closing_speed
approach_angle

num_pass_rushers
```

#### Pressure-play table

One row per quarterback dropback.

Expected fields include:

```text
game_id
play_id
qb_id

num_pass_rushers

pressure_generated
num_pressure_rushers
first_pressure_time

num_synchronized_pressures
pressure_angular_spread

qb_displacement

sack
completion
interception
yards
epa
```

The exact schema may evolve as the analysis develops.

## Important Join Keys

The primary Big Data Bowl identifiers are:

```text
gameId
playId
nflId
frameId
```

Typical joins are:

```text
games.csv
    gameId

plays.csv
    gameId + playId

players.csv
    nflId

pffScoutingData.csv
    gameId + playId + nflId

week*.csv
    gameId + playId + nflId + frameId
```

## Git Policy

The following directories should remain ignored:

```text
data/raw/
data/interim/
data/processed/
```

Only documentation and code required to reproduce the datasets should be committed.
