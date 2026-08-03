"""Roman -> Devanagari transliteration for farmer names and places.

Ported from the prototype. It is deliberately a *suggestion*: the field
stays editable, because no rule set gets every Marathi surname right.
"""

DICT = {
	"shri": "\u0936\u094d\u0930\u0940",
	"patil": "\u092a\u093e\u091f\u0940\u0932",
	"deshmukh": "\u0926\u0947\u0936\u092e\u0941\u0916",
	"pawar": "\u092a\u0935\u093e\u0930",
	"shinde": "\u0936\u093f\u0902\u0926\u0947",
	"jadhav": "\u091c\u093e\u0927\u0935",
	"more": "\u092e\u094b\u0930\u0947",
	"kale": "\u0915\u093e\u0933\u0947",
	"gaikwad": "\u0917\u093e\u092f\u0915\u0935\u093e\u0921",
	"sangamner": "\u0938\u0902\u0917\u092e\u0928\u0947\u0930",
}

CONS = {
	"kh": "\u0916", "gh": "\u0918", "ch": "\u091a", "chh": "\u091b",
	"jh": "\u091d", "th": "\u0925", "dh": "\u0927", "ph": "\u092b",
	"bh": "\u092d", "sh": "\u0936", "k": "\u0915", "g": "\u0917",
	"j": "\u091c", "t": "\u0924", "d": "\u0926", "n": "\u0928",
	"p": "\u092a", "b": "\u092c", "m": "\u092e", "y": "\u092f",
	"r": "\u0930", "l": "\u0932", "v": "\u0935", "w": "\u0935",
	"s": "\u0938", "h": "\u0939",
}

MATRA = {
	"aa": "\u093e", "ai": "\u0948", "au": "\u094c", "ee": "\u0940",
	"oo": "\u0942", "a": "", "i": "\u093f", "u": "\u0941",
	"e": "\u0947", "o": "\u094b",
}

INDEP = {
	"aa": "\u0906", "ai": "\u0910", "au": "\u0914", "ee": "\u0908",
	"oo": "\u090a", "a": "\u0905", "i": "\u0907", "u": "\u0909",
	"e": "\u090f", "o": "\u0913",
}

_C = sorted(CONS, key=len, reverse=True)
_V = sorted(MATRA, key=len, reverse=True)


def _word(w):
	low = w.lower()
	if low in DICT:
		return DICT[low]

	out, i, last_was_cons = "", 0, False
	while i < len(low):
		for c in _C:
			if low.startswith(c, i):
				out += CONS[c]
				i += len(c)
				last_was_cons = True
				break
		else:
			for v in _V:
				if low.startswith(v, i):
					out += MATRA[v] if last_was_cons else INDEP[v]
					i += len(v)
					last_was_cons = False
					break
			else:
				out += low[i]
				i += 1
				last_was_cons = False
	return out


def to_marathi(text):
	if not text:
		return ""
	return " ".join(_word(w) for w in str(text).split())
