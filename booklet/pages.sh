#!/bin/sh
# Publishes the files build.sh just made to GitHub Pages (branch gh-pages).
# Run from the workflow after ./build.sh; needs BOOKLET_VERSION.
#   draft build (dev)  -> MIMs-draft-<xx>.pdf / .docx    (overwritten every time)
#   edition (main)     -> MIMs-latest-<xx>.pdf / .docx   (overwritten every time)
# The site holds nothing else. Numbered editions (MIMs-9.0.2-<xx>.pdf) are the files of
# the GitHub releases, which the index links to. index.html is rebuilt every time.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
case "$BOOKLET_VERSION" in "") echo "BOOKLET_VERSION is not set" >&2; exit 1 ;;
  *dev) name=draft ;; *) name=$BOOKLET_VERSION ;; esac
ls MIMs-"$name"-* >/dev/null

git config user.name  >/dev/null || git config user.name  "github-actions[bot]"
git config user.email >/dev/null || git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

index() {   # the latest edition first and large; the draft and the link to the releases small below
  list() { while read -r f; do echo "<li><a href=\"$f\">$f</a></li>"; done; }
  {
    echo '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
    echo '<title>Procurement Checklist using the MIMs</title>'
    echo '<body style="font:16px/1.6 system-ui,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem">'
    echo '<h1>Procurement Checklist using the MIMs</h1>'
    echo '<h2>Latest edition</h2><ul style="font-size:1.25rem">'; ls MIMs-latest-* 2>/dev/null | list; echo '</ul>'
    echo '<div style="font-size:.85rem;color:#555">'
    echo '<h3>Draft (work in progress, may change any day)</h3><ul>'; ls MIMs-draft-* 2>/dev/null | list; echo '</ul>'
    [ -z "$GITHUB_REPOSITORY" ] || echo "<h3>Numbered editions</h3><p><a href=\"${GITHUB_SERVER_URL:-https://github.com}/$GITHUB_REPOSITORY/releases\">All editions (MIMs-9.0.N-&lt;lang&gt;.pdf) are on the releases page</a></p>"
    echo '</div></body>'
  } > index.html
}

for try in 1 2 3; do
  rm -rf "$ROOT/site"; git worktree prune; git branch -qD gh-pages 2>/dev/null || true
  if git fetch -q origin gh-pages 2>/dev/null; then
    git worktree add -q -B gh-pages site origin/gh-pages
  else
    git worktree add -q --detach site                  # first publish ever: empty branch
    ( cd site && git checkout -q --orphan gh-pages && git rm -rfq . )
  fi
  [ "$name" = draft ] && as=draft || as=latest
  for f in MIMs-"$name"-*; do cp "$f" "site/MIMs-$as-${f#MIMs-$name-}"; done
  ( cd site && touch .nojekyll && git rm -q --ignore-unmatch "MIMs-[0-9]*" && index && git add -A &&
    { git diff --cached --quiet || git commit -q -m "booklet $BOOKLET_VERSION"; } &&
    git push -q origin gh-pages ) && exit 0
  echo "push to gh-pages failed (another build published meanwhile?), retry $try" >&2
done
exit 1
