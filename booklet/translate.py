#!/usr/bin/env python3
"""First draft of a language with a language model (Gemini 3.8 Flash on OpenRouter).

  OPENROUTER_API_KEY=… python3 translate.py de fr     # these languages
  OPENROUTER_API_KEY=… python3 translate.py --all     # every EU language without a file
  python3 translate.py --all --dry-run                # estimate only, nothing sent
  OPENROUTER_API_KEY=… python3 translate.py --changed de fr   # only the strings whose English changed
  python3 translate.py --selftest                     # split / merge / shape, offline

en.json goes out in one request: the answer of a Latin-script language is about 20,000
tokens, well under the 65,536 the model can return. When the answer is cut or its keys
are wrong, the language is sent again in three parts (PARTS) and the answers are merged
in the key order of en.json. check_content.py then validates the language. The prompt is the ```text block of
TRANSLATE_PROMPT.md. A language that already has a file is skipped unless --force:
a reviewed translation is never overwritten by a machine draft.

--changed compares en.json with its version at the git ref --since (default HEAD) and sends
only the strings that differ, each with its current translation, so the rest of an existing
file stays as it is. It needs the same structure in both versions; with --all it takes
every language that has a file, so name the languages to leave reviewed ones out.

The result is a draft. A person who knows the procurement vocabulary of the country
reads the PDF before the file reaches dev (see TRANSLATING.md); the page number in
cross/items[6]/text is checked against the built PDF then.
"""
import argparse, json, os, re, subprocess, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_content import PROTECTED, LONG      # the same rules the build enforces
MODEL = "google/gemini-3.8-flash"
USD_IN, USD_OUT = 0.75e-6, 3.75e-6           # listed price per token, for the estimate only
URL = "https://openrouter.ai/api/v1/chat/completions"

# part 2 and 3 are named; part 1 is everything else (covers, how-to, clauses, table, glossary)
PARTS = [None, {"mims"}, {"quote_translations", "capability_translations"}]

LANGS = {"bg": "Bulgarian", "cs": "Czech", "da": "Danish", "de": "German", "el": "Greek",
         "es": "Spanish", "et": "Estonian", "fi": "Finnish", "fr": "French", "ga": "Irish",
         "hr": "Croatian", "hu": "Hungarian", "it": "Italian", "lt": "Lithuanian",
         "lv": "Latvian", "mt": "Maltese", "nl": "Dutch", "pl": "Polish",
         "pt": "Portuguese (Portugal)", "ro": "Romanian", "sk": "Slovak", "sl": "Slovenian",
         "sv": "Swedish"}


def split(en, parts=PARTS):
    named = set().union(*(p for p in parts if p))
    return [{k: v for k, v in en.items() if (k in p if p else k not in named)} for p in parts]


def merge(en, parts):
    flat = {k: v for p in parts for k, v in p.items()}
    return {k: flat[k] for k in en}              # key order of en.json


def shape_errors(a, b, path=""):
    """Differences in structure between the English part and its translation."""
    if type(a) is not type(b):
        return [f"{path}: {type(b).__name__} instead of {type(a).__name__}"]
    if isinstance(a, dict):
        out = [f"{path}/{k}: missing" for k in a if k not in b] + [f"{path}/{k}: extra" for k in b if k not in a]
        return out + [e for k in a if k in b for e in shape_errors(a[k], b[k], f"{path}/{k}")]
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: {len(b)} items instead of {len(a)}"]
        return [e for i, (x, y) in enumerate(zip(a, b)) for e in shape_errors(x, y, f"{path}[{i}]")]
    return [f"{path}: empty"] if isinstance(a, str) and a.strip() and not b.strip() else []


def suspects(en, tr, path=""):
    """(path, English, container, key) of every string check_content.py would object to:
    a lost MIMn or symbol, or a text far longer than the English (the model embellished)."""
    items = en.items() if isinstance(en, dict) else enumerate(en) if isinstance(en, list) else ()
    for k, e in items:
        p = f"{path}[{k}]" if isinstance(en, list) else f"{path}/{k}"
        if isinstance(e, str):
            lost = set(PROTECTED.findall(e)) - set(PROTECTED.findall(tr[k]))
            if lost or (len(e) >= 20 and len(tr[k]) > LONG * len(e)):
                yield p, e, tr, k
        else:
            yield from suspects(e, tr[k], p)


def repair(lang, en, result, key, effort):
    """One small request for the strings that lost a code or grew too long."""
    bad = list(suspects(en, result))
    if not bad:
        return 0.0
    ask_for = {p: {"english": e, "translation": c[k]} for p, e, c, k in bad}
    prompt = (prompt_for(lang) + "\nThese translations broke a rule: a code such as MIM6 or a symbol of the "
              "English is missing, a clause of the English was left out, or content was added (the text is far "
              "longer than the English). Translate each English text again, completely and with nothing added. "
              "Return one JSON object: the same keys, each value the corrected translation as a string.\n"
              + json.dumps(ask_for, ensure_ascii=False, indent=1))
    try:
        fixed, usage = ask(prompt, key, effort)
    except Exception as e:                       # noqa: BLE001  (the draft stays as it was; the validator reports it)
        print(f"  {lang} repair failed: {e}", file=sys.stderr)
        return 0.0
    for p, e, c, k in bad:
        if isinstance(fixed.get(p), str) and fixed[p].strip():
            c[k] = fixed[p]
    print(f"  {lang} repaired {len(bad)} string(s), still suspect: {len(list(suspects(en, result)))}")
    return usage.get("cost") or 0


def leaves(node, path=()):
    """(path, string) of every string in the tree."""
    items = node.items() if isinstance(node, dict) else enumerate(node) if isinstance(node, list) else ()
    for k, v in items:
        if isinstance(v, str):
            yield path + (k,), v
        else:
            yield from leaves(v, path + (k,))


def at(node, path):
    for k in path:
        node = node[k]
    return node


def update(lang, en, old, key, effort):
    """Translate again only the strings whose English differs from the old en.json."""
    before = dict(leaves(old))
    todo = [(p, e) for p, e in leaves(en) if before.get(p) != e]
    result = json.load(open(os.path.join(HERE, "content", f"{lang}.json"), encoding="utf-8"))
    if errors := shape_errors(en, result):
        print(f"  {lang}: structure differs from en.json, use --force: {'; '.join(errors[:4])}", file=sys.stderr)
        return lang, None, 0.0
    ask_for = {"/".join(map(str, p)): {"english": e, "previous_english": before.get(p, ""), "previous_translation": at(result, p)}
               for p, e in todo}
    prompt = (prompt_for(lang) + "\nThe English of these strings changed. Translate each new English text completely, "
              "with nothing added. Keep the wording and the terms of the previous translation wherever the English "
              "kept them. Return one JSON object: the same keys, each value the new translation as a string.\n"
              + json.dumps(ask_for, ensure_ascii=False, indent=1))
    try:
        fixed, usage = ask(prompt, key, effort)
    except Exception as e:                       # noqa: BLE001  (the file stays as it was)
        print(f"  {lang} failed: {e}", file=sys.stderr)
        return lang, None, 0.0
    missing = [k for k in ask_for if not (isinstance(fixed.get(k), str) and fixed[k].strip())]
    if missing:
        print(f"  {lang}: no translation for {'; '.join(missing[:4])}", file=sys.stderr)
        return lang, None, usage.get("cost") or 0
    for p, _ in todo:
        at(result, p[:-1])[p[-1]] = fixed["/".join(map(str, p))]
    return lang, result, (usage.get("cost") or 0) + repair(lang, en, result, key, effort)


def prompt_for(lang):
    md = open(os.path.join(HERE, "TRANSLATE_PROMPT.md"), encoding="utf-8").read()
    text = re.search(r"```text\n(.*?)```", md, re.S).group(1)
    return text.replace("<LANGUAGE>", LANGS[lang]).replace("<xx>", lang)


def ask(prompt, key, effort):
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 60000,
            "response_format": {"type": "json_object"}, "usage": {"include": True},
            "reasoning": {"effort": effort}}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.load(r)
    if "error" in d:
        raise RuntimeError(d["error"])
    ch = d["choices"][0]
    if ch.get("finish_reason") == "length":
        raise RuntimeError("answer cut at max_tokens")
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (ch["message"]["content"] or "").strip())
    return json.loads(text), d.get("usage", {})


def translate(lang, en, key, effort):
    """One request; three when that fails."""
    cost = 0.0
    for parts in ([None], PARTS):
        result, c = translate_parts(lang, en, key, effort, parts)
        cost += c
        if result:
            cost += repair(lang, en, result, key, effort)
            break
    return lang, result, cost


def translate_parts(lang, en, key, effort, parts):
    base, done, cost = prompt_for(lang), [], 0.0
    for n, part in enumerate(split(en, parts), 1):
        note = f"\nThis request carries part {n} of {len(parts)} of the file; the other keys are absent on purpose.\n" if len(parts) > 1 else "\n"
        if done:                                 # part 1 fixes the wording of the keywords for the rest
            terms = {k: v["term"] for k, v in done[0]["howto"]["legend"].items()}
            note += "Use these translations of the keywords, chosen in part 1: " + json.dumps(terms, ensure_ascii=False) + "\n"
        errors = None
        for attempt in (1, 2) if len(parts) > 1 else (1,):   # parts get one retry: network, broken JSON, wrong keys
            try:
                out, usage = ask(base + note + json.dumps(part, ensure_ascii=False, indent=1), key, effort)
                cost += usage.get("cost") or 0
                errors = shape_errors(part, out)
            except Exception as e:               # noqa: BLE001  (report and retry, whatever it was)
                errors = [f"{type(e).__name__}: {e}"]
            if not errors:
                break
            print(f"  {lang} part {n} attempt {attempt}: {'; '.join(errors[:4])}", file=sys.stderr)
        if errors:
            return None, cost
        done.append(out)
        print(f"  {lang} part {n}/{len(parts)} ok")
    return merge(en, done), cost


def with_page(text, n):
    """The first number inside brackets is the page: "(p. 23)", "(S. 23)", "(23. o.)"."""
    return re.sub(r"(\([^)\d]*)\d+", lambda m: m.group(1) + n, text, count=1)


def set_table_page(lang):
    """The last clause names the page of the compliance table; the model copies the English
    number. Ask Typst for the real one (translated editions are longer) and write it in."""
    typst = os.path.join(HERE, "tools", "typst")
    if not os.access(typst, os.X_OK):
        return
    r = subprocess.run([typst, "eval", "counter(page).at(<table>).first()", "--in", "main.typ", "--font-path",
                        os.path.join(HERE, "tools", "fonts"), "--input", f"lang={lang}"],
                       cwd=HERE, capture_output=True, text=True)
    if r.returncode:
        return
    path = os.path.join(HERE, "content", f"{lang}.json")
    L = json.load(open(path, encoding="utf-8"))
    clause = L["cross"]["items"][-1]
    clause["text"] = with_page(clause["text"], r.stdout.strip())
    with open(path, "w", encoding="utf-8") as f:
        json.dump(L, f, ensure_ascii=False, indent=2)
        f.write("\n")


def selftest():
    en = {"cover": {"t": "a"}, "mims": [{"x": "b"}], "back": "c", "quote_translations": {"q": "d"},
          "capability_translations": {"c": "e"}}
    parts = split(en)
    assert [list(p) for p in parts] == [["cover", "back"], ["mims"], ["quote_translations", "capability_translations"]]
    assert merge(en, reversed(parts)) == en and list(merge(en, parts)) == list(en)
    assert shape_errors(en, en) == []
    assert shape_errors(en, {**en, "back": ""}) == ["/back: empty"]
    assert shape_errors({"a": [1, 2]}, {"a": [1], "b": 0}) == ["/b: extra", "/a: 1 items instead of 2"]
    assert shape_errors({"a": {"k": "v"}}, {"a": "v"}) == ["/a: str instead of dict"]
    e = {"a": ["MIM6 lists it among its prerequisites", "No fees for the city at all."], "b": "ok → fine"}
    t = {"a": ["listet es", "Keine Gebühren für die Stadt, weder nutzer- noch volumen- noch abfragebasiert."], "b": "gut → so"}
    assert [p for p, *_ in suspects(e, t)] == ["/a[0]", "/a[1]"]
    assert list(leaves(e)) == [(("a", 0), e["a"][0]), (("a", 1), e["a"][1]), (("b",), "ok → fine")]
    assert at(e, ("a", 1)) == e["a"][1]
    assert with_page("the table (p. 23); an annex", "28") == "the table (p. 28); an annex"
    assert with_page("táblázatot (23. o.); ez", "28") == "táblázatot (28. o.); ez"
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("langs", nargs="*")
    ap.add_argument("--all", action="store_true", help="every EU language that has no file yet")
    ap.add_argument("--force", action="store_true", help="overwrite an existing language file")
    ap.add_argument("--changed", action="store_true", help="only the strings whose English differs from en.json at --since")
    ap.add_argument("--since", default="HEAD", metavar="REF", help="git ref that --changed compares with (default HEAD)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--jobs", type=int, default=4, help="languages in parallel")
    ap.add_argument("--effort", default="low", help="reasoning effort: low, medium, high")
    ap.add_argument("--max-usd", type=float, default=5.0, help="stop starting languages above this spend")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    path = lambda l: os.path.join(HERE, "content", f"{l}.json")
    en = json.load(open(path("en"), encoding="utf-8"))
    langs = list(LANGS) if a.all else a.langs
    if bad := [l for l in langs if l not in LANGS]:
        sys.exit(f"unknown language code: {' '.join(bad)} (known: {' '.join(LANGS)})")
    old = None
    if a.changed:
        show = subprocess.run(["git", "show", f"{a.since}:./content/en.json"], cwd=HERE, capture_output=True, text=True)
        if show.returncode:
            sys.exit(f"cannot read en.json at {a.since}: {show.stderr.strip()}")
        old = json.loads(show.stdout)
    skipped = [l for l in langs if os.path.exists(path(l)) != bool(a.changed) and not (a.force and not a.changed)]
    langs = [l for l in langs if l not in skipped]
    if skipped:
        print("skipped, no file yet:" if a.changed else "skipped, file exists (use --force):", " ".join(skipped))
    if not langs:
        sys.exit("nothing to translate")

    # estimate: ~3.7 characters per token of English JSON; the answer about 1.4 times the
    # input (2.6 times in Greek and Cyrillic) plus a third for reasoning tokens
    text = dict(leaves(en))
    if old is not None:
        before = dict(leaves(old))
        text = {p: e for p, e in text.items() if before.get(p) != e}
        print(f"{len(text)} changed string(s) since {a.since}")
        if not text:
            return
    tok_in = (len(json.dumps(en if old is None else list(text.values()) * 3, ensure_ascii=False)) + len(prompt_for(langs[0]))) / 3.7
    est = sum(tok_in * USD_IN + tok_in * (2.6 if l in ("bg", "el") else 1.4) * 1.33 * USD_OUT for l in langs)
    print(f"{len(langs)} language(s), one request each, model {MODEL}: about {est:.2f} USD")
    if a.dry_run:
        return
    key = os.environ.get("OPENROUTER_API_KEY") or sys.exit("OPENROUTER_API_KEY is not set")

    spent, failed = 0.0, []
    with ThreadPoolExecutor(a.jobs) as pool:
        def one(lang):
            if spent >= a.max_usd:
                return lang, None, 0.0
            return translate(lang, en, key, a.effort) if old is None else update(lang, en, old, key, a.effort)
        for lang, result, cost in pool.map(one, langs):
            spent += cost
            if result is None:
                failed.append(lang)
                continue
            with open(path(lang), "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                f.write("\n")
            print(f"wrote content/{lang}.json ({cost:.3f} USD, total {spent:.3f})")

    ok = [l for l in langs if l not in failed]
    for l in ok:
        set_table_page(l)
    py = os.path.join(HERE, "tools", "venv", "bin", "python")
    if ok and os.path.exists(py):
        subprocess.run([py, os.path.join(HERE, "check_content.py"), *ok])
    print(f"spent {spent:.3f} USD; done: {' '.join(ok) or '-'}; failed: {' '.join(failed) or '-'}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
