import frappe
from frappe.utils import add_days, today


def flag_stalled_projects():
	"""Nudge the owner when a project sits in one stage too long."""
	limits = {"Lead": 7, "Qualified": 7, "Surveyed": 5, "Quoted": 10,
	          "Order Booked": 15, "Dispatched": 5, "Delivered": 7,
	          "Installing": 10}

	for stage, days in limits.items():
		stale = frappe.get_all(
			"Pond Project",
			filters={"stage": stage, "modified": ["<", add_days(today(), -days)]},
			fields=["name", "farmer_name", "owner"],
		)
		for p in stale:
			frappe.get_doc({
				"doctype": "Notification Log",
				"subject": f"{p.farmer_name} has been at '{stage}' for over {days} days",
				"for_user": p.owner,
				"type": "Alert",
				"document_type": "Pond Project",
				"document_name": p.name,
			}).insert(ignore_permissions=True)


def request_feedback():
	"""Three days after completion, ask for feedback if none exists yet."""
	due = frappe.get_all(
		"Pond Project",
		filters={
			"stage": ["in", ("Completed", "Commission Claimed", "Closed")],
			"feedback": ["in", (None, "")],
			"installation_end": ["<=", add_days(today(), -3)],
		},
		fields=["name", "farmer_name", "mobile", "owner"],
	)
	for p in due:
		frappe.get_doc({
			"doctype": "Notification Log",
			"subject": f"Collect feedback from {p.farmer_name} ({p.mobile})",
			"for_user": p.owner,
			"type": "Alert",
			"document_type": "Pond Project",
			"document_name": p.name,
		}).insert(ignore_permissions=True)
