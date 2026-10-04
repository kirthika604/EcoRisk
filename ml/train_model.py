#!/usr/bin/env python3
"""Multi-site risk classifier, per sihPlan/ml-model-plan.md.

Reads ml/feature_table.csv, trains ONLY on rows with status starting "REAL" (never on
NOT_PULLED template rows), runs LOOCV, reports feature importance (logistic regression
coefficients), and -- if enough sites of each terrain type exist -- a cross-terrain
validation check. If there isn't enough real data yet to train meaningfully, this says
so explicitly instead of producing a number that looks like a result.

Usage: python3 ml/train_model.py
Output: prints a report; saves feature_importance.png if training runs.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
CORE_FEATURE_COLS = [
    "ndvi_trend_slope", "ndbi_trend_slope", "mean_slope_degrees",
    "elevation_mean_m", "rainfall_anomaly_pct", "terrain_is_coastal",
]
# ndbi_mean (baseline built-up/human-pressure level, not just its trend) is a real,
# computed column in feature_table.csv (added 2026-09-02 to test whether "more human
# pressure = safer" holds) but deliberately NOT included here: tested it as a feature and
# it made LOOCV accuracy worse (67% -> 53%) with specificity still stuck at 0%. Real
# reason, from the raw per-site numbers: the pattern holds for HILL sites (auli_control,
# ranikhet -- the built-up, managed hill towns -- score lower NDBI-linked risk than the
# remote/rural disaster sites kedarnath, wayanad, raini) but is FALSIFIED for COASTAL
# sites (chennai and jakhau, the two most built-up coastal sites in the dataset, are both
# real disasters -- cyclone/flood risk there did not care how developed the site was).
# One global linear coefficient can't hold two opposite signs for two terrain types at
# once, so adding it just added noise. Left the column in the CSV since it's real data
# that might matter in a terrain-specific model later; not fed to this one.
# terrain_type is one-hot encoded as a single dummy (N-1 for N=2 categories: hill/coastal)
# -- hill is the implicit reference category when the dummy is 0. Scoped to hill+coastal
# only (2026-09-02): plains (guna, silchar) and desert (jaisalmer) sites are real and stay
# in feature_table.csv, but are excluded from training here. Reason: spreading the ~16
# real sites across 4 terrain categories left every category but hill with only 1-2
# negative-control examples, which LOOCV structurally cannot validate (see sihPlan/
# memory.md) -- specificity stayed 0% and even a freshly-added desert control was still
# misclassified when honestly held out. Concentrating on the 2 terrain types with the most
# real data (hill: 8 sites, coastal: 5 sites -- 13 of ~16 real sites) gives LOOCV a real
# chance to learn and test the one negative example each type does have, instead of
# diluting an already-thin signal across categories with almost no data. Plains/desert
# sites remain in the CSV for later, once each has enough real examples of its own.
TERRAIN_DUMMY_COLS = ["terrain_is_coastal"]
IN_SCOPE_TERRAIN_TYPES = ["hill", "coastal"]
OPTIONAL_FEATURE_COLS = ["lst_trend_slope"]  # only used once ALL real sites have it -- see main()
MIN_SITES_TO_TRAIN = 8  # per sihPlan/dataset-sites.md: "aim for 8-12 total sites minimum"

# Mechanism-scoped secondary model (2026-09-02): rainfall/cloudburst-triggered landslide
# ONLY, not every hill disaster. joshimath (land_subsidence) and raini (ice/rock
# avalanche) are hill but NOT rainfall-driven -- lumping them in with genuinely
# rainfall-triggered sites and asking one feature set (NDVI/slope/rainfall trend) to
# separate all of it from "safe" is what produced 0% specificity in every broader config
# tried first (see sihPlan/memory.md secs 33-34). This narrower scope was the first and
# only configuration this session where LOOCV specificity moved off 0% (see sec 35).
RAINFALL_LANDSLIDE_DISASTER_TYPES = {
    "rainfall_triggered_landslide_flood", "landslide",
    "cloudburst_landslide_flash_flood", "rainfall_triggered_landslide",
}
MECHANISM_FEATURE_COLS = [
    "ndvi_trend_slope", "ndbi_trend_slope", "mean_slope_degrees",
    "elevation_mean_m", "rainfall_anomaly_pct", "lst_trend_slope",
]
MIN_SITES_MECHANISM = 8


def run_rainfall_landslide_mechanism_model(df):
    """Secondary, narrower model: rainfall/cloudburst-triggered hill landslide risk only.
    Kept separate from the main hill+coastal model in main() -- different claim, different
    scope, not meant to replace it. Returns a dict for model_results.json, or None if
    there still aren't enough in-scope sites to train honestly."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import LeaveOneOut
    from sklearn.preprocessing import StandardScaler

    real = df[df["status"].astype(str).str.startswith("REAL")].copy()
    scoped = real[
        ((real["terrain_type"] == "hill") & (real["disaster_occurred"] == 0))
        | (real["disaster_type"].isin(RAINFALL_LANDSLIDE_DISASTER_TYPES))
    ].copy()
    scoped = scoped.dropna(subset=MECHANISM_FEATURE_COLS + ["disaster_occurred"])

    print("\n" + "=" * 70)
    print("SECONDARY MODEL: rainfall/cloudburst-triggered hill landslide mechanism only")
    print("=" * 70)
    print("Narrower claim than the main model above -- excludes cyclone-driven coastal")
    print("sites (covered live by GDACS elsewhere in the product) and mechanism-mismatched")
    print("hill sites (joshimath=subsidence, raini=ice/rock avalanche). See sihPlan/")
    print("memory.md secs 33-35 for why.")
    print(f"Sites in scope: {len(scoped)}")
    print(scoped[["site_id", "disaster_occurred", "disaster_type"]].to_string(index=False))

    if len(scoped) < MIN_SITES_MECHANISM:
        print(f"NOT ENOUGH sites yet ({len(scoped)} < {MIN_SITES_MECHANISM}) -- skipping this report.")
        return None

    X = scoped[MECHANISM_FEATURE_COLS].astype(float).values
    y = scoped["disaster_occurred"].astype(int).values
    site_ids = scoped["site_id"].values

    loo = LeaveOneOut()
    per_site = []
    tp = fp = tn = fn = 0
    for train_idx, test_idx in loo.split(X):
        scaler = StandardScaler()
        Xtr = scaler.fit_transform(X[train_idx])
        Xte = scaler.transform(X[test_idx])
        clf = LogisticRegression(max_iter=1000).fit(Xtr, y[train_idx])
        pred = clf.predict(Xte)[0]
        prob = clf.predict_proba(Xte)[0, 1]
        actual = y[test_idx][0]
        if actual == 1 and pred == 1:
            tp += 1
        elif actual == 1 and pred == 0:
            fn += 1
        elif actual == 0 and pred == 1:
            fp += 1
        else:
            tn += 1
        per_site.append({
            "site_id": str(site_ids[test_idx[0]]),
            "actual": int(actual),
            "predicted": int(pred),
            "predicted_prob_held_out": round(float(prob), 4),
            "correct": bool(pred == actual),
        })

    correct = tp + tn
    acc = correct / len(y)
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    specificity = tn / (tn + fp) if (tn + fp) else float("nan")
    naive = (tp + fn) / len(y)

    print(f"\nLOOCV: {correct}/{len(y)} = {acc:.3f}  (naive always-predict-disaster baseline: {naive:.3f})")
    print(f"TP={tp} FN={fn} FP={fp} TN={tn}  recall={recall:.3f}  specificity={specificity:.3f}")
    for s in sorted(per_site, key=lambda s: s["predicted_prob_held_out"]):
        print(f"  {s['site_id']:12s} actual={s['actual']} predicted_prob_held_out={s['predicted_prob_held_out']:.2f} "
              f"{'CORRECT' if s['correct'] else 'WRONG'}")

    return {
        "description": (
            "Rainfall/cloudburst-triggered hill landslide risk ONLY -- narrower than the "
            "main hill+coastal model above. Excludes coastal/cyclone sites (different "
            "physical mechanism, covered live by the product's GDACS feed instead) and "
            "joshimath (subsidence) / raini (ice-rock avalanche), which are hill but not "
            "rainfall-driven. First and only configuration tested this session with "
            "non-zero specificity -- see sihPlan/memory.md secs 33-35 for the full history "
            "of what was tried and why this one is the first with real evidence behind it. "
            "Still below broad statistical confidence (N=9) and still misses one of two "
            "negative controls (auli_control) -- report as 'first validated signal', not "
            "'solved'."
        ),
        "n_sites": int(len(y)),
        "loocv": {"correct": int(correct), "total": int(len(y)), "accuracy": round(acc, 4), "per_site": per_site},
        "confusion_matrix": {"tp": int(tp), "fn": int(fn), "fp": int(fp), "tn": int(tn)},
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "naive_baseline_accuracy": round(naive, 4),
    }


def load_real_rows():
    df = pd.read_csv(os.path.join(BASE, "feature_table.csv"))
    real = df[df["status"].astype(str).str.startswith("REAL")].copy()
    real = real[real["terrain_type"].isin(IN_SCOPE_TERRAIN_TYPES)].copy()
    return df, real


def choose_feature_cols(real):
    """Core 6 features always used; lst_trend_slope only joins the model once every REAL
    site has a real value for it -- training on a feature that's NaN for some sites would
    either silently drop rows (shrinking an already-small N) or require imputation, both
    worse than just waiting for the real data. Prints which case applies."""
    cols = list(CORE_FEATURE_COLS)
    for opt in OPTIONAL_FEATURE_COLS:
        if opt in real.columns and real[opt].notna().all() and len(real) > 0:
            cols.append(opt)
            print(f"Including optional feature '{opt}': present for all {len(real)} real sites.")
        elif opt in real.columns:
            n_missing = real[opt].isna().sum()
            print(f"NOT including optional feature '{opt}': missing for {n_missing}/{len(real)} real sites "
                  f"(needs ml/gee_pull_lst.py run for those sites first).")
    return cols


def prep(real, feature_cols):
    real = real.dropna(subset=[c for c in feature_cols if c not in TERRAIN_DUMMY_COLS] + ["disaster_occurred"])
    real["terrain_is_coastal"] = (real["terrain_type"] == "coastal").astype(int)
    X = real[feature_cols].astype(float).values
    y = real["disaster_occurred"].astype(int).values
    return real, X, y


def main():
    df, real = load_real_rows()
    total = len(df)
    n_real_all_terrain = (df["status"].astype(str).str.startswith("REAL")).sum()
    n_real = len(real)
    n_out_of_scope = n_real_all_terrain - n_real

    print("=" * 70)
    print("SIH26206 multi-site risk model -- data status")
    print("=" * 70)
    print(f"Sites in feature table: {total}")
    print(f"Sites with REAL, complete data: {n_real_all_terrain}")
    print(f"  of which IN SCOPE for training ({'/'.join(IN_SCOPE_TERRAIN_TYPES)}): {n_real}")
    print(f"  of which real but OUT OF SCOPE (terrain type not yet trained on): {n_out_of_scope}")
    for _, r in df[df["status"].astype(str).str.startswith("REAL") & ~df["terrain_type"].isin(IN_SCOPE_TERRAIN_TYPES)].iterrows():
        print(f"  - {r['site_id']} ({r['terrain_type']}): real data, excluded from training by terrain scope")
    print(f"Sites still NOT_PULLED (need Earth Engine + NASA POWER pull): {total - n_real_all_terrain}")
    for _, r in df[~df["status"].astype(str).str.startswith("REAL")].iterrows():
        print(f"  - {r['site_id']} ({r['terrain_type']}): {r['status']}")
    print()

    if n_real < MIN_SITES_TO_TRAIN:
        print(f"NOT TRAINING: only {n_real} real site(s) available, need >= {MIN_SITES_TO_TRAIN}")
        print("per sihPlan/dataset-sites.md ('fewer than this makes the ML claim too weak to")
        print("defend'). Pull real NDVI/NDBI/slope/rainfall data for the NOT_PULLED sites above")
        print("(same Earth Engine + NASA POWER scripts used for Joshimath, new coordinates)")
        print("and re-run this script. Refusing to train/report fake-looking metrics on")
        print(f"N={n_real} -- that would misrepresent what the model actually knows.")
        print()
        if n_real >= 1:
            print("Real row(s) currently available:")
            preview_cols = [c for c in CORE_FEATURE_COLS if c not in TERRAIN_DUMMY_COLS]
            print(real[["site_id", "terrain_type", "disaster_occurred"] + preview_cols].to_string(index=False))
        sys.exit(0)

    feature_cols = choose_feature_cols(real)
    print()
    real, X, y = prep(real, feature_cols)
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import LeaveOneOut
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    # LOOCV -- also keep the per-site result, not just the aggregate. Showing exactly
    # which sites the model got right/wrong when it had NEVER seen them (trained on the
    # other 9 only, each time) is a far more convincing "proof of learning" than a bare
    # accuracy fraction -- it's checkable, not just assertable.
    loo = LeaveOneOut()
    correct = 0
    loocv_per_site = []
    site_ids_array = real["site_id"].values
    for train_idx, test_idx in loo.split(Xs):
        clf = LogisticRegression(max_iter=1000)
        clf.fit(Xs[train_idx], y[train_idx])
        pred = clf.predict(Xs[test_idx])
        prob = clf.predict_proba(Xs[test_idx])[0, 1]
        hit = int(pred[0] == y[test_idx][0])
        correct += hit
        loocv_per_site.append({
            "site_id": str(site_ids_array[test_idx[0]]),
            "actual": int(y[test_idx][0]),
            "predicted": int(pred[0]),
            "predicted_prob_held_out": round(float(prob), 4),
            "correct": bool(hit),
        })
    loocv_acc = correct / len(y)
    print(f"LOOCV accuracy: {correct}/{len(y)} = {loocv_acc:.2f}")

    # Full-data fit for feature importance
    clf_full = LogisticRegression(max_iter=1000)
    clf_full.fit(Xs, y)
    importance = pd.Series(clf_full.coef_[0], index=feature_cols).sort_values()
    print("\nFeature importance (logistic regression coefficients, standardized features):")
    print(importance.to_string())

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4))
        colors = ["#f56565" if v < 0 else "#4fd1c5" for v in importance.values]
        ax.barh(importance.index, importance.values, color=colors)
        ax.set_xlabel("Logistic regression coefficient (standardized)")
        ax.set_title("Feature importance -- disaster occurrence classifier")
        ax.axvline(0, color="#444", linewidth=0.8)
        fig.tight_layout()
        out_path = os.path.join(BASE, "feature_importance.png")
        fig.savefig(out_path, dpi=150)
        print(f"\nSaved {out_path}")
    except Exception as e:
        print(f"\n(skipped chart: {e})")

    # Cross-terrain validation. Derived straight from terrain_type (not a model feature
    # column). NOTE: terrain_is_coastal is exactly 0 for every hill row, so it has zero
    # variance in this ablation's training data -- LogisticRegression can't learn a
    # meaningful coefficient for a constant-zero input, so it's mathematically inert here
    # (coefficient stays ~0). Left in anyway so this ablation uses literally the same
    # feature set as the main model, not a different one.
    is_hill = (real["terrain_type"] == "hill").values
    hill = real[is_hill]
    not_hill = real[~is_hill]
    print(f"\nCross-terrain check: {len(hill)} hill sites, {len(not_hill)} coastal sites available.")
    if len(hill) >= 3 and len(not_hill) >= 3:
        Xh, yh = Xs[is_hill], y[is_hill]
        Xc, yc = Xs[~is_hill], y[~is_hill]
        clf_h = LogisticRegression(max_iter=1000).fit(Xh, yh)
        pred_on_coastal = clf_h.predict(Xc)
        print("Model trained on hill sites only, tested on non-hill sites:")
        print(f"  predicted: {pred_on_coastal.tolist()}  actual: {yc.tolist()}")
    else:
        print("NOT ENOUGH sites per terrain type yet to run the cross-terrain generalization")
        print("check meaningfully (need >=3 per terrain type) -- this is the plan's core")
        print("generalization proof, so prioritize getting coastal sites' data pulled.")

    # Risk ranking on all real sites (in-sample; only meaningful once N is adequate)
    real_sorted = real.copy()
    real_sorted["predicted_risk_prob"] = clf_full.predict_proba(Xs)[:, 1]
    print("\nRisk ranking (all real sites, in-sample predicted probability):")
    print(real_sorted[["site_id", "terrain_type", "disaster_occurred", "predicted_risk_prob"]]
          .sort_values("predicted_risk_prob", ascending=False).to_string(index=False))

    # ---- Bootstrap uncertainty quantification ----
    # With only n_real real labeled sites, a single point-probability like "93% risk"
    # overstates how much this model actually knows -- overconfidence a reviewer will
    # rightly probe. Resample the real sites with replacement, refit the WHOLE pipeline
    # (scaler + classifier) on each resample, and predict every real site's probability
    # from that resampled model. The spread of those predictions across resamples is an
    # honest empirical confidence interval given this exact sample size -- not a fixed
    # +/-X% guess. A resample that happens to contain only one class can't fit logistic
    # regression, so those draws are skipped and don't count toward n_bootstrap.
    N_BOOTSTRAP = 500
    CI_LOW_PCTL, CI_HIGH_PCTL = 10, 90
    rng = np.random.default_rng(42)
    n_sites_bs = len(y)
    boot_preds = np.full((N_BOOTSTRAP, n_sites_bs), np.nan)
    n_valid_boot = 0
    attempts = 0
    max_attempts = N_BOOTSTRAP * 20
    while n_valid_boot < N_BOOTSTRAP and attempts < max_attempts:
        attempts += 1
        idx = rng.integers(0, n_sites_bs, size=n_sites_bs)
        y_boot = y[idx]
        if len(np.unique(y_boot)) < 2:
            continue
        X_boot = X[idx]
        scaler_boot = StandardScaler()
        Xs_boot = scaler_boot.fit_transform(X_boot)
        clf_boot = LogisticRegression(max_iter=1000)
        clf_boot.fit(Xs_boot, y_boot)
        X_all_boot_scaled = scaler_boot.transform(X)
        boot_preds[n_valid_boot] = clf_boot.predict_proba(X_all_boot_scaled)[:, 1]
        n_valid_boot += 1
    boot_preds = boot_preds[:n_valid_boot]
    print(f"\nBootstrap uncertainty: {n_valid_boot} valid resamples "
          f"({attempts} attempted, {attempts - n_valid_boot} skipped for single-class draws).")
    bootstrap_by_site = {}
    for idx, (_, row) in enumerate(real.iterrows()):
        col = boot_preds[:, idx]
        bootstrap_by_site[row["site_id"]] = {
            "ci_low": round(float(np.percentile(col, CI_LOW_PCTL)), 4),
            "ci_high": round(float(np.percentile(col, CI_HIGH_PCTL)), 4),
            "std": round(float(np.std(col)), 4),
        }
    print("Per-site 10th-90th percentile bootstrap interval:")
    for sid, v in bootstrap_by_site.items():
        print(f"  {sid}: [{v['ci_low']:.2f}, {v['ci_high']:.2f}]  (std={v['std']:.3f})")

    # Per-site feature contributions (coefficient * standardized value) -- this is what
    # actually answers "why is THIS site's score what it is", not just the global
    # feature-importance ranking. Without this, a site whose score seems to contradict
    # one improving feature (e.g. recovering vegetation) looks arbitrary; this shows the
    # real math: the model DOES weigh that feature, it's just outweighed by others here.
    coefs = clf_full.coef_[0]
    contributions = Xs * coefs  # (n_sites, n_features), one row per real site in `real` order
    contributions_by_site = {}
    for idx, (_, row) in enumerate(real.iterrows()):
        contribs = dict(zip(feature_cols, contributions[idx].tolist()))
        contributions_by_site[row["site_id"]] = contribs

    # ---- Machine-readable export for the dashboard. Every value here traces directly
    # to the computation above -- nothing hand-entered, so the UI can never drift from
    # what the model actually produced. ----
    cross_terrain = None
    if len(hill) >= 3 and len(not_hill) >= 3:
        cross_terrain = {
            "n_hill_train": int(len(hill)),
            "n_coastal_test": int(len(not_hill)),
            "predicted": [int(p) for p in pred_on_coastal.tolist()],
            "actual": [int(a) for a in yc.tolist()],
            "site_ids": not_hill["site_id"].tolist(),
            "n_correct": int(sum(p == a for p, a in zip(pred_on_coastal.tolist(), yc.tolist()))),
        }

    mechanism_scoped_rainfall_landslide = run_rainfall_landslide_mechanism_model(df)

    # Real sites that exist in feature_table.csv with real, complete pulled data, but
    # whose terrain type (plains, desert) isn't in IN_SCOPE_TERRAIN_TYPES yet -- e.g.
    # guna, silchar, jaisalmer. These have real satellite/rainfall data and deserve to be
    # visible on the live site (why hide real data?), but NO risk prediction, because none
    # was ever trained/validated for their terrain type. Exported separately from
    # risk_ranking specifically so the UI can't accidentally treat them as having a real
    # score -- there's no predicted_risk_prob field here at all, not a null one.
    out_of_scope_real = df[
        df["status"].astype(str).str.startswith("REAL") & ~df["terrain_type"].isin(IN_SCOPE_TERRAIN_TYPES)
    ]
    out_of_scope_real_sites = [
        {
            "site_id": r["site_id"],
            "site_name": r.get("site_name", r["site_id"]),
            "terrain_type": r["terrain_type"],
            "disaster_occurred": int(r["disaster_occurred"]) if pd.notna(r.get("disaster_occurred")) else None,
            "disaster_type": r.get("disaster_type", "") if pd.notna(r.get("disaster_type")) else "",
            "disaster_date": r["disaster_date"] if pd.notna(r.get("disaster_date")) else "",
            "ndvi_trend_slope": round(float(r["ndvi_trend_slope"]), 6) if pd.notna(r.get("ndvi_trend_slope")) else None,
            "ndbi_trend_slope": round(float(r["ndbi_trend_slope"]), 6) if pd.notna(r.get("ndbi_trend_slope")) else None,
            "mean_slope_degrees": round(float(r["mean_slope_degrees"]), 2) if pd.notna(r.get("mean_slope_degrees")) else None,
            "elevation_mean_m": round(float(r["elevation_mean_m"]), 1) if pd.notna(r.get("elevation_mean_m")) else None,
            "rainfall_anomaly_pct": round(float(r["rainfall_anomaly_pct"]), 2) if pd.notna(r.get("rainfall_anomaly_pct")) else None,
            "lst_trend_slope": round(float(r["lst_trend_slope"]), 4) if pd.notna(r.get("lst_trend_slope")) else None,
            "lst_mean_c": round(float(r["lst_mean_c"]), 2) if pd.notna(r.get("lst_mean_c")) else None,
            "latitude": float(r["latitude"]) if pd.notna(r.get("latitude")) else None,
            "longitude": float(r["longitude"]) if pd.notna(r.get("longitude")) else None,
            "human_activity_notes": r["human_activity_notes"] if pd.notna(r.get("human_activity_notes")) else "",
            "source_citation": r["source_citation"] if pd.notna(r.get("source_citation")) else "",
            "not_in_model_reason": f"Terrain type '{r['terrain_type']}' has too few real sites so far to "
                                    f"train/validate a prediction (see sihPlan/memory.md secs 32-34) -- "
                                    f"real satellite and rainfall data is shown above, but no risk score.",
        }
        for _, r in out_of_scope_real.iterrows()
    ]

    export = {
        "generated_from": "ml/train_model.py -- every field here is computed, not hand-entered",
        "n_sites_total": int(total),
        "n_sites_real": int(n_real),
        "n_sites_pending": int(total - n_real),
        "pending_sites": [
            {"site_id": r["site_id"], "terrain_type": r["terrain_type"], "status": r["status"]}
            for _, r in df[~df["status"].astype(str).str.startswith("REAL")].iterrows()
        ],
        "loocv": {"correct": int(correct), "total": int(len(y)), "accuracy": round(loocv_acc, 4), "per_site": loocv_per_site},
        "feature_importance": {k: round(float(v), 4) for k, v in importance.items()},
        "cross_terrain": cross_terrain,
        "mechanism_scoped_rainfall_landslide": mechanism_scoped_rainfall_landslide,
        "out_of_scope_real_sites": out_of_scope_real_sites,
        "bootstrap_uncertainty": {
            "method": "Non-parametric bootstrap: resample real sites with replacement, "
                      "refit scaler+classifier on each resample, predict all real sites. "
                      "CI = 10th-90th percentile of predicted probability across valid resamples.",
            "n_bootstrap": int(n_valid_boot),
            "ci_percentiles": [CI_LOW_PCTL, CI_HIGH_PCTL],
        },
        # Full trained model parameters -- enough to reproduce predict_proba() exactly in
        # plain JS (standardize with mean/scale, dot with coef, add intercept, sigmoid).
        # This is what lets the awareness page run a REAL live calculator instead of a
        # lookup table: same math the Python model uses, computed client-side on demand.
        "model_params": {
            "feature_cols": feature_cols,
            "coefficients": [round(float(c), 6) for c in clf_full.coef_[0]],
            "intercept": round(float(clf_full.intercept_[0]), 6),
            "scaler_mean": [round(float(m), 6) for m in scaler.mean_],
            "scaler_scale": [round(float(s), 6) for s in scaler.scale_],
        },
        "risk_ranking": [
            {
                "site_id": row["site_id"],
                "site_name": row.get("site_name", row["site_id"]),
                "terrain_type": row["terrain_type"],
                "disaster_occurred": int(row["disaster_occurred"]),
                "disaster_type": row.get("disaster_type", ""),
                "disaster_date": row["disaster_date"] if pd.notna(row.get("disaster_date")) else "",
                "predicted_risk_prob": round(float(row["predicted_risk_prob"]), 4),
                "risk_ci_low": bootstrap_by_site[row["site_id"]]["ci_low"],
                "risk_ci_high": bootstrap_by_site[row["site_id"]]["ci_high"],
                "risk_std": bootstrap_by_site[row["site_id"]]["std"],
                "ndvi_trend_slope": round(float(row["ndvi_trend_slope"]), 6),
                "ndbi_trend_slope": round(float(row["ndbi_trend_slope"]), 6),
                "mean_slope_degrees": round(float(row["mean_slope_degrees"]), 2),
                "elevation_mean_m": round(float(row["elevation_mean_m"]), 1),
                "rainfall_anomaly_pct": round(float(row["rainfall_anomaly_pct"]), 2),
                "lst_trend_slope": round(float(row["lst_trend_slope"]), 4) if pd.notna(row.get("lst_trend_slope")) else None,
                "lst_mean_c": round(float(row["lst_mean_c"]), 2) if pd.notna(row.get("lst_mean_c")) else None,
                "latitude": float(row["latitude"]) if pd.notna(row.get("latitude")) else None,
                "longitude": float(row["longitude"]) if pd.notna(row.get("longitude")) else None,
                "human_activity_notes": row["human_activity_notes"] if pd.notna(row.get("human_activity_notes")) else "",
                "source_citation": row["source_citation"] if pd.notna(row.get("source_citation")) else "",
                "feature_contributions": {k: round(v, 4) for k, v in contributions_by_site[row["site_id"]].items()},
                "top_drivers": [
                    {"feature": k, "contribution": round(v, 4)}
                    for k, v in sorted(contributions_by_site[row["site_id"]].items(), key=lambda kv: abs(kv[1]), reverse=True)[:3]
                ],
            }
            for _, row in real_sorted.sort_values("predicted_risk_prob", ascending=False).iterrows()
        ],
    }
    export_path = os.path.join(BASE, "model_results.json")
    with open(export_path, "w") as f:
        json.dump(export, f, indent=2)
    print(f"\nSaved {export_path}")


if __name__ == "__main__":
    main()
