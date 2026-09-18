# Translating the booklet

The English master is `content/en.json`. One file per language sits next to it:
`content/de.json`, `content/fr.json`, … Crowdin creates and updates them.

## From English to a published translation

1. Crowdin reads `content/en.json` from the branch `dev`. The file holds translatable
   text only.
2. You translate in Crowdin. Crowdin pushes `content/<xx>.json` to its own branch and
   opens a pull request into `dev`. The GitHub workflow validates the file and attaches
   the built PDF and DOCX to its run.
3. After the merge into `dev` the draft is on GitHub Pages as `MIMs-draft-<xx>.pdf`.
   Read your language there before anyone publishes it.
4. A pull request from `dev` to `main` publishes the next edition as
   `MIMs-latest-<xx>.pdf`.

Crowdin exports a string you have not translated yet in English, so a half-done
language still builds. The validator lists those strings as a warning.

Two files never reach Crowdin, because they are the same in every language:
`content/shared.json` (web addresses, requirement references such as `MIM0 R1.1`, tool
names) and `content/quotes.json` (the verbatim English requirements). A translated
edition prints your wording above the English original.

## Setting up Crowdin (project owner)

- The configuration is `crowdin.yml` in the repository root. Connect the Crowdin
  project to the branch `dev`.
- Choose the target languages in the Crowdin project, from the table under "Languages".
- Pick "Portuguese" (pt-PT). Brazilian Portuguese would export to the same `pt.json`.
- The booklet font, Inter, covers Latin, Greek and Cyrillic. Add a font to `style.typ`
  before you add a language in another script; the validator reports every character
  the font cannot draw.
- The Crowdin CLI takes its credentials from the environment: `CROWDIN_PROJECT_ID` and
  `CROWDIN_PERSONAL_TOKEN`. Keep them out of the repository.

## Languages

The 24 official languages of the European Union. The code is the file name and the last
part of the PDF name (`MIMs-latest-de.pdf`). Inter draws all three scripts.

| Code | Language | Own name | Script | File | State |
|---|---|---|---|---|---|
| `bg` | Bulgarian | български | Cyrillic | `content/bg.json` | machine draft |
| `cs` | Czech | čeština | Latin | `content/cs.json` | published |
| `da` | Danish | dansk | Latin | `content/da.json` | machine draft |
| `de` | German | Deutsch | Latin | `content/de.json` | machine draft |
| `el` | Greek | ελληνικά | Greek | `content/el.json` | machine draft |
| `en` | English | English | Latin | `content/en.json` | master |
| `es` | Spanish | español | Latin | `content/es.json` | machine draft |
| `et` | Estonian | eesti | Latin | `content/et.json` | machine draft |
| `fi` | Finnish | suomi | Latin | `content/fi.json` | machine draft |
| `fr` | French | français | Latin | `content/fr.json` | machine draft |
| `ga` | Irish | Gaeilge | Latin | `content/ga.json` | machine draft |
| `hr` | Croatian | hrvatski | Latin | `content/hr.json` | machine draft |
| `hu` | Hungarian | magyar | Latin | `content/hu.json` | machine draft |
| `it` | Italian | italiano | Latin | `content/it.json` | machine draft |
| `lt` | Lithuanian | lietuvių | Latin | `content/lt.json` | machine draft |
| `lv` | Latvian | latviešu | Latin | `content/lv.json` | machine draft |
| `mt` | Maltese | Malti | Latin | `content/mt.json` | machine draft |
| `nl` | Dutch | Nederlands | Latin | `content/nl.json` | machine draft |
| `pl` | Polish | polski | Latin | `content/pl.json` | machine draft |
| `pt` | Portuguese (pt-PT) | português | Latin | `content/pt.json` | machine draft |
| `ro` | Romanian | română | Latin | `content/ro.json` | machine draft |
| `sk` | Slovak | slovenčina | Latin | `content/sk.json` | published |
| `sl` | Slovenian | slovenščina | Latin | `content/sl.json` | machine draft |
| `sv` | Swedish | svenska | Latin | `content/sv.json` | machine draft |

A language outside this list works the same way as long as its two-letter code is free
and the font draws its script. "machine draft" is the output of `translate.py`, not yet read by
a person who knows the procurement vocabulary of the country; set "published" after that reading.

## Rules for translators

- Translate the text. Keep these exactly as they are: `MIM0` … `MIM8`, the
  symbols `✓ ~ ✗ →`, version numbers (`MIMs Plus 9.0`, `TLS 1.3`), product and
  standard names (OpenAPI, NGSI-LD, GeoJSON).
- Use your country's public-procurement vocabulary, the words a tender uses.
- Length: aim for the English length. Up to a third longer is fine. The short
  names in the compliance table (`tearout_short`) must stay on one line: 75
  characters at most.
- `cover/title` is the full name of the booklet. " · " marks where the lines break on
  the cover; keep three or four balanced lines.
- `nav` holds the short section names of the footer strip on every page. Keep
  each to one or two words; `nav/page` is your abbreviation for "page" ("p.", "s.").
- The compliance table lets the bidder answer with one letter (`tearout/headers`,
  "M / E / N": meets, meets by an equivalent, does not meet). Pick the letters of
  your language and use the same ones in `tearout/intro` and `example/filled_rows`.
- The clause that sends the bidder to the compliance table names its page
  (`cross/items[6]/text`, "(p. 23)"). Translated editions are longer, so the number
  differs; the validator names the right one.
- `quote_translations` are the specification requirements (all of them, every
  MIM) and `capability_translations` the capability headings above them.
  Translate them closely; the English original is printed under them.
- `spec_translation_note` is printed on every specification page of a translated
  edition (never in English): name your language in it ("the Slovak wording is an
  unofficial translation …").
- Translate the keywords SHALL / SHOULD / MAY the same way in every requirement
  (sk: MUSÍ/MUSIA, MÁ/MAJÚ, MÔŽE/MÔŽU), upper-case only where the English is
  upper-case. Never strengthen or soften one ("should not" is not "must not").
  In `howto/legend`, put your words for the keyword first in `term`, the English
  keyword after them in brackets: "MUSÍ, MUSIA (SHALL / MUST)".
- Requirement references and web addresses are not in your file.
  They live in `content/shared.json` and are the same in every language.

## What happens to a long translation

Every fixed page is wrapped in `fit-page` (see `style.typ`). A page that gets too
tall is zoomed out in 2 % steps, down to 76 %, so it always stays one page and
the spreads stay aligned. A page with four times the English text still fits at
about 90 %.

## Validation

    tools/venv/bin/python check_content.py        # all languages
    tools/venv/bin/python check_content.py de fr  # some

| Check | Result |
|---|---|
| A key is missing or extra compared with `en.json` | error |
| One of the seven MIMs is missing anywhere | error |
| An empty string | error |
| `MIM0`…`MIM8` or a symbol `✓ ~ ✗ →` lost | error |
| A character the font cannot draw | error |
| A page overflows even at 76 % zoom | error |
| The clause names another page than the one the compliance table is on | error |
| A page had to be zoomed out | warning |
| A string is more than 1.6 times the English length | warning |
| A one-line spot is over its character budget | warning |
| Longer strings still identical to English | warning |

`build.sh` runs the validator first and stops on an error. Warnings never stop it.

## Adding a language by hand

Copy `en.json` to `<xx>.json`, translate, run `./build.sh`. Nothing else to
register: the build picks up every two-letter file in `content/`.

For a first draft from a language model, use the prompt in
[TRANSLATE_PROMPT.md](TRANSLATE_PROMPT.md).
