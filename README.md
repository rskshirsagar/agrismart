# AgriSmart

Farm pond liner sales, installation and commission management for ERPNext.

Ported from the `AgriSmart-Pond-Liner-ERP-2.html` prototype. See
[DESIGN.md](DESIGN.md) for the mapping rationale and the open architectural
question about the agency vs. resale business model.

## Requirements

Frappe v15+ and ERPNext v15+ (tested shape targets v16).

## Install

```bash
cd ~/frappe-bench
bench get-app agrismart /path/to/agrismart
bench --site your-site.local install-app agrismart
bench --site your-site.local migrate
bench build --app agrismart
```

`after_install` seeds the qualification checklist, installation steps, feedback
criteria, complaint natures, soil types and water sources, and creates four
roles: **AgriSmart Manager**, **AgriSmart Executive**, **AgriSmart Logistics**,
**AgriSmart Installation**.

## First-run setup

1. **AgriSmart Settings** — company, fiscal-year short code (`26-27`), rates,
   GSM, anchor width, extra %, commission rate, GST/TDS %, principal bank rows
   and the quotation T&C table.
2. **Geography** — create `Pond District` → `Pond Taluka` → `Pond Village`. The
   prototype ships Ahilyanagar/Nashik/Pune and their talukas; import them as a
   CSV rather than typing.
3. **Godowns**, **Installation Teams**, **Vehicles** and **Drivers** (the last
   two are ERPNext's own Fleet doctypes).
4. Import the Workflow fixture (`agrismart/fixtures/workflow.json`) or build
   *Pond Project Stage* through the UI.

## Daily flow

| Step | Where |
| --- | --- |
| Capture enquiry | New **Pond Project**, stage *Lead* |
| Qualify | Tick the checklist, workflow action *Qualify* |
| Survey | Fill the four **Pond Wall** rows; area and volume compute on save |
| Quote | *Send Quotation*, print the bilingual format |
| Book order | Record payments/UTRs, tick off **Documents** |
| Dispatch | New **Dispatch Trip**, add stops in loading order, submit |
| Deliver | `mark_delivered()` per stop, or set Delivered On |
| Install | New **Installation Job**, add sites, submit |
| Complete | Set end dates on the job's sites |
| Claim | New **Commission Claim** → *Fetch Completed Projects* → submit → Sales Invoice |

Stops on a Dispatch Trip are numbered in **loading order** — the controller
reverses that into `unload_sequence`, because the roll loaded first comes off
the truck last.

## Layout

```
agrismart/
├── agrismart/
│   ├── agrismart/doctype/     31 doctypes
│   ├── agrismart/report/      Pond Project Register
│   ├── utils/
│   │   ├── pond.py            geometry, pricing, commission  ← the important one
│   │   ├── numbering.py       ASF/<kind>/<fy>/<0000>
│   │   ├── marathi.py         roman → devanagari
│   │   └── settings.py
│   ├── events/lead.py         CRM Lead → Pond Project sync
│   ├── tasks/daily.py         stalled-stage nudges, feedback reminders
│   ├── public/js/pond_calc.js browser mirror of pond.py
│   ├── fixtures/workflow.json 12 states, 14 transitions
│   ├── install.py             seed data + roles
│   └── hooks.py
├── DESIGN.md
└── README.md
```

## Still to build

The scaffold covers data model, calculation, workflow and automation. Not yet
written:

- **Print formats** — quotation, order estimate, trip sheet, job sheet, bank
  slip, completion certificate, feedback form, commission statement. The
  prototype's `Print` object has all eight laid out in HTML; they port to Jinja
  fairly directly.
- **Workspace / dashboard** — number cards and charts.
- **Web Form** at `/pond-feedback` (the `submit_public_feedback` endpoint is
  ready for it).
- **WhatsApp** order confirmations and feedback links.
- **Pond diagram SVG** — currently a table; the prototype's `pondSVG()` is worth
  porting for the quotation print.

## Tests

`utils/pond.py` was verified for exact parity against a transcription of the
prototype's JavaScript across 3,000 randomised geometries. If you change the
calculation, re-run that check before shipping — the two implementations
(Python and the browser mirror) must not drift.
