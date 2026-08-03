// Copyright (c) 2026, AgriSmart Farm Solutions LLP and contributors

frappe.ui.form.on("Pond Project", {
	refresh(frm) {
		frm.trigger("render_diagram");

		if (!frm.is_new()) {
			frm.add_custom_button(__("Quotation"), () => frm.trigger("print_quote"),
				__("Print"));
			frm.add_custom_button(__("Order Estimate"), () => frappe.utils.print(
				frm.doc.doctype, frm.doc.name, "Pond Order Estimate"), __("Print"));
			frm.add_custom_button(__("Completion Certificate"), () => frappe.utils.print(
				frm.doc.doctype, frm.doc.name, "Pond Completion Certificate"), __("Print"));

			frm.add_custom_button(__("Complaint"), () => {
				frappe.new_doc("Pond Complaint", { pond_project: frm.doc.name });
			}, __("Create"));
			frm.add_custom_button(__("Feedback"), () => {
				frappe.new_doc("Customer Feedback", { pond_project: frm.doc.name });
			}, __("Create"));
		}

		if (frm.doc.map_link) {
			frm.add_custom_button(__("Open Map"), () => window.open(frm.doc.map_link));
		}
	},

	print_quote(frm) {
		frappe.utils.print(frm.doc.doctype, frm.doc.name, "Pond Quotation");
	},

	village(frm) {
		if (!frm.doc.village) return;
		frappe.db.get_value("Pond Village", frm.doc.village, ["taluka", "district"])
			.then(r => {
				frm.set_value("taluka", r.message.taluka);
				frm.set_value("district", r.message.district);
			});
	},

	render_diagram(frm) {
		const w = {};
		(frm.doc.walls || []).forEach(r => {
			w[(r.wall || "").toLowerCase()] = r;
		});
		const g = k => w[k] || {};
		const html = `
			<div style="border:1px solid var(--border-color);border-radius:8px;padding:14px">
				<div style="text-align:center;font-weight:600;margin-bottom:8px">
					${__("Pond Layout")}
				</div>
				<table class="table table-bordered" style="margin:0">
					<thead><tr>
						<th>${__("Wall")}</th><th class="text-right">${__("Top (m)")}</th>
						<th class="text-right">${__("Height (m)")}</th>
						<th class="text-right">${__("Bottom (m)")}</th>
						<th class="text-right">${__("Area (sq.m)")}</th>
					</tr></thead>
					<tbody>
					${["north", "south", "east", "west"].map(k => `
						<tr><td>${__(k[0].toUpperCase() + k.slice(1))}</td>
						<td class="text-right">${flt(g(k).top_length, 2)}</td>
						<td class="text-right">${flt(g(k).height, 2)}</td>
						<td class="text-right">${flt(g(k).bottom_length, 2)}</td>
						<td class="text-right">${flt(g(k).wall_area, 2)}</td></tr>`).join("")}
					</tbody>
				</table>
			</div>`;
		frm.get_field("pond_diagram").$wrapper.html(html);
	},
});

frappe.ui.form.on("Pond Wall", {
	top_length: recalc, height: recalc, bottom_length: recalc, walls_remove: recalc,
});

function recalc(frm) {
	frm.dirty();
	frm.trigger("render_diagram");
}
