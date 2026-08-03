import frappe


def get_settings():
	"""Cached handle on the AgriSmart Settings single."""
	return frappe.get_cached_doc("AgriSmart Settings")
