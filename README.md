# AgriSmart

Farm pond liner sales, installation and commission management for ERPNext.

Built from the `AgriSmart-Pond-Liner-ERP-2.html` prototype. See
[DESIGN.md](DESIGN.md) for the architecture and the open question about the
agency vs. resale business model.

## Requirements

Frappe v15+ and ERPNext v15+. Tested shape targets v16.

## Install

```bash
cd ~/frappe-bench
bench get-app agrismart /path/to/agrismart
bench --site your-site.local install-app agrismart
bench --site your-site.local migrate
bench build --app agrismart
bench --site your-site.local clear-cache
```

`after_install` creates four roles (**AgriSmart Manager**, **Executive**,
**Logistics**, **Installation**) and seeds the qualification checklist,
installation steps, feedback criteria, complaint natures, soil types, water
sources, lead sources and six placeholder Knowledge Assets.

## First-run setup

1. **AgriSmart Settings** — company, fiscal-year code (`26-27`), rates, GSM,
   anchor width, waste %, commission rate, GST/TDS %, banks, quotation T&C.
2. **Geography** — `Pond District` → `Pond Taluka` → `Pond Village`.
3. **Godowns**, **Installation Teams**, plus ERPNext's own **Vehicle** and
   **Driver** records.
4. **Knowledge Assets** — attach the real brochure, video and deck files to the
   seeded placeholder rows.
5. Import `agrismart/fixtures/workflow.json` or build *Pond Project Stage* in
   the UI.

## Pond Project

One record per farmer, thirteen tabs following the real sequence of work:

| Tab | Holds |
| --- | --- |
| Lead | Farmer, contact, location, pipeline, stage timestamps |
| Lead Qualification | Fixed checklist, expected size, target month, decision |
| Survey | Survey date, surveyor, soil, water source, site notes, photos |
| Pond Calculator and Report | Measurements, live diagram, full report |
| Quotation | Quotation number, validity, notes |
| Sales Order | Order booking, advance, documents collected |
| Purchase Order | Liner supplier and installation contractor POs and payments |
| Delivery Programme | Trip, vehicle, driver, LR, challans |
| Installation | Job, team, dates, step checklist |
| Feedback | Score and band |
| Complaints | Count plus a before/after photo table |
| Commission Calculation | Rate, GST, TDS, net receivable |
| Knowledge Bank | Library of material and a per-farmer share log |

### The calculator

Type a dimension and the area, capacity, amounts, plan view, cross-section and
report all update immediately — nothing waits for a save.

`agrismart/utils/pond.py` is the authority; `agrismart/public/js/pond_calc.js`
is a browser mirror that must agree with it exactly. Both were verified against
2,001 randomised geometries and against every figure in
`Pond_Calculation_Report.docx`. **If you change one, change both**, or users
will see numbers shift the instant they hit Save.

Two things that look like details but are not:

- **Rounding.** JS `Math.round` rounds .5 up; Python's `round` uses banker's
  rounding. `_round_half_up()` keeps them identical — on a 4,000 sq.m pond the
  difference is real money.
- **Explicit zeros.** An anchor width of 0 is a survey finding, not "unset", so
  only `None`/`""` falls back to the default, and defaults seed on creation only.

Geometry: each wall is a trapezium `(top + bottom) / 2 × height`; base is
`mean bottom length × mean bottom width`; anchor trench is
`top perimeter × anchor width`. Sum, add waste %, round to the nearest 10.

## Field naming

Calculator fields follow the prototype: `anchor_width`, `waste_pct`,
`water_depth`, `mean_length`, `mean_breadth`, `height_used`, `capacity_cum`,
`capacity_litres`, `capacity_lakh_litres`; `Pond Wall` is `top` / `height` /
`bottom` / `area`.

`area_sqm` is kept deliberately — Dispatch Trip Stop, Installation Job Site,
Commission Claim Item and the register report all `fetch_from` it, so renaming
it to `liner_area` would cascade for no functional gain. It is labelled
"Liner Required (sq.m)".

## Lead source and ERPNext v16

ERPNext v16 removed the CRM `Lead Source` doctype (`Lead.source` became
`Lead.utm_source` → `UTM Source`). Linking to either breaks the other version,
so the app owns **Pond Lead Source** and seeds thirteen values.

## Layout

```
agrismart/
├── agrismart/
│   ├── agrismart/doctype/       34 doctypes
│   ├── agrismart/report/        Pond Project Register
│   ├── agrismart/print_format/  Pond Calculation Report
│   ├── agrismart/workspace/     AgriSmart workspace
│   ├── utils/
│   │   ├── pond.py              geometry, pricing, commission, formatting
│   │   ├── numbering.py         ASF/<kind>/<fy>/<0000>
│   │   ├── marathi.py           roman → devanagari
│   │   ├── permissions.py       apps-screen role gate
│   │   ├── diagnose.py          apps-screen self-diagnostic
│   │   └── settings.py
│   ├── public/js/pond_calc.js   browser mirror of pond.py
│   ├── patches/                 field renames, dashboard widgets
│   ├── events/, tasks/, fixtures/
│   ├── install.py, hooks.py
├── DESIGN.md
└── README.md
```

## Upgrading an existing site

`patches/rename_calculator_fields.py` runs under `[pre_model_sync]` so renamed
columns keep their data — migrate would otherwise drop them. Back up first:

```bash
bench --site your-site.local backup
bench --site your-site.local migrate
```

Fresh installs need nothing; the patch is a no-op.

## Troubleshooting

No app tile on `/apps`:

```bash
bench --site your-site.local execute agrismart.utils.diagnose.apps_screen
```

It walks each gate `frappe/apps.py::get_apps()` applies and names the first
failure.

## Still to build

- Print formats: quotation, order estimate, trip sheet, job sheet, bank slip,
  completion certificate, feedback form, commission statement. The prototype's
  `Print` object has all eight in HTML; they port to Jinja fairly directly.
- Web Form at `/pond-feedback` (`submit_public_feedback` is ready for it).
- WhatsApp order confirmations and feedback links.
- Marathi transliteration button on the farmer name field.
