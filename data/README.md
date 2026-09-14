# Data

This directory contains local data used by the NFL Pressure Geometry project.

Raw NFL Big Data Bowl data is **not included in this repository** and should never be committed to Git.

## Data Source

The primary dataset is the **NFL Big Data Bowl 2025** dataset distributed through Kaggle.

The project uses NFL player-tracking data together with play-level and player-play metadata to investigate the geometry of quarterback pressure.

## Required Files

Place the downloaded Big Data Bowl files in:

```text
data/raw/bdb2025/
```

Initial development requires:

```text
games.csv
plays.csv
players.csv
player_play.csv
tracking_week_1.csv
```

Additional weekly tracking files can be added once the Week 1 pipeline has been validated:

```text
tracking_week_2.csv
tracking_week_3.csv
...
```

## Directory Structure

```text
data/
├── raw/
│   └── bdb2025/
│       ├── games.csv
│       ├── plays.csv
│       ├── players.csv
│       ├── player_play.csv
│       └── tracking_week_*.csv
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

The project is expected to eventually produce two main processed tables:

#### Pressure-event table

One row per defender-generated pressure event.

Expected fields include:

```text
game_id
play_id
qb_id
rusher_id

pressure_time
pressure_frame

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

num_initial_rushers
```

#### Pressure-play table

One row per quarterback dropback.

Expected fields include:

```text
game_id
play_id
qb_id

num_initial_rushers

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

player_play.csv
    gameId + playId + nflId

tracking_week_*.csv
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
