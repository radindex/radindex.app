#!/usr/bin/env python3
"""
add_cta_click_tracking.py — RadIndex

Problema: le pagine del sito linkano App Store/Play Store direttamente
(apps.apple.com / play.google.com) — zero modo di sapere quanti click reali
genera il traffico SEO verso lo store, perché Cloudflare Web Analytics (unico
tracking presente sul sito) misura solo pageview, non supporta custom events
(confermato dalla FAQ ufficiale Cloudflare: "Does Web Analytics support
custom events? Not yet").

Soluzione senza nuovi account/infrastruttura: i badge non puntano più
direttamente allo store, ma a una pagina ponte /go/<lang>/{app-store,
play-store}.html che fa un redirect quasi istantaneo (meta refresh + JS,
beacon Cloudflare già presente) e poi rimanda al vero store. Il passaggio
su quella pagina registra una pageview Cloudflare normalissima — da lì in
poi basta leggere /go/<lang>/... con cloudflare_pageviews.py per contare i
click reali per lingua, senza bisogno di GA4 sul sito o di Zaraz.

<lang> è "it"/"en"/"es" a seconda del prefisso di cartella della pagina
(default it per le pagine senza prefisso, es. /glossario/, /proiezioni-
radiografiche/, index.html).

- Idempotente: dopo il primo giro gli URL diretti allo store non esistono
  più nelle pagine normali, quindi un rilancio non trova nulla da sostituire.
- Le pagine /go/*.html stesse vanno escluse (contengono il vero URL finale).

⚠️ Le pagine glossario vengono rigenerate da build_glossario.sh (generator.py +
generate_static_i18n.py), che ripristinerebbe i link diretti allo store — per
questo è già lo step 4/4 dentro build_glossario.sh, non va rilanciato a mano
dopo una build normale. Serve rilanciarlo a mano solo se nuove pagine (es.
proiezioni-radiografiche) vengono aggiunte/editate fuori da quella catena.

USO:  python3 add_cta_click_tracking.py            # applica
      python3 add_cta_click_tracking.py --dry-run  # mostra solo cosa farebbe
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent

APPLE_URL = "https://apps.apple.com/it/app/rad-index/id6770671896"
PLAY_URL = "https://play.google.com/store/apps/details?id=com.radindex.app"

BEACON = ("<script defer src='https://static.cloudflareinsights.com/beacon.min.js' "
          "data-cf-beacon='{\"token\": \"e94eb4bff7374521ba1b71b5bb958c5f\"}'></script>")

FALLBACK_TEXT = {
    "it": 'Reindirizzamento allo store… <a href="{url}">clicca qui se non succede nulla</a>.',
    "en": 'Redirecting to the store… <a href="{url}">click here if nothing happens</a>.',
    "es": 'Redirigiendo a la tienda… <a href="{url}">haz clic aquí si no pasa nada</a>.',
}


def bridge_page(lang, store_url):
    text = FALLBACK_TEXT[lang].format(url=store_url)
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<meta http-equiv="refresh" content="1;url={store_url}">
<title>Rad Index</title>
{BEACON}
<script>setTimeout(function(){{ location.replace("{store_url}"); }}, 150);</script>
</head>
<body>
<p>{text}</p>
</body>
</html>
"""


def lang_for(path: Path) -> str:
    parts = path.relative_to(ROOT).parts
    if parts[0] == "es":
        return "es"
    if parts[0] == "en":
        return "en"
    return "it"


def main():
    dry = "--dry-run" in sys.argv
    verb = "SIMULAZIONE — " if dry else ""

    go_dir = ROOT / "go"
    if not dry:
        for lang in ("it", "en", "es"):
            (go_dir / lang).mkdir(parents=True, exist_ok=True)
            (go_dir / lang / "app-store.html").write_text(bridge_page(lang, APPLE_URL), encoding="utf-8")
            (go_dir / lang / "play-store.html").write_text(bridge_page(lang, PLAY_URL), encoding="utf-8")
    print(f"{verb}Pagine ponte /go/<lang>/{{app-store,play-store}}.html: 6 scritte")

    pages = [p for p in ROOT.rglob("*.html") if ".git" not in p.parts and "go" not in p.relative_to(ROOT).parts]
    changed = 0
    apple_hits = play_hits = 0
    for p in pages:
        html = p.read_text(encoding="utf-8")
        if APPLE_URL not in html and PLAY_URL not in html:
            continue
        lang = lang_for(p)
        new_html = html.replace(APPLE_URL, f"/go/{lang}/app-store.html")
        new_html = new_html.replace(PLAY_URL, f"/go/{lang}/play-store.html")
        apple_hits += html.count(APPLE_URL)
        play_hits += html.count(PLAY_URL)
        if new_html != html:
            changed += 1
            if not dry:
                p.write_text(new_html, encoding="utf-8")

    print(f"{verb}Pagine HTML totali scansionate: {len(pages)}")
    print(f"{verb}Pagine con badge store sostituiti: {changed}")
    print(f"{verb}Link Apple riscritti: {apple_hits}  —  Link Play riscritti: {play_hits}")


if __name__ == "__main__":
    main()
