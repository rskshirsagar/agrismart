# Copyright (c) 2026, AgriSmart Farm Solutions LLP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

from agrismart.utils.numbering import next_no
from agrismart.utils.pond import compute_pond, money
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
		self.apply_defaults()
		self.calculate()
		self.roll_up_children()
		self.stamp_stage()

	# ------------------------------------------------------------------ #
	def set_names(self):
		self.farmer_name = " ".join(
			[p for p in (self.first_name, self.middle_name, self.last_name) if p]
		)
		if self.gps_lat and self.gps_long:
			self.map_link = "https://maps.google.com/?q={0},{1}".format(
				self.gps_lat, self.gps_long
			)
		if self.village and not self.taluka:
			self.taluka = frappe.db.get_value("Pond Village", self.village, "taluka")
		if self.taluka and not self.district:
			self.district = frappe.db.get_value("Pond Taluka", self.taluka, "district")

	def apply_defaults(self):
		s = get_settings()
		if not self.is_new():
			return
		for field, default in (
			("anchor_width", s.anchor_width),
			("extra_pct", s.extra_pct),
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
				"top": flt(row.top_length),
				"ht": flt(row.height),
				"bot": flt(row.bottom_length),
			}
			for row in (self.walls or [])
			if row.wall
		}
		r = compute_pond(
			walls,
			anchor_w=self.anchor_width,
			extra_pct=self.extra_pct,
			depth_override=self.depth_override,
			round_to=self.round_to,
		)

		for row in self.walls or []:
			row.wall_area = flt(r["wall_areas"].get((row.wall or "").lower()), 3)

		self.wall_area_total = r["walls"]
		self.base_area = r["base"]
		self.perimeter = r["perim"]
		self.anchor_area = r["anchor"]
		self.subtotal_area = r["sub"]
		self.area_with_extra = r["with_extra"]
		self.area_sqm = r["area"]
		self.mean_length = r["L"]
		self.mean_width = r["B"]
		self.mean_depth = r["H"]
		self.volume_cum = r["vol"]
		self.litres = r["litres"]
		self.liner_weight_kg = flt(self.area_sqm) * flt(s.gsm) / 1000.0

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
		self.commission_amount = flt(self.area_sqm) * flt(s.commission_rate)

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
			self.open_complaints = frappe.db.count(
				"Pond Complaint",
				{"pond_project": self.name, "status": ["in", ("Open", "In Progress")]},
			)

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
def preview_calculation(walls, anchor_width=None, extra_pct=None,
                        depth_override=None, round_to=None):
	"""Live preview for the client script — mirrors the browser calculator."""
	if isinstance(walls, str):
		walls = frappe.parse_json(walls)
	data = {
		(w.get("wall") or "").lower(): {
			"top": flt(w.get("top_length")),
			"ht": flt(w.get("height")),
			"bot": flt(w.get("bottom_length")),
		}
		for w in (walls or [])
	}
	return compute_pond(data, anchor_width, extra_pct, depth_override, round_to)


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
	q.custom_pond_project = doc.name
	return q
