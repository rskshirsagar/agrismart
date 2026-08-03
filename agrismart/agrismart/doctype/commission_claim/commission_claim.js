frappe.ui.form.on("Commission Claim", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Fetch Completed Projects"), () => {
				frm.call("fetch_eligible").then(r => {
					frm.refresh_field("items");
					frappe.show_alert(__("{0} project(s) added", [r.message || 0]));
				});
			});
		}
		if (frm.doc.docstatus === 1 && !frm.doc.sales_invoice) {
			frm.add_custom_button(__("Sales Invoice"), () => {
				frm.call("make_sales_invoice").then(r => {
					if (r.message) frappe.set_route("Form", "Sales Invoice", r.message);
				});
			}, __("Create"));
		}
	},
});
