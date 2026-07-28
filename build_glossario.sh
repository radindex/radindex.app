#!/usr/bin/env bash
# build_glossario.sh — catena COMPLETA e sicura per rigenerare il glossario RadIndex.
#
# PERCHÉ ESISTE: `_glossario/generator.py` da solo produce hreflang `?lang=` e NON
# include il beacon Cloudflare. Eseguirlo isolato REGREDISCE la SEO EN/ES (il fix
# canonical/hreflang statico) e il tracciamento. Questo script esegue i tre stadi
# nell'ordine giusto, poi verifica che l'output non sia regredito.
#
# USO:  ./build_glossario.sh            (dalla root del repo)
set -euo pipefail
cd "$(dirname "$0")"

echo "== 1/3 generator.py (pagine IT glossario) =="
python3 _glossario/generator.py

echo "== 2/3 generate_static_i18n.py (hreflang IT→statico + /en/ /es/) =="
python3 _i18n/generate_static_i18n.py

echo "== 3/3 add_analytics_beacon.py (beacon Cloudflare) =="
python3 add_analytics_beacon.py

echo "== VERIFICA ANTI-REGRESSIONE =="
sample="glossario/acromion.html"
fail=0
# hreflang EN deve essere statico /en/glossario/, NON ?lang=en
if ! grep -q 'hreflang="en" href="https://radindex.app/en/glossario/' "$sample"; then
  echo "  ✗ hreflang EN NON statico in $sample (regressione ?lang=)"; fail=1
else echo "  ✓ hreflang statico"; fi
# beacon Cloudflare presente
if ! grep -q "cloudflareinsights.com/beacon" "$sample"; then
  echo "  ✗ beacon Cloudflare ASSENTE in $sample"; fail=1
else echo "  ✓ beacon presente"; fi
# le 8 pagine SEO devono avere il title ottimizzato (non il suffisso generico)
if grep -q "<title>Angolo di Louis (angolo sternale) — Glossario di radiologia" glossario/angolo-di-louis-angolo-sternale.html; then
  echo "  ✗ seo_title NON applicato (title generico) — controlla i campi seo_ nel JSON"; fail=1
else echo "  ✓ seo_title applicato"; fi

if [ "$fail" -ne 0 ]; then
  echo "!! BUILD REGREDITA — NON committare. Rivedi gli script a valle."; exit 1
fi
echo "== OK: glossario rigenerato senza regressioni =="
