# Procurement Checklist using the Minimal Interoperability Mechanisms (MIMs)

What to put in a tender so your city keeps its data: a plain-language checklist
for public procurement, built on MIMs Plus 9.0, the Minimal Interoperability
Mechanisms of Open & Agile Smart Cities (OASC). One PDF and one DOCX per language.

| Language | Title |
|---|---|
| English | Procurement Checklist using the Minimal Interoperability Mechanisms (MIMs) |
| Slovak | Kontrolný zoznam pre verejné obstarávanie pomocou minimálnych mechanizmov interoperability (MIMs) |
| Czech | Kontrolní seznam pro veřejné zakázky pomocí minimálních mechanismů interoperability (MIMs) |

## Download

| | PDF | DOCX (editable, with the compliance table) |
|---|---|---|
| English | [MIMs-latest-en.pdf](https://marek-mraz.github.io/mims-procurement-checklist/MIMs-latest-en.pdf) | [MIMs-latest-en.docx](https://marek-mraz.github.io/mims-procurement-checklist/MIMs-latest-en.docx) |
| Slovak | [MIMs-latest-sk.pdf](https://marek-mraz.github.io/mims-procurement-checklist/MIMs-latest-sk.pdf) | [MIMs-latest-sk.docx](https://marek-mraz.github.io/mims-procurement-checklist/MIMs-latest-sk.docx) |
| Czech | [MIMs-latest-cs.pdf](https://marek-mraz.github.io/mims-procurement-checklist/MIMs-latest-cs.pdf) | [MIMs-latest-cs.docx](https://marek-mraz.github.io/mims-procurement-checklist/MIMs-latest-cs.docx) |

- All downloads, with the work-in-progress draft: <https://marek-mraz.github.io/mims-procurement-checklist/>
- Numbered editions (`MIMs-9.0.N-<lang>.pdf`): <https://github.com/marek-mraz/mims-procurement-checklist/releases>
- Source and issues: <https://github.com/marek-mraz/mims-procurement-checklist>
- The specification: <https://mims.oascities.org>

## Build

    ./build.sh

The script downloads Typst and the Inter font on first run, validates every
language, and writes `MIMs-draft-<lang>.pdf` and `.docx` next to itself. GitHub
runs the same script.

## Translating

Translators work in Crowdin on the English master and never touch the layout. The
flow, the Crowdin setup, the rules for translators and the validator checks are in
[`booklet/TRANSLATING.md`](booklet/TRANSLATING.md).

## Where things are

| Path | What |
|---|---|
| `booklet/content/en.json` | English master, the only file translators see |
| `booklet/content/<lang>.json` | one file per language (Crowdin writes these) |
| `booklet/content/quotes.json` | every requirement of every MIM, verbatim |
| `booklet/content/shared.json` | spec links and requirement references |
| `booklet/style.typ` | all formatting, commented block by block |
| `booklet/readable/` | the same booklet with the text inline, generated |
| `booklet/TRANSLATING.md` | rules for translators and what the validator checks |

## Branches and editions

| Where | Result |
|---|---|
| any branch, pull request | draft build, files attached to the workflow run |
| `dev` | draft on GitHub Pages: `MIMs-draft-<lang>.pdf` |
| `main` | next edition number, tag `v9.0.N`, GitHub release with `MIMs-9.0.N-<lang>.pdf`; GitHub Pages: `MIMs-latest-<lang>.pdf` |
| `release/<n>` | editions of an older MIMs Plus line: GitHub release only, never on Pages |

Work on `dev`. Merging a pull request from `dev` into `main` publishes the next
edition: the number is the count of `v9.0.*` tags plus one, so nobody edits it by
hand. `booklet/VERSION` holds the base (`9.0`, the MIMs Plus release).

## Setting up the GitHub repository

Name: `mims-procurement-checklist`

About, description:

    Procurement Checklist using the Minimal Interoperability Mechanisms (MIMs): what to put in a tender so your city keeps its data. Built on OASC MIMs Plus 9.0. PDF and DOCX in English, Slovak and Czech.

About, website: `https://marek-mraz.github.io/mims-procurement-checklist/`

Topics: `mims` `oasc` `interoperability` `public-procurement` `smart-cities`
`open-data` `vendor-lock-in` `checklist` `typst` `living-in-eu`

Settings, once:

1. Create the branches `main` and `dev`. Protect `main`: changes reach it only
   through a pull request from `dev`.
2. Settings → Actions → General → Workflow permissions: "Read and write". The
   workflow creates tags and releases and writes the branch `gh-pages`.
3. Settings → Pages → Source: "GitHub Actions". Settings → Environments →
   `github-pages` → Deployment branches: add `dev` next to `main`. The workflow
   stores the files in the branch `gh-pages` and deploys that branch itself.
4. Connect Crowdin to the branch `dev` (`crowdin.yml` is in the repository root).
5. Put the address of the editable compliance table (the DOCX on Pages) into
   `sheet_url` in `booklet/content/shared.json`; the booklet then prints it under
   the table.

## Licence

Author: Marek Mráz. Booklet text, translations, templates and scripts: CC BY 4.0,
see `LICENSE`. The requirements quoted from the specification are © Open & Agile
Smart Cities (OASC).
