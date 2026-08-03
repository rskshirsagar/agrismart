# AgriSmart Pond Liner ERP — design and mapping

How `AgriSmart-Pond-Liner-ERP-2.html` becomes a Frappe/ERPNext app.

---

## 1. The one decision that shapes everything

Reading the prototype's own numbers: the farmer is quoted ₹105/sq.m, of which
₹89 goes to Texel (liner) and ₹16 to Risha (installation) — leaving AgriSmart a
margin of exactly **zero**. The real revenue sits in the commission block:
₹5.5/sq.m from the principal, plus GST, less 2% TDS, less freight and expenses.

That reads as an **agency / channel-partner model**: AgriSmart never owns the
material, never invoices the farmer for it, and never holds stock. If that's
right, three consequences follow, and the app below is built on them:

- **No Stock module involvement.** No Item stock ledger, no Delivery Note, no
  Perpetual Inventory. Godowns are a plain master, not a Warehouse.
- **No Sales Order / Sales Invoice to the farmer.** The farmer-facing document
  is a quotation/estimate that AgriSmart prints; the tax invoices come from
  Texel and Risha directly.
- **The only ERPNext accounting document that matters is the commission Sales
  Invoice raised on the principal**, from a Commission Claim.

If instead AgriSmart *does* buy from Texel and sell to the farmer on its own
GSTIN, the architecture changes materially — Purchase Order → Purchase Receipt
→ Delivery Note → Sales Invoice, with real stock in a Texel warehouse. Worth
confirming before you build past the scaffold.

---

## 2. Architecture

The prototype keeps **one record per farmer** that accumulates survey, quote,
order, dispatch, installation, feedback and commission data as it moves through
eleven stages. That single-record shape is genuinely good for field work — a
sales executive on a phone in a village wants one screen, not seven linked
documents — so the app preserves it.

**`Pond Project` is the spine.** Everything else either hangs off it as a child
table or links back to it.

```
Pond Project  (ASF/LD/26-27/0001)  ── stage: Lead → … → Closed
├── Pond Wall                (4 rows: N/S/E/W top, height, bottom)
├── Pond Qualification Item  (checklist)
├── Pond Document            (Aadhaar, PAN, 7/12, receipts, signed estimate)
├── Pond Challan             (LR / delivery challans)
├── Pond Installation Step   (site checklist)
└── Pond Photo               (stage-tagged gallery)

Dispatch Trip      (1 vehicle → many projects)   ─┐
Installation Job   (1 team    → many projects)   ─┼─→ push stage back to project
Commission Claim   (1 month   → many projects)   ─┘

Pond Complaint     (many per project)
Customer Feedback  (one per project, public web form capable)
```

The three "many projects" documents are **submittable**. Submitting a Dispatch
Trip is what moves every farmer on it to *Dispatched*; submitting an
Installation Job with end dates moves them to *Completed*. That replaces the
prototype's manual per-record stage clicking with a single action that can't
leave half the truck in the wrong state.

---

## 3. Module-by-module mapping

| Prototype screen | ERPNext implementation |
| --- | --- |
| Dashboard | Workspace with number cards + charts on `Pond Project` |
| Leads & projects | `Pond Project` list + form, Kanban view on `stage` |
| Pond calculator | `Pond Wall` child table + `utils/pond.py`, live preview via `public/js/pond_calc.js` |
| Quotations | Print Format on `Pond Project`; optional native `Quotation` via `make_quotation()` |
| Order booking | Order section + `Pond Document` table with a pending-docs counter |
| Dispatch & delivery | `Dispatch Trip` (submittable) + `Pond Challan` |
| Installation | `Installation Job` (submittable) + `Pond Installation Step` |
| Commission | `Commission Claim` (submittable) → `Sales Invoice` on the principal |
| Complaints | `Pond Complaint` with Open/In Progress/Resolved/Closed |
| Service quality | `Customer Feedback` + Feedback Criterion master; group-by reports |
| Reports | `Pond Project Register` script report + standard ERPNext reporting |
| Masters | `Pond District/Taluka/Village`, `Godown`, `Installation Team`, `Soil Type`, `Water Source`, `Complaint Nature`, `Qualification Item`, `Installation Step`, `Feedback Criterion` |
| Settings | `AgriSmart Settings` (Single) |

### Deliberately reused from ERPNext rather than rebuilt

`Lead` (CRM pipeline), `Customer`, `Sales Person` (sales executives),
`Vehicle` and `Driver` (from the Vehicle/Fleet module), `Lead Source`, `Item`,
`Sales Invoice`, `Company`. Rebuilding these would cost you every stock,
reporting and permission feature that already works.

### Deliberately *not* reused

- **Warehouse** for godowns — pulls in stock accounting AgriSmart doesn't want.
- **Territory** for the village hierarchy — Territory is a nested set; rebuilding
  it every time you add one of thousands of Maharashtra villages is slow, and
  you'd fight it for reporting anyway. Three flat linked doctypes are simpler.
- **Delivery Note** — see §1.

---

## 4. The calculation engine

`utils/pond.py` is a line-for-line port of the prototype's `computePond`,
`money` and `commissionRow`. It is tested for exact parity against a faithful
transcription of the original JavaScript across 3,000 randomised wall
geometries — including the awkward edges:

- **Rounding.** JS `Math.round` rounds .5 *up*; Python's built-in `round` uses
  banker's rounding and would send 3477.5 → 3475 where the prototype gives 3480.
  `_round_half_up()` fixes this. On a 4,000 sq.m pond that's a real ₹525.
- **Explicit zeros.** An anchor width of 0 or an extra allowance of 0 is a
  legitimate choice, not "unset". `_or_default()` only falls back on `None`/`""`,
  and `Pond Project.apply_defaults()` seeds settings values on creation only —
  so a survey deliberately recorded with no anchor trench stays that way.

The browser mirror in `public/js/pond_calc.js` exists for instant on-form
feedback. **Keep the two in step** — if you change one, change both, and re-run
the parity test.

Geometry, for the record: each of the four walls is a trapezium
`(top + bottom) / 2 × slope height`; the base is `mean bottom length × mean
bottom width`; the anchor trench is `top perimeter × anchor width`. Sum, add the
extra %, round to the nearest 10.

---

## 5. Things the prototype does that need rethinking on a server

**Photos.** The prototype base64-encodes images into localStorage. On Frappe use
`Attach Image` fields and the File doctype — the child tables are already shaped
for it. Compress client-side before upload; the originals off a phone camera
will be 4–8 MB each and a project can carry thirty of them.

**Marathi transliteration.** `utils/marathi.py` ports the rule set, but no rule
set gets Marathi surnames right every time. Keep `farmer_name_mr` editable and
treat the transliteration as a suggestion button, not an auto-fill.

**Feedback collection.** The prototype's Google Form + CSV-matching bridge was a
workaround for having no server. You have one now: expose a Web Form at
`/pond-feedback`, send the farmer a WhatsApp link, and `submit_public_feedback()`
matches on mobile number. Drop the CSV path entirely.

**Numbering.** `ASF/LD/26-27/0001` is reproduced by `utils/numbering.py` using
`make_autoname`. The fiscal-year segment comes from `AgriSmart Settings.fy_short`
— remember to roll it over each April, or add a hook that derives it from the
active Fiscal Year.

**Offline.** Village sites often have no signal. Nothing in this scaffold solves
that; if it matters, the honest options are a PWA against the REST API or
keeping the existing HTML as a field client that syncs. Worth deciding early —
it's hard to retrofit.

---

## 6. Suggested build order

1. `bench install-app`, then fill `AgriSmart Settings` and the geography masters.
2. Import existing farmers into `Pond Project` (the prototype exports CSV —
   `Rep.csv()` — so migration is a mapping exercise, not a re-keying one).
3. Print formats: Quotation, Order Estimate, Trip Sheet, Job Sheet, Bank Slip,
   Completion Certificate, Feedback Form, Commission Statement. These are the
   most visible part to the business and the most fiddly — the bilingual
   quotation with Marathi T&C is worth doing first and properly.
4. Workspace and dashboard charts.
5. WhatsApp integration for order confirmations and feedback links.
