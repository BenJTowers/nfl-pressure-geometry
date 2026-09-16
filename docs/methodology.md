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
* number of pass rushers
* first pressure time
* simultaneous pressure
* pressure angular spread
* quarterback response
* play outcome

Maintaining these levels separately avoids incorrectly treating multiple pressures from the same play as statistically independent play outcomes.

---

## 2. Successful Pass-Rush Definition

The project will use NFL Big Data Bowl 2023 tracking data and PFF scouting data.

Pass rushers will be identified by `pff_role == "Pass Rush"`. A successful pass rush is a rusher-play record with at least one PFF outcome label equal to `1` among:

* `pff_hurry`
* `pff_hit`
* `pff_sack`

These labels identify rush events to analyze; they do not supply the frame at which pressure began.

The project will derive that frame from tracking data. It will not claim to recreate PFF's labeling process.

---

## 3. Fixed-Horizon Geometry Anchor

The primary directional analysis does not require an exact inferred pressure-onset time. PFF identifies rushers credited with a hurry, hit, or sack; the project will measure their QB-relative geometry at a common point before the terminal event.

The initial anchor is the tracking frame exactly:

$$
0.5\text{ seconds before pass release or sack}
$$

The initial directional analysis is limited to plays where `dropBackType == "TRADITIONAL"`. Scrambles and designed rollouts are excluded because quarterback movement can materially alter the QB-relative geometry. They will be addressed later as a separate quarterback-movement extension.

For each PFF-positive rusher:

1. identify the first tracked pass-release or sack event
2. select the frame 0.5 seconds before that terminal event
3. locate the quarterback and successful rusher at that shared frame
4. calculate their normalized QB-relative vector and pressure angle

The primary results will be checked at nearby horizons such as 0.3 and 0.7 seconds before the terminal event. If directional conclusions change substantially, that sensitivity will be reported.

### Secondary threat timing research

The following threat metrics remain useful secondary features and may later support severity, multi-rusher timing, or an exploratory onset analysis. They are not required to define the primary geometry frame.

Minimum distance alone will not be the initial definition because it can occur after the rusher has already influenced the quarterback. One candidate is a STRAIN-like threat score:

$$
\operatorname{threat}(t) = \frac{v_{\text{closing}}(t)}{d(t)}
$$

where positive `v_closing` indicates movement toward the quarterback. The selected onset rule, eligibility thresholds, and sensitivity to alternatives must be documented.

No onset rule should be considered valid until individual plays have been visually inspected.

### Threat signal and calibration

For every PFF pass rusher at every post-snap tracking frame, the project will calculate QB distance:

$$
d_t = \sqrt{(x_{r,t}-x_{q,t})^2 + (y_{r,t}-y_{q,t})^2}
$$

Distance will be modestly smoothed before differentiation to reduce tracking jitter. Calibration will compare unsmoothed distance with 3-frame and 5-frame centered smoothers to confirm that smoothing does not materially shift onset timing. At the 10 Hz tracking frequency, radial closing speed is:

$$
c_t = -\frac{d_t-d_{t-1}}{0.1}
$$

The continuous threat signal is the STRAIN-style relative contraction rate:

$$
S_t = \frac{c_t}{d_t}
$$

When \(c_t > 0\), the implied time to contact (TTC) is:

$$
TTC_t = \frac{d_t}{c_t} = \frac{1}{S_t}
$$

PFF hurry, hit, and sack labels define whether pressure occurred; the tracking signal estimates *when* that PFF-labeled threat became imminent. Candidate onset rules will combine a maximum TTC, maximum distance, and a consecutive-frame persistence requirement. For each rule, the project will classify whether every pass rusher ever crosses the rule and compare that result to the PFF pressure label using precision, recall, specificity, F1, and balanced accuracy.

Candidate rules will be calibrated on Week 1 and evaluated unchanged on later tracking weeks. A rule will not be selected solely because it performs well on the same week used to search the threshold grid.

The selected rule will be evaluated separately for edge and interior rushers before it is used for spatial comparisons. The initial edge group is `LE`, `RE`, `LEO`, `REO`, `LOLB`, `ROLB`, `LLB`, and `RLB`; the initial interior group is `DLT`, `DRT`, `NLT`, `NRT`, and `NT`. Other alignments will be reported separately. This check guards against a definition that systematically detects one rush path more readily than another.

Each successful rusher will retain three distinct moments:

* **Onset:** first sustained calibrated threat crossing, retained as an exploratory timing feature.
* **Peak:** maximum STRAIN frame, used as a severity measure.
* **Terminal event:** the tracked pass, sack, or related end-of-play event.

### Candidate within-pressure onset rule

Because PFF already establishes whether a rusher produced pressure, the project will also evaluate onset rules that estimate timing *within known PFF-positive rushes* rather than attempting to classify pressure from scratch. For each rusher, let \(S_{\max}\) be peak positive STRAIN before the terminal pass or sack event. A candidate onset is the first sustained frame satisfying:

$$
S_t \geq \max(\alpha S_{\max}, S_{\min})
$$

while the rusher is closing and within a broad distance guard. Here, \(\alpha\) controls how far into the rusher's own eventual threat ramp onset occurs. This rule will be assessed primarily through timing distributions, smoothing stability, and visual validation rather than event-level pressure-classification accuracy.

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

A play may contain multiple rushers credited by PFF with a hurry, hit, or sack.

At minimum, calculate:

```text
num_pressure_rushers
```

However, multiple successful rush events may occur at substantially different times.

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

Pass rushers will be counted at the play level using `pff_role`.

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

Compare outcomes by number of pass rushers.

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
week1.csv
```

The first target output is a table containing, for every validated Week 1 successful pass-rush event:

```text
game_id
play_id
qb_id
rusher_id
pressure_time
pressure_frame
pressure_label
relative_x
relative_y
pressure_angle
pressure_distance
```

Only after the pressure-onset rule and this table have been validated should the pipeline be expanded across additional weeks.

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
epa.py
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

---

## 21. Exploratory Directional Heat Maps

The first circular visualization uses PFF's supplied outcome labels at the
fixed 0.5-second pre-terminal anchor. It separates two quantities:

* the number of PFF-positive rushers by direction; and
* a descriptive outcome-severity score (hurry = 0, hit = 1, sack = 2).

The severity score is a visual aid, not a claim that the categories have
equal football value or that direction caused the outcome. Sparse angular
bins are masked rather than colored.

The next layer joins 2021 nflverse play-by-play through Big Data Bowl's
numeric `gameId` and `playId`, using nflverse's `old_game_id` as the game-ID
bridge. nflverse EPA is expressed from the offense's perspective. The primary
directional EPA view colors raw offensive EPA directly: negative values mean a
worse offensive result. A defensive-EPA version (`defense_epa = -epa`) remains
available for analyses framed from the defense's perspective.

Because several PFF-positive rushers can occur on the same play, each rusher
receives `1 / number_of_positive_rushers_on_play` weight in directional EPA
averages. Thus, no play contributes more than one total observation across
the map. These are still descriptive, play-level associations; subsequent
analysis should add uncertainty intervals, larger samples, and situation
controls before drawing substantive conclusions.

To distinguish directional association from the obvious value difference
between hurries, hits, and sacks, a second map centers EPA within the supplied
PFF outcome label. `outcome_adjusted_epa` is the play's offensive EPA minus
the play-equal season mean for that same label. Negative values identify a
result worse for the offense than the typical hurry, hit, or sack; this is a
first descriptive conditional analysis, not a causal adjustment.
