"""Carry data across the calculator field renames and seed new masters.

The Pond Project / Pond Wall fields were renamed to track the HTML prototype's
vocabulary. rename_field must run BEFORE the new schema syncs, otherwise
migrate drops the old columns and the data with them — hence pre_model_sync.

Idempotent: rename_field is a no-op once the old column is gone.
"""

import frappe
from frappe.model.utils.rename_field import rename_field

# (doctype, old, new)
RENAMES = [
	("Pond Project", "extra_pct", "waste_pct"),
	("Pond Project", "depth_override", "water_depth"),
	("Pond Project", "subtotal_area", "sub_total_area"),
	("Pond Project", "mean_width", "mean_breadth"),
	("Pond Project", "mean_depth", "height_used"),
	("Pond Project", "volume_cum", "capacity_cum"),
	("Pond Project", "litres", "capacity_litres"),
	("Pond Wall", "top_length", "top"),
	("Pond Wall", "bottom_length", "bottom"),
	("Pond Wall", "wall_area", "area"),
]

SOURCES = [
	"Walk-in", "Referral", "Existing Customer", "Exhibition", "Field Visit",
	"WhatsApp", "Phone Enquiry", "Facebook", "Instagram", "Google",
	"Dealer", "Agriculture Officer", "Other",
]


def execute():
	for doctype, old, new in RENAMES:
		if not frappe.db.exists("DocType", doctype):
			continue
		if not frappe.db.has_column(doctype, old):
			continue
		try:
			rename_field(doctype, old, new)
			frappe.logger().info(f"agrismart: renamed {doctype}.{old} -> {new}")
		except Exception:
			frappe.log_error(
				title="agrismart rename_field",
				message=f"{doctype}.{old} -> {new}\n{frappe.get_traceback()}",
			)

	migrate_lead_source()
	frappe.db.commit()


def migrate_lead_source():
	"""Pond Project.source used to link to ERPNext's Lead Source.

	v16 removed that doctype (Lead.source became Lead.utm_source -> UTM Source),
	which is why the field errored with "DocType Lead Source not found". The app
	now owns Pond Lead Source, so seed it and carry over whatever was recorded.
	"""
	if not frappe.db.exists("DocType", "Pond Lead Source"):
		return

	existing = set()
	if frappe.db.has_column("Pond Project", "source"):
		existing = {
			r.source for r in frappe.db.sql(
				"SELECT DISTINCT source FROM `tabPond Project` "
				"WHERE source IS NOT NULL AND source != ''", as_dict=True
			)
		}

	for value in SOURCES + sorted(existing):
		if not frappe.db.exists("Pond Lead Source", value):
			frappe.get_doc({
				"doctype": "Pond Lead Source",
				"source_name": value,
				"is_active": 1,
			}).insert(ignore_permissions=True)
