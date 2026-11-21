#!/bin/bash
# Rigenera go/it/libro.html come copia ESATTA della home (index.html), con i percorsi
# relativi degli asset convertiti in assoluti (necessario perché vive due livelli più in basso)
# e il meta robots noindex,nofollow (non deve finire indicizzata separatamente, è un duplicato
# usato solo per isolare su Cloudflare Web Analytics le visite che arrivano dal QR del libro
# Minerva Medica). Il canonical nell'head resta quello reale (https://radindex.app/), già corretto.
#
# Da rilanciare ogni volta che si modifica index.html, altrimenti questa copia invecchia.
set -euo pipefail
cd "$(dirname "$0")"

SRC="index.html"
DEST="go/it/libro.html"

sed \
  -e 's/href="assets\//href="\/assets\//g' \
  -e 's/src="assets\//src="\/assets\//g' \
  -e 's/url(assets\//url(\/assets\//g' \
  -e 's/<meta charset="UTF-8">/<meta charset="UTF-8">\n  <meta name="robots" content="noindex,nofollow">/' \
  "$SRC" > "$DEST"

echo "Rigenerato $DEST da $SRC"
