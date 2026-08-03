"""ASF/<kind>/<fy>/<0000> numbering, matching the prototype's series."""

import frappe
from frappe.model.naming import make_autoname

PREFIX = {
	"lead": "LD", "qtn": "QTN", "so": "SO", "po": "PO", "dc": "DC",
	"cmp": "CMP", "cs": "CS", "trip": "TRIP", "job": "JOB",
}


def next_no(kind):
	from agrismart.utils.settings import get_settings

	fy = get_settings().fy_short or "00-00"
	return make_autoname("ASF/{0}/{1}/.####".format(PREFIX.get(kind, "X"), fy))
