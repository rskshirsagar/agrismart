import frappe

ROLES = [
	"AgriSmart Manager",
	"AgriSmart Executive",
	"AgriSmart Logistics",
	"AgriSmart Installation",
]

QUALIFICATION_ITEMS = [
	"Land available and ownership clear",
	"Pond already excavated or excavation planned",
	"Water source available to fill the pond",
	"Budget available for liner and installation",
	"Decision maker met in person",
	"Road access for a truck up to the site",
	"Electricity or generator available for welding",
]

INSTALLATION_STEPS = [
	"Surface cleaned, stones and burrows removed",
	"Sheets laid and positioned",
	"Hot-wedge welding of all joints done",
	"Anchor trench filled and locked",
	"Joint air / spark test passed",
	"Finishing and site cleaned",
]

FEEDBACK_CRITERIA = [
	"Sales executive behaviour",
	"Site survey quality",
	"Quotation explanation",
	"Timely material delivery",
	"Installation quality",
	"Installation team conduct",
	"Site cleanliness after work",
	"Overall experience",
]

COMPLAINT_NATURES = [
	"Water seepage", "Joint / weld failure", "Sheet puncture",
	"Anchor trench slip", "Wrinkle / air pocket", "Short supply",
	"Damaged roll", "Delay in installation", "Rat / animal damage", "Other",
]

SOILS = ["Murum", "Black cotton", "Red soil", "Sandy", "Rocky", "Mixed"]
WATER = ["Borewell", "Open well", "Canal", "River lift",
         "Rainwater harvest", "Tanker"]


def after_install():
	ensure_workflow_masters()
	create_roles()
	seed("Qualification Item", "qualification_item", QUALIFICATION_ITEMS)
	seed("Installation Step", "installation_step", INSTALLATION_STEPS)
	seed("Feedback Criterion", "feedback_criterion", FEEDBACK_CRITERIA)
	seed("Complaint Nature", "complaint_nature", COMPLAINT_NATURES)
	seed("Soil Type", "soil_type", SOILS)
	seed("Water Source", "water_source", WATER)
	frappe.db.commit()


def create_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({
				"doctype": "Role", "role_name": role, "desk_access": 1
			}).insert(ignore_permissions=True)


def seed(doctype, fieldname, values):
	for i, v in enumerate(values):
		if not frappe.db.exists(doctype, v):
			doc = frappe.new_doc(doctype)
			doc.set(fieldname, v)
			if doc.meta.has_field("sequence"):
				doc.sequence = i + 1
			doc.insert(ignore_permissions=True)


WORKFLOW_STATES = [
	("Lead", "Info"),
	("Qualified", "Info"),
	("Surveyed", "Warning"),
	("Quoted", "Warning"),
	("Order Booked", "Primary"),
	("Dispatched", "Primary"),
	("Delivered", "Primary"),
	("Installing", "Warning"),
	("Completed", "Success"),
	("Commission Claimed", "Success"),
	("Closed", "Success"),
	("Lost", "Danger"),
]

WORKFLOW_ACTIONS = [
	"Qualify", "Record Survey", "Send Quotation", "Book Order", "Dispatch",
	"Confirm Delivery", "Start Installation", "Complete", "Claim Commission",
	"Close", "Mark Lost",
]


def ensure_workflow_masters():
	"""Link targets for fixtures/workflow.json. sync_fixtures does not
	guarantee file order, so create these explicitly rather than relying
	on a second fixture file."""
	for state, style in WORKFLOW_STATES:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({
				"doctype": "Workflow State",
				"workflow_state_name": state,
				"style": style,
			}).insert(ignore_permissions=True)

	for action in WORKFLOW_ACTIONS:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({
				"doctype": "Workflow Action Master",
				"workflow_action_name": action,
			}).insert(ignore_permissions=True)

	frappe.db.commit()
