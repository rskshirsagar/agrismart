# Copyright (c) 2026, AgriSmart Farm Solutions LLP and contributors

import frappe
from frappe.model.document import Document
from frappe.utils import today

from agrismart.utils.numbering import next_no


class PondComplaint(Document):
	def autoname(self):
		self.name = next_no("cmp")

	def validate(self):
		if self.status == "Closed" and not self.closed_on:
			self.closed_on = today()
		if self.status != "Closed":
			self.closed_on = None

	def on_update(self):
		if self.pond_project:
			count = frappe.db.count("Pond Complaint", {
				"pond_project": self.pond_project,
				"status": ["in", ("Open", "In Progress")],
			})
			frappe.db.set_value("Pond Project", self.pond_project,
			                    "open_complaints", count)
