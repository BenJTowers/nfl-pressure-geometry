# NFL Pressure Geometry — Research Plan

## Working Title

**Pressure From All Angles: The Geometry of NFL Quarterback Pressure**

## Project Motivation

Traditional pass-rush statistics often reduce quarterback pressure to binary or categorical outcomes such as pressure, sack, or pressure attributed to a particular offensive-line position.

NFL player-tracking data, combined with PFF pass-rush outcomes, makes it possible to examine pressure spatially.

Rather than describing pressure only as coming from the left, middle, or right, this project will represent each pressure using its actual position and movement relative to the quarterback.

The objective is to derive an interpretable pressure-onset measure and determine whether the **geometry of pressure** provides useful information about how disruptive a pass rush is.

## Primary Research Question

> How does the spatial geometry of pass-rush pressure affect quarterback and passing outcomes?

## Core Research Areas

### 1. Pressure Direction

Determine whether the angle from which pressure reaches the quarterback is associated with differences in play outcomes.

Questions include:

* Where does NFL pressure most frequently originate?
* Are some pressure directions more disruptive than others?
* Does sack probability vary with pressure angle?
* Does passing efficiency vary with pressure angle?
* Does the quarterback tend to move away from incoming pressure in predictable ways?

The long-term goal is to represent pressure continuously across 360 degrees rather than dividing the field into only left, middle, and right categories.

---

### 2. Multiple and Simultaneous Pressure

Many pressured dropbacks contain more than one defender reaching the quarterback.

This section will investigate:

* single-defender pressure
* multiple pressure events on the same play
* simultaneous or near-simultaneous pressure
* pressure arriving from similar directions
* pressure arriving from widely separated directions

A key question is:

> For the same number of pressure defenders, does pressure arriving from multiple directions produce worse outcomes than pressure concentrated in one area?

---

### 3. Pressure Timing and Intensity

Pressure direction alone does not describe the full threat.

Additional characteristics may include:

* time to pressure
* defender-to-quarterback distance
* defender speed
* closing speed
* approach angle

This allows two pressures arriving from the same location to be distinguished based on how quickly and aggressively they reach the quarterback.

---

### 4. Rush Strategy

The project will also examine whether sending additional rushers changes the geometry of the resulting pressure.

Rather than beginning with a broad "Do blitzes work?" question, the initial analysis will compare rush counts directly.

For example:

```text
4 pass rushers
vs.
5+ pass rushers
```

Two separate questions must be preserved:

#### Strategy-level analysis

Compare four-man and five-plus-man rushes across **all eligible dropbacks**.

This addresses whether sending additional rushers is effective overall.

#### Pressure-level analysis

Among plays that successfully produce pressure, compare the resulting pressure characteristics.

This addresses whether additional rushers create:

* faster pressure
* more pressure defenders
* more simultaneous pressure
* greater angular spread
* different quarterback outcomes

This distinction prevents the analysis from conditioning only on successful pressures.

---

## Pressure Representation

Each PFF-labeled successful pass-rush event will eventually be represented approximately as:

$$
P_i =
(\theta_i,\ t_i,\ d_i,\ v_i)
$$

where:

* \(\theta_i\) = pressure source angle relative to the quarterback
* \(t_i\) = derived pressure-onset time
* \(d_i\) = rusher-to-quarterback distance
* \(v_i\) = closing speed or related velocity measurement

Additional features may be added if they provide meaningful football interpretation.

## Expected Visualizations

Potential final visualizations include:

* 360-degree pressure frequency map
* 360-degree pressure effectiveness map
* sack probability by pressure angle
* pressure angle vs. quarterback escape direction
* single vs. multi-pressure comparisons
* pressure angular-spread distributions
* four-man vs. five-plus-man rush comparisons
* selected individual play diagrams
* quarterback-specific pressure profiles, if sample sizes permit

## Project Scope

The project should remain primarily an **interpretable exploratory football analytics project**.

The objective is not to build the most complex predictive model possible.

Priority should be given to:

1. correct tracking-data processing
2. interpretable spatial metrics
3. careful validation
4. strong visualizations
5. statistically responsible comparisons
6. clear football conclusions

Complex machine-learning methods should only be introduced if they directly help answer the research question.

## Development Milestones

### Milestone 1 — Data validation

Using `week1.csv` only:

* load required datasets
* identify pass rushers using `pff_role`
* identify successful rushers using `pff_hurry`, `pff_hit`, and `pff_sack`
* identify quarterbacks
* identify the terminal pass-release or sack frame
* locate QB and successful rusher at a common pre-terminal reference frame
* assess nearby reference horizons as a sensitivity check
* normalize field direction
* compute QB-relative coordinates
* calculate pressure angle

**Deliverable:** validated Week 1 successful-rush event table, including a documented pre-terminal geometry anchor.

### Milestone 2 — Visual validation

Select approximately 10–20 individual pressure plays and plot:

* QB trajectory
* pass-rusher trajectory
* pressure frame
* pressure vector
* calculated pressure angle

Verify that derived measurements visually match the play.

### Milestone 3 — League-wide pressure distribution

Scale the validated pipeline across available tracking weeks.

Produce the initial 360-degree pressure-frequency visualization.

### Milestone 4 — Multiple pressure

Identify:

* number of pressure defenders
* timing between pressure events
* synchronized pressure groups
* angular separation between simultaneous pressures

### Milestone 5 — Outcomes

Attach relevant play outcomes such as:

* sack
* completion
* interception
* yards
* EPA

Supplemental public NFL data may be joined if required.

### Milestone 6 — Rush strategy

Compare standard and extra-rusher pressure strategies.

### Milestone 7 — Final analysis

Produce:

* polished figures
* statistical comparisons
* methodology documentation
* limitations
* conclusions
* GitHub README suitable for public presentation

## Success Criteria

The project is successful if it produces a defensible answer to:

> Does where, when, and how pressure reaches an NFL quarterback meaningfully affect the outcome of the play?

A useful negative result is still a valid result.

The objective is to investigate the question rigorously rather than to prove that pressure direction must matter.
