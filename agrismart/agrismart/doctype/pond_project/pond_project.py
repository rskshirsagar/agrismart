# Copyright (c) 2026, AgriSmart Farm Solutions LLP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

from agrismart.utils.numbering import next_no
from agrismart.utils.pond import commission_row, compute_pond, in_words, money
from agrismart.utils.settings import get_settings

STAGES = [
	"Lead", "Qualified", "Surveyed", "Quoted", "Order Booked", "Dispatched",
	"Delivered", "Installing", "Completed", "Commission Claimed", "Closed",
]

STAGE_STAMP = {
	"Qualified": "ts_qualified",
	"Surveyed": "ts_survey",
	"Quoted": "ts_quotation",
	"Order Booked": "ts_order",
	"Dispatched": "ts_dispatch",
	"Delivered": "ts_delivered",
	"Installing": "ts_install",
	"Completed": "ts_completed",
}


def stage_idx(stage):
	try:
		return STAGES.index(stage or "Lead")
	except ValueError:
		return -1


class PondProject(Document):
	def autoname(self):
		self.name = next_no("lead")

	def validate(self):
		self.set_names()
		self.sync_whatsapp()
		self.compose_address()
		self.apply_defaults()
		self.calculate()
		self.roll_up_children()
		self.handle_qualification()
		self.stamp_stage()

	# ------------------------------------------------------------------ #
	def set_names(self):
		self.farmer_name = " ".join(
			p for p in (self.first_name, self.middle_name, self.last_name) if p
		)
		if self.gps_lat and self.gps_long:
			self.map_link = f"https://maps.google.com/?q={self.gps_lat},{self.gps_long}"
		if self.village and not self.taluka:
			self.taluka = frappe.db.get_value("Pond Village", self.village, "taluka")
		if self.taluka and not self.district:
			self.district = frappe.db.get_value("Pond Taluka", self.taluka, "district")

	def sync_whatsapp(self):
		"""The tick means 'keep these equal', not 'copy once'."""
		if self.whatsapp_same_as_mobile:
			self.whatsapp = self.mobile

	def compose_address(self):
		"""Village, Tal. X, Dist. Y, State - PIN — mirrors the prototype's place()."""
		if not self.address_auto:
			return
		village = frappe.db.get_value("Pond Village", self.village, "village_name") \
			if self.village else None
		parts = [
			village or self.village,
			f"Tal. {self.taluka}" if self.taluka else None,
			f"Dist. {self.district}" if self.district else None,
			self.state,
		]
		line = ", ".join(p for p in parts if p)
		if self.pin_code:
			line = f"{line} - {self.pin_code}" if line else str(self.pin_code)
		self.address = line

	def apply_defaults(self):
		if not self.is_new():
			return
		s = get_settings()
		for field, default in (
			("anchor_width", s.anchor_width),
			("waste_pct", s.extra_pct),
			("round_to", s.round_to),
			("rate_farmer", s.rate_farmer),
			("rate_texel", s.rate_texel),
			("rate_risha", s.rate_risha),
		):
			if not flt(self.get(field)):
				self.set(field, default)

	# ------------------------------------------------------------------ #
	def calculate(self):
		s = get_settings()
		walls = {
			row.wall.lower(): {
				"top": flt(row.top),
				"ht": flt(row.height),
				"bot": flt(row.bottom),
			}
			for row in (self.walls or [])
			if row.wall
		}
		r = compute_pond(
			walls,
			anchor_w=self.anchor_width,
			extra_pct=self.waste_pct,
			depth_override=self.water_depth,
			round_to=self.round_to,
		)

		for row in self.walls or []:
			row.area = flt(r["wall_areas"].get((row.wall or "").lower()), 3)

		self.wall_area_total = r["walls"]
		self.base_area = r["base"]
		self.perimeter = r["perim"]
		self.anchor_area = r["anchor"]
		self.sub_total_area = r["sub"]
		self.waste_area = r["waste_area"]
		self.area_sqm = r["area"]
		self.liner_weight_kg = flt(self.area_sqm) * flt(s.gsm) / 1000.0

		self.mean_length = r["L"]
		self.mean_breadth = r["B"]
		self.height_used = r["H"]
		self.capacity_cum = r["vol"]
		self.capacity_litres = r["litres"]
		self.capacity_lakh_litres = r["lakh_litres"]

		m = money(
			self.area_sqm,
			rate_farmer=self.rate_farmer,
			rate_texel=self.rate_texel,
			rate_risha=self.rate_risha,
		)
		self.amount_total = m["total"]
		self.amount_texel = m["texel"]
		self.amount_risha = m["risha"]
		self.amount_margin = m["margin"]
		self.amount_in_words = in_words(m["total"])

		# purchase-order and order-value figures follow the same areas
		self.po_texel_amount = m["texel"]
		self.po_risha_amount = m["risha"]
		self.order_value = m["total"]
		self.balance_due = flt(self.order_value) - flt(self.advance_received)

		c = commission_row(self.area_sqm)
		self.commission_rate = c["commission_rate"]
		self.commission_amount = c["commission"]
		self.commission_gst = c["gst_amount"]
		self.commission_tds = c["tds"]
		self.commission_net = c["net_receivable"]

	# ------------------------------------------------------------------ #
	def roll_up_children(self):
		q = self.qualification_items or []
		self.qualification_score = (
			100.0 * len([x for x in q if x.checked]) / len(q) if q else 0
		)

		steps = self.installation_steps or []
		self.installation_progress = (
			100.0 * len([x for x in steps if x.done]) / len(steps) if steps else 0
		)

		self.documents_pending = len(
			[d for d in (self.documents or []) if not d.received]
		)

		if not self.is_new():
			self.open_complaints = frappe.db.count("Pond Complaint", {
				"pond_project": self.name,
				"status": ["in", ("Open", "In Progress")],
			})
			self.total_complaints = frappe.db.count(
				"Pond Complaint", {"pond_project": self.name}
			)

	def handle_qualification(self):
		"""Qualifying is what unlocks the survey; failing it ends the project."""
		if self.qualification_status in ("Qualified", "Not Qualified") \
				and not self.qualified_on:
			self.qualified_on = today()
		if self.qualification_status == "Pending":
			self.qualified_on = None

		if self.qualification_status == "Qualified" \
				and stage_idx(self.stage) < stage_idx("Qualified"):
			self.stage = "Qualified"
		elif self.qualification_status == "Not Qualified" and self.stage != "Lost":
			self.stage = "Lost"
			if not self.lost_reason:
				self.lost_reason = self.not_qualified_reason or _("Did not qualify")

	def stamp_stage(self):
		field = STAGE_STAMP.get(self.stage)
		if field and not self.get(field):
			self.set(field, today())

	# ------------------------------------------------------------------ #
	def advance_to(self, stage, save=True):
		"""Move forward only — never drag a project backwards."""
		if self.stage == "Lost":
			return
		if stage_idx(stage) > stage_idx(self.stage):
			self.stage = stage
			self.stamp_stage()
			if save:
				self.save(ignore_permissions=True)

	@frappe.whitelist()
	def load_qualification_checklist(self):
		"""Fill the checklist from the master, keeping ticks already recorded."""
		existing = {r.qualification_item: r for r in (self.qualification_items or [])}
		items = frappe.get_all(
			"Qualification Item", filters={"is_active": 1},
			fields=["name"], order_by="sequence asc, name asc",
		)
		self.set("qualification_items", [])
		for item in items:
			prev = existing.get(item.name)
			self.append("qualification_items", {
				"qualification_item": item.name,
				"checked": prev.checked if prev else 0,
				"notes": prev.notes if prev else None,
			})
		return len(items)


# ══════════════════════════════════════════════════════════════════════
@frappe.whitelist()
def preview_calculation(walls, anchor_width=None, waste_pct=None,
                        water_depth=None, round_to=None,
                        rate_farmer=None, rate_texel=None, rate_risha=None):
	"""Server-side truth for the on-form calculator.

	The browser mirror draws instantly; this is what the form trusts, so the
	two can never disagree about what actually gets saved.
	"""
	if isinstance(walls, str):
		walls = frappe.parse_json(walls)
	data = {
		(w.get("wall") or "").lower(): {
			"top": flt(w.get("top")),
			"ht": flt(w.get("height")),
			"bot": flt(w.get("bottom")),
		}
		for w in (walls or [])
		if w.get("wall")
	}
	r = compute_pond(data, anchor_width, waste_pct, water_depth, round_to)
	r["money"] = money(
		r["area"], rate_farmer=rate_farmer, rate_texel=rate_texel,
		rate_risha=rate_risha,
	)
	r["money"]["in_words"] = in_words(r["money"]["total"])
	r["weight_kg"] = flt(r["area"]) * flt(get_settings().gsm) / 1000.0
	return r


@frappe.whitelist()
def get_knowledge_library():
	"""Active assets for the Knowledge Bank tab."""
	return frappe.get_all(
		"Knowledge Asset",
		filters={"is_active": 1},
		fields=["name", "title", "title_mr", "asset_type", "language",
		        "file", "external_url", "thumbnail", "tags"],
		order_by="asset_type asc, title asc",
	)


@frappe.whitelist()
def get_complaints(pond_project):
	return frappe.get_all(
		"Pond Complaint",
		filters={"pond_project": pond_project},
		fields=["name", "complaint_date", "nature", "status", "closed_on",
		        "photo_before", "photo_after"],
		order_by="complaint_date desc",
	)


@frappe.whitelist()
def make_quotation(source_name):
	"""Optional: raise a native ERPNext Quotation from a Pond Project."""
	doc = frappe.get_doc("Pond Project", source_name)
	s = get_settings()
	if not s.default_item:
		frappe.throw(_("Set a Default Liner Item in AgriSmart Settings first."))

	q = frappe.new_doc("Quotation")
	q.quotation_to = "Lead" if doc.lead else "Customer"
	q.party_name = doc.lead or doc.customer
	q.transaction_date = doc.quotation_date or today()
	q.append("items", {
		"item_code": s.default_item,
		"qty": flt(doc.area_sqm),
		"rate": flt(doc.rate_farmer),
		"description": s.product_description,
	})
	return q
