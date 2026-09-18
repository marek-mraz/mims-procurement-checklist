"""Load one language edition: content/<lang>.json merged with the language-neutral
content/shared.json (spec URLs, requirement references) and
content/quotes.json (every requirement of every MIM, verbatim English, grouped by capability).

The language files hold only translatable text, so that is all Crowdin shows to
translators. Everything that must never change between languages lives in
shared.json and is joined back in here, in the order shared.json gives.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))


def _json(name):
    with open(os.path.join(HERE, "content", name), encoding="utf-8") as f:
        return json.load(f)


def languages():
    """Two-letter language files present in content/ (en first)."""
    langs = sorted(f[:-5] for f in os.listdir(os.path.join(HERE, "content"))
                   if len(f) == 7 and f.endswith(".json"))
    return ["en"] + [l for l in langs if l != "en"]


def load(lang):
    L, SH, Q = _json(f"{lang}.json"), _json("shared.json"), _json("quotes.json")
    D, L["sheet_url"] = SH["mims"], SH.get("sheet_url", "")
    L["urls"] = {i: d["url"] for i, d in D.items()}
    L["quotes"] = Q
    L["howto"]["legend"] = list(L["howto"]["legend"].values())
    L["glance"]["items"] = [{"id": i, **L["glance"]["items"][i]} for i in D]
    L["mims"] = [{"id": i, **L["mims"][i], "items": [{**it, "refs": r} for it, r in zip(L["mims"][i]["items"], d["refs"])]}
                 for i, d in D.items()]
    L["glossary"]["links"] = [{"name": n, "d": x} for n, x in L["glossary"]["links"].items()]
    if lang != "en":                      # translated editions say so on every specification page
        L["spec_leadin"] += " " + L["spec_translation_note"]
    if lang == "en":                      # en.json carries the English only as the Crowdin source
        L["quote_translations"] = L["capability_translations"] = {}
    return L
