/* Browser mirror of agrismart/utils/pond.py — keep the two in step. */
frappe.provide("agrismart.pond");

agrismart.pond.compute = function (walls, opts) {
	opts = opts || {};
	const g = k => {
		const x = walls[k] || {};
		return {
			top: flt(x.top_length ?? x.top),
			ht: flt(x.height ?? x.ht),
			bot: flt(x.bottom_length ?? x.bot),
		};
	};
	const N = g("north"), S = g("south"), E = g("east"), W = g("west");
	const trap = o => ((o.top + o.bot) / 2) * o.ht;

	const wallAreas = {
		north: trap(N), south: trap(S), east: trap(E), west: trap(W),
	};
	const walls_total = Object.values(wallAreas).reduce((a, b) => a + b, 0);

	const meanBotL = (N.bot + S.bot) / 2;
	const meanBotW = (E.bot + W.bot) / 2;
	const meanTopL = (N.top + S.top) / 2;
	const meanTopW = (E.top + W.top) / 2;

	const base = meanBotL * meanBotW;
	const perim = N.top + S.top + E.top + W.top;
	const aw = flt(opts.anchor_width) || 1.5;
	const anchor = perim * aw;

	const sub = walls_total + base + anchor;
	const ex = flt(opts.extra_pct) || 5;
	const withExtra = sub * (1 + ex / 100);
	const rt = flt(opts.round_to) || 10;
	const area = rt > 0 ? Math.round(withExtra / rt) * rt : Math.round(withExtra);

	const L = (meanTopL + meanBotL) / 2;
	const B = (meanTopW + meanBotW) / 2;
	const htAvg = (N.ht + S.ht + E.ht + W.ht) / 4;
	const H = flt(opts.depth_override) > 0 ? flt(opts.depth_override) : htAvg;

	return {
		wall_areas: wallAreas, walls: walls_total, base, perim, anchor,
		sub, with_extra: withExtra, area, L, B, H,
		vol: L * B * H, litres: L * B * H * 1000,
	};
};
