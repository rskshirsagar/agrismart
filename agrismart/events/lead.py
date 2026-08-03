import frappe


def sync_pond_project(doc, method=None):
	"""Keep a Pond Project's contact details in step with its CRM Lead."""
	projects = frappe.get_all("Pond Project", filters={"lead": doc.name},
	                          fields=["name"])
	for p in projects:
		frappe.db.set_value("Pond Project", p.name, {
			"mobile": doc.mobile_no or doc.phone,
			"email": doc.email_id,
		}, update_modified=False)
