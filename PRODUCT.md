# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: plain static HTML/CSS/JS, matching the existing `demo/index.html` Joshimath
deep-dive page exactly -- no build step, no dependencies, no framework. Chosen for zero
risk of a broken build immediately before judging, and because the dashboard's
interactivity (table sort/filter, chart, site drill-in) doesn't need a framework's state
management to do well.

## Users

Hackathon judges for SIH26206 (Smart India Hackathon), Disaster Management theme. Two
usage modes, both real: (1) the team presenter walks judges through it live during the
pitch, revealing sections in a scripted sequence; (2) after the pitch or during Q&A, a
judge may take the laptop and explore it hands-on unassisted. Design for both -- a clear
guided order AND standalone discoverability.

## Product Purpose

Demonstrate that a simple, interpretable ML model trained on real multi-site data (7
Himalayan hill sites + 3 coastal sites, real disaster events + control sites) independently
confirms that human-activity land-change signals (vegetation loss, construction growth)
predict disaster occurrence -- and that this predictive signal generalizes across terrain
types (a model trained only on hill sites still correctly flags real coastal disasters).
Success = judges leave believing the data pipeline and model are real, rigorously
validated, and honestly reported -- not a mockup or an inflated claim.

## Positioning

Unlike tools that try to predict *when/where* a specific disaster will strike, this
project demonstrates that human-driven land change is a measurable, model-confirmed
amplifier of disaster risk -- validated across multiple real, independently-sourced sites
spanning two mechanistically different hazard types (slow-onset landslide/subsidence vs.
acute cyclone), not asserted from a single anecdote.

## Operating Context

Presented live during SIH26206 judging (a few-minute walkthrough), then potentially
explored hands-on by a judge afterward. Runs from a laptop; venue wifi/hotspot is assumed
reliable enough for one live API call (confirmed by the user -- no offline fallback
required for the live-rainfall element).

## Capabilities and Constraints

- 10 real, fully-instrumented sites: 7 hill (Joshimath, Raini, Kedarnath, Wazri, Dharali,
  Malpa, Auli_control) + 3 coastal (Sundarbans, Odisha_coast, Coastal_control_tbd/Kakinada).
  Each has real NDVI/NDBI trend slope, slope/elevation, and rainfall anomaly. Source of
  truth: `ml/feature_table.csv`.
- 2 additional candidate sites (`garhwal_control_tbd`, `sundarbans_control`) exist in the
  table but are NOT_PULLED (no coordinates confirmed yet) -- may be shown as pending/greyed
  or omitted; must never be presented as if they have real data.
- Trained logistic regression classifier: LOOCV accuracy **7/10 (70%)** -- state this
  exact fraction, never round up or imply a higher number.
- Feature importance (the centerpiece finding): `ndvi_trend_slope` is the strongest
  predictor (coefficient -1.032, standardized), ahead of rainfall anomaly, slope, NDBI,
  elevation, and terrain type. This is the model's own output, not an asserted claim.
  Chart already generated at `ml/feature_importance.png`.
- Cross-terrain validation: a model trained ONLY on the 7 hill sites, tested on the 3
  coastal sites, predicted [1,1,1] against actual [1,1,0] -- **2 of 3 correct**, not 3/3.
  Both real coastal disasters were correctly flagged; one false positive on the coastal
  control. State this exactly, including the miss.
- Coastal narrative constraint: coastal disasters in this dataset are driven predominantly
  by acute cyclone intensity, not a slow human-activity land-use trend -- real NDBI/mangrove
  data was checked and does NOT cleanly separate coastal disaster from control sites (see
  `sihPlan/memory.md` sec 15). Do not force a symmetric "human activity" narrative onto the
  coastal side; the honest framing is that the two hazard types have different mechanisms,
  and the model still generalized to coastal sites despite having no coastal-specific
  human-activity signal to lean on -- which is the more interesting finding.
- An existing separate page, `demo/index.html`, is a single-site deep-dive on Joshimath
  (a Current -> BAU-2030 -> Intervention-2030 slider). This new multi-site dashboard must
  link out to it as "the fully-instrumented example," not rebuild or absorb it.
- A live "today's rainfall" element (real API call, not yet implemented) should be wired
  in on this new page for demo credibility -- this is new work, separate from the
  historical NASA POWER pulls already baked into the feature table.
- No backend/server, no user accounts, no database. All data is precomputed and static;
  the only live network dependency is the one rainfall API call.

## Brand Commitments

Project title (from `sihPlan/project-plan.md`, already decided by the team): **"EcoRisk
AI: Learning How Human Activity Erodes Natural Disaster Resilience"** (SIH26206). Scripted
one-line pitch to echo, not rewrite: "Instead of studying one disaster, we trained a model
on how human activity changes the land across multiple sites in the Himalayas and coastal
India -- it learned, on its own, that vegetation loss and construction growth are the
strongest predictors of disaster severity, and correctly flags high-risk sites without
being told what happened there."

## Evidence on Hand

- `ml/feature_table.csv` -- real per-site data, source of truth for every number shown.
- `ml/feature_importance.png` -- already-generated chart (may be redesigned to match the
  dashboard's visual system, but the underlying values must not change).
- `ml/train_model.py` output -- LOOCV accuracy, risk-ranking table, cross-terrain result.
- `sihPlan/memory.md` -- fact ledger with exact numbers and caveats; this is the
  authoritative source if any number here and there ever conflict, memory.md wins.
- `datasourceSIH/` and `datasourceSIH/sites/<site_id>/` -- raw per-site pulled data
  (NDVI/NDBI time series, DEM slope, GMW mangrove where pulled).
- State explicitly: no production deployment, no user accounts, no live database. This is
  a hackathon demo artifact.

## Product Principles

1. Never show a number the model didn't actually produce -- every stat traces to
   `sihPlan/memory.md` or `ml/feature_table.csv`; never invent or round favorably.
2. Report limitations as plainly as findings -- 70% not "strong," 2/3 not 3/3. Credibility
   with judges depends on this (the team's own `ml-model-plan.md` says so explicitly).
3. The feature-importance result is the centerpiece, not decoration: it's the model's own
   output independently confirming the team's hypothesis.
4. Keep the hill and coastal narratives distinct rather than forcing symmetry the data
   doesn't support.
5. Ship something that works standalone in a browser with zero build step -- reliability
   before judging outranks technical sophistication.

## Accessibility & Inclusion

No project-specific requirement established beyond standard baseline practice.
