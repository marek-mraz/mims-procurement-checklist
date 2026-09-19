#!/usr/bin/env python3
"""Second reading of a translation by a language model: proposals only, nothing is changed.

  OPENROUTER_API_KEY=… tools/venv/bin/python review_translation.py sk de   # these languages
  OPENROUTER_API_KEY=… tools/venv/bin/python review_translation.py --all   # every language built
  tools/venv/bin/python review_translation.py --all --text-only            # only write the markdown

The built PDFs are the input (../MIMs-draft-<xx>.pdf, so run ./build.sh first): the model
reads what the reader reads, page by page. Each PDF becomes ../review/<xx>/<xx>.md next to
../review/<xx>/en.md; both go to Gemini 3.8 Flash in one request. The answer lands in
../review/<xx>/findings.md (and .json): page, current text, proposed text, reason, and the
key in content/<xx>.json when the current text is found there word for word.

  tools/venv/bin/python review_translation.py --apply sk 1 4 12     # after a person has decided

writes the proposals with these numbers into content/sk.json (edit "proposed" in
findings.json first to apply a different wording) and marks them "applied" there.
"""
import argparse, json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from translate import LANGS, ask, leaves      # the same model, request and language names

TOP, BOTTOM = 46, 812     # pt: above is the draft fit label, below the navigation strip

PROMPT = """You are a native speaker of <LANGUAGE> who writes public procurement documents for a
municipality in a country where <LANGUAGE> is official. Below are two markdown files made from PDFs:
the English original of a booklet for procurement officers, and its <LANGUAGE> translation.

Read the translation as its reader would and compare it with the English. Report every place where
the translation
- says something else than the English, leaves a clause out or adds one,
- makes no sense or is hard to understand for a procurement officer who is not an engineer,
- uses a term that procurement law or IT practice in <LANGUAGE> does not use (give the usual term),
- names the same thing in two ways (a clause, a document, a role) in different places,
- reads as a word-for-word machine translation where a natural sentence exists,
- sounds colloquial, chatty or like marketing: the booklet is an official publication for civil
  servants, so propose the professional, formal register of public administration in <LANGUAGE>.

Do not report: English text kept on purpose (verbatim quotes of the specification printed under
their translation, names of standards, codes such as MIM0 R1.1, SHALL / SHOULD), page numbers,
line breaks and hyphenation of the PDF, the order of table cells (a table of the PDF arrives as one
cell per paragraph), matters of taste. English IT terms that practitioners in
<LANGUAGE> use in English are correct as they stand and are never to be translated or replaced:
fork, webhook, API, cache, token, endpoint, open source, log ("fork" is never "branch"). Report
the opposite instead: an invented native word where practitioners say the English term. When a term is wrong in many places,
report it once and say "everywhere". At most 40 findings, the most serious first.

Return one JSON object:
{"summary": "three sentences on the overall quality, in English",
 "findings": [{"page": <page of the translation>, "severity": "meaning" | "term" | "consistency" | "style",
   "current": "<the text exactly as printed in the translation, one sentence or phrase>",
   "proposed": "<the replacement in <LANGUAGE>>",
   "reason": "<one sentence in English>"}]}
"""


DAILY_LIMIT = float(os.environ.get("BIGSHOT_DAILY_LIMIT", "5"))     # USD per day, the same cap as the bigshot tools


def spent_today(key):
    req = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return float(json.load(r)["data"].get("usage_daily") or 0)
    except Exception:                            # noqa: BLE001  (no answer = do not spend)
        return DAILY_LIMIT


def markdown(pdf, title):
    """One heading per page, text of the page body in reading order, paragraphs unwrapped."""
    out = [f"# {title}"]
    for n, page in enumerate(pymupdf.open(pdf), 1):
        clip = pymupdf.Rect(0, TOP, page.rect.width, BOTTOM)
        # no sort: Typst writes the text in the order of the source, which is the reading order;
        # sorting by position mixes the columns of the glossary and of the tables
        blocks = [b[4].strip() for b in page.get_text("blocks", clip=clip) if b[6] == 0 and b[4].strip()]
        out.append(f"## Page {n}\n\n" + "\n\n".join(
            " ".join(b.replace("\u00a0", " ").split()).replace("\u00ad ", "").replace("\u00ad", "") for b in blocks))
    return "\n\n".join(out) + "\n"


def review(lang, key, effort):
    folder = os.path.join(ROOT, "review", lang)
    os.makedirs(folder, exist_ok=True)
    texts = {}
    for l in ("en", lang):
        texts[l] = markdown(os.path.join(ROOT, f"MIMs-draft-{l}.pdf"), f"{'English' if l == 'en' else LANGS[l]} booklet")
        with open(os.path.join(folder, f"{l}.md"), "w", encoding="utf-8") as f:
            f.write(texts[l])
    if key is None:
        return lang, None, 0.0
    prompt = PROMPT.replace("<LANGUAGE>", LANGS[lang]) + "\n\n" + texts["en"] + "\n\n" + texts[lang]
    try:
        answer, usage = ask(prompt, key, effort)
        findings = answer["findings"]
    except Exception as e:                       # noqa: BLE001  (report the language as failed, go on with the rest)
        print(f"  {lang} failed: {type(e).__name__}: {e}", file=sys.stderr)
        return lang, None, 0.0

    norm = lambda s: " ".join(s.replace("\u00a0", " ").split())
    strings = [("/".join(map(str, p)), norm(s)) for p, s in
               leaves(json.load(open(os.path.join(HERE, "content", f"{lang}.json"), encoding="utf-8")))]
    for f in findings:                           # where to make the change, when the text is found as printed
        cur = norm(str(f.get("current", "")))
        f["keys"] = [p for p, s in strings if cur and cur in s][:4]
    with open(os.path.join(folder, "findings.json"), "w", encoding="utf-8") as f:
        json.dump(answer, f, ensure_ascii=False, indent=2)
    md = [f"# {LANGS[lang]}: proposed changes to the translation", "",
          "Proposals of a language model (Gemini 3.8 Flash). Nothing was changed; a person decides.", "",
          answer.get("summary", ""), ""]
    for n, f in enumerate(findings, 1):
        md += [f"## {n}. p. {f.get('page', '?')} · {f.get('severity', '')}", "",
               f"- current: {f.get('current', '')}", f"- proposed: {f.get('proposed', '')}",
               f"- reason: {f.get('reason', '')}",
               f"- key: {', '.join(f'`{k}`' for k in f['keys']) or 'not found word for word in the JSON'}", ""]
    with open(os.path.join(folder, "findings.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    return lang, len(findings), usage.get("cost") or 0


def apply(lang, numbers):
    """Put the chosen proposals into content/<lang>.json, wherever the current text stands."""
    fpath = os.path.join(ROOT, "review", lang, "findings.json")
    cpath = os.path.join(HERE, "content", f"{lang}.json")
    answer = json.load(open(fpath, encoding="utf-8"))
    raw = open(cpath, encoding="utf-8").read()
    content, nb = json.loads(raw), "\u00a0" in raw
    failed = []
    for n in numbers:
        f = answer["findings"][n - 1]
        # the PDF prints the item number or the requirement code before the text and puts
        # quotation marks around a requirement; the JSON string has neither
        core = lambda t: re.sub(r"^(?:[0-8X]\.\d|(?:R|RC|C|M)\d+(?:\.\d+)?[a-z]?)\s+", "", str(t).strip()).strip(" «»„“”\"")
        words = core(f["current"]).replace("\u00a0", " ").split()
        pattern = re.compile(r"[ \u00a0]+".join(map(re.escape, words)))
        new = core(f["proposed"])
        if nb:        # this language keeps a one-letter word on the line of the next word
            new = re.sub(r"(?<![\w.])([aAiIkKoOsSuUvVzZ]|s\.) ", "\\1\u00a0", new)
        hits = 0
        for path, text in list(leaves(content)):
            if words and pattern.search(text):
                node = content
                for k in path[:-1]:
                    node = node[k]
                node[path[-1]] = pattern.sub(lambda m: new, text)
                hits += 1
        f["decision"] = "applied" if hits else f.get("decision", "")
        if not hits:
            failed.append(n)
        print(f"{lang} {n}: {hits} string(s)")
    for path, out in ((cpath, content), (fpath, answer)):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    sys.exit(f"not found in content/{lang}.json: {failed}" if failed else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("langs", nargs="*")
    ap.add_argument("--all", action="store_true", help="every language with a built PDF")
    ap.add_argument("--text-only", action="store_true", help="write the markdown files, send nothing")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--effort", default="medium", help="reasoning effort: low, medium, high")
    ap.add_argument("--max-usd", type=float, default=4.0, help="stop starting languages above this spend")
    ap.add_argument("--apply", action="store_true", help="LANG N N …: write these proposals into content/LANG.json")
    a = ap.parse_args()
    if a.apply:
        return apply(a.langs[0], [int(n) for n in a.langs[1:]])
    langs = [l for l in LANGS if os.path.exists(os.path.join(ROOT, f"MIMs-draft-{l}.pdf"))] if a.all else a.langs
    if bad := [l for l in langs if l not in LANGS]:
        sys.exit(f"unknown language code: {' '.join(bad)}")
    key = None if a.text_only else os.environ.get("OPENROUTER_API_KEY") or sys.exit("OPENROUTER_API_KEY is not set")
    spent = 0.0
    with ThreadPoolExecutor(a.jobs) as pool:
        def one(lang):
            # the key's own count of today: it also sees requests of a run that was stopped
            # (a stopped run still pays for the requests in flight) and of other tools
            if key and spent_today(key) + 0.3 >= DAILY_LIMIT:
                print(f"  {lang} not started: the daily limit of {DAILY_LIMIT} USD is reached", file=sys.stderr)
                return lang, None, 0.0
            return (lang, None, 0.0) if spent >= a.max_usd else review(lang, key, a.effort)
        for lang, n, cost in pool.map(one, langs):
            spent += cost
            print(f"{lang}: " + ("markdown written" if key is None else "FAILED" if n is None else f"{n} finding(s), {cost:.3f} USD"))
    print(f"spent {spent:.3f} USD; results in review/<xx>/")


if __name__ == "__main__":
    main()
