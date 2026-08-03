# Copyright (c) 2026, AgriSmart Farm Solutions LLP and contributors

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt

BANDS = [
	(4.5, "Excellent"),
	(3.5, "Good"),
	(2.5, "Average"),
	(1.5, "Poor"),
	(0.0, "Very Poor"),
]


def band(score):
	for floor, label in BANDS:
		if flt(score) >= floor:
			return label
	return "Very Poor"


class CustomerFeedback(Document):
	def validate(self):
		vals = [cint(r.rating) for r in (self.ratings or []) if cint(r.rating)]
		self.average_score = (sum(vals) / len(vals)) if vals else 0
		self.band = band(self.average_score)

	def on_update(self):
		if self.pond_project:
			frappe.db.set_value("Pond Project", self.pond_project, {
				"feedback": self.name,
				"feedback_score": self.average_score,
			})


@frappe.whitelist(allow_guest=True)
def submit_public_feedback(mobile, payload):
	"""Entry point for the public web form / QR link."""
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)

	project = frappe.db.get_value(
		"Pond Project", {"mobile": mobile}, "name", order_by="modified desc"
	)
	if not project:
		frappe.throw("No project found for this mobile number.")

	doc = frappe.new_doc("Customer Feedback")
	doc.pond_project = project
	doc.update(payload)
	doc.insert(ignore_permissions=True)
	return doc.name
