// EcoRisk AI awareness page. All numbers come from window.MODEL_DATA (generated from
// ml/model_results.json) and window.PROJECTION_DATA (generated from real NDVI/NDBI time
// series) -- nothing here is hand-entered. Descriptive site text is transcribed from
// sihPlan/dataset-sites.md and sihPlan/memory.md's confirmed sources -- no casualty/
// impact figures are stated unless actually verified and logged this session (only
// Joshimath's NDMA housing figure qualifies).
//
// v2: everything about ONE site (what happened, why here, the model's real risk score,
// before/after imagery, the "if this continues" projection, live weather) now renders
// together in one profile panel driven by a single site selection, instead of being
// scattered across separate full-page sections. See index.html's direction-contract
// comment for why.
(function () {
  const D = window.MODEL_DATA;
  const MAP = window.INDIA_MAP;
  const PROJ = window.PROJECTION_DATA || {};
  // In-scope sites (real prediction, hasModel: true) plus real sites whose terrain type
  // isn't in the trained model's scope yet (plains/desert -- guna, silchar, jaisalmer):
  // their real satellite/rainfall data is shown, but no risk score, since none was ever
  // trained/validated for that terrain. hasModel distinguishes the two so nothing here
  // accidentally reads a missing predicted_risk_prob as a number.
  const allSites = D.risk_ranking.map((s) => ({ ...s, hasModel: true }))
    .concat((D.out_of_scope_real_sites || []).map((s) => ({ ...s, hasModel: false })));

  // Real Supabase backend (project: sih26206-ecorisk, dercrxstnclfkcokcsdf). Anon/
  // publishable key -- safe to ship client-side, RLS restricts it to public-read only
  // (see sihPlan/memory.md sec 25). Used for the live GDACS check below.
  const SUPABASE_URL = "https://dercrxstnclfkcokcsdf.supabase.co";
  const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlcmNyeHN0bmNsZmtjb2tjc2RmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgxOTM5ODQsImV4cCI6MjEwMzc2OTk4NH0.vLtHMbIY-eZKj70z4Jv4fOmhxq_ASerO5MSKCt8LY2s";

  // ---------- reveal-on-scroll ----------
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) e.target.classList.add("in"); });
  }, { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));

  // ---------- descriptive site text (real, sourced -- see file header) ----------
  const SITE_DESCRIPTIONS = {
    joshimath: "Two subsidence events: 8.9cm of ground movement over seven months (Apr–Nov 2022), then 5.4cm in just twelve days (late Dec 2022–Jan 2023). A government expert committee (NDMA, GSI, CBRI) reported 1,403 of 2,152 surveyed houses affected, 472 needing full reconstruction.",
    raini: "A rock-ice avalanche and flash flood swept down the Rishiganga valley on 7 February 2021.",
    kedarnath: "Extreme rainfall triggered widespread landslides and flooding across the Kedarnath area, 15–17 June 2013.",
    wazri: "A landslide struck Wazri village near Yamunotri on 12 September 2017.",
    dharali: "A cloudburst triggered a landslide and flash flood at Dharali in August 2025.",
    malpa: "A landslide struck Malpa village in Pithoragarh district on 18 August 1998.",
    sundarbans: "Cyclone Amphan made landfall near the Sundarbans on 20 May 2020 as an Extremely Severe Cyclonic Storm (real IMD/NOAA track data: ~167 km/h winds at landfall).",
    odisha_coast: "Cyclone Fani made landfall on the Odisha coast on 3 May 2019 as an Extremely Severe Cyclonic Storm (real IMD/NOAA track data: ~185 km/h winds at landfall).",
    auli_control: "No major documented disaster in this window. Included as a comparison site: similar terrain to Joshimath, a few kilometres away.",
    coastal_control_tbd: "No major cyclone made close landfall here in the years checked (nearest was 157km away). Included as a comparison site on the same coastline.",
  };

  const DISASTER_TYPE_LABELS = {
    land_subsidence: "land subsidence",
    flash_flood_rock_ice_avalanche: "a rock-ice avalanche and flash flood",
    rainfall_triggered_landslide_flood: "rainfall-triggered landslides and flooding",
    landslide: "a landslide",
    cloudburst_landslide_flash_flood: "a cloudburst-triggered landslide and flash flood",
    cyclone: "a cyclone",
  };
  function humanizeDisasterType(t) {
    if (!t) return "control site";
    return DISASTER_TYPE_LABELS[t] || t.replace(/_/g, " ");
  }

  function riskWord(pct) {
    if (pct >= 80) return { label: "Very High", cls: "very-high" };
    if (pct >= 60) return { label: "High", cls: "high" };
    if (pct >= 40) return { label: "Elevated", cls: "elevated" };
    return { label: "Lower", cls: "lower" };
  }
  // ---------- map ----------
  document.getElementById("india-outline").setAttribute("d", MAP.pathD);
  const proj = MAP.proj;
  function projectLatLon(lon, lat) {
    const x = proj.pad + (lon - proj.minx) / (proj.maxx - proj.minx) * (proj.vb_w - 2 * proj.pad);
    const y = proj.pad + (proj.maxy - lat) / (proj.maxy - proj.miny) * (proj.vb_h - 2 * proj.pad);
    return [x, y];
  }
  const markersG = document.getElementById("markers");
  const svgNS = "http://www.w3.org/2000/svg";
  allSites.forEach((s) => {
    if (s.latitude == null || s.longitude == null) return;
    const [x, y] = projectLatLon(s.longitude, s.latitude);
    const g = document.createElementNS(svgNS, "g");
    g.setAttribute("class", "map-marker " + (s.disaster_occurred ? "disaster" : "control"));
    g.setAttribute("data-site", s.site_id);
    const pulse = document.createElementNS(svgNS, "circle");
    pulse.setAttribute("class", "pulse");
    pulse.setAttribute("cx", x); pulse.setAttribute("cy", y); pulse.setAttribute("r", 5);
    g.appendChild(pulse);
    const core = document.createElementNS(svgNS, "circle");
    core.setAttribute("class", "core");
    core.setAttribute("cx", x); core.setAttribute("cy", y); core.setAttribute("r", 5);
    g.appendChild(core);
    g.addEventListener("click", () => selectSite(s.site_id));
    markersG.appendChild(g);
  });

  // ---------- site picker pills (map column) ----------
  const pickerEl = document.getElementById("site-picker");
  allSites.forEach((s) => {
    const pill = document.createElement("button");
    pill.className = "site-pill";
    pill.dataset.site = s.site_id;
    pill.textContent = s.site_name.split(",")[0];
    pill.addEventListener("click", () => selectSite(s.site_id));
    pickerEl.appendChild(pill);
  });

  // ---------- before/after slider component ----------
  function buildSlider(siteId, siteName) {
    const wrap = document.createElement("div");
    wrap.className = "ba-slider";
    const beforeSrc = `../dashboard/images/${siteId}_before.jpg`;
    const afterSrc = `../dashboard/images/${siteId}_after.jpg`;
    const testImg = new Image();
    testImg.onload = () => {
      wrap.innerHTML = `
        <img class="img-before" src="${beforeSrc}" alt="${siteName} before">
        <img class="img-after" src="${afterSrc}" alt="${siteName} after">
        <div class="ba-label before-label">Before</div>
        <div class="ba-label after-label">After</div>
        <div class="handle" style="left:50%"></div>
      `;
      const handle = wrap.querySelector(".handle");
      const afterImg = wrap.querySelector(".img-after");
      let dragging = false;
      function setPos(clientX) {
        const rect = wrap.getBoundingClientRect();
        let pct = ((clientX - rect.left) / rect.width) * 100;
        pct = Math.max(0, Math.min(100, pct));
        handle.style.left = pct + "%";
        afterImg.style.clipPath = `inset(0 0 0 ${pct}%)`;
      }
      wrap.addEventListener("pointerdown", (e) => { dragging = true; setPos(e.clientX); });
      window.addEventListener("pointermove", (e) => { if (dragging) setPos(e.clientX); });
      window.addEventListener("pointerup", () => { dragging = false; });
      wrap.addEventListener("touchstart", (e) => setPos(e.touches[0].clientX), { passive: true });
      wrap.addEventListener("touchmove", (e) => setPos(e.touches[0].clientX), { passive: true });
    };
    testImg.onerror = () => {
      wrap.innerHTML = `<div class="ba-placeholder">Satellite imagery for ${siteName} pending — run ml/gee_pull_thumbnail.py for this site.</div>`;
    };
    testImg.src = beforeSrc;
    return wrap;
  }

  // ---------- profile renderers ----------
  function renderProfileHead(site) {
    const desc = SITE_DESCRIPTIONS[site.site_id] || "";
    const metaParts = [site.terrain_type + " terrain"];
    if (site.disaster_date) metaParts.push(site.disaster_date);
    metaParts.push(site.disaster_occurred ? "disaster site" : "control site");
    document.getElementById("profile-head").innerHTML = `
      <div class="site-name">${site.site_name}</div>
      <div class="site-meta">${metaParts.join(" · ")}</div>
      <div class="site-desc">${desc}</div>
      <div class="site-source">Source: ${site.source_citation || "see sihPlan/memory.md"}</div>
    `;
  }

  function renderProfileWhy(site) {
    // "warn" = the direction that raises concern for that specific variable, "good" =
    // the reassuring direction. NDVI falling is concerning; NDBI rising is concerning.
    const ndviFalling = site.ndvi_trend_slope < 0;
    const ndbiRising = site.ndbi_trend_slope > 0;
    const rows = [
      `<div class="why-here-row"><span class="arrow ${ndviFalling ? "up" : "down"}">${ndviFalling ? "↓" : "↑"}</span>
        Vegetation here has been ${ndviFalling ? "thinning" : "recovering"}, year over year (real Sentinel-2 data, ${site.ndvi_trend_slope >= 0 ? "+" : ""}${site.ndvi_trend_slope.toFixed(4)}/yr).</div>`,
      `<div class="why-here-row"><span class="arrow ${ndbiRising ? "up" : "down"}">${ndbiRising ? "↑" : "→"}</span>
        Built-up area has been ${ndbiRising ? "growing" : "flat or shrinking"}, year over year (${site.ndbi_trend_slope >= 0 ? "+" : ""}${site.ndbi_trend_slope.toFixed(4)}/yr).</div>`,
    ];
    if (site.lst_trend_slope != null) {
      const lstWarming = site.lst_trend_slope > 0;
      rows.push(`<div class="why-here-row"><span class="arrow ${lstWarming ? "up" : "down"}">${lstWarming ? "↑" : "↓"}</span>
        The land itself has been ${lstWarming ? "warming" : "cooling"}, year over year (real MODIS satellite thermal data, ${site.lst_trend_slope >= 0 ? "+" : ""}${site.lst_trend_slope.toFixed(3)}°C/yr${site.lst_mean_c != null ? `, averaging ${site.lst_mean_c.toFixed(1)}°C` : ""}).</div>`);
    }
    let html = `<div class="why-here-legend">Measured from satellite light readings, roughly -1 to +1 scale: vegetation greenness (NDVI) and how built-up an area looks (NDBI)${site.lst_trend_slope != null ? ", plus real satellite-measured surface temperature (LST)" : ""}. The numbers below are how fast each has been changing per year, over the real observed period.</div>` + rows.join("");
    document.getElementById("profile-why").innerHTML = html;
  }

  // Real per-site driver phrases -- generated from the trained model's ACTUAL
  // coefficient x standardized-value contribution (ml/train_model.py), not a guess
  // based on whether the site's raw trend looks "good" or "bad" in isolation. A site's
  // vegetation can be absolutely recovering (positive raw slope) and still push its
  // score UP if it's recovering more slowly than most other sites in the sample --
  // standardization compares sites to each other, not to zero. Say that plainly rather
  // than paper over an apparent contradiction.
  const DRIVER_PHRASES = {
    ndvi_trend_slope: { up: "Vegetation trend here is weaker than most other sites we measured", down: "Vegetation trend here is healthier than most other sites we measured" },
    ndbi_trend_slope: { up: "Construction is growing faster here than most other sites we measured", down: "Construction here is flatter than most other sites we measured" },
    mean_slope_degrees: { up: "This slope is steeper than most other sites we measured", down: "This slope is gentler than most other sites we measured" },
    rainfall_anomaly_pct: { up: "Rainfall here has been more extreme than most other sites we measured", down: "Rainfall here is closer to typical than most other sites we measured" },
    elevation_mean_m: { up: "This site sits higher than most other sites we measured", down: "This site sits lower than most other sites we measured" },
    terrain_is_coastal: { up: "Being a coastal site (not mountain) raises this score", down: "Being a hill/mountain site (not coastal) lowers this score" },
    lst_trend_slope: { up: "This land is warming faster than most other sites we measured", down: "This land is warming slower (or cooling) compared to most other sites we measured" },
  };
  const DRIVER_LABELS = {
    ndvi_trend_slope: "Vegetation trend", ndbi_trend_slope: "Construction trend",
    mean_slope_degrees: "Slope", rainfall_anomaly_pct: "Rainfall anomaly",
    elevation_mean_m: "Elevation", terrain_is_coastal: "Terrain type", lst_trend_slope: "Land surface warming",
  };

  function renderProfileRisk(site) {
    const el = document.getElementById("profile-risk-num");
    const driversEl = document.getElementById("risk-drivers");

    if (!site.hasModel) {
      el.textContent = "—";
      el.style.color = "";
      document.getElementById("profile-risk-label").textContent = "No trained risk score for this terrain yet";
      document.getElementById("profile-risk-sub").textContent = "";
      driversEl.innerHTML = `<div class="driver-title">Why there's no score here:</div>
        <div class="risk-driver-row">${site.not_in_model_reason || "This terrain type isn't in the trained model's scope yet."}</div>
        <div class="risk-driver-row">Real satellite and rainfall data for this site is shown in the sections below -- it's just not run through a risk model, rather than showing a guess.</div>`;
      return;
    }

    const pct = site.predicted_risk_prob * 100;
    const rw = riskWord(pct);
    el.textContent = pct.toFixed(0) + "%";
    el.style.color = riskWordColor(rw.cls);
    document.getElementById("profile-risk-label").textContent = rw.label + " risk pattern";
    document.getElementById("profile-risk-sub").textContent =
      site.disaster_occurred
        ? " — this is a site the model was trained knowing had a real disaster."
        : " — this is a control site with no disaster; a lower/matching score here is a good sign for the model.";

    if (site.top_drivers && site.top_drivers.length) {
      const rows = site.top_drivers.map((d) => {
        const up = d.contribution > 0;
        const phrase = (DRIVER_PHRASES[d.feature] || {})[up ? "up" : "down"] || DRIVER_LABELS[d.feature] || d.feature;
        return `<div class="risk-driver-row"><span class="dsign ${up ? "up" : "down"}">${up ? "↑" : "↓"}</span>${phrase}</div>`;
      }).join("");
      driversEl.innerHTML = `<div class="driver-title">What's actually driving this score (the model's real math, biggest effect first):</div>${rows}`;
    } else {
      driversEl.innerHTML = "";
    }
  }

  function renderProfileBA(site) {
    const container = document.getElementById("profile-ba");
    container.innerHTML = "";
    container.appendChild(buildSlider(site.site_id, site.site_name));
  }

  let liveFetchToken = 0;
  function renderProfileLive(site) {
    const myToken = ++liveFetchToken;
    const statusEl = document.getElementById("live-status");
    document.getElementById("live-precip").textContent = "–";
    document.getElementById("live-temp").textContent = "–";
    statusEl.textContent = `Fetching live weather for ${site.site_name}…`;
    if (site.latitude == null || site.longitude == null) {
      statusEl.textContent = "No coordinates available for this site.";
      return;
    }
    fetch(`https://api.open-meteo.com/v1/forecast?latitude=${site.latitude}&longitude=${site.longitude}&current=precipitation,temperature_2m&timezone=auto`)
      .then((r) => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then((json) => {
        if (myToken !== liveFetchToken) return; // user switched sites before this landed
        document.getElementById("live-precip").textContent = json.current.precipitation.toFixed(1);
        document.getElementById("live-temp").textContent = json.current.temperature_2m.toFixed(1);
        statusEl.textContent = `Live at ${site.site_name}, fetched ${new Date(json.current.time).toLocaleString()}`;
      })
      .catch((err) => {
        if (myToken !== liveFetchToken) return;
        statusEl.textContent = "Live fetch failed (" + err.message + ").";
      });
  }

  // ---------- early warning check (real, cited threshold + real live rolling rainfall) ----------
  // The rainfall threshold below is real, cited, and specific to one place: Kanungo &
  // Sharma (2014) derived it from actual landslide events in the Chamoli-Joshimath
  // region. Applying it to a different geology/region would be exactly the kind of
  // overclaiming this project has tried hard to avoid all along -- so this only renders
  // for the sites it was actually validated for, and says so plainly everywhere else.
  const CHAMOLI_SITES = new Set(["joshimath", "raini", "auli_control"]);
  const RAINFALL_THRESHOLD = {
    day10: 55, day20: 185,
    source: "Kanungo & Sharma (2014), Landslides 11:629-638 -- derived for the Chamoli-Joshimath region specifically",
  };
  let ewFetchToken = 0;
  let ewDailyPrecip = [];

  function renderEarlyWarning(site) {
    const block = document.getElementById("ew-block");
    const myToken = ++ewFetchToken;
    if (!CHAMOLI_SITES.has(site.site_id)) {
      block.innerHTML = `<div class="ew-note">The real cited rainfall threshold (Kanungo &amp; Sharma, 2014) was derived for the Chamoli-Joshimath region specifically and hasn't been validated here -- not shown for this site, to avoid implying it applies everywhere.</div>`;
      return;
    }
    block.innerHTML = `<div class="ew-title">Early warning check<span class="tag real">Real, cited</span></div><div class="ew-note">Loading real rainfall history…</div>`;
    if (site.latitude == null || site.longitude == null) return;
    fetch(`https://api.open-meteo.com/v1/forecast?latitude=${site.latitude}&longitude=${site.longitude}&daily=precipitation_sum&past_days=20&forecast_days=1&timezone=auto`)
      .then((r) => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then((json) => {
        if (myToken !== ewFetchToken) return;
        ewDailyPrecip = json.daily.time.map((d, i) => ({ date: d, mm: json.daily.precipitation_sum[i] || 0 }));
        buildEwUI();
      })
      .catch((err) => {
        if (myToken !== ewFetchToken) return;
        block.innerHTML = `<div class="ew-note">Rainfall history fetch failed (${err.message}).</div>`;
      });
  }

  function ewRollingSum(days) {
    return ewDailyPrecip.slice(-days).reduce((a, r) => a + r.mm, 0);
  }

  function buildEwUI() {
    const block = document.getElementById("ew-block");
    block.innerHTML = `
      <div class="ew-title">Early warning check<span class="tag real">Real, cited</span></div>
      <div class="ew-bar-row"><div class="ew-bar-label">10-day rain</div><div class="ew-bar-track"><div class="ew-bar-fill" id="ew-bar-10"></div></div><div class="ew-bar-val" id="ew-val-10"></div></div>
      <div class="ew-bar-row"><div class="ew-bar-label">20-day rain</div><div class="ew-bar-track"><div class="ew-bar-fill" id="ew-bar-20"></div></div><div class="ew-bar-val" id="ew-val-20"></div></div>
      <div class="ew-slider-row">
        <div class="ew-slider-label"><span>+ hypothetical rain, next few days</span><span class="val" id="ew-hyp-val">+0mm</span></div>
        <input type="range" id="ew-hyp-slider" min="0" max="150" step="5" value="0">
      </div>
      <div class="ew-narrative" id="ew-narrative"></div>
      <div class="ew-disclaimer">Real threshold: ${RAINFALL_THRESHOLD.source}. Real rainfall: Open-Meteo, last 20 days, fetched live.</div>
    `;
    document.getElementById("ew-hyp-slider").addEventListener("input", (e) => updateEwDisplay(parseFloat(e.target.value)));
    updateEwDisplay(0);
  }

  function updateEwDisplay(hypothetical) {
    const sum10 = ewRollingSum(10) + hypothetical;
    const sum20 = ewRollingSum(20) + hypothetical;
    document.getElementById("ew-hyp-val").textContent = (hypothetical > 0 ? "+" : "") + hypothetical.toFixed(0) + "mm";

    function setBar(barId, valId, sum, threshold) {
      const pct = Math.min(100, (sum / threshold) * 100);
      const over = sum >= threshold;
      const fill = document.getElementById(barId);
      fill.style.transform = `scaleX(${pct / 100})`;
      fill.className = "ew-bar-fill " + (over ? "over" : "under");
      document.getElementById(valId).textContent = `${sum.toFixed(0)}/${threshold}mm`;
    }
    setBar("ew-bar-10", "ew-val-10", sum10, RAINFALL_THRESHOLD.day10);
    setBar("ew-bar-20", "ew-val-20", sum20, RAINFALL_THRESHOLD.day20);

    const over = sum10 >= RAINFALL_THRESHOLD.day10 || sum20 >= RAINFALL_THRESHOLD.day20;
    const narrative = document.getElementById("ew-narrative");
    if (hypothetical === 0) {
      narrative.textContent = over
        ? "Real rainfall right now is at or above the cited danger threshold."
        : "Real rainfall right now is below the cited danger threshold.";
    } else {
      narrative.textContent = over
        ? `With ${hypothetical.toFixed(0)}mm more over the next few days, this crosses the cited threshold.`
        : `Even with ${hypothetical.toFixed(0)}mm more over the next few days, this stays under the cited threshold.`;
    }
  }

  // ---------- projection ("if this continues") ----------
  // Real satellite time series extrapolated with plain linear regression -- NOT the
  // trained classifier run into the future (see ml/build_projection_data.py's docstring
  // for why). Tracks exactly two things, stated explicitly in the UI: vegetation cover
  // and built-up area, this site's own real 2019+ trend.
  //
  // Uses the SAME riskWord() bands/colors as the real "Disaster risk prediction" card
  // above (Very High/High/Elevated/Lower, same thresholds) rather than a second,
  // differently-labeled scale -- two "risk" vocabularies on one page was itself a source
  // of confusion, flagged by the user.
  const MS_PER_DAY = 86400000;
  const HORIZON_YEARS = [0, 5, 10, 20, 30];
  let projYearsIdx = 0;

  function riskWordColor(cls) {
    if (cls === "very-high" || cls === "high") return "var(--danger)";
    if (cls === "elevated") return "var(--accent2)";
    return "var(--ok)";
  }

  function vulnerabilityIndex(site, ndviVal, ndbiVal) {
    const ndviComponent = Math.max(0, Math.min(1, (site.ndvi_baseline - ndviVal) / site.ndvi_baseline));
    const ndbiComponent = Math.max(0, Math.min(1, (ndbiVal - site.ndbi_min) / (site.ndbi_max - site.ndbi_min)));
    return ((ndviComponent + ndbiComponent) / 2) * 100;
  }

  document.getElementById("proj-slider").addEventListener("input", (e) => {
    projYearsIdx = parseInt(e.target.value, 10);
    if (currentSite) renderProfileProjection(currentSite);
  });

  function renderProfileProjection(site) {
    const pj = PROJ[site.site_id];

    // Self-contained: restate the real trend right here, so this card never depends on
    // the reader remembering the "Why here" card above.
    const ndviFalling = site.ndvi_trend_slope < 0;
    const ndbiRising = site.ndbi_trend_slope > 0;
    document.getElementById("proj-trend-summary").innerHTML =
      `<div><strong>This site's real trend:</strong></div>
       <div>Vegetation ${ndviFalling ? "declining" : "recovering"} (${site.ndvi_trend_slope >= 0 ? "+" : ""}${site.ndvi_trend_slope.toFixed(4)}/yr)</div>
       <div>Construction ${ndbiRising ? "growing" : "flat/shrinking"} (${site.ndbi_trend_slope >= 0 ? "+" : ""}${site.ndbi_trend_slope.toFixed(4)}/yr)</div>`;

    document.getElementById("proj-tracking").textContent =
      `Extending that same trend forward, ${pj ? pj.ref_date.slice(0, 4) : "2019"}–present continued.`;
    if (!pj) {
      document.getElementById("proj-bau-val").textContent = "–";
      document.getElementById("proj-interv-val").textContent = "–";
      document.getElementById("proj-narrative").textContent = "No satellite time series available for this site yet.";
      document.getElementById("proj-disclaimer").textContent = "";
      return;
    }
    const refDate = new Date(pj.ref_date + "T00:00:00Z");
    const lastDate = new Date(pj.last_date + "T00:00:00Z");
    const years = HORIZON_YEARS[projYearsIdx];
    const targetDate = new Date(lastDate.getTime() + years * 365.25 * MS_PER_DAY);
    const daysFromRefAtTarget = (targetDate.getTime() - refDate.getTime()) / MS_PER_DAY;
    const daysFromRefAtLast = (lastDate.getTime() - refDate.getTime()) / MS_PER_DAY;

    const ndviBau = pj.ndvi_slope_per_day * daysFromRefAtTarget + pj.ndvi_intercept;
    const ndbiBau = pj.ndbi_slope_per_day * daysFromRefAtTarget + pj.ndbi_intercept;
    const ndviInterv = pj.ndvi_slope_per_day * daysFromRefAtLast + pj.ndvi_intercept;
    const ndbiInterv = pj.ndbi_slope_per_day * daysFromRefAtLast + pj.ndbi_intercept;

    const bauPct = vulnerabilityIndex(pj, ndviBau, ndbiBau);
    const intervPct = vulnerabilityIndex(pj, ndviInterv, ndbiInterv);
    const bauBand = riskWord(bauPct);
    const intervBand = riskWord(intervPct);
    const bauColor = riskWordColor(bauBand.cls);
    const intervColor = riskWordColor(intervBand.cls);

    const bauValEl = document.getElementById("proj-bau-val");
    bauValEl.textContent = bauPct.toFixed(0) + "%";
    bauValEl.style.color = bauColor;
    document.getElementById("proj-bau-band").textContent = bauBand.label;
    document.getElementById("proj-bau-band").style.color = bauColor;

    const intervValEl = document.getElementById("proj-interv-val");
    intervValEl.textContent = intervPct.toFixed(0) + "%";
    intervValEl.style.color = intervColor;
    document.getElementById("proj-interv-band").textContent = intervBand.label;
    document.getElementById("proj-interv-band").style.color = intervColor;

    const name = site.site_name;
    const realPctPrefix = site.hasModel ? `Real risk score today: ${(site.predicted_risk_prob * 100).toFixed(0)}%. ` : "";
    const narrative = document.getElementById("proj-narrative");
    if (years === 0) {
      narrative.textContent = site.hasModel
        ? `Our model's real disaster-risk score for ${name} today is ${(site.predicted_risk_prob * 100).toFixed(0)}%. This illustrative trend measure reads ${bauPct.toFixed(0)}% (${bauBand.label}) today, for comparison.`
        : `This illustrative trend measure reads ${bauPct.toFixed(0)}% (${bauBand.label}) today. No trained risk score exists for this site's terrain yet (see the card above) -- this measure alone isn't a substitute for one.`;
    } else {
      const gap = Math.round(bauPct - intervPct);
      if (gap > 0) {
        narrative.textContent = `${realPctPrefix}If the trend above continues for ${years} more years, this illustrative measure reaches ${bauPct.toFixed(0)}% (${bauBand.label}) — ${gap} points higher than if activity had stopped today.`;
      } else if (gap < 0) {
        narrative.textContent = `${realPctPrefix}But this site's trend is actually improving — in ${years} years the illustrative measure could drop to ${bauPct.toFixed(0)}% (${bauBand.label}). Not every site tells the same story.`;
      } else {
        narrative.textContent = `${realPctPrefix}In ${years} years, the illustrative measure holds around ${bauPct.toFixed(0)}% either way.`;
      }
    }
    document.getElementById("proj-disclaimer").textContent = site.hasModel
      ? `The two numbers above use only vegetation + construction trend, extended with simple math (${refDate.getFullYear()}–${lastDate.getFullYear()} real data) — not the trained model re-run into the future. The real risk score above also weighs slope, elevation, and rainfall, which is why the two numbers can land far apart.`
      : `This measure uses only vegetation + construction trend, extended with simple math (${refDate.getFullYear()}–${lastDate.getFullYear()} real data) — it is not a trained, validated risk score, since this terrain type isn't in the trained model's scope yet.`;
  }

  // ---------- global disaster watch (real Supabase backend) ----------
  // Calls a server-side Edge Function (fetch-gdacs) backed by a real Postgres database.
  // GDACS itself blocks direct browser requests (confirmed: no Access-Control-Allow-Origin
  // header on its API), which is exactly why this needs a real backend and can't be done
  // as a static page -- see sihPlan/memory.md for the CORS check that led to this.
  // (SUPABASE_URL / SUPABASE_ANON_KEY declared once, near the top of this file.)

  function resetGdacsPanel() {
    const btn = document.getElementById("gdacs-check-btn");
    const result = document.getElementById("gdacs-result");
    btn.disabled = false;
    btn.textContent = "Check live now";
    result.className = "gdacs-result";
    result.innerHTML = "";
  }

  // Real bearing (site -> event) from the actual lat/lon pair, so "how far" also comes
  // with "which direction" -- both computed, neither guessed.
  function compassDirection(lat1, lon1, lat2, lon2) {
    const toRad = (d) => (d * Math.PI) / 180;
    const dLon = toRad(lon2 - lon1);
    const y = Math.sin(dLon) * Math.cos(toRad(lat2));
    const x = Math.cos(toRad(lat1)) * Math.sin(toRad(lat2)) - Math.sin(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.cos(dLon);
    const brng = ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][Math.round(brng / 45) % 8];
  }

  function checkGdacs() {
    if (!currentSite) return;
    const btn = document.getElementById("gdacs-check-btn");
    const result = document.getElementById("gdacs-result");
    btn.disabled = true;
    btn.textContent = "Checking…";
    result.className = "gdacs-result";
    result.innerHTML = `<div class="gdacs-detail">Checking GDACS now…</div>`;

    fetch(`${SUPABASE_URL}/functions/v1/fetch-gdacs`, {
      method: "POST",
      headers: { Authorization: `Bearer ${SUPABASE_ANON_KEY}`, apikey: SUPABASE_ANON_KEY },
    })
      .then((r) => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then((json) => {
        btn.disabled = false;
        btn.textContent = "Check again";
        if (!json.ok) throw new Error(json.error || "unknown error");
        const mine = (json.snapshots || []).find((s) => s.site_id === currentSite.site_id);
        const fetchedAt = mine ? new Date(mine.fetched_at) : new Date();
        const timeStr = fetchedAt.toLocaleTimeString();
        if (mine && mine.distance_km != null) {
          const dir = compassDirection(currentSite.latitude, currentSite.longitude, mine.event_lat, mine.event_lon);
          const eventName = mine.event_name || "Active event";
          const country = (mine.raw || {}).country;
          const showCountry = country && !eventName.toLowerCase().includes(country.toLowerCase());
          result.className = "gdacs-result hit";
          result.innerHTML = `
            <div class="gdacs-headline">${eventName} — ${mine.distance_km}km ${dir}${showCountry ? `, ${country}` : ""}</div>
            <div class="gdacs-detail">GDACS alert level: ${mine.alert_level || "n/a"}. Type: ${mine.event_type || "n/a"}.</div>
            <div class="gdacs-meta">Checked live at ${timeStr}.</div>`;
        } else {
          result.className = "gdacs-result clear";
          result.innerHTML = `
            <div class="gdacs-headline">No active GDACS event within 500km right now</div>
            <div class="gdacs-meta">Checked live at ${timeStr}.</div>`;
        }
      })
      .catch((err) => {
        btn.disabled = false;
        btn.textContent = "Try again";
        result.className = "gdacs-result";
        result.innerHTML = `<div class="gdacs-detail">Live check failed (${err.message}).</div>`;
      });
  }
  document.getElementById("gdacs-check-btn").addEventListener("click", checkGdacs);

  // ---------- select site (drives the whole profile) ----------
  let currentSite = null;
  function selectSite(siteId) {
    const site = allSites.find((s) => s.site_id === siteId);
    if (!site) return;
    currentSite = site;
    document.querySelectorAll(".map-marker").forEach((m) => m.classList.toggle("active", m.getAttribute("data-site") === siteId));
    document.querySelectorAll(".site-pill").forEach((p) => p.classList.toggle("active", p.dataset.site === siteId));
    renderProfileHead(site);
    renderProfileWhy(site);
    renderProfileRisk(site);
    renderProfileBA(site);
    renderProfileProjection(site);
    renderProfileLive(site);
    renderEarlyWarning(site);
    resetGdacsPanel();
    if (typeof loadSiteIntoCalculator === "function") {
      if (site.hasModel) loadSiteIntoCalculator(site);
      else showCalcUnavailable(site);
    }
  }
  // Initial site selection happens after the calculator is built below (see
  // `selectSite(...)` call near the end of this file) -- calling it here, before
  // loadSiteIntoCalculator exists yet, would skip syncing the calculator on first load.

  // ---------- live calculator (real trained model, running client-side) ----------
  // Reproduces ml/train_model.py's predict_proba() exactly: standardize each feature
  // with the real fitted scaler mean/scale, dot with the real fitted coefficients, add
  // the real intercept, sigmoid. Verified against the Python output before this UI was
  // built (see sihPlan/memory.md) -- this is not an approximation.
  const MP = D.model_params;
  const CALC_CONFIG = {
    ndvi_trend_slope: { label: "Vegetation trend", unit: "/yr", min: -0.01, max: 0.03, step: 0.0005, decimals: 4, group: "controllable" },
    ndbi_trend_slope: { label: "Construction trend", unit: "/yr", min: -0.02, max: 0.085, step: 0.0005, decimals: 4, group: "controllable" },
    mean_slope_degrees: { label: "Slope steepness", unit: "°", min: 0, max: 35, step: 0.5, decimals: 1, group: "fixed" },
    elevation_mean_m: { label: "Elevation", unit: "m", min: 0, max: 3700, step: 50, decimals: 0, group: "fixed" },
    rainfall_anomaly_pct: { label: "Rainfall anomaly", unit: "%", min: -80, max: 180, step: 1, decimals: 0, group: "fixed" },
    lst_trend_slope: { label: "Land surface warming", unit: "°C/yr", min: -0.25, max: 1.1, step: 0.01, decimals: 2, group: "fixed" },
  };

  function sigmoid(z) { return 1 / (1 + Math.exp(-z)); }

  function calcPredict(values) {
    // values: {feature: rawValue}. terrain_is_coastal is 0/1 directly (not a slider).
    let z = MP.intercept;
    MP.feature_cols.forEach((col, i) => {
      const x = values[col];
      const standardized = (x - MP.scaler_mean[i]) / MP.scaler_scale[i];
      z += standardized * MP.coefficients[i];
    });
    return sigmoid(z);
  }

  let calcValues = {};

  function calcDefaultValues() {
    // Start from the sample mean of each real feature -- a "typical" site, not an
    // arbitrary zero.
    const vals = {};
    MP.feature_cols.forEach((col, i) => { vals[col] = MP.scaler_mean[i]; });
    return vals;
  }

  const slidersEl = document.getElementById("calc-sliders");
  function buildCalcSliders() {
    calcValues = calcDefaultValues();
    calcValues.terrain_is_coastal = Math.round(calcValues.terrain_is_coastal);
    slidersEl.innerHTML = "";
    ["controllable", "fixed"].forEach((group) => {
      const title = document.createElement("div");
      title.className = "calc-group-title" + (group === "controllable" ? " controllable" : "");
      title.textContent = group === "controllable" ? "You can influence these" : "Fixed geography & weather";
      slidersEl.appendChild(title);
      MP.feature_cols.forEach((col) => {
        const cfg = CALC_CONFIG[col];
        if (!cfg || cfg.group !== group) return;
        const row = document.createElement("div");
        row.className = "calc-slider-row";
        row.innerHTML = `
          <div class="calc-label"><span class="name">${cfg.label}</span><span class="val" id="calc-val-${col}"></span></div>
          <input type="range" id="calc-slider-${col}" min="${cfg.min}" max="${cfg.max}" step="${cfg.step}" value="${calcValues[col]}">
        `;
        slidersEl.appendChild(row);
      });
      if (group === "fixed") {
        const toggleRow = document.createElement("div");
        toggleRow.className = "calc-slider-row";
        toggleRow.innerHTML = `
          <div class="calc-label"><span class="name">Terrain type</span></div>
          <div class="calc-toggle">
            <button id="calc-terrain-hill" class="active">Hill / mountain</button>
            <button id="calc-terrain-coastal">Coastal</button>
          </div>
        `;
        slidersEl.appendChild(toggleRow);
      }
    });

    MP.feature_cols.forEach((col) => {
      if (col === "terrain_is_coastal") return;
      const slider = document.getElementById(`calc-slider-${col}`);
      if (!slider) return;
      slider.addEventListener("input", (e) => {
        calcValues[col] = parseFloat(e.target.value);
        updateCalcDisplay();
      });
    });
    document.getElementById("calc-terrain-hill").addEventListener("click", () => { calcValues.terrain_is_coastal = 0; updateCalcDisplay(); });
    document.getElementById("calc-terrain-coastal").addEventListener("click", () => { calcValues.terrain_is_coastal = 1; updateCalcDisplay(); });
    updateCalcDisplay();
  }

  function updateCalcDisplay() {
    MP.feature_cols.forEach((col) => {
      const cfg = CALC_CONFIG[col];
      if (!cfg) return;
      const el = document.getElementById(`calc-val-${col}`);
      if (el) el.textContent = (calcValues[col] >= 0 && cfg.min < 0 ? "+" : "") + calcValues[col].toFixed(cfg.decimals) + cfg.unit;
      const slider = document.getElementById(`calc-slider-${col}`);
      if (slider) slider.value = calcValues[col];
    });
    document.getElementById("calc-terrain-hill").classList.toggle("active", calcValues.terrain_is_coastal === 0);
    document.getElementById("calc-terrain-coastal").classList.toggle("active", calcValues.terrain_is_coastal === 1);

    const prob = calcPredict(calcValues);
    const pct = prob * 100;
    const rw = riskWord(pct);
    const numEl = document.getElementById("calc-result-num");
    numEl.textContent = pct.toFixed(0) + "%";
    numEl.style.color = riskWordColor(rw.cls);
    document.getElementById("calc-result-label").textContent = rw.label + " modeled risk";

    renderCalcRecommendation(calcValues, prob);
  }

  // Which of the two controllable levers actually moves the number more, AT THESE
  // CURRENT settings -- this is what makes the calculator a real (if narrow) planning
  // signal instead of just a toy. Compares an equal-sized nudge to each lever: one
  // standard deviation (the real sample's own scaler_scale, already fitted by
  // ml/train_model.py) in the risk-reducing direction, so the two levers are compared on
  // a fair, model-native unit rather than an arbitrary "amount of effort" guess. Not a
  // cost/feasibility comparison -- says so explicitly in the UI.
  function renderCalcRecommendation(values, baselineProb) {
    const el = document.getElementById("calc-recommend");
    if (!el) return;
    const ndviIdx = MP.feature_cols.indexOf("ndvi_trend_slope");
    const ndbiIdx = MP.feature_cols.indexOf("ndbi_trend_slope");
    if (ndviIdx === -1 || ndbiIdx === -1) { el.innerHTML = ""; return; }

    const ndviStep = MP.scaler_scale[ndviIdx]; // higher ndvi trend lowers risk (coef < 0)
    const ndbiStep = MP.scaler_scale[ndbiIdx]; // lower ndbi trend lowers risk (coef > 0)
    const ndviBetter = calcPredict({ ...values, ndvi_trend_slope: values.ndvi_trend_slope + ndviStep });
    const ndbiBetter = calcPredict({ ...values, ndbi_trend_slope: values.ndbi_trend_slope - ndbiStep });
    const ndviGain = Math.max(0, (baselineProb - ndviBetter) * 100);
    const ndbiGain = Math.max(0, (baselineProb - ndbiBetter) * 100);
    const maxGain = Math.max(ndviGain, ndbiGain, 0.1);

    const rows = [
      { label: "Vegetation restoration", gain: ndviGain },
      { label: "Slower construction", gain: ndbiGain },
    ].sort((a, b) => b.gain - a.gain);

    const barsHtml = rows.map((r, i) => `
      <div class="cr-bar-row">
        <div class="cr-bar-label">${r.label}</div>
        <div class="cr-bar-track"><div class="cr-bar-fill ${i === 0 ? "lead" : "behind"}" style="transform:scaleX(${r.gain / maxGain})"></div></div>
        <div class="cr-bar-val">-${r.gain.toFixed(1)}pt</div>
      </div>`).join("");

    const leader = rows[0], laggard = rows[1];
    const verdict = leader.gain < 0.5
      ? `Neither lever moves the number much at these settings — risk here is dominated by fixed factors (slope, rainfall, elevation), not vegetation or construction trend.`
      : `At this site's current settings, an equal-sized push on <strong>${leader.label.toLowerCase()}</strong> cuts modeled risk about ${(leader.gain / Math.max(laggard.gain, 0.01)).toFixed(1)}× more than the same-sized push on ${laggard.label.toLowerCase()}.`;

    el.innerHTML = `
      <div class="calc-recommend-title">Which lever matters more, here (one standard deviation of improvement, either way)</div>
      <div class="calc-recommend-bars">${barsHtml}</div>
      <div class="calc-recommend-verdict">${verdict}</div>
    `;
  }

  // Presets: load a REAL site's real values, so the calculator visibly reproduces the
  // exact number already shown for that site above -- the credibility check -- before
  // the user drags anything.
  const presetsEl = document.getElementById("calc-presets");
  const presetBtns = {};

  // Loads any real site's actual values into the calculator -- used by both the quick-
  // preset buttons below AND by selectSite() up top, so picking a site anywhere on the
  // page (all 17 real sites, not just the 4 with a dedicated button) carries through to
  // the calculator instead of leaving it on stale/unrelated numbers.
  const calcUnavailableEl = document.getElementById("calc-unavailable-note");

  function loadSiteIntoCalculator(s) {
    calcUnavailableEl.style.display = "none";
    MP.feature_cols.forEach((col) => {
      if (col === "terrain_is_coastal") return;
      if (s[col] != null) calcValues[col] = s[col];
    });
    calcValues.terrain_is_coastal = s.terrain_type === "coastal" ? 1 : 0;
    presetsEl.querySelectorAll(".calc-preset-btn").forEach((b) => b.classList.remove("active"));
    if (presetBtns[s.site_id]) presetBtns[s.site_id].classList.add("active");
    updateCalcDisplay();
  }

  // guna/silchar/jaisalmer etc -- real data exists, but no trained model for their
  // terrain type, so the calculator can't score them either. Leaves the calculator on
  // whatever it last showed rather than guessing, and says why plainly.
  function showCalcUnavailable(s) {
    presetsEl.querySelectorAll(".calc-preset-btn").forEach((b) => b.classList.remove("active"));
    calcUnavailableEl.style.display = "";
    calcUnavailableEl.textContent = `Calculator not available for ${s.site_name.split(",")[0]} -- ${s.not_in_model_reason || `terrain type '${s.terrain_type}' isn't in the trained model's scope yet.`} Showing the last loaded site's values below instead of a guess.`;
  }

  const presetSites = ["joshimath", "auli_control", "sundarbans", "coastal_control_tbd"].map((id) => allSites.find((s) => s.site_id === id)).filter(Boolean);
  presetSites.forEach((s) => {
    const btn = document.createElement("button");
    btn.className = "calc-preset-btn";
    btn.textContent = "Load " + s.site_name.split(",")[0];
    btn.addEventListener("click", () => loadSiteIntoCalculator(s));
    presetsEl.appendChild(btn);
    presetBtns[s.site_id] = btn;
  });
  const resetBtn = document.createElement("button");
  resetBtn.className = "calc-preset-btn";
  resetBtn.textContent = "Reset to average";
  resetBtn.addEventListener("click", () => {
    presetsEl.querySelectorAll(".calc-preset-btn").forEach((b) => b.classList.remove("active"));
    resetBtn.classList.add("active");
    buildCalcSliders();
  });
  presetsEl.appendChild(resetBtn);

  buildCalcSliders();

  // Now that the calculator exists, do the initial site selection -- this also syncs
  // the calculator to the default site via loadSiteIntoCalculator() inside selectSite().
  const modeledSites = allSites.filter((s) => s.hasModel);
  if (modeledSites.length) selectSite([...modeledSites].sort((a, b) => b.predicted_risk_prob - a.predicted_risk_prob)[0].site_id);


  // ---------- risk list (click a row to open it in the explorer above) ----------
  const riskListEl = document.getElementById("risk-list");
  // Only sites with a real trained score belong in a RISK RANKING -- guna/silchar/
  // jaisalmer are explorable above (real data) but have no score to rank by.
  [...modeledSites].sort((a, b) => b.predicted_risk_prob - a.predicted_risk_prob).forEach((s) => {
    const pct = s.predicted_risk_prob * 100;
    const rw = riskWord(pct);
    const row = document.createElement("div");
    row.className = "risk-row";
    row.style.cursor = "pointer";
    row.innerHTML = `
      <span class="name">${s.site_name}</span>
      <span class="terrain-badge">${s.terrain_type}</span>
      <span class="risk-word ${rw.cls}">${rw.label} (${pct.toFixed(0)}%)</span>
    `;
    row.addEventListener("click", () => {
      selectSite(s.site_id);
      document.getElementById("explore-section").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    riskListEl.appendChild(row);
  });
})();
