#!/usr/bin/env python3
"""Validate the booklet content before it is printed.

  python3 check_content.py            # every language in content/
  python3 check_content.py de fr      # only these

Two passes per language:
  TEXT    the language file against the English master: same keys, all seven MIMs
          in every place they must appear, nothing empty, protected symbols kept,
          no characters the font cannot draw, strings that grew suspiciously long.
  LAYOUT  compiles the booklet and asks Typst how each fixed page went: a page
          that had to be zoomed out is a warning, a page that still overflows at
          the smallest zoom is an error (shorten that text).

Exit code 1 if any language has an error. Warnings never fail the build.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TYPST = os.path.join(HERE, "tools", "typst")
FONTS = os.path.join(HERE, "tools", "fonts")
MIMS = ["MIM0", "MIM1", "MIM2", "MIM3", "MIM6", "MIM7", "MIM8"]   # MIMs Plus 9.0
PROTECTED = re.compile(r"MIM\d|[✓✗~→]")     # must survive translation unchanged
KEYWORD = re.compile(r"\b(SHALL|MUST|SHOULD|MAY|CAN)\b")   # a normative keyword of the English spec text
LONG = 1.6                                  # translation / English length, above = warn
ONE_LINE = {"tearout_short": 75, "tearout/headers": 24, "cover/title": 110}


def jload(name):
    with open(os.path.join(HERE, "content", name), encoding="utf-8") as f:
        return json.load(f)


def leaves(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, f"{p}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f"{p}[{i}]")
    else:
        yield p.lstrip("/"), o


def font_has():
    """Returns has(ch) for the booklet font, or None when pymupdf is not installed."""
    try:
        import pymupdf
    except ImportError:
        return None
    faces = [pymupdf.Font(fontfile=os.path.join(FONTS, f)) for f in ("Inter-Regular.ttf",)]
    return lambda ch: any(f.has_glyph(ord(ch)) for f in faces)


def unquoted_refs(shared, qids):
    """Every requirement a checklist item points to must be printed on the spec page."""
    err = []
    for m, d in shared.items():
        for ref in d["refs"]:
            ref = re.sub(r"(RC?)(\d)\.(\d)–\1\2\.(\d)",     # RC4.1–RC4.3 -> each id
                         lambda x: ", ".join(f"{x[1]}{x[2]}.{i}" for i in range(int(x[3]), int(x[4]) + 1)), ref)
            for rid in re.findall(r"\b(?:RC?\d\.\d[ab]?|M\d(?:\.\d)?|C\d)\b", ref):
                if f"{m} · {rid}" not in qids:
                    err.append(f"shared.json refers to {m} {rid}, but quotes.json has no such requirement")
    return err


def check_text(lang, en, shared, quotes, has):
    err, warn = [], []
    L = jload(f"{lang}.json")
    E, T = dict(leaves(en)), dict(leaves(L))

    for p in sorted(set(E) - set(T)):
        err.append(f"missing: {p}")
    for p in sorted(set(T) - set(E)):
        err.append(f"not in the English master: {p}")

    # all seven MIMs, everywhere they must be
    qids = [q["id"] for m in MIMS for c in quotes.get(m, []) for q in c["quotes"]]
    cids = [c["cap"] for m in MIMS for c in quotes.get(m, [])]
    for where, got in (("shared.json mims", list(shared)), ("quotes.json", list(quotes)),
                       ("mims", list(L.get("mims", {}))),
                       ("glance/items", list(L.get("glance", {}).get("items", {}))),
                       ("tearout_short", [k for k in L.get("tearout_short", {}) if k != "CROSS"])):
        if sorted(got) != MIMS:
            err.append(f"{where}: expected {MIMS}, found {sorted(got)}")
    for m in MIMS:
        n = len(shared.get(m, {}).get("refs", []))
        for where, got in ((f"mims/{m}/items", len(L.get("mims", {}).get(m, {}).get("items", []))),
                           (f"tearout_short/{m}", len(L.get("tearout_short", {}).get(m, [])))):
            if got != n:
                err.append(f"{where}: {got} entries, shared.json has {n} requirement refs")
    # block X of the compliance table = the first clauses (contract conditions a bidder accepts);
    # the clauses after them are rules of procedure and have no row
    if len(L.get("tearout_short", {}).get("CROSS", [])) > len(L.get("cross", {}).get("items", [])):
        err.append("tearout_short/CROSS has more rows than cross/items has clauses")
    miss = sorted(set(qids) - set(L.get("quote_translations", {})))
    if miss:
        err.append(f"quote_translations missing: {', '.join(miss)}")
    miss = sorted(set(cids) - set(L.get("capability_translations", {})))
    if miss:
        err.append(f"capability_translations missing: {', '.join(miss)}")
    if lang == "en":
        err += unquoted_refs(shared, set(qids) | set(cids))
        # en.json repeats the verbatim spec text only as the Crowdin source: it must not drift
        src = {q["id"]: q["en"] for m in MIMS for c in quotes.get(m, []) for q in c["quotes"]}
        src.update({c["cap"]: c["title"] for m in MIMS for c in quotes.get(m, [])})
        both = {**L.get("quote_translations", {}), **L.get("capability_translations", {})}
        err += [f"en.json differs from quotes.json (the verbatim spec text): {i}" for i, t in src.items() if both.get(i) != t]

    # capitals carry the meaning of a keyword (see howto/note): a requirement that writes
    # "should" in lower case must not get the capital keyword of the legend, and the reverse
    if lang != "en":
        kw = {w for v in L.get("howto", {}).get("legend", {}).values()
              for w in re.findall(r"[^\W\d_]{2,}", v.get("term", "").split("(")[0]) if w.isupper()}
        has_kw = lambda t: any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", t) for w in kw)
        EQ, LQ = en.get("quote_translations", {}), L.get("quote_translations", {})
        up = [i for i, t in LQ.items() if i in EQ and has_kw(t) and not KEYWORD.search(EQ[i])]
        caps = lambda t: {w for w in re.findall(r"[^\W\d_]{3,}", t) if w.isupper()}      # an inflected keyword counts too
        low = [i for i, t in LQ.items() if i in EQ and KEYWORD.search(EQ[i]) and not has_kw(t) and not caps(t) - caps(EQ[i])]
        if up:
            warn.append(f"keyword in capitals where the English has lower case: {', '.join(up[:6])}{' …' if len(up) > 6 else ''}")
        if low:
            warn.append(f"no capital keyword where the English has one: {', '.join(low[:6])}{' …' if len(low) > 6 else ''}")

    same, tofu = 0, {}
    for p, t in T.items():
        if not isinstance(t, str) or p not in E:
            continue
        e = E[p]
        if not t.strip():
            err.append(f"empty: {p}")
            continue
        for ch in t:
            if has and not ch.isspace() and not has(ch):
                tofu.setdefault(ch, p)
        if lang == "en":
            continue
        lost = sorted(set(PROTECTED.findall(e)) - set(PROTECTED.findall(t)))
        if lost:
            err.append(f"lost {' '.join(lost)} in: {p}")
        if t == e and len(e) > 25:
            same += 1
        if len(e) > 40 and len(t) > LONG * len(e):
            warn.append(f"{len(t) / len(e):.1f}x the English length: {p}")
        for key, limit in ONE_LINE.items():
            if p.startswith(key) and len(t) > limit:
                warn.append(f"{len(t)} chars, this spot holds about {limit}: {p}")
    for ch, p in tofu.items():
        err.append(f"font has no glyph for {ch!r} (U+{ord(ch):04X}), first seen in: {p}")
    if same:
        warn.append(f"{same} longer strings are still identical to English (untranslated?)")
    return err, warn


def check_layout(lang):
    err, warn = [], []
    if not os.access(TYPST, os.X_OK):
        return err, ["layout not checked: tools/typst missing (run build.sh once)"]
    expr = '(fit: query(<fit>).map(it => it.value), table: counter(page).at(<table>).first())'
    r = subprocess.run([TYPST, "eval", expr, "--in", "main.typ",
                        "--font-path", FONTS, "--input", f"lang={lang}"],
                       cwd=HERE, capture_output=True, text=True)
    if r.returncode:
        return [f"typst cannot compile this language:\n{r.stderr.strip()}"], warn
    out = json.loads(r.stdout)
    # the clause that sends the bidder to the compliance table prints its page number
    clause = jload(f"{lang}.json")["cross"]["items"][-1]["text"]
    if str(out["table"]) not in re.findall(r"\d+", clause):
        err.append(f"cross/items[-1]/text names page {' '.join(re.findall(r'[0-9]+', clause)) or '?'}, "
                   f"the compliance table is on page {out['table']}")
    for page in out["fit"]:
        if page["overflow"]:
            err.append(f"page '{page['page']}' overflows even at {page['zoom']} % zoom: shorten its text")
        elif page.get("flows"):
            warn.append(f"page '{page['page']}' runs on to a second page")
        elif page["zoom"] < 100:
            warn.append(f"page '{page['page']}' zoomed out to {page['zoom']} % to fit")
    return err, warn


def main():
    langs = sys.argv[1:] or sorted(f[:-5] for f in os.listdir(os.path.join(HERE, "content"))
                                   if re.fullmatch(r"[a-z]{2}\.json", f))
    en, shared, quotes, has = jload("en.json"), jload("shared.json")["mims"], jload("quotes.json"), font_has()
    if has is None:
        print("note: pymupdf not installed, glyph coverage not checked")
    failed = False
    for lang in langs:
        err, warn = check_text(lang, en, shared, quotes, has)
        if not err:                      # a broken file would only produce noise here
            e2, w2 = check_layout(lang)
            err, warn = err + e2, warn + w2
        print(f"{lang}: {'FAIL' if err else 'ok'}"
              + (f", {len(err)} errors" if err else "") + (f", {len(warn)} warnings" if warn else ""))
        for m in err:
            print(f"   ERROR  {m}")
        for m in warn:
            print(f"   warn   {m}")
        failed |= bool(err)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
