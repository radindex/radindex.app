#!/usr/bin/env python3
"""
add_analytics_beacon.py — RadIndex

Inserisce il beacon Cloudflare Web Analytics (già usato sul resto del sito) in
tutte le pagine HTML che ne sono prive — in particolare le pagine /glossario/
e le sezioni glossario EN/ES, che al 14/07/2026 risultavano NON tracciate.

- Idempotente: salta le pagine che hanno già il beacon.
- Inserisce lo snippet subito prima di </head>.

⚠️ Se le pagine glossario/proiezioni vengono rigenerate da un tool esterno,
RILANCIARE questo script per ripristinare il tracciamento.

USO:  python3 add_analytics_beacon.py            # applica
      python3 add_analytics_beacon.py --dry-run  # mostra solo cosa farebbe
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
BEACON = ("<script defer src='https://static.cloudflareinsights.com/beacon.min.js' "
          "data-cf-beacon='{\"token\": \"e94eb4bff7374521ba1b71b5bb958c5f\"}'></script>")
MARKER = "cloudflareinsights"  # per idempotenza


def main():
    dry = "--dry-run" in sys.argv
    pages = [p for p in ROOT.rglob("*.html") if ".git" not in p.parts]
    already = added = skipped_nohead = 0
    for p in pages:
        html = p.read_text(encoding="utf-8")
        if MARKER in html:
            already += 1
            continue
        if "</head>" not in html:
            skipped_nohead += 1
            continue
        if not dry:
            p.write_text(html.replace("</head>", BEACON + "\n</head>", 1), encoding="utf-8")
        added += 1

    verb = "SIMULAZIONE — " if dry else ""
    print(f"{verb}Pagine HTML totali: {len(pages)}")
    print(f"{verb}Già col beacon: {already}")
    print(f"{verb}Beacon aggiunto: {added}")
    if skipped_nohead:
        print(f"{verb}Saltate (senza </head>): {skipped_nohead}")


if __name__ == "__main__":
    main()
