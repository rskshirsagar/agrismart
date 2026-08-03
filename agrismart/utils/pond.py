"""Pond geometry, pricing and commission engine.

This is a line-for-line port of the calculation block in the browser
prototype (validated there against the 4,230 sq.m reference sheet).
Keep this module and `public/js/pond_calc.js` in step — they must agree.
"""

from frappe.utils import flt

WALLS = ("north", "south", "east", "west")


def _round_half_up(x):
	"""JS Math.round semantics — .5 always goes up, never to even."""
	import math

	return math.floor(flt(x) + 0.5)


def _or_default(value, fallback):
	"""An explicit 0 is a real choice; only None/"" falls back."""
	return flt(value) if value not in (None, "") else flt(fallback)


def _wall(w, key):
	x = (w or {}).get(key) or {}
	return {
		"top": flt(x.get("top")),
		"ht": flt(x.get("ht")),
		"bot": flt(x.get("bot")),
	}


def compute_pond(walls, anchor_w=None, extra_pct=None, depth_override=None,
                 round_to=None):
	"""Return every intermediate figure, not just the final area.

	The farmer signs off on the working, so each step has to be printable.
	"""
	from agrismart.utils.settings import get_settings

	s = get_settings()
	N, S, E, W = (_wall(walls, k) for k in WALLS)

	def trapezoid(o):
		# a sloping wall is a trapezium: mean of top and bottom, times the slope
		return (o["top"] + o["bot"]) / 2.0 * o["ht"]

	wall_areas = {
		"north": trapezoid(N), "south": trapezoid(S),
		"east": trapezoid(E), "west": trapezoid(W),
	}
	walls_total = sum(wall_areas.values())

	mean_top_l = (N["top"] + S["top"]) / 2.0
	mean_bot_l = (N["bot"] + S["bot"]) / 2.0
	mean_top_w = (E["top"] + W["top"]) / 2.0
	mean_bot_w = (E["bot"] + W["bot"]) / 2.0

	base = mean_bot_l * mean_bot_w
	perim = N["top"] + S["top"] + E["top"] + W["top"]

	aw = _or_default(anchor_w, s.anchor_width)
	anchor = perim * aw

	sub = walls_total + base + anchor
	ex = _or_default(extra_pct, s.extra_pct)
	with_extra = sub * (1 + ex / 100.0)

	rt = flt(round_to) or flt(s.round_to) or 10.0
	area = (_round_half_up(with_extra / rt) * rt if rt > 0
	         else _round_half_up(with_extra))

	L = (mean_top_l + mean_bot_l) / 2.0
	B = (mean_top_w + mean_bot_w) / 2.0
	ht_avg = (N["ht"] + S["ht"] + E["ht"] + W["ht"]) / 4.0
	H = flt(depth_override) if flt(depth_override) > 0 else ht_avg
	vol = L * B * H

	return {
		"wall_areas": wall_areas,
		"walls": walls_total,
		"mean_top_l": mean_top_l, "mean_bot_l": mean_bot_l,
		"mean_top_w": mean_top_w, "mean_bot_w": mean_bot_w,
		"ht_avg": ht_avg,
		"base": base, "perim": perim, "anchor_width": aw, "anchor": anchor,
		"sub": sub, "extra_pct": ex, "with_extra": with_extra, "area": area,
		"L": L, "B": B, "H": H,
		"depth_used": "entered" if flt(depth_override) > 0 else "average of heights",
		"vol": vol, "litres": vol * 1000.0,
		"valid": (N["top"] + S["top"] + E["top"] + W["top"]
		          + N["bot"] + S["bot"] + E["bot"] + W["bot"]) > 0,
	}


def money(area, rate_farmer=None, rate_texel=None, rate_risha=None):
	from agrismart.utils.settings import get_settings

	s = get_settings()
	rf = flt(rate_farmer) or flt(s.rate_farmer)
	rt = flt(rate_texel) or flt(s.rate_texel)
	rr = flt(rate_risha) or flt(s.rate_risha)
	area = flt(area)
	total, texel, risha = area * rf, area * rt, area * rr
	return {
		"rate_farmer": rf, "rate_texel": rt, "rate_risha": rr,
		"total": total, "texel": texel, "risha": risha,
		"margin": total - texel - risha,
	}


def commission_row(qty, bill_rate=None, actual_rate=None, supply_rate=None,
                   comm_rate=None, gst_pct=None, tds_pct=None,
                   freight=0, expenses=0):
	from agrismart.utils.settings import get_settings

	s = get_settings()
	qty = flt(qty)
	bill = flt(bill_rate) or flt(s.bill_rate)
	actual = flt(actual_rate) or flt(s.actual_rate)
	supply = flt(supply_rate) or flt(s.supply_rate)
	cr = flt(comm_rate) or flt(s.commission_rate)
	gst_pct = flt(gst_pct) if gst_pct is not None else flt(s.gst_pct)
	tds_pct = flt(tds_pct) if tds_pct is not None else flt(s.tds_pct)

	disc_rate = bill - actual
	commission = qty * cr
	gst = commission * gst_pct / 100.0
	gross = commission + gst
	# TDS is deducted on the commission value, before GST
	tds = commission * tds_pct / 100.0

	return {
		"qty_sqm": qty,
		"bill_rate": bill, "actual_rate": actual, "supply_rate": supply,
		"discount_rate": disc_rate, "discount_amount": qty * disc_rate,
		"billing_amount": qty * actual,
		"commission_rate": cr, "commission": commission,
		"gst_amount": gst, "gross": gross, "tds": tds,
		"freight": flt(freight), "expenses": flt(expenses),
		"net_receivable": gross - tds - flt(freight) - flt(expenses),
	}
