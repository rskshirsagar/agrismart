app_name = "agrismart"
app_title = "AgriSmart"
app_publisher = "AgriSmart Farm Solutions LLP"
app_description = "Farm pond liner sales, installation and commission management"
app_email = "info@example.com"
app_license = "mit"
required_apps = ["erpnext"]

# ---------------------------------------------------------------- assets
app_include_js = "/assets/agrismart/js/pond_calc.js"

# ---------------------------------------------------------------- fixtures
fixtures = [
	{"dt": "Workflow", "filters": [["name", "in", ["Pond Project Stage"]]]},
	{"dt": "Workflow State", "filters": [["name", "like", "%"]]},
	{"dt": "Workflow Action Master", "filters": [["name", "like", "%"]]},
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
