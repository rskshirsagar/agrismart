# AgriSmart — design notes

How the `AgriSmart-Pond-Liner-ERP-2.html` prototype maps onto Frappe/ERPNext,
and why the structural choices were made.

---

## 1. The one decision that shapes everything

The prototype's own numbers: the farmer is quoted ₹105/sq.m, of which ₹89 goes
to the liner supplier and ₹16 to the installer — leaving AgriSmart a margin of
exactly **zero**. The real revenue sits in the commission block: ₹5.5/sq.m from
the principal, plus GST, less 2% TDS, less freight and expenses.

That reads as an **agency / channel-partner model**: AgriSmart never owns the
material, never invoices the farmer for it, and never holds stock. Three
consequences follow, and the app is built on them:

- **No Stock module involvement.** No stock ledger, no Delivery Note, no
  Perpetual Inventory. Godowns are a plain master, not a Warehouse.
- **No Sales Invoice to the farmer.** The farmer-facing documents are the
  quotation and estimate AgriSmart prints; the tax invoices come from the liner
  supplier and the installer directly.
- **The only accounting document that matters is the commission Sales Invoice**
  raised on the principal, from a Commission Claim.

If AgriSmart actually buys on its own GSTIN and resells, the architecture
changes materially — Purchase Order → Purchase Receipt → Delivery Note → Sales
Invoice, with real stock. Worth confirming before print formats are built out,
because that is the point where rework becomes expensive.

---

## 2. Architecture

The prototype keeps **one record per farmer** that accumulates survey, quote,
order, dispatch, installation, feedback and commission data across eleven
stages. That single-record shape is right for field work — a sales executive on
a phone in a village wants one screen, not seven linked documents — so the app
preserves it, and uses tabs rather than one long scroll.

**`Pond Project` is the spine.** Everything else hangs off it as a child table
or links back to it.

```
Pond Project  (ASF/LD/26-27/0001)  ── stage: Lead → … → Closed
├── Pond Wall                (4 rows: N/S/E/W — top, height, bottom, area)
├── Pond Qualification Item  (fixed checklist from the master)
├── Pond Document            (Aadhaar, PAN, 7/12, receipts, signed estimate)
├── Pond Challan             (LR / delivery challans)
├── Pond Installation Step   (site checklist)
├── Pond Photo               (stage-tagged gallery)
└── Pond Knowledge Share     (what material this farmer was sent)

Dispatch Trip      (1 vehicle → many projects)   ─┐
Installation Job   (1 team    → many projects)   ─┼─→ push stage back to project
Commission Claim   (1 month   → many projects)   ─┘

Pond Complaint     (many per project, with before/after photos)
Customer Feedback  (one per project, public web form capable)
Knowledge Asset    (shared library: brochures, videos, decks, certificates)
```

The three "many projects" documents are **submittable**. Submitting a Dispatch
Trip moves every farmer on it to *Dispatched*; submitting an Installation Job
with end dates moves them to *Completed*. That replaces per-record stage
clicking with one action that cannot leave half a truckload in the wrong state.

---

## 3. Module mapping

| Prototype screen | Implementation |
| --- | --- |
| Dashboard | Workspace with number cards and a stage chart |
| Leads & projects | `Pond Project` list, form and Kanban on `stage` |
| Pond calculator | `Pond Wall` + `utils/pond.py`, live preview via `public/js/pond_calc.js` |
| Quotations | Print Format; optional native `Quotation` via `make_quotation()` |
| Order booking | Sales Order tab + `Pond Document` with a pending counter |
| Dispatch & delivery | `Dispatch Trip` (submittable) + `Pond Challan` |
| Installation | `Installation Job` (submittable) + `Pond Installation Step` |
| Commission | `Commission Claim` (submittable) → `Sales Invoice` on the principal |
| Complaints | `Pond Complaint`, before/after photos, Open→Closed status |
| Service quality | `Customer Feedback` + `Feedback Criterion` master |
| Reports | `Pond Project Register` plus standard ERPNext reporting |
| Masters | Geography, Godown, Installation Team, Soil Type, Water Source, Complaint Nature, Qualification Item, Installation Step, Feedback Criterion, Pond Lead Source, Knowledge Asset |
| Settings | `AgriSmart Settings` (Single) |

### Reused from ERPNext rather than rebuilt

`Lead`, `Customer`, `Supplier`, `Sales Person`, `Vehicle`, `Driver`, `Item`,
`Quotation`, `Sales Invoice`, `Company`. Rebuilding these would forfeit the
reporting, permission and integration behaviour that already works.

### Deliberately not reused

- **Warehouse** for godowns — drags in stock accounting AgriSmart doesn't want.
- **Territory** for villages — a nested set rebuilt on every insert; thousands
  of Maharashtra villages would make that slow, and reporting would fight it.
  Three flat linked doctypes are simpler and faster.
- **Lead Source / UTM Source** — see §5.
- **Delivery Note** — see §1.

---

## 4. The calculation engine

`utils/pond.py` is a line-for-line port of the prototype's `computePond`,
`money` and `commissionRow`, with `indian_format` and `in_words` added for the
report. `public/js/pond_calc.js` mirrors it so the form updates as the user
types, and `validate()` recomputes server-side on save.

Verified two ways: exact agreement between JS and Python across 2,001
randomised geometries, and exact reproduction of every figure in
`Pond_Calculation_Report.docx` (27,810 sq.m liner, 4,30,313 cu.m, ₹29,20,050,
"Twenty Nine Lakh Twenty Thousand Fifty Only").

Two edges that matter more than they look:

- **Rounding.** JS `Math.round` rounds .5 up; Python's built-in `round` uses
  banker's rounding and would turn 3477.5 into 3475 where the prototype gives
  3480. `_round_half_up()` fixes it — on a 4,000 sq.m pond that is real money.
- **Explicit zeros.** An anchor width of 0 or a waste allowance of 0 is a
  legitimate survey finding, not "unset". `_or_default()` only falls back on
  `None`/`""`, and defaults seed on creation only, so a deliberate 0 survives.

Geometry: each wall is a trapezium `(top + bottom) / 2 × height`; the base is
`mean bottom length × mean bottom width`; the anchor trench is
`top perimeter × anchor width`. Sum, add waste %, round to the nearest 10.

**Keep the two implementations in step.** Drift shows up as figures that change
the moment the user hits Save — the most corrosive kind of bug in a tool a
farmer signs off on.

---

## 5. Version-sensitive choices

**Lead Source.** ERPNext v16 removed the CRM `Lead Source` doctype; `Lead.source`
became `Lead.utm_source` linking to `UTM Source`. Linking to `Lead Source`
breaks on v16, and linking to `UTM Source` breaks on v15. The app owns
`Pond Lead Source` instead, seeded with thirteen values and independent of both.

**Apps screen.** `frappe/apps.py::get_apps()` skips any installed app that does
not declare the `add_to_apps_screen` hook, whatever else it defines. The
`has_permission` call sits inside a `try/except` that only logs, so an
unimportable path hides the tile *silently* and looks identical to the hook
being missing. `utils/diagnose.py` walks these gates in order.

---

## 6. Things the prototype does that needed rethinking on a server

**Photos.** The prototype base64-encodes into localStorage. Here they are
`Attach Image` fields and File records. Compress client-side before upload —
phone-camera originals are 4–8 MB each and a project can carry thirty.

**Marathi transliteration.** `utils/marathi.py` ports the rule set, but no rule
set gets every Marathi surname right. Keep `farmer_name_mr` editable and treat
transliteration as a suggestion, not an auto-fill.

**Feedback collection.** The Google Form + CSV bridge was a workaround for
having no server. Expose a Web Form at `/pond-feedback` instead and let
`submit_public_feedback()` match on mobile number.

**Numbering.** `ASF/LD/26-27/0001` comes from `utils/numbering.py`. The
fiscal-year segment reads `AgriSmart Settings.fy_short` — roll it over each
April, or derive it from the active Fiscal Year.

**Offline.** Village sites often have no signal, and nothing here solves that.
The honest options are a PWA against the REST API, or keeping the HTML as a
field client that syncs. Decide early; it is hard to retrofit.

---

## 7. Known tension worth revisiting

Setting `qualification_status` to Qualified writes `stage` directly in
`validate()`. The *Pond Project Stage* workflow governs that same field, so this
bypasses its transition rules. It works, and it keeps qualification a one-click
action, but if the workflow's role gating on that transition matters, convert
`handle_qualification()` to call `apply_workflow` instead.
