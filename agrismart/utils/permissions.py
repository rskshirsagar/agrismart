import frappe

APP_ROLES = {
	"AgriSmart Manager",
	"AgriSmart Executive",
	"AgriSmart Logistics",
	"AgriSmart Installation",
	"System Manager",
	"Administrator",
}


def has_app_permission():
	"""Who sees the AgriSmart tile on the /apps screen."""
	if frappe.session.user == "Administrator":
		return True
	return bool(APP_ROLES & set(frappe.get_roles()))
