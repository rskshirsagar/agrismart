/* Browser mirror of agrismart/utils/pond.py — keep the two in step.
 *
 * compute() must agree with compute_pond() to the last decimal: the form shows
 * these numbers live, then validate() recomputes server-side on save. Any
 * drift shows up as figures that change the moment the user hits Save.
 */
frappe.provide("agrismart.pond");

(function () {
	const DEF = { anchor_width: 1.5, waste_pct: 5, round_to: 10, gsm: 420,
		rate_farmer: 105, rate_texel: 89, rate_risha: 16 };

	const num = (v) => {
		const x = parseFloat(v);
		return isFinite(x) ? x : 0;
	};
	// only null/"" fall back — an explicit 0 is a real choice
	const orDef = (v, d) => (v === null || v === undefined || v === "" ? d : num(v));

	agrismart.pond.compute = function (walls, opts) {
		opts = opts || {};
		const g = (k) => {
			const x = walls[k] || {};
			return { top: num(x.top), ht: num(x.height), bot: num(x.bottom) };
		};
		const N = g("north"), S = g("south"), E = g("east"), W = g("west");
		const trap = (o) => ((o.top + o.bot) / 2) * o.ht;

		const wall_areas = {
			north: trap(N), south: trap(S), east: trap(E), west: trap(W),
		};
		const walls_total = wall_areas.north + wall_areas.south
			+ wall_areas.east + wall_areas.west;

		const meanTopL = (N.top + S.top) / 2, meanBotL = (N.bot + S.bot) / 2;
		const meanTopW = (E.top + W.top) / 2, meanBotW = (E.bot + W.bot) / 2;

		const base = meanBotL * meanBotW;
		const perim = N.top + S.top + E.top + W.top;
		const aw = orDef(opts.anchor_width, DEF.anchor_width);
		const anchor = perim * aw;

		const sub = walls_total + base + anchor;
		const ex = orDef(opts.waste_pct, DEF.waste_pct);
		const withExtra = sub * (1 + ex / 100);

		const rt = num(opts.round_to) || DEF.round_to;
		// Math.floor(x + 0.5) === Python _round_half_up; Math.round differs on
		// negatives only, but keeping them identical avoids a future surprise
		const area = rt > 0 ? Math.floor(withExtra / rt + 0.5) * rt
			: Math.floor(withExtra + 0.5);

		const L = (meanTopL + meanBotL) / 2, B = (meanTopW + meanBotW) / 2;
		const htAvg = (N.ht + S.ht + E.ht + W.ht) / 4;
		const H = num(opts.water_depth) > 0 ? num(opts.water_depth) : htAvg;
		const vol = L * B * H;

		return {
			wall_areas,
			aN: wall_areas.north, aS: wall_areas.south,
			aE: wall_areas.east, aW: wall_areas.west,
			walls: walls_total, base, perim, anchor_width: aw, anchor,
			sub, waste_pct: ex, with_extra: withExtra,
			waste_area: withExtra - sub, area,
			meanTopL, meanBotL, meanTopW, meanBotW,
			L, B, H, ht_avg: htAvg,
			depth_entered: num(opts.water_depth) > 0,
			vol, litres: vol * 1000, lakh_litres: (vol * 1000) / 100000,
			weight_kg: (area * DEF.gsm) / 1000,
			valid: perim + N.bot + S.bot + E.bot + W.bot > 0,
		};
	};

	agrismart.pond.money = function (area, cfg) {
		cfg = cfg || {};
		const rf = orDef(cfg.rate_farmer, DEF.rate_farmer);
		const rt = orDef(cfg.rate_texel, DEF.rate_texel);
		const rr = orDef(cfg.rate_risha, DEF.rate_risha);
		const total = area * rf, texel = area * rt, risha = area * rr;
		return { rate_farmer: rf, rate_texel: rt, rate_risha: rr,
			total, texel, risha, margin: total - texel - risha };
	};

	/* ── formatting (Indian conventions, as in the prototype) ───────── */
	const fmt = (v, d) => num(v).toLocaleString("en-IN", {
		minimumFractionDigits: d === undefined ? 2 : d,
		maximumFractionDigits: d === undefined ? 2 : d,
	});
	const inr = (v) => "\u20B9" + num(v).toLocaleString("en-IN", { maximumFractionDigits: 0 });
	agrismart.pond.fmt = fmt;
	agrismart.pond.inr = inr;

	const A = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
		"Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
		"Sixteen", "Seventeen", "Eighteen", "Nineteen"];
	const B = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
		"Eighty", "Ninety"];
	const two = (x) => (x < 20 ? A[x] : B[Math.floor(x / 10)] + (x % 10 ? " " + A[x % 10] : ""));
	const three = (x) => (x > 99 ? A[Math.floor(x / 100)] + " Hundred" + (x % 100 ? " " : "") : "")
		+ (x % 100 ? two(x % 100) : "");

	agrismart.pond.inWords = function (v) {
		let n = Math.round(num(v));
		if (n === 0) return "Zero Only";
		let out = "";
		const cr = Math.floor(n / 10000000); n %= 10000000;
		const lk = Math.floor(n / 100000); n %= 100000;
		const th = Math.floor(n / 1000); n %= 1000;
		if (cr) out += three(cr) + " Crore ";
		if (lk) out += three(lk) + " Lakh ";
		if (th) out += three(th) + " Thousand ";
		if (n) out += three(n);
		return out.trim() + " Only";
	};

	/* ── pond plan + cross section, ported from the prototype ───────── */
	agrismart.pond.svg = function (c) {
		if (!c.valid) {
			return `<div style="height:180px;display:grid;place-items:center;
				border:1px dashed var(--border-color);border-radius:8px;
				color:var(--text-muted);font-size:12px;letter-spacing:.12em;
				text-transform:uppercase">Enter measurements</div>`;
		}
		const TL = c.meanTopL || 1, TW = c.meanTopW || 1;
		const BL = c.meanBotL, BW = c.meanBotW;
		const PW = 380, PH = 250, pad = 34;
		const sc = Math.min((PW - pad * 2) / TL, (PH - pad * 2) / TW);
		const ow = TL * sc, oh = TW * sc;
		const iw = Math.max(BL * sc, 4), ih = Math.max(BW * sc, 4);
		const ox = (PW - ow) / 2, oy = (PH - oh) / 2;
		const ix = (PW - iw) / 2, iy = (PH - ih) / 2;
		const an = Math.max(4, c.anchor_width * sc);

		const t = (x, y, s, anc, col, sz) =>
			`<text x="${x}" y="${y}" text-anchor="${anc || "middle"}" fill="${col || "#8FB0B5"}"
			 font-family="ui-monospace,monospace" font-size="${sz || 8.5}"
			 letter-spacing=".08em">${s}</text>`;

		let g = "";
		g += `<rect x="${ox - an}" y="${oy - an}" width="${ow + an * 2}" height="${oh + an * 2}"
			rx="6" fill="none" stroke="#B4552B" stroke-width="1.4" stroke-dasharray="5 4" opacity=".85"/>`;
		g += `<path d="M${ox} ${oy}L${ox + ow} ${oy}L${ox + ow} ${oy + oh}L${ox} ${oy + oh}Z
			M${ix} ${iy}L${ix} ${iy + ih}L${ix + iw} ${iy + ih}L${ix + iw} ${iy}Z"
			fill="#0B6E7F" fill-rule="evenodd" opacity=".38"/>`;
		g += `<rect x="${ox}" y="${oy}" width="${ow}" height="${oh}" fill="none"
			stroke="#7FC8CE" stroke-width="1.6"/>`;
		g += `<rect x="${ix}" y="${iy}" width="${iw}" height="${ih}" fill="#0E3D46"
			stroke="#7FC8CE" stroke-width="1.2" stroke-dasharray="3 3"/>`;
		[[ox, oy, ix, iy], [ox + ow, oy, ix + iw, iy],
			[ox, oy + oh, ix, iy + ih], [ox + ow, oy + oh, ix + iw, iy + ih]]
			.forEach((p) => {
				g += `<line x1="${p[0]}" y1="${p[1]}" x2="${p[2]}" y2="${p[3]}"
					stroke="#7FC8CE" stroke-width=".8" opacity=".5"/>`;
			});
		g += t(PW / 2, oy - an - 7, "NORTH  " + fmt(c.aN, 0) + " m\u00B2", "middle", "#CFE3E6", 9);
		g += t(PW / 2, oy + oh + an + 16, "SOUTH  " + fmt(c.aS, 0) + " m\u00B2", "middle", "#CFE3E6", 9);
		g += `<text transform="translate(${ox - an - 8},${oy + oh / 2}) rotate(-90)"
			text-anchor="middle" fill="#CFE3E6" font-family="ui-monospace,monospace"
			font-size="9" letter-spacing=".08em">WEST  ${fmt(c.aW, 0)} m\u00B2</text>`;
		g += `<text transform="translate(${ox + ow + an + 13},${oy + oh / 2}) rotate(90)"
			text-anchor="middle" fill="#CFE3E6" font-family="ui-monospace,monospace"
			font-size="9" letter-spacing=".08em">EAST  ${fmt(c.aE, 0)} m\u00B2</text>`;
		g += t(PW / 2, PH / 2 - 3, "BASE", "middle", "#7FC8CE", 9);
		g += t(PW / 2, PH / 2 + 10, fmt(c.base, 0) + " m\u00B2", "middle", "#CFE3E6", 10);
		g += t(PW / 2, oy + 14, fmt(c.meanTopL, 1) + " m top", "middle", "#5E8188", 8);
		g += t(PW / 2, iy - 5, fmt(c.meanBotL, 1) + " m bottom", "middle", "#5E8188", 8);

		/* cross-section */
		const SW = 380, SH = 118, sy = 26, baseY = SH - 22;
		const slope = Math.min(52, (SW - 140) / 2);
		const topL = 40, topR = SW - 40, botL = topL + slope, botR = topR - slope;
		const wl = sy + (baseY - sy) * 0.12;
		const tfrac = (wl - sy) / (baseY - sy);
		const wxL = topL + (botL - topL) * tfrac, wxR = topR - (topR - botR) * tfrac;
		let s = "";
		s += `<path d="M${topL} ${sy}L${botL} ${baseY}L${botR} ${baseY}L${topR} ${sy}"
			fill="none" stroke="#B4552B" stroke-width="7" stroke-linejoin="round" opacity=".5"/>`;
		s += `<path d="M${wxL} ${wl}L${botL} ${baseY}L${botR} ${baseY}L${wxR} ${wl}Z"
			fill="#0B6E7F" opacity=".55"/>`;
		s += `<line x1="${wxL}" y1="${wl}" x2="${wxR}" y2="${wl}" stroke="#7FC8CE" stroke-width="1.2"/>`;
		s += `<path d="M${topL} ${sy}L${botL} ${baseY}L${botR} ${baseY}L${topR} ${sy}"
			fill="none" stroke="#12262B" stroke-width="3.4" stroke-linejoin="round"/>`;
		s += `<line x1="${topL - 16}" y1="${sy}" x2="${topL}" y2="${sy}" stroke="#B4552B" stroke-width="3"/>`;
		s += `<line x1="${topR}" y1="${sy}" x2="${topR + 16}" y2="${sy}" stroke="#B4552B" stroke-width="3"/>`;
		s += `<line x1="${SW - 24}" y1="${sy}" x2="${SW - 24}" y2="${baseY}"
			stroke="#5E8188" stroke-width=".9" stroke-dasharray="3 3"/>`;
		s += `<text x="${SW - 20}" y="${(sy + baseY) / 2}" fill="#8FB0B5"
			font-family="ui-monospace,monospace" font-size="8">${fmt(c.H, 1)} m</text>`;
		s += `<text x="${topL}" y="${sy - 9}" fill="#B4552B"
			font-family="ui-monospace,monospace" font-size="8">ANCHOR ${fmt(c.anchor_width, 1)} m</text>`;
		s += `<text x="${SW / 2}" y="${baseY + 15}" text-anchor="middle" fill="#5E8188"
			font-family="ui-monospace,monospace" font-size="8" letter-spacing=".12em">SECTION</text>`;

		return `<div style="background:#0A1F24;border-radius:10px;padding:10px">
			<div style="color:#5E8188;font-family:ui-monospace,monospace;font-size:9px;
				letter-spacing:.14em;text-transform:uppercase;margin-bottom:4px">
				Pond plan &middot; live from measurements</div>
			<svg viewBox="0 0 ${PW} ${PH}" style="width:100%;max-width:520px"
				role="img" aria-label="Pond plan view">${g}</svg>
			<svg viewBox="0 0 ${SW} ${SH}" style="width:100%;max-width:520px;margin-top:2px"
				role="img" aria-label="Pond cross section">${s}</svg>
			<div style="display:flex;gap:16px;color:#8FB0B5;font-size:10px;
				font-family:ui-monospace,monospace;margin-top:6px">
				<span><i style="display:inline-block;width:9px;height:9px;background:#0B6E7F;
					opacity:.6;border-radius:2px"></i> Slope walls</span>
				<span><i style="display:inline-block;width:9px;height:9px;background:#0E3D46;
					border:1px solid #7FC8CE;border-radius:2px"></i> Base floor</span>
				<span><i style="display:inline-block;width:9px;height:9px;background:#B4552B;
					border-radius:2px"></i> Anchor trench</span>
			</div></div>`;
	};

	/* ── the three report cards from Pond_Calculation_Report.docx ────── */
	agrismart.pond.report = function (c, m) {
		if (!c.valid) {
			return `<div class="text-muted" style="padding:12px">${
				__("Enter wall measurements to see the report.")}</div>`;
		}
		const card = (title, note, body) => `
			<div style="border:1px solid var(--border-color);border-radius:10px;
				overflow:hidden;margin-bottom:14px;background:var(--card-bg)">
				<div style="display:flex;justify-content:space-between;align-items:baseline;
					padding:12px 16px;border-bottom:1px solid var(--border-color)">
					<strong style="font-size:14px">${title}</strong>
					<span style="color:var(--text-muted);font-family:ui-monospace,monospace;
						font-size:10px;letter-spacing:.1em;text-transform:uppercase">${note}</span>
				</div>
				<table class="table" style="margin:0">${body}</table></div>`;

		const row = (label, sub, val, strong) => `
			<tr><td style="border-top:none">
				<div style="${strong ? "font-weight:600" : ""}">${label}</div>
				${sub ? `<div style="color:var(--text-muted);font-size:11px">${sub}</div>` : ""}
			</td><td style="border-top:none;text-align:right;font-family:ui-monospace,monospace;
				${strong ? "font-weight:600" : ""}">${val}</td></tr>`;

		const liner = card(__("Liner area"), __("Trapezoid method"),
			row(__("North wall"), fmt(c.meanTopL, 1) + " " + __("trapezoid"), fmt(c.aN))
			+ row(__("South wall"), "", fmt(c.aS))
			+ row(__("East wall"), "", fmt(c.aE))
			+ row(__("West wall"), "", fmt(c.aW))
			+ row(__("Base floor"), fmt(c.meanBotL) + " \u00D7 " + fmt(c.meanBotW), fmt(c.base))
			+ row(__("Anchor trench"),
				fmt(c.perim, 1) + " m " + __("perimeter") + " \u00D7 " + fmt(c.anchor_width, 1) + " m",
				fmt(c.anchor))
			+ row(__("Sub total"), "", fmt(c.sub), true)
			+ row(__("Overlap &amp; wastage") + " " + fmt(c.waste_pct, 0) + "%", "", fmt(c.waste_area))
			+ `<tr><td colspan="2" style="border-top:none;padding:0">
				<div style="background:#12262B;color:#EAEEEB;border-radius:8px;margin:8px;
					padding:14px 16px;display:flex;justify-content:space-between;align-items:flex-end">
					<div><div style="color:#7FC8CE;font-size:10px;letter-spacing:.12em;
						text-transform:uppercase">${__("Liner required")}</div>
						<div style="font-size:26px;font-weight:700;font-family:ui-monospace,monospace">
							${fmt(c.area, 0)} <span style="font-size:12px;font-weight:400">sq.mtr</span></div></div>
					<div style="text-align:right"><div style="color:#7FC8CE;font-size:10px;
						letter-spacing:.12em;text-transform:uppercase">${__("Water")}</div>
						<div style="font-size:18px;font-weight:600;font-family:ui-monospace,monospace">
							${fmt(c.lakh_litres, 1)} <span style="font-size:11px">${__("lakh L")}</span></div></div>
				</div></td></tr>`);

		const water = card(__("Water capacity"), "L \u00D7 B \u00D7 H",
			row(__("Mean length (top+bottom)/2"), "", fmt(c.L) + " m")
			+ row(__("Mean breadth (top+bottom)/2"), "", fmt(c.B) + " m")
			+ row(__("Height used"), "", fmt(c.H) + " m")
			+ row(__("Capacity"), "", fmt(c.vol, 0) + " cu.m", true)
			+ row(__("In litres"), "", fmt(c.litres, 0))
			+ row(__("In lakh litres"), "", fmt(c.lakh_litres))
			+ `<tr><td colspan="2" style="border-top:none;color:var(--text-muted);font-size:11px">
				L \u00D7 B \u00D7 H \u00b7 ${c.depth_entered
					? __("depth as entered.") : __("height taken from average of heights.")}</td></tr>`);

		const amounts = card(__("Amounts"), "",
			row(__("Liner") + " @ " + inr(m.rate_texel), "", inr(m.texel))
			+ row(__("Installation") + " @ " + inr(m.rate_risha), "", inr(m.risha))
			+ row(__("Farmer pays") + " @ " + inr(m.rate_farmer), "", inr(m.total), true)
			+ `<tr><td colspan="2" style="border-top:none;color:var(--text-muted);font-size:11px">
				${agrismart.pond.inWords(m.total)}</td></tr>`);

		return `<div class="agrismart-report" style="max-width:640px">${liner}${water}${amounts}</div>`;
	};
})();
