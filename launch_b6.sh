#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# B6 — Script lancio radindex.app
# Esegui la mattina del 1° luglio DOPO aver pubblicato le app
#
# Uso:
#   ./launch_b6.sh "https://apps.apple.com/app/id..." "https://play.google.com/store/apps/details?id=com.radindex.app"
#
# Lo trovi in App Store Connect → App → Informazioni generali → link
# e in Play Console → Dashboard → link store
# ═══════════════════════════════════════════════════════════════

set -e

IOS_URL="$1"
ANDROID_URL="$2"

if [ -z "$IOS_URL" ] || [ -z "$ANDROID_URL" ]; then
  echo "Uso: ./launch_b6.sh <iOS_URL> <Android_URL>"
  echo ""
  echo "Esempio:"
  echo '  ./launch_b6.sh "https://apps.apple.com/app/rad-index/id123456789" "https://play.google.com/store/apps/details?id=com.radindex.app"'
  exit 1
fi

echo "🚀 B6 — Attivazione lancio radindex.app"
echo ""

# ─── 1. Link store nel hero (App Store + Google Play badges) ───
# I due badge hanno markup identico — usare l'img alt come ancora per distinguerli
echo "1/5 Attivando link store nel hero..."
sed -i '' "s|href=\"#\" class=\"badge-link\" onclick=\"showComingSoon(event)\">\s*<img src=\"assets/badges/app-store|href=\"$IOS_URL\" class=\"badge-link\" target=\"_blank\"><img src=\"assets/badges/app-store|" index.html
sed -i '' "s|href=\"#\" class=\"badge-link\" onclick=\"showComingSoon(event)\">\s*<img src=\"assets/badges/google-play|href=\"$ANDROID_URL\" class=\"badge-link\" target=\"_blank\"><img src=\"assets/badges/google-play|" index.html

# ─── 2. Link store nel pricing CTA ───
echo "2/5 Attivando link pricing CTA..."
sed -i '' "s|href=\"#\" class=\"price-cta\" onclick=\"showComingSoon(event)\"|href=\"$IOS_URL\" class=\"price-cta\" target=\"_blank\"|" index.html

# ─── 3. Rimuovere "Lancio luglio 2026" dalla trust line ───
echo "3/5 Rimuovendo trust line 'Lancio luglio 2026'..."
sed -i '' '/heroTrust3.*Lancio luglio 2026/d' index.html
sed -i '' "s|heroTrust3: 'Lancio luglio 2026',||" index.html
sed -i '' "s|heroTrust3: 'Launching July 2026',||" index.html
sed -i '' "s|heroTrust3: 'Lanzamiento julio 2026',||" index.html

# ─── 4. Rimuovere il toast "In arrivo" ───
echo "4/5 Rimuovendo toast 'In arrivo'..."
sed -i '' '/toastMsgs/d' index.html
sed -i '' '/showComingSoon/d' index.html
sed -i '' '/toastTimer/d' index.html

# ─── 5. Aggiornare le pagine proiezioni (toast sui bottoni store) ───
echo "5/5 Aggiornando link store nelle 148 pagine proiezioni..."
for f in proiezioni-radiografiche/*.html; do
  # I due bottoni (App Store / Google Play) hanno markup IDENTICO sulla stessa riga:
  # senza il testo del link come ancora, sed sostituirebbe solo il primo (App Store)
  # lasciando Google Play rotto per sempre. Pattern distinto includendo il testo visibile.
  sed -i '' "s|href=\"#\" class=\"btn-store\" onclick=\"showComingSoon(event)\">App Store|href=\"$IOS_URL\" class=\"btn-store\" target=\"_blank\">App Store|" "$f" 2>/dev/null || true
  sed -i '' "s|href=\"#\" class=\"btn-store\" onclick=\"showComingSoon(event)\">Google Play|href=\"$ANDROID_URL\" class=\"btn-store\" target=\"_blank\">Google Play|" "$f" 2>/dev/null || true
done

echo ""
echo "✅ B6 completato!"
echo ""
echo "Prossimi passi:"
echo "  1. Verifica il sito: open https://radindex.app"
echo "  2. git add -A && git commit -m 'feat: B6 — lancio live, link store attivati'"
echo "  3. git push origin main"
echo "  4. Aspetta 1-2 min per il deploy GitHub Pages"
echo "  5. Verifica di nuovo dal telefono"
