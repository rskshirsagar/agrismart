// Copyright (c) 2026, AgriSmart Farm Solutions LLP and contributors
//
// The calculator has to feel like the HTML prototype: type a dimension, see
// the area and the sketch change. So everything below is computed in the
// browser from agrismart.pond.compute() and written straight into the
// read-only fields. validate() recomputes server-side on save, so the browser
// is a preview, never the source of truth.

const WALLS = ["North", "South", "East", "West"];

frappe.ui.form.on("Pond Project", {
	onload(frm) {
		if (frm.is_new() && !(frm.doc.walls || []).length) {
			WALLS.forEach((w) => frm.add_child("walls", { wall: w }));
			frm.refresh_field("walls");
		}
	},

	refresh(frm) {
		frm.trigger("recalculate");
		frm.trigger("render_knowledge_library");
		frm.trigger("render_complaints");

		if (frm.is_new()) return;

		frm.add_custom_button(__("Quotation"), () =>
			frappe.utils.print(frm.doc.doctype, frm.doc.name, "Pond Quotation"), __("Print"));
		frm.add_custom_button(__("Calculation Report"), () =>
			frappe.utils.print(frm.doc.doctype, frm.doc.name, "Pond Calculation Report"), __("Print"));

		frm.add_custom_button(__("Complaint"), () =>
			frappe.new_doc("Pond Complaint", { pond_project: frm.doc.name }), __("Create"));
		frm.add_custom_button(__("Feedback"), () =>
			frappe.new_doc("Customer Feedback", { pond_project: frm.doc.name }), __("Create"));

		if (frm.doc.map_link) {
			frm.add_custom_button(__("Open Map"), () => window.open(frm.doc.map_link));
		}
	},

	// ── contact ───────────────────────────────────────────────────────
	mobile(frm) { frm.trigger("sync_whatsapp"); },
	whatsapp_same_as_mobile(frm) { frm.trigger("sync_whatsapp"); },
	sync_whatsapp(frm) {
		if (frm.doc.whatsapp_same_as_mobile && frm.doc.whatsapp !== frm.doc.mobile) {
			frm.set_value("whatsapp", frm.doc.mobile);
		}
	},

	// ── location ──────────────────────────────────────────────────────
	village(frm) {
		if (!frm.doc.village) return frm.trigger("compose_address");
		frappe.db.get_value("Pond Village", frm.doc.village,
			["taluka", "district", "pin_code"]).then((r) => {
			const v = r.message || {};
			return Promise.all([
				frm.set_value("taluka", v.taluka),
				frm.set_value("district", v.district),
				v.pin_code && !frm.doc.pin_code ? frm.set_value("pin_code", v.pin_code) : null,
			]);
		}).then(() => frm.trigger("compose_address"));
	},
	taluka(frm) {
		if (frm.doc.taluka) {
			frappe.db.get_value("Pond Taluka", frm.doc.taluka, "district")
				.then((r) => frm.set_value("district", (r.message || {}).district))
				.then(() => frm.trigger("compose_address"));
		} else {
			frm.trigger("compose_address");
		}
	},
	district(frm) { frm.trigger("compose_address"); },
	state(frm) { frm.trigger("compose_address"); },
	pin_code(frm) { frm.trigger("compose_address"); },
	address_auto(frm) { frm.trigger("compose_address"); },

	compose_address(frm) {
		if (!frm.doc.address_auto) return;
		const bits = [];
		if (frm.doc.village) {
			// the village key is "Name (Taluka)" — show only the name
			bits.push(String(frm.doc.village).replace(/\s*\(.*\)\s*$/, ""));
		}
		if (frm.doc.taluka) bits.push(__("Tal.") + " " + frm.doc.taluka);
		if (frm.doc.district) bits.push(__("Dist.") + " " + frm.doc.district);
		if (frm.doc.state) bits.push(frm.doc.state);
		let line = bits.join(", ");
		if (frm.doc.pin_code) line = line ? line + " - " + frm.doc.pin_code : String(frm.doc.pin_code);
		if (line !== frm.doc.address) frm.set_value("address", line);
	},

	gps_lat(frm) { frm.trigger("set_map"); },
	gps_long(frm) { frm.trigger("set_map"); },
	set_map(frm) {
		if (frm.doc.gps_lat && frm.doc.gps_long) {
			frm.set_value("map_link",
				`https://maps.google.com/?q=${frm.doc.gps_lat},${frm.doc.gps_long}`);
		}
	},

	// ── qualification ─────────────────────────────────────────────────
	load_checklist(frm) {
		frm.call("load_qualification_checklist").then((r) => {
			frm.refresh_field("qualification_items");
			frappe.show_alert({
				message: __("{0} parameter(s) loaded", [r.message || 0]),
				indicator: "green",
			});
		});
	},

	qualification_status(frm) {
		if (frm.doc.qualification_status === "Qualified") {
			frappe.show_alert({
				message: __("Qualified — the Survey tab is the next step."),
				indicator: "green",
			});
		}
	},

	// ── calculator ────────────────────────────────────────────────────
	anchor_width(frm) { frm.trigger("recalculate"); },
	waste_pct(frm) { frm.trigger("recalculate"); },
	water_depth(frm) { frm.trigger("recalculate"); },
	round_to(frm) { frm.trigger("recalculate"); },
	rate_farmer(frm) { frm.trigger("recalculate"); },
	rate_texel(frm) { frm.trigger("recalculate"); },
	rate_risha(frm) { frm.trigger("recalculate"); },
	advance_received(frm) { frm.trigger("recalculate"); },

	recalculate(frm) {
		const walls = {};
		(frm.doc.walls || []).forEach((row) => {
			if (row.wall) walls[row.wall.toLowerCase()] = row;
		});

		const c = agrismart.pond.compute(walls, {
			anchor_width: frm.doc.anchor_width,
			waste_pct: frm.doc.waste_pct,
			water_depth: frm.doc.water_depth,
			round_to: frm.doc.round_to,
		});

		// per-wall areas back into the grid
		(frm.doc.walls || []).forEach((row) => {
			const a = c.wall_areas[(row.wall || "").toLowerCase()] || 0;
			if (flt(row.area, 3) !== flt(a, 3)) {
				frappe.model.set_value(row.doctype, row.name, "area", a);
			}
		});

		const m = agrismart.pond.money(c.area, {
			rate_farmer: frm.doc.rate_farmer,
			rate_texel: frm.doc.rate_texel,
			rate_risha: frm.doc.rate_risha,
		});

		const vals = {
			wall_area_total: c.walls,
			base_area: c.base,
			perimeter: c.perim,
			anchor_area: c.anchor,
			sub_total_area: c.sub,
			waste_area: c.waste_area,
			area_sqm: c.area,
			mean_length: c.L,
			mean_breadth: c.B,
			height_used: c.H,
			capacity_cum: c.vol,
			capacity_litres: c.litres,
			capacity_lakh_litres: c.lakh_litres,
			amount_texel: m.texel,
			amount_risha: m.risha,
			amount_total: m.total,
			amount_margin: m.margin,
			amount_in_words: agrismart.pond.inWords(m.total),
			po_texel_amount: m.texel,
			po_risha_amount: m.risha,
			order_value: m.total,
			balance_due: flt(m.total) - flt(frm.doc.advance_received),
		};
		Object.keys(vals).forEach((k) => {
			// set_value on a read-only field is fine and keeps the doc dirty-aware
			if (flt(frm.doc[k]) !== flt(vals[k]) || frm.doc[k] !== vals[k]) {
				frm.doc[k] = vals[k];
				frm.refresh_field(k);
			}
		});

		frm.trigger("render_diagram");
		frm.trigger("render_report");
	},

	render_diagram(frm) {
		const walls = {};
		(frm.doc.walls || []).forEach((r) => {
			if (r.wall) walls[r.wall.toLowerCase()] = r;
		});
		const c = agrismart.pond.compute(walls, {
			anchor_width: frm.doc.anchor_width,
			waste_pct: frm.doc.waste_pct,
			water_depth: frm.doc.water_depth,
			round_to: frm.doc.round_to,
		});
		const field = frm.get_field("pond_diagram");
		if (field) field.$wrapper.html(agrismart.pond.svg(c));
	},

	render_report(frm) {
		const field = frm.get_field("calculation_report");
		if (!field) return;
		const walls = {};
		(frm.doc.walls || []).forEach((r) => {
			if (r.wall) walls[r.wall.toLowerCase()] = r;
		});
		const c = agrismart.pond.compute(walls, {
			anchor_width: frm.doc.anchor_width,
			waste_pct: frm.doc.waste_pct,
			water_depth: frm.doc.water_depth,
			round_to: frm.doc.round_to,
		});
		const m = agrismart.pond.money(c.area, {
			rate_farmer: frm.doc.rate_farmer,
			rate_texel: frm.doc.rate_texel,
			rate_risha: frm.doc.rate_risha,
		});
		field.$wrapper.html(agrismart.pond.report(c, m));
	},

	// ── knowledge bank ────────────────────────────────────────────────
	render_knowledge_library(frm) {
		const field = frm.get_field("knowledge_library");
		if (!field) return;
		frappe.call({
			method: "agrismart.agrismart.doctype.pond_project.pond_project.get_knowledge_library",
			callback(r) {
				const rows = r.message || [];
				if (!rows.length) {
					field.$wrapper.html(
						`<div class="text-muted" style="padding:12px">${
							__("No active material yet. Add records in Knowledge Asset.")}</div>`);
					return;
				}
				const grouped = {};
				rows.forEach((a) => {
					(grouped[a.asset_type] = grouped[a.asset_type] || []).push(a);
				});
				let html = '<div class="agrismart-kb">';
				Object.keys(grouped).forEach((type) => {
					html += `<div style="margin-bottom:14px">
						<div style="font-weight:600;margin-bottom:6px">${frappe.utils.escape_html(type)}</div>`;
					grouped[type].forEach((a) => {
						const link = a.file || a.external_url;
						const title = frappe.utils.escape_html(a.title || a.name);
						html += `<div style="display:flex;align-items:center;gap:10px;
							padding:6px 8px;border:1px solid var(--border-color);
							border-radius:6px;margin-bottom:5px">
							<span style="flex:1">${title}
								<span class="text-muted" style="font-size:11px">
									${frappe.utils.escape_html(a.language || "")}</span></span>
							${link ? `<a class="btn btn-xs btn-default" target="_blank"
								href="${frappe.utils.escape_html(link)}">${__("Open")}</a>` : ""}
							<button class="btn btn-xs btn-default agrismart-share"
								data-asset="${frappe.utils.escape_html(a.name)}">${__("Share")}</button>
						</div>`;
					});
					html += "</div>";
				});
				html += "</div>";
				field.$wrapper.html(html);

				field.$wrapper.find(".agrismart-share").on("click", function () {
					const asset = $(this).data("asset");
					const already = (frm.doc.knowledge_shares || [])
						.some((s) => s.knowledge_asset === asset);
					if (already) {
						frappe.show_alert({ message: __("Already logged"), indicator: "orange" });
						return;
					}
					frm.add_child("knowledge_shares", {
						knowledge_asset: asset,
						shared_on: frappe.datetime.get_today(),
					});
					frm.refresh_field("knowledge_shares");
					frappe.show_alert({ message: __("Logged — remember to save"), indicator: "green" });
				});
			},
		});
	},

	// ── complaints ────────────────────────────────────────────────────
	render_complaints(frm) {
		const field = frm.get_field("complaint_list");
		if (!field || frm.is_new()) return;
		frappe.call({
			method: "agrismart.agrismart.doctype.pond_project.pond_project.get_complaints",
			args: { pond_project: frm.doc.name },
			callback(r) {
				const rows = r.message || [];
				if (!rows.length) {
					field.$wrapper.html(
						`<div class="text-muted" style="padding:12px">${__("No complaints recorded.")}</div>`);
					return;
				}
				const colour = { Open: "red", "In Progress": "orange", Resolved: "blue", Closed: "green" };
				let html = '<table class="table table-bordered" style="margin:0"><thead><tr>' +
					`<th>${__("Complaint")}</th><th>${__("Date")}</th><th>${__("Nature")}</th>` +
					`<th>${__("Status")}</th><th>${__("Before")}</th><th>${__("After")}</th>` +
					"</tr></thead><tbody>";
				rows.forEach((c) => {
					const img = (u) => u
						? `<a href="${frappe.utils.escape_html(u)}" target="_blank">
							<img src="${frappe.utils.escape_html(u)}" style="height:38px;border-radius:4px"></a>`
						: '<span class="text-muted">—</span>';
					html += `<tr>
						<td><a href="/app/pond-complaint/${encodeURIComponent(c.name)}">${
							frappe.utils.escape_html(c.name)}</a></td>
						<td>${frappe.datetime.str_to_user(c.complaint_date) || ""}</td>
						<td>${frappe.utils.escape_html(c.nature || "")}</td>
						<td><span class="indicator ${colour[c.status] || "gray"}">${
							frappe.utils.escape_html(c.status || "")}</span></td>
						<td>${img(c.photo_before)}</td><td>${img(c.photo_after)}</td></tr>`;
				});
				field.$wrapper.html(html + "</tbody></table>");
			},
		});
	},
});

// Any dimension edit re-runs the whole calculation.
frappe.ui.form.on("Pond Wall", {
	top(frm) { frm.trigger("recalculate"); },
	height(frm) { frm.trigger("recalculate"); },
	bottom(frm) { frm.trigger("recalculate"); },
	wall(frm) { frm.trigger("recalculate"); },
	walls_add(frm) { frm.trigger("recalculate"); },
	walls_remove(frm) { frm.trigger("recalculate"); },
});

frappe.ui.form.on("Pond Qualification Item", {
	checked(frm) {
		const q = frm.doc.qualification_items || [];
		frm.doc.qualification_score = q.length
			? (100 * q.filter((x) => x.checked).length) / q.length : 0;
		frm.refresh_field("qualification_score");
	},
});
