#!/usr/bin/env python3
"""
add_glossary_links.py — RadIndex SEO

Inietta un blocco "Glossario" (link interni alle voci di glossario correlate)
in ogni pagina di /proiezioni-radiografiche/*.html.

Scopo SEO: passare autorevolezza dalle 147 pagine proiezione (indicizzate) alle
pagine di glossario, che ricevono impressioni per termini anatomici ad alta
domanda (es. "forame magno", "angolo di Louis") ma sono ancora in pagina 3.

- Rileva i termini di glossario presenti nel TESTO della scheda (word-boundary,
  case/accent-insensitive).
- Prioritizza i termini più specifici (multi-parola), scarta acronimi/tecnica generici.
- Max 6 link per pagina (no over-linking).
- IDEMPOTENTE: usa il marcatore <!-- gloss-auto -->; se rilanci, sostituisce il blocco.

⚠️ Le pagine proiezione sono generate da un tool ESTERNO al repo: RILANCIA questo
script dopo ogni rigenerazione delle 147 pagine (come per l'inserimento meta).

USO:  python3 add_glossary_links.py            # applica
      python3 add_glossary_links.py --dry-run  # mostra solo cosa farebbe
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent
GLOSS_JSON = ROOT / "_glossario" / "glossario_i18n.json"
PROJ_DIR = ROOT / "proiezioni-radiografiche"
MAX_LINKS = 6
MIN_TERM_LEN = 5          # scarta acronimi (kV, mAs, CR, DR, AEC, DFD, DI, EI...)
MARKER = "<!-- gloss-auto -->"

# Mappa CURATA: termini ad alta domanda GSC che NON compaiono letteralmente nel
# testo delle schede, ma sono clinicamente pertinenti a specifiche proiezioni.
# {slug_glossario: [stem pagina proiezione]}. Questi link hanno priorità.
CURATED = {
    "forame-magno": ["rx-cranio-towne-occipite", "rx-cranio-smv-submento-vertice"],
    "angolo-di-louis-angolo-sternale": ["rx-torace-pa", "rx-torace-pa-espirazione",
                                        "rx-torace-ll", "rx-sterno-oa", "rx-sterno-ll"],
    "forami-di-coniugazione": ["rx-rachide-cervicale-obliqua", "rx-rachide-lombare-ll",
                               "rx-rachide-dorsale-ll"],
    "angolo-di-costa-bertani": ["rx-torace-pa", "rx-torace-ll"],
}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def norm(s: str) -> str:
    return strip_accents(s).lower()


def load_terms():
    """Ritorna (terms, display_map). terms = lista (slug, display, keys[])."""
    data = json.load(open(GLOSS_JSON, encoding="utf-8"))
    terms = []
    display_map = {}
    for slug, entry in data.items():
        it = entry.get("it", {})
        display = it.get("termine", "").strip()
        if not display:
            continue
        display_map[slug] = display
        core = display.split("(")[0].strip()          # "Angolo di Louis (…)" -> "Angolo di Louis"
        if len(core) < MIN_TERM_LEN:                   # scarta acronimi generici
            continue
        keys = {core}
        # eventuale alias tra parentesi (es. "angolo sternale")
        m = re.search(r"\(([^)]+)\)", display)
        if m and len(m.group(1).strip()) >= MIN_TERM_LEN:
            keys.add(m.group(1).strip())
        terms.append((slug, core, sorted(keys, key=len, reverse=True)))
    # più lungo (specifico) prima → vince nel cap per pagina
    terms.sort(key=lambda t: len(t[1]), reverse=True)
    return terms, display_map


def visible_text(html: str) -> str:
    """Testo della sola scheda (proj-body), senza tag."""
    m = re.search(r'<div class="proj-body">(.*?)</div>\s*(?=<div class="related)',
                  html, re.S)
    body = m.group(1) if m else html
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"&[a-zA-Z#0-9]+;", " ", body)
    return norm(body)


def build_block(matches):
    items = "".join(
        f'<a href="/glossario/{slug}.html" class="related-item">'
        f'<span class="related-name">{display}</span></a>'
        for slug, display in matches
    )
    return (f'<div class="related gloss-related">{MARKER}'
            f'<h3>Glossario</h3><div class="related-list">{items}</div></div>\n')


def process(path: Path, terms, display_map, dry=False):
    html = path.read_text(encoding="utf-8")
    # rimuovi blocco precedente (idempotenza)
    html = re.sub(r'<div class="related gloss-related">.*?</div></div>\n?', "",
                  html, flags=re.S)
    text = visible_text(html)

    found = []
    seen = set()
    # 1) CURATI (priorità): termini pertinenti a questa proiezione
    for slug, stems in CURATED.items():
        if path.stem in stems and slug not in seen and slug in display_map:
            found.append((slug, display_map[slug]))
            seen.add(slug)
    # 2) AUTO-MATCH: termini che compaiono nel testo della scheda
    for slug, display, keys in terms:
        if len(found) >= MAX_LINKS:
            break
        if slug in seen:
            continue
        for key in keys:
            if re.search(r"\b" + re.escape(norm(key)) + r"\b", text):
                found.append((slug, display))
                seen.add(slug)
                break

    found = found[:MAX_LINKS]
    if not found:
        return 0

    block = build_block(found)
    # inserisci prima del <footer>
    new_html, n = re.subn(r"(?=<footer)", block, html, count=1)
    if n == 0:  # nessun footer? in coda al main
        new_html = html.replace("</main>", block + "</main>", 1)
    if not dry:
        path.write_text(new_html, encoding="utf-8")
    return len(found)


def main():
    dry = "--dry-run" in sys.argv
    terms, display_map = load_terms()
    pages = sorted(PROJ_DIR.glob("*.html"))
    tot_pages = tot_links = 0
    for p in pages:
        n = process(p, terms, display_map, dry)
        if n:
            tot_pages += 1
            tot_links += n
    verb = "SIMULAZIONE — " if dry else ""
    print(f"{verb}{len(terms)} termini glossario · {len(pages)} pagine proiezione")
    print(f"{verb}Modificate {tot_pages} pagine · {tot_links} link glossario totali "
          f"(media {tot_links/max(tot_pages,1):.1f}/pagina)")


if __name__ == "__main__":
    main()
