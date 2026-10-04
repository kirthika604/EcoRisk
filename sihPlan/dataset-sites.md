# Candidate Site List — SIH26206 Multi-Site Dataset

Real, named locations to start from. Coordinates are approximate for sites not yet
pinned precisely — confirm/refine each before running the Earth Engine pipeline.
**Verify every citation yourself before finalizing** — this list is a starting point
for your team's research, not a substitute for it.

---

## A. Hill Sites (Himalayan / Uttarakhand-focused)

| Site | Approx. Coordinates | Disaster? | Event & Date | Source lead |
|---|---|---|---|---|
| Joshimath, Chamoli | 30.5551°N, 79.5641°E | Yes (1) | Land subsidence, Dec 2022–Jan 2023 (already fully collected) | Already in your data |
| Raini village, Chamoli | ~30.5642°N, 79.7369°E | Yes (1) | Rishiganga flash flood/rock-ice avalanche, Feb 7, 2021 | News archives, academic papers on Rishiganga debris flow |
| Kedarnath area, Rudraprayag | ~30.7346°N, 79.0669°E | Yes (1) | Kedarnath disaster — extreme rainfall-triggered landslides/floods, June 15–17, 2013 | Martha et al. 2015 (cited in ResearchGate search) |
| Wazri, near Yamunotri, Uttarkashi | 30°54'22.87"N, 78°20'46.87"E | Yes (1) | Wazri landslide, Sep 12, 2017 | Academic paper: "Landslides Over Two Places of Uttarakhand: An Observation" |
| Dharali, Uttarkashi | ~30.83°N, 78.45°E (verify) | Yes (1) | Landslide + flash flood, cloudburst, Aug 2025 | Recent news coverage (ETV Bharat and others, Aug 2025) |
| Malpa village, Pithoragarh | ~29.85°N, 80.35°E (verify) | Yes (1) | Malpa landslide, 1998 — wiped out village | Rautela & Pande, 2005 |
| **Control site candidate:** Auli, Chamoli | ~30.5271°N, 79.5665°E | No (0) — weak evidence only | Popular hill town near Joshimath. WebSearch 2026-08-31 found no news/GSI hits for a major recorded event at Auli — but this is absence-of-hits, not a confirmed-clean record (no access to GSI's actual landslide inventory database to check directly). Still needs real confirmation. | Team to check GSI inventory directly if possible |
| **Control site candidate:** Another Garhwal town of similar elevation/slope, no recorded event | TBD — not found | No (0) — unresolved | Search 2026-08-31 did not surface a specific citable second site. Team to identify. | To be confirmed by team |

---

## B. Coastal Sites (Indian Ocean coast — mangrove/cyclone focus)

| Site | Approx. Coordinates | Disaster? | Event & Date | Source lead |
|---|---|---|---|---|
| Sundarbans (West Bengal side) | ~21.9497°N, 88.9468°E (verify exact sub-area) | Yes (1) | Cyclone Amphan, May 2020 — severe damage, mangrove buffer role widely studied | State disaster reports, mangrove-cyclone damage studies |
| Odisha coast (Puri/Bhitarkanika area) | ~19.7°N, 85.8°E (verify) | Yes (1) | Cyclone Fani, May 2019 | Odisha SDMA reports, news archives |
| **Control site candidate:** A Sundarbans sub-area with denser/protected mangrove cover, same cyclone exposure, lower damage | TBD — unresolved | No (0) or lower severity — unresolved | Checked 2026-08-31: the Frontiers (Bhargava et al. 2022) paper on Sundarbans cyclone susceptibility confirms damage is spatially heterogeneous, but publishes no named sub-region or coordinates for the lower-damage zone (contacted-author-only supplementary data). A guessed eastern-Sundarbans point (21.6°N, 89.05°E) was checked against real IBTrACS tracks and found NOT clean (Cyclone Bulbul, 2019, passed within 23km at Severe Cyclonic Storm strength) — so that guess doesn't hold up either. Genuinely unresolved. | Team needs the paper's supplementary spatial data, or a different source |
| **Control site candidate:** Coringa mangrove area, Kakinada, Andhra Pradesh | 16.75°N, 82.28°E | No (0) — real IBTrACS check, needs team sign-off | Checked 2026-08-31 against real NOAA IBTrACS track data (not a guess): nearest IMD-graded Severe-or-stronger cyclone (≥48kt) in 2015-2023 was Cyclone Asani (2022, SCS, 50kt) at 157km distance — no close/direct severe hit in this window. Also genuinely a mangrove-coastal site (Coringa Wildlife Sanctuary), matching Sundarbans' terrain type, unlike a generic non-mangrove coastline. 157km-no-severe-hit is real evidence but is not the same as "zero cyclone exposure ever" — team should confirm this reads as a fair comparison before locking it in. | NOAA IBTrACS v04r01 (real track data, checked directly, see sihPlan/memory.md §13) |

---

## C. Notes on Building This List Out

- **Aim for 8-12 total sites minimum** (mix of hill + coastal, disaster + control) —
  fewer than this makes the ML claim too weak to defend.
- **Precision matters less than you'd think for older/rural events** — if exact
  coordinates aren't findable, use the nearest named village/town center and document
  that as an approximation (same fallback approach used for Joshimath's land records).
- **Prioritize sites with the clearest documentation** over sites that are geographically
  "interesting" but poorly sourced — a defensible smaller list beats a padded uncertain one.
- **Every "no disaster" control site needs a one-line justification** for why it's a fair
  comparison (similar terrain, similar exposure, just no recorded event) — write this
  down as you confirm each one.

---

## D. Immediate Next Step

Pick 2-3 sites from this list (one hill disaster site, one hill control, one coastal
disaster site) and run the FULL pipeline (NDVI, NDBI, slope, rainfall) on just those
first, before committing to the whole list — this confirms the pipeline generalizes
beyond Joshimath before you invest time in the rest.
