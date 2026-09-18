# Prompt for a machine translation

A first draft of a new language can come from a language model. Replace `<LANGUAGE>`
and `<xx>` in the prompt, paste the content of `content/en.json` under it, save the
answer as `content/<xx>.json` and run `./build.sh`. A person who knows the
procurement vocabulary of the country then reads the draft PDF; the rules that person
follows are in [TRANSLATING.md](TRANSLATING.md).

- `translate.py` does all of this with Gemini 3.8 Flash on OpenRouter: one request per
  language (three parts when the answer is cut), a repair request for strings that lost a
  code or grew too long, then the validator. `python3 translate.py de`, or `--all`;
  `--dry-run` prints the estimated cost. It needs `OPENROUTER_API_KEY`.
- By hand: `en.json` holds about 49,000 characters. It fits in one request, but the answer
  is as long: raise the output limit of the model, or the answer stops half way.
- The validator stops the build on a missing or extra key, an empty string, a lost MIM
  code or symbol, and a page that overflows.

## The prompt

```text
You translate a JSON file from English into <LANGUAGE> (<xx>).

The file is the text of a booklet for city officials: "Procurement Checklist using
the Minimal Interoperability Mechanisms (MIMs)". It tells a municipality what to put
in a tender so the city keeps its data. It follows OASC MIMs Plus 9.0. Your readers
are procurement officers and lawyers, not engineers.

OUTPUT
- Return one valid JSON document and nothing else: no commentary, no code fence.
- Keep every key, the nesting and the order of array items exactly as they are.
  Translate values only. Never translate, add, remove or rename a key.
- Leave no value empty and leave none in English, unless a rule below says
  "keep unchanged".
- Inside a value use the typographic quotation marks of your language („ “ ” « »),
  never the ASCII double quote: an unescaped one breaks the JSON.
- Translate every sentence and every clause of a value. Leave nothing out and add
  nothing: no extra examples, no explanations, no legal wording the English lacks.

KEEP UNCHANGED INSIDE THE TEXT
- MIM0, MIM1, MIM2, MIM3, MIM6, MIM7, MIM8 and requirement codes such as R1.1, C4,
  RC5.1, M1.2, "MIM1 · §3.1".
- The symbols ✓ ~ ✗ → ○ and the separator " · ".
- Version numbers and names of products, standards and organisations: MIMs Plus 9.0,
  TLS 1.3, OpenAPI, NGSI-LD, GeoJSON, DCAT-AP, ISO/IEC 27001, OASC, Living-in.EU.
- Numbers of the checklist items (0.1 … 8.4) and of the clauses (X.1 … X.7).

VOCABULARY AND TONE
- Use the public-procurement vocabulary of your country: the words a real tender,
  the procurement act and the national transposition of Directive 2014/24/EU use.
  Do the same for "contracting authority", "bidder", "award criteria",
  "selection criteria", "technical specification".
- Plain, direct sentences. Address the reader the way an official guide in your
  language does. No marketing tone.
- The booklet is international. Do not add references to national laws.

LENGTH
- Aim for the English length; up to a third longer is acceptable. Prefer the
  shorter of two correct wordings, because the page layout is fixed.
- "tearout_short": each value stays on one line, 75 characters at most.
- "nav": one or two words per value. "nav/page" is your abbreviation of "page"
  (English "p.").
- "cover/title": the full name of the booklet. " · " marks a line break on the
  cover; produce three or four lines of similar length.

NORMATIVE KEYWORDS
- Translate SHALL / MUST, MUST NOT, SHOULD, SHOULD NOT, MAY and CAN the same way in
  every requirement. Never strengthen or soften one: "should not" is not "must not".
- Write the keyword in upper case only where the English is in upper case.
- In "howto/legend", each "term" is your keyword first and the English keyword after
  it in brackets. Slovak example: "MÁ, MAJÚ (SHOULD)".

SPECIFICATION TEXT
- "quote_translations" holds every requirement of the specification and
  "capability_translations" the capability headings. Translate them closely,
  sentence by sentence; add nothing, explain nothing, drop nothing. The booklet
  prints the English original under your wording.
- "[sic]" marks a typing error in the English original. Translate the intended
  meaning and leave "[sic]" out.
- "spec_translation_note": name your language in it ("the <LANGUAGE> wording is an
  unofficial translation …").

COMPLIANCE TABLE
- The bidder answers with one letter. English uses "M / E / N": meets, meets by an
  equivalent solution, does not meet. Choose three letters that fit your language
  (Slovak uses "S / E / N") and use the same letters in "tearout/headers",
  "tearout/intro" and "example/filled_rows".
- "cross/items[6]/text" names the page of the compliance table: "(p. 23)". Keep the
  number; translate only the abbreviation of "page".

BEFORE YOU ANSWER, CHECK
1. The JSON parses and has the same keys as the input.
2. Every MIMn, every requirement code and every symbol of the input is still there.
3. Each keyword has one translation across the whole file.
4. No "tearout_short" value is longer than 75 characters.
5. The three bidder letters are identical in all three places.

INPUT (content of en.json):
```
