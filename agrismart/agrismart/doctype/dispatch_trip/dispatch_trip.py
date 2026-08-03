# Copyright (c) 2026, AgriSmart Farm Solutions LLP and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from agrismart.utils.numbering import next_no
from agrismart.utils.settings import get_settings


class DispatchTrip(Document):
	def autoname(self):
		self.name = next_no("trip")

	def validate(self):
		s = get_settings()
		if not self.stops:
			frappe.throw(_("Add at least one stop."))

		total_area = total_weight = 0.0
		count = len(self.stops)
		for idx, row in enumerate(self.stops):
			row.weight_kg = flt(row.area_sqm) * flt(s.gsm) / 1000.0
			# loaded first comes off the truck last
			row.unload_sequence = count - idx
			total_area += flt(row.area_sqm)
			total_weight += flt(row.weight_kg)

		self.total_area = total_area
		self.total_weight = total_weight
		self.stop_count = count

		if self.driver and not self.driver_mobile:
			self.driver_mobile = frappe.db.get_value("Driver", self.driver, "cell_number")
		if self.godown and not self.godown_incharge:
			inch, mob = frappe.db.get_value(
				"Godown", self.godown, ["incharge", "mobile"]
			) or (None, None)
			self.godown_incharge = inch
			self.godown_incharge_mobile = mob

	def on_submit(self):
		self.push_to_projects("Dispatched")

	def on_cancel(self):
		for row in self.stops:
			frappe.db.set_value("Pond Project", row.pond_project, "dispatch_trip", None)

	def push_to_projects(self, stage):
		for row in self.stops:
			p = frappe.get_doc("Pond Project", row.pond_project)
			p.dispatch_trip = self.name
			p.godown = self.godown
			p.vehicle = self.vehicle
			p.driver = self.driver
			p.dispatch_date = self.trip_date
			p.lr_no = self.lr_no
			p.advance_to(stage, save=False)
			p.save(ignore_permissions=True)


@frappe.whitelist()
def mark_delivered(trip, pond_project, delivered_on=None):
	from frappe.utils import today

	delivered_on = delivered_on or today()
	doc = frappe.get_doc("Dispatch Trip", trip)
	for row in doc.stops:
		if row.pond_project == pond_project:
			row.db_set("delivered_on", delivered_on)

	p = frappe.get_doc("Pond Project", pond_project)
	p.delivered_on = delivered_on
	p.advance_to("Delivered", save=False)
	p.save(ignore_permissions=True)
	return True
