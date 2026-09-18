// MIMs procurement checklist booklet, built straight from the content JSON.
//   typst compile --font-path tools/fonts --input lang=cs main.typ out.pdf
// All formatting is in style.typ. This file only walks the JSON in page order.
// The same booklet with the text written inline: readable/booklet-<lang>.typ.
#import "style.typ": *

#let lang = sys.inputs.at("lang", default: "en")
#let L = json("content/" + lang + ".json")     // translatable text only (Crowdin)
#let S = json("content/shared.json")
#let D = S.mims      // per MIM: url, refs (never translated)
#let Q = json("content/quotes.json")           // every requirement, verbatim English, by capability

// non-English editions print the translation beside the English original
#let tr(key, id) = if lang != "en" { L.at(key, default: (:)).at(id, default: none) }
#let short(id) = id.split(" · ").last()        // "MIM0 · R1.1" -> "R1.1"

// one record per MIM, in the order of shared.json: text from L, the rest from D
#let mims = D.pairs().map(((id, d)) => (
  id: id, ..d, ..L.mims.at(id),
  items: L.mims.at(id).items.enumerate().map(((i, it)) => (..it, refs: d.refs.at(i)))))

#show: booklet.with(title: L.cover.title, lang: lang, nav: L.nav, mims: D.keys())

// "How to use" steps 2 to 4 point at the pages they need
#let step-links = ((), ("clauses", "example"), ("table",), ("table",))

// ───── cover ─────
#cover(title: L.cover.title, subtitle: L.cover.subtitle,
  tagline: L.cover.tagline, footer: L.cover.footer, author: L.back.author)

// ───── why this booklet ─────
#fit-page("why", {
  band(L.why.title)
  for p in L.why.paras { lead(p) }
  pull-quote(L.why.quote.text)
  policy-box(L.why.policy.title, L.why.policy.intro, note: L.why.policy.note,
    ..L.why.policy.items)
})
#pagebreak()

// ───── how to use ─────
#fit-page("howto", {
  band(L.howto.title)
  steps(..L.howto.steps.enumerate().map(((i, s)) =>
    step(s.name, s.text, links: step-links.at(i, default: ()).map(k => (k, L.nav.at(k))))))
  legend(L.howto.legend_title, note: L.howto.legend_note, ..L.howto.legend.values().map(e => entry(e.term, e.text)))
  note(L.howto.note)
})
#pagebreak()

// ───── the seven MIMs at a glance ─────
#fit-page("glance", {
  band(L.glance.title, id: "glance")
  intro(L.glance.intro)
  glance(note: L.glance.numbering_note, ..D.pairs().map(((id, d)) => {
    let g = L.glance.items.at(id)
    card(id, g.name, g.q, g.d, d.url)
  }))
  tools(L.glance.tools_title, ..L.glance.tools.pairs().map(((k, t)) => tool(k, t.name, t.q, t.d)))
  menu-line(("glossary", L.glossary.title), ("more", L.glossary.more_title))
})
#pagebreak()

// ───── one spread per MIM: checklist left, specification right ─────
#for m in mims {
  fit-page(m.id + " checklist", {
    mim-page(id: m.id, name: m.name, question: m.question, url: m.url, intro: m.intro, list: L.nav.list)
    for (i, it) in m.items.enumerate() {
      item(it.text, why: it.why, refs: it.refs, num: m.id.slice(3) + "." + str(i + 1), label: it.at("label", default: none))
    }
    panels(why: (L.why_title, m.why_panel), flags: (L.flags_title, m.red_flags))
  })
  pagebreak()

  fit-page(m.id + " specification", floor: 92, flow: true, {
    spec-page(id: m.id, title: L.spec_title, leadin: L.spec_leadin + if lang != "en" { " " + L.spec_translation_note }, back: L.nav.back)
    spec-list(mim: m.id, ..Q.at(m.id).map(c => (
      capability(short(c.cap), c.title, tr: tr("capability_translations", c.cap), sub: c.at("sub", default: false)),
      ..c.quotes.map(q => req(short(q.id), en: q.en, tr: tr("quote_translations", q.id),
        note: L.quote_notes.at(q.id, default: none))))).flatten())
    spec-link(L.spec_link_label, m.url)
  })
  pagebreak()
}

// ───── cross-cutting contract clauses ─────
#fit-page("clauses", {
  band(L.cross.title, sub: L.cross.subtitle, id: "clauses")
  intro(L.cross.intro, size: 9.8pt)
  clauses(..L.cross.items)
})
#pagebreak()

// ───── worked example: what goes into which tender document ─────
#fit-page("example", {
  let x = L.example
  band(x.title, id: "example")
  intro(x.scenario, size: 9.8pt)
  text(size: 10pt, weight: "bold", fill: eu-blue, x.table_title)
  v(4pt)
  doc-table(x.table_headers, x.table_rows)
  sample-text(x.sample_title, x.sample)
  note(x.tip, size: 9pt)
  v(4pt)
  text(size: 10pt, weight: "bold", fill: eu-blue, x.filled_title)
  v(4pt)
  filled-table((0, 1, 4, 5, 6).map(i => L.tearout.headers.at(i)), x.filled_rows)
  note(x.filled_note, size: 9pt, gap: 5pt)
  note(x.note, size: 9pt, gap: 5pt)
})
#pagebreak()

// ───── compliance table (a table that may run over two pages, so not fit-page) ─────
#band(L.tearout.title, id: "table")
#intro(L.tearout.intro, size: 9.4pt, gap: 5pt)
#intro(L.tearout.intro2, size: 9.4pt, gap: 8pt)
#score-sheet(headers: L.tearout.headers, roles: L.tearout.header_roles,
  ..mims.map(m => section(m.id + " · " + m.question,
    ..L.tearout_short.at(m.id).enumerate().map(((i, short)) =>
      (m.id.slice(3) + "." + str(i + 1), short, m.refs.at(i))))),
  section(L.cross.title, accent: magenta, note: L.tearout.cross_note,
    ..L.tearout_short.at("CROSS").enumerate().map(((i, short)) =>
      ("X." + str(i + 1), short, "—"))))
#note(L.tearout.note, size: 8.4pt, gap: 6pt)
#if S.sheet_url != "" { spec-link(L.tearout.download_label, S.sheet_url) }
#pagebreak()

// ───── glossary and further reading ─────
#fit-page("glossary", {
  band(L.glossary.title, id: "glossary")
  glossary(..L.glossary.terms)
  more-links(L.glossary.more_title,
    ..L.glossary.links.pairs().map(((name, d)) => more-link(name, d)))
})

// ───── back cover ─────
#pagebreak()
#back-cover(L.back.text, L.back.credits, author: L.back.author)
