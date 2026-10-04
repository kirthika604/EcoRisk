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
| **Control site candidate:** Auli, Chamoli | ~30.5271°N, 79.5665°E | No (0) — verify | Popular hill town near Joshimath, no major documented event in the same window — confirm via GSI/news search | To be confirmed by team |
| **Control site candidate:** Another Garhwal town of similar elevation/slope, no recorded event | TBD | No (0) — verify | TBD | To be confirmed by team |

---

## B. Coastal Sites (Indian Ocean coast — mangrove/cyclone focus)

| Site | Approx. Coordinates | Disaster? | Event & Date | Source lead |
|---|---|---|---|---|
| Sundarbans (West Bengal side) | ~21.9497°N, 88.9468°E (verify exact sub-area) | Yes (1) | Cyclone Amphan, May 2020 — severe damage, mangrove buffer role widely studied | State disaster reports, mangrove-cyclone damage studies |
| Odisha coast (Puri/Bhitarkanika area) | ~19.7°N, 85.8°E (verify) | Yes (1) | Cyclone Fani, May 2019 | Odisha SDMA reports, news archives |
| **Control site candidate:** A Sundarbans sub-area with denser/protected mangrove cover, same cyclone exposure, lower damage | TBD | No (0) or lower severity — verify | Same cyclone events, differing mangrove cover — useful contrast pair | Mangrove-cover comparison studies |
| **Control site candidate:** A coastal stretch with no major cyclone landfall in the study period | TBD | No (0) — verify | TBD | To be confirmed by team |

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
