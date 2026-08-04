"""Why isn't the AgriSmart tile showing?

Run against a site:

    bench --site your-site.local execute agrismart.utils.diagnose.apps_screen

It walks the same gates frappe/apps.py::get_apps() applies, in order, and
reports the first one that fails — quicker than guessing.
"""

import frappe


def apps_screen():
	ok = True

	def check(label, passed, hint=""):
		nonlocal ok
		mark = "PASS" if passed else "FAIL"
		print(f"[{mark}] {label}")
		if not passed:
			ok = False
			if hint:
				print(f"       -> {hint}")
		return passed

	print("\n--- AgriSmart apps-screen diagnostic ---\n")

	# 1. installed at all?
	installed = "agrismart" in frappe.get_installed_apps()
	check(
		"app is in installed_apps",
		installed,
		"bench --site <site> install-app agrismart",
	)
	if not installed:
		return

	# 2. the hook itself — the usual culprit
	hooks = frappe.get_hooks("add_to_apps_screen", app_name="agrismart")
	if not check(
		"add_to_apps_screen hook is declared",
		bool(hooks),
		"hooks.py is missing add_to_apps_screen, or bench is still serving an "
		"old copy of the app source. get_apps() skips the app outright.",
	):
		return

	detail = hooks[0]
	print(f"       hook: {detail}")

	# 3. has_permission path must import AND return truthy
	path = detail.get("has_permission")
	if path:
		try:
			result = frappe.get_attr(path)()
			check(
				f"has_permission ({path}) returns true for {frappe.session.user}",
				bool(result),
				"The user lacks every AgriSmart role. Assign one, or drop the "
				"has_permission line from hooks.py to rule this out.",
			)
		except Exception as e:
			check(
				f"has_permission ({path}) is importable",
				False,
				f"{e!r} — get_apps() swallows this and hides the app silently.",
			)

	# 4. setup-wizard gate
	row = frappe.db.get_value(
		"Installed Application",
		{"app_name": "agrismart"},
		["has_setup_wizard", "is_setup_complete"],
		as_dict=True,
	)
	if row:
		gate_ok = (not row.has_setup_wizard) or row.is_setup_complete
		check(
			"setup-wizard gate",
			gate_ok or "System Manager" in frappe.get_roles(),
			"Installed Application says a setup wizard is pending.",
		)

	# 5. the route's workspace must exist and be visible
	route = detail.get("route", "")
	if route.startswith("/app/"):
		slug = route.split("/")[2]
		ws = frappe.db.get_value(
			"Workspace",
			{"name": ["like", slug]},
			["name", "public", "is_hidden"],
			as_dict=True,
		)
		if check(
			f"workspace for route {route} exists",
			bool(ws),
			"bench migrate did not sync the workspace JSON. Check the file sits "
			"at agrismart/agrismart/workspace/agrismart/agrismart.json",
		):
			check(
				f"workspace '{ws.name}' is public and not hidden",
				bool(ws.public) and not ws.is_hidden,
				"A private or hidden workspace makes get_route() fall back.",
			)

	# 6. widgets the workspace points at
	for card in ("Open Leads", "Orders Booked", "Awaiting Installation",
	             "Completed This Month"):
		check(
			f"number card '{card}' exists",
			bool(frappe.db.exists("Number Card", card)),
			"Run: bench --site <site> execute "
			"agrismart.patches.create_dashboard_widgets.execute",
		)
	check(
		"dashboard chart 'Pond Projects by Stage' exists",
		bool(frappe.db.exists("Dashboard Chart", "Pond Projects by Stage")),
		"Same patch as above.",
	)

	# 7. built assets
	import os

	logo = frappe.get_site_path("..", "..", "sites", "assets", "agrismart",
	                            "images", "logo.svg")
	check(
		"logo asset is built",
		os.path.exists(logo),
		"bench build --app agrismart (the tile renders blank without it)",
	)

	print("\n--- " + ("all checks passed" if ok else "see failures above") + " ---\n")
