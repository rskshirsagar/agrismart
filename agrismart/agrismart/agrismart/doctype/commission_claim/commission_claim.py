# Copyright (c) 2026, AgriSmart Farm Solutions LLP and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_first_day, get_last_day, today

from agrismart.utils.numbering import next_no
from agrismart.utils.pond import commission_row
from agrismart.utils.settings import get_settings


class CommissionClaim(Document):
	def autoname(self):
		self.name = next_no("cs")

	def validate(self):
		if self.claim_month and not self.from_date:
			self.from_date = get_first_day(self.claim_month + "-01")
			self.to_date = get_last_day(self.claim_month + "-01")

		s = get_settings()
		totals = dict.fromkeys(
			("qty_sqm", "commission", "gst_amount", "gross", "tds",
			 "freight", "expenses", "net_receivable", "billing_amount"), 0.0
		)

		for row in self.items:
			r = commission_row(
				row.qty_sqm,
				bill_rate=row.bill_rate or s.bill_rate,
				actual_rate=row.actual_rate or s.actual_rate,
				supply_rate=row.supply_rate or s.supply_rate,
				comm_rate=row.commission_rate or s.commission_rate,
				gst_pct=s.gst_pct,
				tds_pct=s.tds_pct,
				freight=row.freight,
				expenses=row.expenses,
			)
			for k, v in r.items():
				if hasattr(row, k):
					row.set(k, v)
			for k in totals:
				totals[k] += flt(row.get(k))

		self.total_qty = totals["qty_sqm"]
		self.total_commission = totals["commission"]
		self.total_gst = totals["gst_amount"]
		self.total_gross = totals["gross"]
		self.total_tds = totals["tds"]
		self.total_deductions = totals["freight"] + totals["expenses"]
		self.net_receivable = totals["net_receivable"]

	def on_submit(self):
		for row in self.items:
			p = frappe.get_doc("Pond Project", row.pond_project)
			p.commission_claim = self.name
			p.advance_to("Commission Claimed", save=False)
			p.save(ignore_permissions=True)

	def on_cancel(self):
		for row in self.items:
			frappe.db.set_value("Pond Project", row.pond_project,
			                    "commission_claim", None)

	@frappe.whitelist()
	def fetch_eligible(self):
		"""Pull completed, unclaimed projects for the selected month."""
		s = get_settings()
		filters = {"stage": "Completed", "commission_claim": ["in", (None, "")]}
		if self.from_date and self.to_date:
			filters["installation_end"] = ["between", (self.from_date, self.to_date)]

		rows = frappe.get_all(
			"Pond Project", filters=filters,
			fields=["name", "area_sqm", "installation_end", "lr_no"],
		)
		self.set("items", [])
		for r in rows:
			self.append("items", {
				"pond_project": r.name,
				"qty_sqm": r.area_sqm,
				"completed_on": r.installation_end,
				"voucher_no": r.lr_no,
				"bill_rate": s.bill_rate,
				"actual_rate": s.actual_rate,
				"supply_rate": s.supply_rate,
				"commission_rate": s.commission_rate,
			})
		return len(rows)

	@frappe.whitelist()
	def make_sales_invoice(self):
		"""Raise the commission invoice on the principal."""
		s = get_settings()
		if not (s.commission_item and self.principal_customer):
			frappe.throw(_("Set a Commission Item in Settings and a Principal Customer."))

		si = frappe.new_doc("Sales Invoice")
		si.customer = self.principal_customer
		si.posting_date = self.to_date or today()
		si.append("items", {
			"item_code": s.commission_item,
			"qty": flt(self.total_qty),
			"rate": flt(self.total_commission) / flt(self.total_qty or 1),
			"description": _("Commission for {0}").format(self.claim_month or ""),
		})
		si.custom_commission_claim = self.name
		si.insert()
		self.db_set("sales_invoice", si.name)
		return si.name
