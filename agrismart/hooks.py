app_name = "agrismart"
app_title = "AgriSmart"
app_publisher = "AgriSmart Farm Solutions LLP"
app_description = "Farm pond liner sales, installation and commission management"
app_email = "info@example.com"
app_license = "mit"
required_apps = ["erpnext"]

# ---------------------------------------------------------------- assets
app_include_js = "/assets/agrismart/js/pond_calc.js"

# ---------------------------------------------------------------- apps screen
# frappe/apps.py::get_apps() skips any installed app that does not declare this
# hook ("if not len(app_details): continue"). Doctypes, Module Def and even a
# workspace make no difference — without this there is no tile on /apps.
add_to_apps_screen = [
	{
		"name": "agrismart",
		"logo": "/assets/agrismart/images/logo.svg",
		"title": "AgriSmart",
		"route": "/app/agrismart",
		"has_permission": "agrismart.utils.permissions.has_app_permission",
	}
]

# ---------------------------------------------------------------- fixtures
fixtures = [
	{"dt": "Workflow", "filters": [["name", "in", ["Pond Project Stage"]]]},
	{"dt": "Workflow State", "filters": [["name", "in", [
		"Lead", "Qualified", "Surveyed", "Quoted", "Order Booked", "Dispatched",
		"Delivered", "Installing", "Completed", "Commission Claimed", "Closed",
		"Lost",
	]]]},
	{"dt": "Workflow Action Master", "filters": [["name", "in", [
		"Qualify", "Record Survey", "Send Quotation", "Book Order", "Dispatch",
		"Confirm Delivery", "Start Installation", "Complete", "Claim Commission",
		"Close", "Mark Lost",
	]]]},
	{"dt": "Role", "filters": [["name", "in", [
		"AgriSmart Manager", "AgriSmart Executive",
		"AgriSmart Logistics", "AgriSmart Installation",
	]]]},
	{"dt": "Custom Field", "filters": [["module", "=", "AgriSmart"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "AgriSmart"]]},
]

# ---------------------------------------------------------------- hooks
after_install = "agrismart.install.after_install"

doc_events = {
	"Lead": {
		"on_update": "agrismart.events.lead.sync_pond_project",
	},
}

scheduler_events = {
	"daily": [
		"agrismart.tasks.daily.flag_stalled_projects",
		"agrismart.tasks.daily.request_feedback",
	],
}

website_route_rules = [
	{"from_route": "/pond-feedback", "to_route": "pond-feedback"},
]
