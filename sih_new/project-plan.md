# SIH26206 — EcoRisk AI: Learning How Human Activity Erodes Natural Disaster Resilience
**Theme:** Disaster Management (Student Innovation) | **Track:** Software | **Team size:** 6

---

## 1. Core Idea

Instead of researching one location, we train a model across multiple sites — Himalayan
slopes and coastal mangrove belts — to learn the relationship between human-activity
signals (vegetation loss, built-up growth) and disaster outcomes (subsidence/landslide,
cyclone damage severity). The model's own feature-importance output becomes the proof:
it independently confirms that human-driven land change predicts disaster severity,
without being told the story in advance.

**One-line pitch:**
> "Instead of studying one disaster, we trained a model on how human activity changes
> the land across multiple sites in the Himalayas and coastal India — it learned, on its
> own, that vegetation loss and construction growth are the strongest predictors of
> disaster severity, and correctly flags high-risk sites without being told what
> happened there."

---

## 2. Where Effort Goes (deliberately NOT frontend-heavy)

| Component | Priority | Notes |
|---|---|---|
| Multi-site data pipeline (NDVI, NDBI, slope, rainfall) | **Highest** | Reuse existing Earth Engine scripts, loop over site list |
| Feature table + labels (disaster / no-disaster per site) | **Highest** | See `dataset-sites.md` |
| ML model (classifier) + feature importance | **Highest** | Logistic Regression or Random Forest — interpretable, not a black box |
| Cross-terrain validation (hill vs. coastal) | **High** | This is the generalization claim — train/test split across terrain types |
| Joshimath deep-dive (already built) | **Medium** | Keep as the one fully-instrumented example the model validates against |
| Dashboard/frontend | **Low — minimal effort** | Simple table/chart output is enough (e.g., a risk-ranked list + one feature-importance chart). Do NOT spend hours on UI polish. |
| Live rainfall API call | **Low, but easy** | One API call, ~15 min, still worth including for demo credibility |

**Explicit instruction to the team: do not let frontend design time compete with data/ML time.**
A plain, functional table or basic chart output is sufficient. Judges are evaluating the model
and the data pipeline here, not visual design.

---

## 3. The ML Task, in Plain Terms

- **Unit of analysis:** one row per site
- **Features per site:**
  - NDVI trend (slope of vegetation index over available years)
  - NDBI trend (slope of built-up index over available years)
  - Terrain risk factor (mean slope angle for hill sites; elevation/coastal exposure for coastal sites)
  - Rainfall pattern (baseline vs. anomaly in the relevant window)
  - Human-activity intensity proxy (construction growth rate / land-use conversion rate)
- **Label per site:** disaster occurred (1) or did not (0) — from documented event records
- **Model:** Logistic Regression or Random Forest classifier (interpretable — feature
  importance is a required output, not optional)
- **Validation:** train on a subset of sites, test on held-out sites; ideally test that a
  model trained mostly on hill sites still meaningfully separates risk on coastal sites
  (this is the generalization proof)

See `ml-model-plan.md` for full detail on model choice, training approach, and evaluation.
See `dataset-sites.md` for the candidate site list.
See `data-sources.md` for exactly what to pull for each site and where from.

---

## 4. Team Split (6 people) — data/ML weighted

- **3 people — data pipeline:** run the existing Earth Engine NDVI/NDBI scripts across
  every site in `dataset-sites.md`; pull rainfall (NASA POWER) and DEM/slope for each;
  compile into one master feature table with labels.
- **2 people — ML model:** build the feature table into a clean dataframe, train the
  classifier, produce feature-importance output, run train/test validation across
  terrain types, prepare the model-explanation slide.
- **1 person — minimal dashboard + live element + pitch:** a simple table/chart showing
  site risk rankings and feature importance; wire the one live rainfall API call;
  build the pitch narrative in parallel from hour 0.

**Do not allocate more than 1 person to anything frontend-related.**

---

## 5. Timeline (~36–48 hrs)

- **Hrs 0–3:** Finalize site list (see `dataset-sites.md`), confirm data pulls work for
  2-3 test sites before committing to the full list.
- **Hrs 3–16:** Data pipeline team runs scripts across all sites, compiles feature table.
  ML team builds the training/evaluation code in parallel using placeholder/partial data,
  so the pipeline is ready the moment real data lands.
- **Hrs 16–24:** Full feature table complete → train model → generate feature importance
  and validation results.
- **Hrs 24–30:** Mandatory rest block in shifts.
- **Hrs 30–36:** Build the minimal output view (table/chart), wire live rainfall call,
  rehearse pitch narrative around the model's actual findings (not hypothetical ones).
- **Final hours:** Feature freeze. Bug fixes and rehearsal only.

---

## 6. Pitch Structure

1. Reframe: this is a framework that learns the human-activity-to-disaster link, validated
   across two different terrains — not a single-location tool.
2. Problem: disaster tools predict events; nobody shows, with evidence across many places,
   how human activity is the actual amplifier.
3. The data: N hill sites + N coastal sites, same features pulled the same way.
4. The model's own findings: feature importance ranking (let the model's output do the
   talking — this is more credible than asserting it yourself).
5. Validation: model trained on one terrain type still ranks the other terrain type's
   sites sensibly — the generalization proof.
6. Close: who deploys this, and why a framework (not a one-off tool) has staying power.

**Be ready for:**
- "Isn't this just correlation, not causation?" → Yes — be upfront. Frame it as
  "risk-amplification signal," not proof of causation. This is honest and still valuable.
- "How much data do you actually have?" → Be exact about your N (number of sites) —
  don't inflate it. A small, honest dataset with a clear method beats an exaggerated claim.
- "Why only these features?" → These are the same features published geotechnical studies
  already cite as relevant (see `data-sources.md` threshold citations).

---

## 7. Biggest Risks

- **Insufficient sites with reliable labels.** If fewer than ~8-10 usable sites can be
  found/verified in time, the "model" becomes too small to be credible — have a fallback
  plan to present it as "proof-of-concept on a small validated sample" rather than
  overclaiming statistical power.
- **Team spending time on dashboard polish instead of the pipeline/model.** This is the
  single biggest risk to catch early — check in at hour 12 and hour 24 on where time is
  actually going.
- **Rainfall/weather data availability varies by exact site** — confirm NASA POWER returns
  clean data for each candidate site before fully committing to it.

---

## 8. Open / Not Yet Decided

- Final confirmed list of sites (hill + coastal) — draft in `dataset-sites.md`
- Exact model type (Logistic Regression vs. Random Forest) — decide after seeing how
  many usable sites you actually end up with (fewer sites → simpler model)
- Which "no-disaster" control sites to use for contrast
