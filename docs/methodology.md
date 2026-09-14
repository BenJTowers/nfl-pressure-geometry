# Methodology

## Overview

This project analyzes NFL quarterback pressure using player-tracking data.

The central methodological idea is to describe each pressure relative to the quarterback rather than using the football field's absolute coordinate system.

Each pressure can therefore be compared across games, teams, field positions, and directions of play.

The methodology will evolve as the analysis progresses. This document should be updated whenever an important analytical definition changes.

---

## 1. Unit of Analysis

Two related datasets will be maintained.

### Pressure-event level

One observation represents one defender generating pressure on one play.

A play may therefore contain multiple pressure-event rows.

This dataset is used to analyze:

* pressure angle
* pressure timing
* rusher position
* rusher velocity
* closing speed
* approach geometry

### Play level

One observation represents one quarterback dropback.

This dataset aggregates pressure events and is used to analyze:

* whether pressure occurred
* number of pressure defenders
* number of initial rushers
* first pressure time
* simultaneous pressure
* pressure angular spread
* quarterback response
* play outcome

Maintaining these levels separately avoids incorrectly treating multiple pressures from the same play as statistically independent play outcomes.

---

## 2. Pressure Definition

The project will initially use the pressure designation supplied in the Big Data Bowl player-play data.

The project will **not attempt to build its own pressure-detection model** during the initial analysis.

Relevant fields should be inspected directly before implementation, including fields describing:

* whether the player was an initial pass rusher
* whether the player caused pressure
* time to pressure

This allows the project to focus on the geometry and consequences of pressure rather than recreating pressure classification.

---

## 3. Pressure Timing

For each recorded pressure:

1. obtain the recorded time to pressure
2. determine the corresponding tracking frame
3. locate the quarterback at that frame
4. locate the pressure-causing defender at that frame

The exact conversion between pressure time and tracking frame must be verified against the dataset's frame/event definitions.

No assumption about frame timing should be considered valid until individual plays have been visually inspected.

---

## 4. Coordinate Normalization

NFL plays occur in both directions on the field.

Before comparing pressure geometry across plays, all plays must be transformed into a common coordinate system.

The normalized coordinate system should satisfy:

```text
Quarterback at pressure = (0, 0)

Offense always attacking the same direction
```

Conceptually:

```text
                 DOWNFIELD
                     ↑
                     |
          LEFT       |       RIGHT
                     |
                QB (0,0)
                     |
                     |
                 BACKFIELD
```

For the quarterback location:

$$
Q = (x_q,y_q)
$$

and pressure defender:

$$
R = (x_r,y_r)
$$

the QB-relative pressure vector is:

$$
\Delta x = x_r-x_q
$$

$$
\Delta y = y_r-y_q
$$

These coordinates must be calculated **after field-direction normalization**.

The implementation should clearly document which normalized axis represents downfield direction.

---

## 5. Pressure Source Angle

Pressure direction will be represented continuously.

Using normalized relative coordinates:

$$
\theta =
\operatorname{atan2}(\Delta y,\Delta x)
$$

The resulting value should be converted into a documented angle convention covering:

$$
0^\circ \leq \theta < 360^\circ
$$

Before league-wide analysis, manually verify that known examples produce the expected interpretation for:

* front pressure
* back pressure
* left-side pressure
* right-side pressure

The chosen angle orientation must remain consistent throughout the project.

---

## 6. Pressure Distance

Pressure distance at the selected frame is:

$$
d =
\sqrt{
(\Delta x)^2+
(\Delta y)^2
}
$$

This allows pressures occurring at different physical distances from the quarterback to be distinguished.

---

## 7. Closing Speed

Pressure threat depends not only on where a defender is but also on how quickly the defender is approaching.

One useful quantity is radial closing speed.

Let:

* \(\vec{v}_r\) = rusher velocity vector
* \(\hat{u}_{rq}\) = unit vector pointing from the rusher toward the quarterback

Then:

$$
v_{\text{closing}}
=
\vec{v}_r \cdot \hat{u}_{rq}
$$

Positive values indicate movement toward the quarterback.

This feature may provide a more meaningful representation of threat than raw defender speed.

---

## 8. Approach Angle

Two distinct angular measurements may be useful.

### Pressure-source angle

Where the defender is located relative to the quarterback.

### Approach angle

How directly the defender is moving toward the quarterback.

The approach angle can be calculated from the defender velocity vector and the defender-to-quarterback vector.

A defender may therefore be located on one side of the quarterback while moving across the pocket at a substantially different approach angle.

---

## 9. Multiple Pressure

A play may contain multiple defenders recorded as causing pressure.

At minimum, calculate:

```text
num_pressure_rushers
```

However, multiple recorded pressure events may occur at substantially different times.

The analysis should therefore distinguish:

* multiple pressures on one play
* simultaneous or near-simultaneous pressures

---

## 10. Synchronized Pressure

A synchronized-pressure group will initially be defined relative to the first pressure time.

For pressure events with times:

$$
t_1,t_2,\ldots,t_n
$$

let:

$$
t_{\min}=\min(t_i)
$$

A pressure may be considered synchronized when:

$$
t_i-t_{\min}\leq\Delta t
$$

The initial candidate threshold is approximately:

$$
\Delta t=0.3 \text{ seconds}
$$

This value should **not** be treated as definitive.

Robustness checks should compare results using alternatives such as:

```text
0.2 seconds
0.3 seconds
0.5 seconds
```

If conclusions change dramatically depending on the threshold, that uncertainty should be reported.

---

## 11. Angular Separation

For two pressure angles:

$$
\theta_1,\theta_2
$$

their circular angular separation is:

$$
\Delta\theta =
\min(
|\theta_1-\theta_2|,
360^\circ-|\theta_1-\theta_2|
)
$$

This is necessary because angular data are circular.

For example:

```text
1° and 359°
```

are only 2 degrees apart, not 358 degrees apart.

For plays with more than two simultaneous pressure defenders, candidate summary measures may include:

* maximum pairwise angular separation
* mean pairwise angular separation
* circular dispersion

The final measure should be chosen based on interpretability.

---

## 12. Circular Statistics

Pressure angle must not be treated as an ordinary linear variable.

In particular:

$$
0^\circ \equiv 360^\circ
$$

Any smoothing or density estimation used for the 360-degree pressure visualization should respect this circular structure.

Potential methods include:

* circular kernel smoothing
* von Mises distributions
* wrapped observations around the 0°/360° boundary

The visualization method should avoid creating an artificial discontinuity at the angular boundary.

---

## 13. Rush Count

Initial rushers will be counted at the play level.

The initial comparison is expected to focus on:

```text
4 rushers
vs.
5+ rushers
```

The project should avoid automatically labeling all five-plus-man rushes as "blitzes" unless the available data provides a sufficiently authoritative blitz definition.

Terminology such as:

> five-plus-man rush

or:

> extra-rusher pressure

is preferable when classification is based only on rusher count.

---

## 14. Rush Strategy vs. Pressure Quality

Two analyses must remain separate.

### Strategy analysis

Use **all eligible dropbacks**.

Compare outcomes by number of initial rushers.

This answers:

> Is sending additional rushers effective overall?

### Pressure-quality analysis

Use pressured dropbacks.

Compare whether additional rushers create:

* faster pressure
* more pressure defenders
* more simultaneous pressure
* greater angular spread
* different pressure locations

This answers:

> When pressure is successfully generated, how does its geometry differ by rush strategy?

Analyzing only successful pressures when evaluating rush strategy would create selection bias.

---

## 15. Play Outcomes

Potential outcome variables include:

```text
sack
completion
interception
passing yards
EPA
time to throw
QB displacement
```

Not all outcomes need to be included.

The final analysis should prioritize metrics that are:

1. interpretable
2. reliably available
3. meaningful for the football question

EPA may be joined from nflverse or another public source once the geometry pipeline has been validated.

---

## 16. Quarterback Movement

A potential extension is to measure how the quarterback responds to incoming pressure.

Possible quantities include:

* total displacement after pressure begins
* lateral displacement
* downfield/backfield displacement
* escape direction
* pressure-to-movement angular relationship

One potential question is:

> Does the quarterback move directly away from incoming pressure, step through it, or escape perpendicular to it?

This should remain secondary until the core pressure model is working.

---

## 17. Validation

Derived tracking metrics must be visually validated before aggregation.

Approximately 10–20 individual pressure plays should be inspected manually.

Each validation plot should display:

* quarterback trajectory
* pressure-rusher trajectory
* pressure frame
* QB position
* rusher position
* pressure vector
* calculated pressure angle

Validation should specifically include:

* plays moving in both field directions
* left-side pressures
* right-side pressures
* interior pressures
* multiple-pressure plays
* unusual or extreme pressure angles

No league-wide heat map should be trusted until these examples behave correctly.

---

## 18. Initial Development Scope

Initial development uses only:

```text
tracking_week_1.csv
```

The first target output is a table containing, for every validated Week 1 pressure event:

```text
game_id
play_id
qb_id
rusher_id
pressure_time
pressure_frame
relative_x
relative_y
pressure_angle
pressure_distance
```

Only after this table has been validated should the pipeline be expanded across additional weeks.

---

## 19. Statistical Analysis

The project is primarily explanatory rather than predictive.

Initial analysis should favor:

* descriptive statistics
* confidence intervals
* interpretable regressions
* smooth relationships
* circular statistics
* stratified comparisons

A complex machine-learning model should not be introduced unless it answers a question that simpler methods cannot.

Potential confounders to consider include:

* time to pressure
* number of rushers
* quarterback identity
* play situation
* down and distance
* dropback characteristics

Observed associations should not automatically be described as causal.

---

## 20. Reproducibility

Reusable transformations should live in:

```text
src/pressure_geometry/
```

rather than only inside notebooks.

Expected modules include:

```text
load.py
plays.py
coordinates.py
pressure.py
outcomes.py
plotting.py
```

Critical calculations such as coordinate normalization and circular angle differences should have automated tests in:

```text
tests/
```

Notebooks should primarily be used for:

* exploration
* validation
* analysis
* visualization
* communicating findings

The goal is for another user to be able to reproduce the analysis from the documented source data and repository code.
