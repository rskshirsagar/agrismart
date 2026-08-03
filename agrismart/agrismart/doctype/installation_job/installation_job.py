# Copyright (c) 2026, AgriSmart Farm Solutions LLP and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from agrismart.utils.numbering import next_no


class InstallationJob(Document):
	def autoname(self):
		self.name = next_no("job")

	def validate(self):
		if not self.sites:
			frappe.throw(_("Add at least one site."))
		self.total_area = sum(flt(r.area_sqm) for r in self.sites)
		self.site_count = len(self.sites)
		if self.installation_team and not self.team_mobile:
			self.team_mobile = frappe.db.get_value(
				"Installation Team", self.installation_team, "mobile"
			)

	def on_submit(self):
		for row in self.sites:
			p = frappe.get_doc("Pond Project", row.pond_project)
			p.installation_job = self.name
			p.installation_team = self.installation_team
			p.installation_start = row.start_date or self.job_date
			if row.end_date:
				p.installation_end = row.end_date
				p.advance_to("Completed", save=False)
			else:
				p.advance_to("Installing", save=False)
			p.save(ignore_permissions=True)

	def on_cancel(self):
		for row in self.sites:
			frappe.db.set_value("Pond Project", row.pond_project,
			                    "installation_job", None)
