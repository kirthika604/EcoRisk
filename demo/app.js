// SIH26206 demo logic. All values either come straight from window.JOSHIMATH_DATA
// (generated from real CSVs by build_data.py) or are computed from it. Anything
// illustrative/mocked is labeled as such in the UI -- see sihPlan/memory.md.
(function () {
  const DATA = window.JOSHIMATH_DATA;
  const MS_PER_DAY = 86400000;

  function toDate(s) { return new Date(s + "T00:00:00Z"); }
  function dayNum(d, ref) { return (d.getTime() - ref.getTime()) / MS_PER_DAY; }

  // ---------- linear regression ----------
  function linreg(xs, ys) {
    const n = xs.length;
    const sx = xs.reduce((a, b) => a + b, 0);
    const sy = ys.reduce((a, b) => a + b, 0);
    const sxx = xs.reduce((a, b) => a + b * b, 0);
    const sxy = xs.reduce((a, b, i) => a + b * ys[i], 0);
    const slope = (n * sxy - sx * sy) / (n * sxx - sx * sx);
    const intercept = (sy - slope * sx) / n;
    return { slope, intercept, at: (x) => slope * x + intercept };
  }

  const timeline = DATA.merged_timeline.map((r) => ({ ...r, d: toDate(r.date) }));
  const refDate = timeline[0].d;
  const lastDate = timeline[timeline.length - 1].d;
  const target2030 = new Date("2030-01-01T00:00:00Z");

  const tNdvi = timeline.map((r) => dayNum(r.d, refDate));
  const yNdvi = timeline.map((r) => r.ndvi);
  const yNdbi = timeline.map((r) => r.ndbi);
  const ndviFit = linreg(tNdvi, yNdvi);
  const ndbiFit = linreg(tNdvi, yNdbi);

  const tLast = dayNum(lastDate, refDate);
  const t2030 = dayNum(target2030, refDate);

  const ndviAtLast = ndviFit.at(tLast);
  const ndviAt2030 = ndviFit.at(t2030);
  const ndbiAtLast = ndbiFit.at(tLast);
  const ndbiAt2030 = ndbiFit.at(t2030);

  const ndviObsMin = Math.min(...yNdvi), ndviObsMax = Math.max(...yNdvi);
  const ndbiObsMin = Math.min(...yNdbi), ndbiObsMax = Math.max(...yNdbi);
  // "healthy baseline" = mean of first 10 real observations (early 2019)
  const ndviBaseline = yNdvi.slice(0, 10).reduce((a, b) => a + b, 0) / 10;

  function clamp01(x) { return Math.max(0, Math.min(1, x)); }

  function vulnerabilityIndex(ndviVal, ndbiVal) {
    const ndviComponent = clamp01((ndviBaseline - ndviVal) / ndviBaseline);
    const ndbiComponent = clamp01((ndbiVal - ndbiObsMin) / (ndbiObsMax - ndbiObsMin));
    return { pct: ((ndviComponent + ndbiComponent) / 2) * 100, ndviComponent, ndbiComponent };
  }

  function bandOf(pct) {
    if (pct < 25) return { label: "Low", color: "var(--ok)" };
    if (pct < 50) return { label: "Moderate", color: "var(--warn)" };
    if (pct < 75) return { label: "Elevated", color: "var(--accent2)" };
    return { label: "High", color: "var(--danger)" };
  }

  const scenarios = [
    {
      key: "current",
      name: "Current (2023)",
      ndvi: ndviAtLast,
      ndbi: ndbiAtLast,
      detail: `Trend-fitted value at last observation (${DATA.merged_timeline[DATA.merged_timeline.length - 1].date}).`,
    },
    {
      key: "bau2030",
      name: "BAU 2030",
      ndvi: ndviAt2030,
      ndbi: ndbiAt2030,
      detail: "Linear trend from 2019–2023 continued unchanged to 2030.",
    },
    {
      key: "intervention2030",
      name: "Intervention 2030",
      ndvi: ndviAtLast,
      ndbi: ndbiAtLast,
      detail: "Human-activity trend held flat at today's level from now to 2030 (activity halted, not reversed).",
    },
  ].map((s) => ({ ...s, ...vulnerabilityIndex(s.ndvi, s.ndbi) }));

  // ---------- SVG line chart ----------
  function drawChart(svgId, key, fit, extendToT) {
    const svg = document.getElementById(svgId);
    const W = 460, H = 220, PAD = 34;
    const xs = tNdvi;
    const ys = timeline.map((r) => r[key]);
    const allYs = ys.concat([fit.at(0), fit.at(extendToT)]);
    const yMin = Math.min(...allYs), yMax = Math.max(...allYs);
    const xMax = extendToT;
    const xScale = (t) => PAD + (t / xMax) * (W - PAD * 2);
    const yScale = (v) => H - PAD - ((v - yMin) / (yMax - yMin)) * (H - PAD * 2);

    let svgNS = "http://www.w3.org/2000/svg";
    function el(tag, attrs) {
      const e = document.createElementNS(svgNS, tag);
      for (const k in attrs) e.setAttribute(k, attrs[k]);
      return e;
    }

    // axes
    svg.appendChild(el("line", { x1: PAD, y1: H - PAD, x2: W - PAD, y2: H - PAD, stroke: "#23324d" }));
    svg.appendChild(el("line", { x1: PAD, y1: PAD, x2: PAD, y2: H - PAD, stroke: "#23324d" }));

    // year ticks
    for (let year = 2019; year <= 2030; year += (year < 2023 ? 1 : (year === 2023 ? 1 : 3))) {
      const d = new Date(Date.UTC(year, 0, 1));
      const t = dayNum(d, refDate);
      if (t < 0 || t > xMax) continue;
      const x = xScale(t);
      svg.appendChild(el("line", { x1: x, y1: H - PAD, x2: x, y2: H - PAD + 4, stroke: "#5a6b8c" }));
      const label = el("text", { x: x, y: H - PAD + 16, fill: "#9fb0c9", "font-size": 9, "text-anchor": "middle" });
      label.textContent = year;
      svg.appendChild(label);
    }

    // observed line
    let path = "";
    timeline.forEach((r, i) => {
      const x = xScale(tNdvi[i]);
      const y = yScale(r[key]);
      path += (i === 0 ? "M" : "L") + x.toFixed(1) + "," + y.toFixed(1) + " ";
    });
    svg.appendChild(el("path", { d: path, fill: "none", stroke: "#4fd1c5", "stroke-width": 1.5 }));

    // trend line from t=0 to extendToT
    const x1 = xScale(0), y1 = yScale(fit.at(0));
    const x2 = xScale(extendToT), y2 = yScale(fit.at(extendToT));
    svg.appendChild(el("line", { x1, y1, x2, y2, stroke: "#f6ad55", "stroke-width": 1.5, "stroke-dasharray": "5,4" }));

    // marker at 2030
    svg.appendChild(el("circle", { cx: x2, cy: y2, r: 3, fill: "#f6ad55" }));
  }

  drawChart("chart-ndvi", "ndvi", ndviFit, t2030);
  drawChart("chart-ndbi", "ndbi", ndbiFit, t2030);

  // ---------- rainfall threshold + backtest ----------
  const rainByDate = new Map(DATA.power_rainfall_daily.map((r) => [r.date, r.rainfall_mm]));
  function rollingSum(endDateStr, days) {
    const end = toDate(endDateStr);
    let sum = 0, found = 0;
    for (let i = 0; i < days; i++) {
      const d = new Date(end.getTime() - i * MS_PER_DAY);
      const key = d.toISOString().slice(0, 10);
      if (rainByDate.has(key)) { sum += rainByDate.get(key); found++; }
    }
    return found > 0 ? sum : null;
  }

  document.getElementById("th-10").textContent = DATA.threshold.antecedent_10day_mm + " mm";
  document.getElementById("th-20").textContent = DATA.threshold.antecedent_20day_mm + " mm";
  document.getElementById("th-citation").innerHTML =
    `Source: ${DATA.threshold.source}. <em>${DATA.threshold.caveat}</em>`;

  const backtestContainer = document.getElementById("backtest-cards");
  const lastRealDate = DATA.merged_timeline[DATA.merged_timeline.length - 1].date;
  const backtestPoints = [
    { label: "Slow window start (1 Apr 2022)", date: "2022-04-01" },
    { label: "Rapid window — reported trigger (2 Jan 2023)", date: "2023-01-02" },
    { label: `Last data point (${lastRealDate})`, date: lastRealDate },
  ];
  let anyExceeded = false;
  backtestPoints.forEach((bp) => {
    const s10 = rollingSum(bp.date, 10);
    const s20 = rollingSum(bp.date, 20);
    if (s10 >= DATA.threshold.antecedent_10day_mm || s20 >= DATA.threshold.antecedent_20day_mm) anyExceeded = true;
    const card = document.createElement("div");
    card.className = "backtest-card";
    function barRow(label, val, threshold) {
      const pct = Math.min(100, (val / threshold) * 100);
      const cls = val >= threshold ? "over" : "under";
      return `<div class="bar-row"><span style="width:60px">${label}</span>
        <span class="bar-track"><span class="bar-fill ${cls}" style="width:${pct}%"></span></span>
        <span class="bar-val">${val.toFixed(0)}/${threshold}mm</span></div>`;
    }
    card.innerHTML = `<div class="title">${bp.label}</div>` +
      (s10 !== null ? barRow("10-day", s10, DATA.threshold.antecedent_10day_mm) : "<div class='bar-row'>10-day: no data</div>") +
      (s20 !== null ? barRow("20-day", s20, DATA.threshold.antecedent_20day_mm) : "<div class='bar-row'>20-day: no data</div>");
    backtestContainer.appendChild(card);
  });
  document.getElementById("backtest-narrative").textContent = anyExceeded
    ? "At least one backtested window crossed the cited rainfall threshold."
    : "Neither documented Joshimath subsidence window crossed the cited rainfall threshold (antecedent rainfall was near zero both times) — this is a real finding from the NASA POWER data, not a display error. It's consistent with the government expert committee's (NDMA/GSI/CBRI) attribution of this subsidence to hydrological imbalance, drainage failure, and anthropogenic activity rather than a rainfall trigger. The threshold is a real, cited landslide-trigger mechanism for this region generally — it just wasn't the proximate cause of these two specific events, which strengthens (not weakens) the case for tracking the slower human-activity trend directly.";

  // ---------- scenario slider ----------
  const slider = document.getElementById("scenario-slider");
  const grid = document.getElementById("scenario-grid");
  const narrative = document.getElementById("scenario-narrative");

  function renderScenarios(activeIdx) {
    grid.innerHTML = "";
    scenarios.forEach((s, i) => {
      const band = bandOf(s.pct);
      const card = document.createElement("div");
      card.className = "scenario-card" + (i === activeIdx ? " active" : "");
      card.innerHTML = `
        <div class="name">${s.name}</div>
        <div class="vuln" style="color:${band.color}">${s.pct.toFixed(0)}%</div>
        <div class="band" style="color:${band.color}">${band.label} vulnerability</div>
        <div class="detail">NDVI: ${s.ndvi.toFixed(3)} · NDBI: ${s.ndbi.toFixed(3)}<br>${s.detail}</div>
      `;
      grid.appendChild(card);
    });
    const active = scenarios[activeIdx];
    const round = (x) => Math.round(x);
    const cur = round(scenarios[0].pct), bauPct = round(scenarios[1].pct), intervPct = round(scenarios[2].pct);
    if (activeIdx === 0) {
      narrative.textContent = `Today's illustrative vulnerability index sits at ${cur}% (${bandOf(active.pct).label}), based on the observed 2019–2023 NDVI/NDBI trend.`;
    } else if (activeIdx === 1) {
      narrative.textContent = `If deforestation/construction trends continue unchanged (business-as-usual) through 2030, the index rises to ${bauPct}% — a ${bauPct - cur} point increase from today.`;
    } else {
      narrative.textContent = `If human activity is held at today's level (not reversed, just halted) through 2030, the index stays at ${intervPct}% — ${bauPct - intervPct} points lower than the BAU 2030 projection.`;
    }
  }
  renderScenarios(0);
  slider.addEventListener("input", () => renderScenarios(parseInt(slider.value, 10)));

  // ---------- live rainfall ----------
  const statusEl = document.getElementById("live-status");
  const { lat, lon } = DATA.coordinates;
  fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=precipitation,temperature_2m&daily=precipitation_sum&timezone=auto`)
    .then((r) => {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then((json) => {
      document.getElementById("live-precip").textContent = json.current.precipitation.toFixed(1);
      document.getElementById("live-temp").textContent = json.current.temperature_2m.toFixed(1);
      document.getElementById("live-today").textContent = json.daily.precipitation_sum[0].toFixed(1);
      statusEl.textContent = "Live — fetched " + new Date(json.current.time).toLocaleString();
      statusEl.className = "live-status ok";
    })
    .catch((err) => {
      statusEl.textContent = "Live fetch failed (" + err.message + ") — network may be unavailable in this environment.";
      statusEl.className = "live-status error";
    });
})();
