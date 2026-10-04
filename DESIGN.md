---
name: EcoRisk AI
description: Multi-site disaster-risk model dashboard, SIH26206
colors:
  bg: "#0b1220"
  panel: "#121b2e"
  panel-deep: "#0d1626"
  panel-border: "#23324d"
  text: "#e7ecf5"
  text-dim: "#9fb0c9"
  accent-signal: "#4fd1c5"
  accent-flag: "#f6ad55"
  danger: "#f56565"
  warn: "#ecc94b"
  ok: "#68d391"
typography:
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "15px"
    lineHeight: 1.5
  heading:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontWeight: 700
  numeric:
    fontFeature: "tabular-nums"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
  xl: "10px"
spacing:
  xs: "6px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "28px"
components:
  tag-real:
    backgroundColor: "rgba(79,209,197,0.15)"
    textColor: "{colors.accent-signal}"
    rounded: "{rounded.sm}"
  tag-mock:
    backgroundColor: "rgba(246,173,85,0.15)"
    textColor: "{colors.accent-flag}"
    rounded: "{rounded.sm}"
  tag-live:
    backgroundColor: "rgba(104,211,145,0.15)"
    textColor: "{colors.ok}"
    rounded: "{rounded.sm}"
  panel-card:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.xl}"
    padding: "20px"
---

# Design System: EcoRisk AI

## Overview

**Creative North Star: "Mission Control for a Slow Disaster"**

This is an evidence dashboard, not a marketing page: dark, dense, numeric, built for
someone deciding whether to trust the model in front of them. The aesthetic borrows from
scientific instrument panels and command-center displays — near-black navy ground, cool
teal telemetry accent, panels that read like readouts rather than cards in a consumer
app. Every claim carries a visible provenance tag (`Real data` / `Illustrative` / `Live`)
because the product's entire credibility argument rests on judges being able to tell real
findings from illustrative ones at a glance, not by reading fine print.

Confirmed visual rejection: no gamification, no rounded-pill marketing chrome, no
decorative illustration. This is instrumentation, not persuasion.

**Key Characteristics:**
- Near-black navy ground with cool, low-saturation panels — a control-room, not a brochure
- One cyan-teal signal color for "this is real and confirmed"; amber strictly reserved for "illustrative/needs confirmation"
- Tabular numerals everywhere a number appears in a data context
- Left-border citation blocks — sourcing is a first-class visual element, not a footnote
- Flat, bordered panels; no drop shadows; depth comes from border + fill contrast, not elevation

## Colors

A near-monochrome navy field carries the whole surface; two accent colors are rationed to specific semantic jobs, never decorative.

### Primary
- **Signal Teal** (#4fd1c5): the "this is real, confirmed, verified" color. Used for the `Real data` tag, primary chart lines/trend markers, citation left-borders, active-state highlights (selected slider position, focused row). Its scarcity IS its credibility — if teal starts appearing on unconfirmed things, the whole tagging system stops meaning anything.

### Secondary
- **Amber Flag** (#f6ad55): the "illustrative, mocked, or needs verification" color. Used for the `Illustrative` tag, secondary trend lines (BAU projections), and any figure that is a demo construct rather than a sourced fact. Never used for anything the team would defend as fact under questioning.

### Tertiary (semantic status only)
- **Alert Red** (#f56565): risk/danger states, values exceeding a threshold, false positives/misses in validation results (state these plainly, don't hide them).
- **Caution Yellow** (#ecc94b): warning/borderline states.
- **Confirm Green** (#68d391): "under threshold" / "live and working" states, the `Live` tag.

### Neutral
- **Deep Space** (#0b1220): page background.
- **Instrument Panel** (#121b2e): card/section background, one step lighter than the page.
- **Panel Well** (#0d1626): recessed inner surfaces — chart backgrounds, citation blocks, stat sub-cards. Reads as "sunken" relative to its parent panel purely through value, no shadow.
- **Panel Line** (#23324d): all borders and dividers.
- **Signal White** (#e7ecf5): primary text.
- **Instrument Grey** (#9fb0c9): secondary/label text, sub-headers, captions.

### Named Rules
**The Provenance Tag Rule.** Every section that makes a claim carries exactly one status tag (`real` / `mock` / `live`) immediately after its heading. A section with no tag is a bug, not a stylistic choice.

**The Teal Scarcity Rule.** Signal Teal marks confirmed fact. It never appears on a projected, illustrative, or unverified value — that is what Amber Flag is for. Mixing them erodes the one visual signal judges can trust at a glance.

## Typography

**Body/Display Font:** -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif (system stack — deliberate, not a fallback of convenience)

**Character:** A workhorse system sans, doing zero personality work of its own so that data and color carry all the expression. This is an Operate-mode instrument, not a Persuade-mode pitch page; a display face here would compete with the numbers for attention.

### Hierarchy
A fine-grained but deliberate scale for a dense instrument panel — each step earns its place by a distinct job, not decoration:
- **Page Title** (700, 22px): the one page-level `<h1>`, states the surface's subject plainly.
- **Claim Quote** (400, 17px, line-height 1.6): reserved for the single callout meant to be read as an assertion, not a caption (e.g. the Claim panel's thesis statement).
- **Section Heading** (700, 16px): panel `<h2>`, always paired with its provenance tag.
- **Stat Value — primary** (700, 28–30px, tabular-nums): the page's single most important number in a given section.
- **Stat Value — standard** (700, 26px, tabular-nums): secondary stat blocks in the same section.
- **Body** (400, 15px, line-height 1.5): running/explanatory text, panel `.sub` captions.
- **Sub-caption** (400, 13px, `--text-dim`): card titles, list body copy, secondary panel text.
- **Label** (400, 12px, `--text-dim`): stat labels, chart legends, table cell text.
- **Small Label** (600–700, 11px): table column headers (uppercase, 0.03em tracking), status badges.
- **Micro Tag** (700, 10px, uppercase, 0.04em tracking): the real/mock/live provenance badges only — the smallest text with semantic weight.
- **Chart Axis** (400, 9px, `--text-dim`): SVG chart tick labels — the one place dense enough to justify going below Micro Tag; never used for anything a judge needs to read at a glance.

### Named Rules
**The Tabular Numerals Rule.** Any number that could sit in a table, ranking, or comparison uses `font-variant-numeric: tabular-nums`. Numbers that don't align make the instrument look broken.

## Layout

Single-column content, `max-width: 1100px`, centered, generous outer padding (24px). Sections stack vertically as full-width panels with consistent 22px gaps — no sidebar, no multi-column page chrome; this reads top-to-bottom like an instrument log, which also suits a presenter scrolling through it in a scripted sequence. Within a panel, sub-content may go to a flex-wrap row (charts side by side, stat blocks in a row, card grids) with a `flex: 1 1 <minwidth>` pattern so it reflows to single-column under ~640px without a defined breakpoint — density degrades gracefully rather than jumping between fixed layouts.

## Elevation & Depth

No shadows anywhere in the system. Depth is conveyed entirely through a three-step fill hierarchy (Deep Space → Instrument Panel → Panel Well) plus 1px borders in Panel Line. A "recessed" surface (chart background, citation block, inner stat card) is simply one step darker than its parent, never shadowed. This keeps the instrument-panel read flat and precise rather than soft/glossy.

### Named Rules
**The Flat Stack Rule.** Depth = fill value + border, never box-shadow. A shadow anywhere in this system is a bug.

## Shapes

Corners are gently rounded throughout (6–10px), never sharp, never pill-shaped. Panels use the largest radius in the scale (10px); nested/inner elements (stat sub-cards, chart boxes, citation blocks) use a smaller radius (6–8px), so nesting reads as a size relationship, not a random mix. Borders are always 1px, always Panel Line color — never a second border weight or color introduced for emphasis (emphasis is a box-shadow-free ring: `box-shadow: 0 0 0 1px var(--accent)` swapped in on the accent color instead, e.g. the active scenario card).

## Components

### Tags (provenance badges)
- **Shape:** 4px radius, tight padding (2px 7px), uppercase, 10px/700 weight, 0.04em tracking.
- **Real:** teal text/border on 15%-opacity teal fill.
- **Mock:** amber text/border on 15%-opacity amber fill.
- **Live:** green text/border on 15%-opacity green fill.
- Always sits inline immediately after a section's `<h2>`, never floated elsewhere.

### Cards / Panels
- **Corner Style:** 10px (outer panel), 6–8px (nested/inner elements).
- **Background:** Instrument Panel (outer), Panel Well (nested/inner).
- **Shadow Strategy:** none — see Elevation & Depth.
- **Border:** 1px Panel Line; active/selected state swaps to a 1px accent-teal border plus a 1px accent-teal focus ring (`box-shadow: 0 0 0 1px var(--accent)`), never a shadow.
- **Internal Padding:** 20px (outer panel), 12–16px (nested cards).

### Stat blocks
- Large tabular-nums value (26–30px/700) over a small dim label (12px). Used for both real metrics (LOOCV accuracy) and illustrative ones (vulnerability index) — the provenance tag on the parent section is what disambiguates, not the stat block's own styling.

### Citation blocks
- Panel Well background, 3px solid-teal left border, 10–12px padding, 4–6px radius, 12px dim text. Sourcing gets the same visual weight as a data callout, not footnote treatment.

### Progress/threshold bars
- 8px track (Panel Line-toned, `#1c2740`), filled bar in Confirm Green (under threshold) or Alert Red (over threshold), 4px radius both. Paired with a right-aligned tabular-nums value.

### Sliders (signature component)
- Native `<input type=range>` with `accent-color` set to Signal Teal — deliberately not a custom-skinned slider; the instrument-panel aesthetic doesn't need a bespoke control here, and native sliders keep touch/keyboard accessibility free.

### Navigation
- No persistent nav chrome. Cross-page links (e.g. to the Joshimath deep-dive) render as inline teal text links or a clearly-labeled panel-level link/button, never a header nav bar — the surface is built to be scrolled through once per session, not navigated repeatedly.

## Do's and Don'ts

### Do:
- **Do** tag every claim-bearing section with exactly one provenance badge (real/mock/live) beside its heading.
- **Do** reserve Signal Teal exclusively for confirmed/real elements; use Amber Flag for anything illustrative or unverified.
- **Do** use tabular-nums on every number that appears in a ranked, tabular, or comparative context.
- **Do** convey emphasis/selection via a 1px accent border + ring, never a shadow.
- **Do** keep citations visually equal in weight to data callouts (left-border block), not shrunk into footnotes.

### Don't:
- **Don't** introduce a box-shadow anywhere — depth is fill + border only.
- **Don't** use Alert Red decoratively; it means an actual over-threshold or a validation miss.
- **Don't** add a persistent header/nav bar — this is a single-scroll instrument, not a multi-page app shell.
- **Don't** use a display/serif font anywhere; the system stack carries the whole surface.
- **Don't** soften a reported limitation (e.g. round 70% up, or present 2/3 as if it were 3/3) — the visual system's credibility argument depends on the numbers being exactly what they say.
