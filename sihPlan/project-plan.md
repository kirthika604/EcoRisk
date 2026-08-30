# SIH26206 — Human-Activity Risk Amplification & Awareness System
**Theme:** Disaster Management (Student Innovation) | **Track:** Software | **Team size:** 6

---

## 1. Core Idea

We don't predict *when* a disaster will strike. We show how human activity (deforestation,
unregulated construction, quarrying) is pushing a specific hill slope/watershed toward a
threshold that has historically caused failures — and what reversing that activity does to
the projected outcome.

**One-line pitch (memorize this):**
> "Every disaster tool predicts the event. We show how human activity is already pushing
> [district] toward a threshold that's caused failures before — and what changing that
> activity does to the outcome."

---

## 2. What We're Actually Building (scope discipline)

| Component | Status | Notes |
|---|---|---|
| Human-activity change detection (satellite before/after) | **Build for real** | NDVI / land-cover diff over time |
| Trend extrapolation (business-as-usual projection) | **Build for real** | Simple linear regression is enough |
| Threshold correlation (risk band logic) | **Mock with real numbers** | Use published GSI/NDMA figures as hardcoded constants — say so openly in the pitch |
| Live data layer | **One real live call only** | e.g. today's rainfall via free weather API — proves the system isn't fully static |
| Awareness/projection dashboard | **Build for real — this is the demo centerpiece** | Slider: Current → BAU 2030 → Intervention 2030 |

**Rule:** do not try to build all 4 pieces to the same depth. Two done well beat four done badly.

---

## 3. Case Study Lock-In (do this FIRST, within 3 hours of start)

Before any code is written, lock:
- [ ] One real hill district
- [ ] One documented past landslide/flood event (exact date + location)
- [ ] Confirm Sentinel-2 imagery is pullable for that location (before + after event + a few years back)
- [ ] Confirm historical daily rainfall is available for that district (IMD or public archive)
- [ ] Confirm at least one credible published threshold figure (deforestation % / rainfall mm) relevant to that geology

**If any of these fail to confirm within 3 hours → switch location immediately.** Do not wait.
See `data-sources.md` for exactly where to pull each of these.

---

## 4. Team Split (6 people)

- **Geospatial (x2):** Pull/process satellite imagery, compute NDVI/land-cover change, produce
  before-after visuals + human-activity trend line. Tooling: Google Earth Engine or QGIS.
- **Threshold/logic (x1):** Encode researched threshold numbers, build scoring function
  (trend value vs. threshold → risk band), build the trend extrapolation.
- **Dashboard/frontend (x2):** Build the visual centerpiece — map/slider comparing
  Current vs. BAU-2030 vs. Intervention-2030. This is what judges actually watch.
- **Pitch + live integration (x1):** Wire the one genuine live API call (rainfall), build
  the narrative/slides in parallel from hour 0, not the night before.

---

## 5. Timeline (~36–48 hrs)

- **Hrs 0–3:** Lock case study. Confirm all data access works (test-pull now, don't assume later).
- **Hrs 3–14:** Parallel build. Geospatial processes imagery; dashboard builds UI skeleton
  with placeholder data; threshold logic finalized.
- **Hrs 14–20:** First integration of real data into dashboard. Expect breakage — budget for it.
- **Hrs 20–28:** Mandatory rest block in shifts. Exhausted teams demo worse, not better.
- **Hrs 28–36:** Polish visuals, wire live rainfall call, rehearse pitch out loud 3+ times.
- **Final hours:** Feature freeze. Bug fixes and pitch rehearsal only.

---

## 6. Pitch Structure

1. Reframe (the one-liner above) — NOT the tech first.
2. Problem: disaster tools predict events; nobody shows the human amplifier or the "what if we stop" picture.
3. The two-layer insight: slow human-activity trend + fast weather trigger.
4. Live demo: slider (Current → BAU 2030 → Intervention 2030).
5. One real live data pull, to prove it isn't fully static.
6. Close: who deploys this (panchayat / state disaster authority / insurance-relief agencies)
   and why it's sustainable, not just clever.

**Be ready for these questions:**
- "So you're predicting the disaster?" → No — we show risk trajectory against a known
  historical threshold, not a specific date or event.
- "Are you blaming the local government/panchayat?" → Frame as *supporting better-informed
  local decisions*, not exposing blame.
- "Who would actually use this after the hackathon?" → State disaster management authorities,
  panchayats, relief/insurance agencies.

---

## 7. Biggest Risks to Watch

- **Skill gap:** if neither geospatial teammate has touched satellite/NDVI data before,
  this timeline breaks. Do a dry run on Google Earth Engine for the chosen district *before*
  the hackathon starts.
- **Threshold numbers not found:** if no citable figure exists for your specific slope/geology,
  soften the claim to a defensible range rather than inventing a precise number.
- **Geolocating the historical event:** news reports often only name a village/taluk, not
  coordinates — budget manual cross-referencing time (news photos, road names) to pin the
  exact satellite pixel/slope.

---

## 8. Open Items / Not Yet Decided

- Final district + event lock-in
- Exact threshold figure/source to cite
- Which weather API to use for the live rainfall call
- Final pitch deck / slide assignments
