"""Check the Python port against the original prototype's JS arithmetic."""
import sys, types, math, random, json

# --- stub frappe so pond.py imports standalone -------------------------
frappe = types.ModuleType("frappe"); utils = types.ModuleType("frappe.utils")
def flt(v, p=None):
    try: x = float(v)
    except (TypeError, ValueError): return 0.0
    if not math.isfinite(x): return 0.0
    return round(x, p) if p is not None else x
utils.flt = flt
frappe.utils = utils
sys.modules["frappe"] = frappe; sys.modules["frappe.utils"] = utils

CFG = dict(anchor_width=1.5, extra_pct=5, round_to=10, rate_farmer=105,
           rate_texel=89, rate_risha=16, bill_rate=107, actual_rate=105,
           supply_rate=89, commission_rate=5.5, gst_pct=18, tds_pct=2, gsm=420)
settings = types.ModuleType("agrismart.utils.settings")
class S:
    def __getattr__(self, k): return CFG[k]
settings.get_settings = lambda: S()
pkg = types.ModuleType("agrismart"); up = types.ModuleType("agrismart.utils")
sys.modules["agrismart"] = pkg; sys.modules["agrismart.utils"] = up
sys.modules["agrismart.utils.settings"] = settings
sys.path.insert(0, "/home/claude/out/agrismart/agrismart/utils")
import importlib.util
spec = importlib.util.spec_from_file_location(
    "agrismart.utils.pond", "/home/claude/out/agrismart/agrismart/utils/pond.py")
pond = importlib.util.module_from_spec(spec)
sys.modules["agrismart.utils.pond"] = pond
spec.loader.exec_module(pond)

# --- faithful transcription of the prototype's computePond -------------
def js_compute(w, anchorW, extraPct, depthOverride, roundTo):
    n = lambda v: float(v) if v not in (None, "") else 0.0
    get = lambda k: {"top": n(w.get(k, {}).get("top")), "ht": n(w.get(k, {}).get("ht")),
                     "bot": n(w.get(k, {}).get("bot"))}
    N, S_, E, W = get("north"), get("south"), get("east"), get("west")
    wa = lambda o: (o["top"] + o["bot"]) / 2 * o["ht"]
    aN, aS, aE, aW = wa(N), wa(S_), wa(E), wa(W)
    meanTopL, meanBotL = (N["top"] + S_["top"]) / 2, (N["bot"] + S_["bot"]) / 2
    meanTopW, meanBotW = (E["top"] + W["top"]) / 2, (E["bot"] + W["bot"]) / 2
    base = meanBotL * meanBotW
    perim = N["top"] + S_["top"] + E["top"] + W["top"]
    aw = CFG["anchor_width"] if anchorW in ("", None) else n(anchorW)
    anchor = perim * aw
    walls = aN + aS + aE + aW
    sub = walls + base + anchor
    ex = CFG["extra_pct"] if extraPct in ("", None) else n(extraPct)
    withEx = sub * (1 + ex / 100)
    rt = roundTo or CFG["round_to"] or 10
    area = math.floor(withEx / rt + 0.5) * rt if rt > 0 else math.floor(withEx + 0.5)
    L, B = (meanTopL + meanBotL) / 2, (meanTopW + meanBotW) / 2
    htAvg = (N["ht"] + S_["ht"] + E["ht"] + W["ht"]) / 4
    H = n(depthOverride) if n(depthOverride) > 0 else htAvg
    return dict(walls=walls, base=base, perim=perim, anchor=anchor, sub=sub,
                with_extra=withEx, area=area, L=L, B=B, H=H, vol=L * B * H)

random.seed(11)
bad = 0
for i in range(3000):
    w = {k: {"top": round(random.uniform(20, 160), 2),
             "ht": round(random.uniform(1, 8), 2),
             "bot": round(random.uniform(10, 150), 2)}
         for k in ("north", "south", "east", "west")}
    aw = random.choice(["", 0, 1.2, 1.5, 2.0])
    ex = random.choice(["", 0, 5, 7.5])
    dep = random.choice([0, 3.5])
    rt = random.choice([0, 1, 10, 25])
    a = pond.compute_pond(w, aw, ex, dep, rt)
    b = js_compute(w, aw, ex, dep, rt)
    for k in b:
        if abs(a[k] - b[k]) > 1e-6:
            bad += 1
            if bad < 4: print("MISMATCH", k, a[k], b[k], aw, ex, rt)
print("random parity cases: 3000, mismatched fields:", bad)

# --- pricing + commission spot checks ---------------------------------
m = pond.money(4230)
assert m["total"] == 4230 * 105 and m["texel"] == 4230 * 89 and m["risha"] == 4230 * 16
assert abs(m["margin"] - 4230 * 0) < 1e-9, m["margin"]
print("money(4230):", {k: round(v, 2) for k, v in m.items()})

c = pond.commission_row(4230)
print("commission_row(4230):", {k: round(v, 2) for k, v in c.items()})
assert abs(c["commission"] - 4230 * 5.5) < 1e-9
assert abs(c["gst_amount"] - c["commission"] * 0.18) < 1e-9
assert abs(c["tds"] - c["commission"] * 0.02) < 1e-9
assert abs(c["net_receivable"] - (c["gross"] - c["tds"])) < 1e-9
print("OK" if bad == 0 else "FAILED")
