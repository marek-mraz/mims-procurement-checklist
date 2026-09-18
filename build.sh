#!/bin/sh
# Rebuild the MIMs procurement booklet: one PDF and one DOCX per language.
# Content: booklet/content/<xx>.json (translatable) + shared.json + quotes.json.
# Output, next to this script:  MIMs-draft-<xx>.pdf / .docx  for a draft build,
#                               MIMs-9.0.2-<xx>.pdf / .docx  for a published edition.
# The same script runs on your machine and in the GitHub workflow.
set -e
ROOT=$(cd "$(dirname "$0")" && pwd)
cd "$ROOT/booklet"

# fetch pinned tools if missing (typst 0.15.1, Inter 4.1)
if [ ! -x tools/typst ]; then
  mkdir -p tools
  case "$(uname -m)" in
    aarch64|arm64) arch=aarch64 ;;
    *)             arch=x86_64 ;;
  esac
  curl -sL -o /tmp/typst.tar.xz "https://github.com/typst/typst/releases/download/v0.15.1/typst-$arch-unknown-linux-musl.tar.xz"
  tar -C tools -xf /tmp/typst.tar.xz --strip-components=1 "typst-$arch-unknown-linux-musl/typst"
fi
if [ ! -f tools/fonts/Inter-Regular.ttf ]; then
  mkdir -p tools/fonts
  curl -sL -o /tmp/inter.zip https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip
  python3 - <<'EOF'
import zipfile
z = zipfile.ZipFile('/tmp/inter.zip')
want = {'Inter-Regular.ttf','Inter-Bold.ttf','Inter-SemiBold.ttf','Inter-Medium.ttf','Inter-Italic.ttf','Inter-Light.ttf'}
for n in z.namelist():
    b = n.split('/')[-1]
    if b in want:
        open('tools/fonts/'+b,'wb').write(z.read(n))
EOF
fi
if [ ! -x tools/venv/bin/python ]; then python3 -m venv tools/venv; fi
tools/venv/bin/python -c "import docx, pymupdf" 2>/dev/null || tools/venv/bin/pip install --quiet python-docx pymupdf

# edition number and date, printed in every PDF and DOCX (see booklet/version.sh):
# "9.0.2-dev" here and on dev, "9.0.2" when the workflow builds main (RELEASE=1)
BOOKLET_VERSION=${BOOKLET_VERSION:-$(./version.sh)}
BOOKLET_DATE=${BOOKLET_DATE:-$(date +%F)}
case "$BOOKLET_VERSION" in *dev) BOOKLET_NAME=draft ;; *) BOOKLET_NAME=$BOOKLET_VERSION ;; esac
export BOOKLET_VERSION BOOKLET_DATE BOOKLET_NAME
echo "building edition $BOOKLET_VERSION ($BOOKLET_DATE)"

# 1. validate every language: text against the English master, then page fit.
#    Stops the build on an error; warnings (long strings, zoomed pages) do not.
tools/venv/bin/python check_content.py
python3 translate.py --selftest          # the machine-translation helper: split, merge, shape (offline)

# 2. readable/booklet-<xx>.typ: the same booklet with its text inline
tools/venv/bin/python gen_typ.py

# 3. PDF and DOCX for every language present in content/
for f in content/[a-z][a-z].json; do
  lang=$(basename "$f" .json)
  tools/typst compile --font-path tools/fonts --input lang=$lang \
    --input version="$BOOKLET_VERSION" --input date="$BOOKLET_DATE" main.typ "$ROOT/MIMs-$BOOKLET_NAME-$lang.pdf"
done
tools/venv/bin/python gen_docx.py

ls -la "$ROOT"/MIMs-"$BOOKLET_NAME"-*
