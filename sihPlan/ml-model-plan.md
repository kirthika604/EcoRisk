# ML Model Plan — SIH26206

---

## 1. Problem Framing

**Task type:** Binary classification (did a disaster occur at this site, given its
human-activity and terrain features) — with feature importance as an equally important
output, not just prediction accuracy.

**Why classification, not regression:** with a small number of sites (likely 8-15), a
classifier is more robust and easier to validate than trying to predict a continuous
severity score. Keep it simple given the data size.

---

## 2. Features (Input)

| Feature | Type | Notes |
|---|---|---|
| `ndvi_trend_slope` | float | Negative = vegetation declining |
| `ndbi_trend_slope` | float | Positive = built-up area increasing |
| `mean_slope_degrees` | float | Hill sites only meaningful as slope; use elevation/coastal proxy for coastal sites |
| `elevation_mean_m` | float | |
| `rainfall_anomaly_pct` | float | Deviation from long-term average |
| `terrain_type` | categorical | "hill" or "coastal" — encode as 0/1 |

**Target:** `disaster_occurred` (0 or 1)

---

## 3. Model Choice

**Primary choice: Logistic Regression**
- Fully interpretable — coefficients directly show feature direction and magnitude
- Works reasonably well even with small N (8-15 sites)
- Easy to explain to judges: "positive coefficient on NDBI trend means more construction
  growth is associated with higher disaster likelihood"

**Secondary/backup: Random Forest (small, e.g., 50-100 trees, max depth 3-4)**
- Use if the relationship looks non-linear once you plot the data
- Still provides feature importance (via built-in importance scores), though less
  directly interpretable than logistic regression coefficients
- Only use this if logistic regression clearly underperforms — don't default to it just
  because it sounds more advanced; with this data size, added complexity is a liability,
  not a strength.

**Do not use:** neural networks, deep learning, or anything requiring large training
data. With ~10-15 rows, these would overfit immediately and be indefensible if a judge
asks about validation methodology.

---

## 4. Training & Validation Approach

Given the small dataset size, standard train/test splits (e.g., 80/20) may leave too few
test examples to mean anything. Use this approach instead:

1. **Leave-one-out cross-validation (LOOCV):** train on all sites except one, predict
   that one, repeat for every site. This is the standard, defensible approach for small
   datasets and gives you a real accuracy figure without wasting data.
2. **Cross-terrain validation (the generalization proof):** additionally, train the
   model using only hill sites, then test whether it meaningfully separates
   high/low-risk among the coastal sites (and vice versa). This doesn't need to be
   perfectly accurate — even a directionally sensible ranking is a legitimate finding
   worth presenting, as long as you're honest about what it does and doesn't show.
3. **Report both:** overall LOOCV accuracy AND the cross-terrain finding, clearly
   separated so judges understand which claim is which.

---

## 5. Feature Importance (the centerpiece output)

- **For Logistic Regression:** report the coefficient for each feature, with direction
  (positive/negative) and relative magnitude. Present as a simple horizontal bar chart —
  no need for anything fancier.
- **For Random Forest (if used):** report `feature_importances_` the same way.
- **This chart is more important to your pitch than model accuracy alone** — it's the
  direct evidence that the model "learned" what you hypothesized (NDVI decline + NDBI
  increase are the top predictors), rather than you asserting it from Joshimath alone.

---

## 6. Honest Limitations to State Upfront (don't wait for a judge to catch these)

- **Small sample size (N ≈ 8-15).** State this plainly. A small, honestly-validated
  model is more credible than an inflated claim.
- **Correlation, not causation.** The model finds association between human-activity
  signals and disaster occurrence — it does not prove human activity *caused* any
  specific event. Frame outputs as "risk-amplification signal."
- **Label noise.** Disaster event records (dates, exact location) are not perfectly
  precise, especially for older events — acknowledge this rather than presenting labels
  as ground truth beyond doubt.
- **Control site selection is a judgment call.** Be ready to explain why each "no
  disaster" site was chosen as a fair comparison.

---

## 7. Deliverables From the ML Team

1. A clean Python notebook/script: load feature table → train model → run LOOCV →
   produce feature importance chart → run cross-terrain validation
2. One feature-importance chart (the pitch centerpiece)
3. One simple risk-ranking table/chart of all sites (output of the model), including
   Joshimath, to show where it lands relative to others
4. A one-paragraph plain-language summary of what the model found, for the pitch script

---

## 8. Tooling

- Python: `pandas` for the feature table, `scikit-learn` for
  `LogisticRegression`, `RandomForestClassifier`, and `LeaveOneOut` cross-validation
- Plotting: `matplotlib` or `seaborn` — simple bar charts are enough, no need for
  anything elaborate (frontend/visual polish is explicitly deprioritized per
  `project-plan.md`)
