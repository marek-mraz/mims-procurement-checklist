# Translating the booklet

The English master is `content/en.json`. One file per language sits next to it:
`content/de.json`, `content/fr.json`, … Crowdin creates and updates them.

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
  (`cross/items[6]/text`, "(p. 23)"). Check the number in your built PDF.
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
| A page had to be zoomed out | warning |
| A string is more than 1.6 times the English length | warning |
| A one-line spot is over its character budget | warning |
| Longer strings still identical to English | warning |

`build.sh` runs the validator first and stops on an error. Warnings never stop it.

## Adding a language by hand

Copy `en.json` to `<xx>.json`, translate, run `./build.sh`. Nothing else to
register: the build picks up every two-letter file in `content/`.
