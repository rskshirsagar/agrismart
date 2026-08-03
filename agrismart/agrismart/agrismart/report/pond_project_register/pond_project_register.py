import frappe
from frappe import _

COLUMNS = [
	("name", _("Project"), "Link", "Pond Project", 130),
	("farmer_name", _("Farmer"), "Data", None, 170),
	("village", _("Village"), "Link", "Pond Village", 110),
	("taluka", _("Taluka"), "Link", "Pond Taluka", 110),
	("mobile", _("Mobile"), "Data", None, 110),
	("stage", _("Stage"), "Data", None, 120),
	("area_sqm", _("Area (sq.m)"), "Float", None, 100),
	("amount_texel", _("Liner Amount"), "Currency", None, 120),
	("amount_risha", _("Installation"), "Currency", None, 110),
	("amount_total", _("Farmer Total"), "Currency", None, 120),
	("commission_amount", _("Commission"), "Currency", None, 110),
	("delivered_on", _("Delivered"), "Date", None, 100),
	("installation_end", _("Completed"), "Date", None, 100),
	("volume_cum", _("Water (cu.m)"), "Float", None, 110),
]


def execute(filters=None):
	filters = filters or {}
	conditions = {}
	for key in ("stage", "taluka", "district", "sales_person"):
		if filters.get(key):
			conditions[key] = filters[key]
	if filters.get("from_date") and filters.get("to_date"):
		conditions["enquiry_date"] = ["between",
		                              (filters["from_date"], filters["to_date"])]

	columns = [{
		"fieldname": fn, "label": lbl, "fieldtype": ft,
		"options": opt, "width": wd,
	} for fn, lbl, ft, opt, wd in COLUMNS]

	data = frappe.get_all(
		"Pond Project", filters=conditions,
		fields=[c[0] for c in COLUMNS], order_by="modified desc",
	)
	return columns, data
