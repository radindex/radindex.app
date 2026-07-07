#!/usr/bin/env python3
"""
generate_static_i18n.py — Static EN/ES page generator for radindex.app
=======================================================================

Reads all Italian HTML pages in /proiezioni-radiografiche/ and /glossario/,
extracts their embedded LANG_DATA translations, and produces fully static
EN and ES copies at /en/... and /es/... with correct canonical and hreflang.

Also:
  - Updates original IT pages' hreflang from ?lang=X to /X/... static URLs
  - Updates sitemap.xml with the new /en/ and /es/ entries

Usage:
    cd /Users/simonezen/radindex-site
    python3 _i18n/generate_static_i18n.py

Why static pages?
    The existing ?lang= approach relies on JS rendering. Google follows
    rel="canonical" (which always points to the IT page) and consolidates
    all language variants to IT — EN/ES content never gets indexed separately.
    Static pages with self-referencing canonicals fix this.
"""

import re, json, pathlib, html as html_module
from datetime import date
from typing import Optional, List

SITE    = pathlib.Path(__file__).parent.parent
BASE    = "https://radindex.app"
LANGS   = ["en", "es"]
TODAY   = str(date.today())

# ── meta description templates for translated pages ──────────────────────────
META_DESC_PROJ = {
    "en": "{name} — {ptype}. Positioning, DR/CR parameters, centering, quality criteria, common errors and practical notes. Zone: {zone}.",
    "es": "{name} — {ptype}. Posicionamiento, parámetros DR/CR, centraje, criterios de calidad, errores comunes y notas prácticas. Zona: {zone}.",
}
META_DESC_GLOSS = {
    "en": "{name} — Radiology glossary term for radiographers and students. Rad Index.",
    "es": "{name} — Término del glosario de radiología para técnicos y estudiantes. Rad Index.",
}
# Index page: fallback title and desc (these pages have heroTitle but not pageTitle)
INDEX_TITLES = {
    "proiezioni-radiografiche": {
        "en": "147 Radiographic Projections — Complete Positioning Guide | Rad Index",
        "es": "147 Proyecciones Radiográficas — Guía completa de posicionamiento | Rad Index",
    },
    "glossario": {
        "en": "Radiology Glossary — 94 technical and anatomical terms | Rad Index",
        "es": "Glosario de Radiología — 94 términos técnicos y anatómicos | Rad Index",
    },
}
INDEX_DESCS = {
    "proiezioni-radiografiche": {
        "en": "147 radiographic projections with positioning, DR/CR parameters, centering, quality criteria and common errors. For radiographers and students.",
        "es": "147 proyecciones radiográficas con posicionamiento, parámetros DR/CR, centraje, criterios de calidad y errores comunes. Para técnicos y estudiantes.",
    },
    "glossario": {
        "en": "Radiology glossary with 94 technical, anatomical and formula terms explained clearly for radiographers and students.",
        "es": "Glosario de radiología con 94 términos técnicos, anatómicos y fórmulas explicados de forma clara para técnicos y estudiantes.",
    },
}


def extract_lang_data(html_text: str) -> Optional[dict]:
    """Extract the LANG_DATA JSON object embedded in the page script block."""
    # Try the projection-page format first (followed by newline + function)
    m = re.search(r'const LANG_DATA = (\{.*?\});\s*\nfunction', html_text, re.DOTALL)
    if not m:
        # Fallback: generator.py format (followed by \nfunction or end of script)
        m = re.search(r'const LANG_DATA = (\{.*?\});', html_text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception as e:
        print(f"    WARN: LANG_DATA parse error: {e}")
        return None


def get_canonical(html_text: str) -> Optional[str]:
    """Extract the canonical URL from the page head."""
    m = re.search(r'<link rel="canonical" href="([^"]*)"', html_text)
    return m.group(1) if m else None


def lang_url(it_url: str, lang: str) -> str:
    """Derive the /lang/ URL from an Italian canonical URL."""
    # https://radindex.app/section/page.html → https://radindex.app/en/section/page.html
    return it_url.replace(BASE + "/", f"{BASE}/{lang}/", 1)


# ── HTML transformation helpers ──────────────────────────────────────────────

def replace_i18n_content(html_text: str, lang_data: dict, target_lang: str) -> str:
    """Replace data-i18n element innerText/innerHTML with translated content.

    Handles: <tag data-i18n="key" [other-attrs]>CONTENT</tag>
    CONTENT may include <br> and other void elements (no nested closing tags).
    """
    d = lang_data.get(target_lang, {})

    def replacer(m):
        prefix = m.group(1)   # data-i18n="key"[other attrs]>
        key    = m.group(2)   # key
        end    = m.group(4)   # </
        translated = d.get(key)
        if translated is not None:
            return f"{prefix}{translated}{end}"
        return m.group(0)     # key not in translations → keep original

    return re.sub(
        r'(data-i18n="([^"]+)"[^>]*>)(.*?)(<\/)',
        replacer,
        html_text,
        flags=re.DOTALL,
    )


def replace_i18n_placeholder(html_text: str, lang_data: dict, target_lang: str) -> str:
    """Replace placeholder attribute on elements with data-i18n-ph.

    Used in: <input data-i18n-ph="search" placeholder="...">
    """
    d = lang_data.get(target_lang, {})

    def replacer(m):
        key  = m.group(1)
        rest = m.group(2)
        translated = d.get(key)
        if translated:
            rest = re.sub(r'placeholder="[^"]*"',
                          f'placeholder="{html_module.escape(translated)}"',
                          rest)
        return f'data-i18n-ph="{key}"{rest}'

    return re.sub(r'data-i18n-ph="([^"]+)"([^>]*>)', replacer, html_text)


def update_html_lang(html_text: str, lang: str) -> str:
    return re.sub(r'<html lang="[^"]*">', f'<html lang="{lang}">', html_text)


def update_title(html_text: str, new_title: str) -> str:
    return re.sub(r'<title>[^<]*</title>',
                  f'<title>{html_module.escape(new_title)}</title>',
                  html_text)


def update_meta_desc(html_text: str, new_desc: str) -> str:
    return re.sub(
        r'<meta name="description" content="[^"]*">',
        f'<meta name="description" content="{html_module.escape(new_desc)}">',
        html_text,
    )


def update_canonical(html_text: str, new_url: str) -> str:
    return re.sub(
        r'<link rel="canonical" href="[^"]*">',
        f'<link rel="canonical" href="{new_url}">',
        html_text,
    )


def update_hreflang(html_text: str, it_url: str, en_url: str, es_url: str) -> str:
    """Replace the hreflang block with the correct static URLs."""
    new_block = (
        f'  <link rel="alternate" hreflang="it" href="{it_url}"/>\n'
        f'  <link rel="alternate" hreflang="en" href="{en_url}"/>\n'
        f'  <link rel="alternate" hreflang="es" href="{es_url}"/>\n'
        f'  <link rel="alternate" hreflang="x-default" href="{it_url}"/>'
    )
    # Remove all existing hreflang alternates + x-default (they may have ?lang= params)
    html_text = re.sub(
        r'\s*<link rel="alternate" hreflang="[^"]*" href="[^"]*"/>',
        '',
        html_text,
    )
    # Re-insert after canonical
    html_text = re.sub(
        r'(<link rel="canonical" href="[^"]*">)',
        r'\1\n' + new_block,
        html_text,
    )
    return html_text


def update_og_tags(html_text: str, title: str, desc: str, url: str) -> str:
    html_text = re.sub(
        r'<meta property="og:title" content="[^"]*">',
        f'<meta property="og:title" content="{html_module.escape(title)}">',
        html_text,
    )
    html_text = re.sub(
        r'<meta property="og:description" content="[^"]*">',
        f'<meta property="og:description" content="{html_module.escape(desc)}">',
        html_text,
    )
    html_text = re.sub(
        r'<meta property="og:url" content="[^"]*">',
        f'<meta property="og:url" content="{url}">',
        html_text,
    )
    return html_text


def fix_asset_paths(html_text: str) -> str:
    """Pages move one level deeper (en/section/page.html) so ../assets/ → ../../assets/."""
    return html_text.replace("../assets/", "../../assets/")


def fix_jsonld_lang_and_url(html_text: str, new_url: str, lang: str) -> str:
    """Update inLanguage and url fields in JSON-LD schema blocks."""
    # inLanguage: ["it","en","es"] → "en" (or "es")
    html_text = re.sub(
        r'"inLanguage":\["it","en","es"\]',
        f'"inLanguage":"{lang}"',
        html_text,
    )
    # url: the page-specific URL (not the base)
    # Only replace the page-level url field, not nested ones
    # We match the first "url":"https://radindex.app/section/..." pattern
    html_text = re.sub(
        r'("url":")(https://radindex\.app/(?!/)(?!en/)(?!es/)[^"]*\.html")',
        lambda m: f'{m.group(1)}{new_url}"',
        html_text,
    )
    return html_text


def fix_iife(html_text: str, lang: str) -> str:
    """Replace auto-detect IIFE with a static-page version that always defaults to lang."""
    new_iife = (
        f"(function(){{var p=new URLSearchParams(location.search).get('lang');"
        f"if(p&&LANG_DATA[p]){{setLang(p);return;}}setLang('{lang}');}})();"
    )
    # Match the IIFE that contains navigator.language (the auto-detect one)
    html_text = re.sub(
        r'\(function\(\)\{.*?navigator\.language.*?\}\)\(\);',
        new_iife,
        html_text,
        flags=re.DOTALL,
    )
    return html_text


# ── IT page hreflang update (point to static /en/ and /es/) ──────────────────

def update_it_page_hreflang(html_text: str, it_url: str) -> str:
    """Update the original Italian page's hreflang links to static /en/ and /es/ URLs."""
    en_url_ = lang_url(it_url, "en")
    es_url_ = lang_url(it_url, "es")
    return update_hreflang(html_text, it_url, en_url_, es_url_)


# ── Main page generation ──────────────────────────────────────────────────────

def generate_lang_page(
    html_text: str,
    lang_data: dict,
    it_url: str,
    target_lang: str,
    page_type: str,     # "proj_detail" | "gloss_detail" | "proj_index" | "gloss_index"
    section: str,       # "proiezioni-radiografiche" | "glossario"
) -> str:
    d = lang_data.get(target_lang, {})
    dest_url = lang_url(it_url, target_lang)

    # ── 1. Derive title and meta description ──────────────────────────────────
    if page_type == "proj_detail":
        title    = d.get("pageTitle", "")
        meta_desc = META_DESC_PROJ[target_lang].format(
            name  = html_module.unescape(d.get("projName", "")),
            ptype = html_module.unescape(d.get("projType", "")),
            zone  = html_module.unescape(d.get("zoneName", "")),
        )
    elif page_type == "gloss_detail":
        title    = d.get("pageTitle", "")
        meta_desc = META_DESC_GLOSS[target_lang].format(
            name = html_module.unescape(d.get("termName", "")),
        )
    elif page_type == "proj_index":
        title    = INDEX_TITLES["proiezioni-radiografiche"][target_lang]
        meta_desc = INDEX_DESCS["proiezioni-radiografiche"][target_lang]
    elif page_type == "gloss_index":
        title    = d.get("pageTitle") or INDEX_TITLES["glossario"][target_lang]
        meta_desc = INDEX_DESCS["glossario"][target_lang]
    else:
        title    = d.get("pageTitle", "")
        meta_desc = ""

    # ── 2. Apply transformations ──────────────────────────────────────────────
    out = html_text

    # Head metadata
    out = update_html_lang(out, target_lang)
    if title:
        out = update_title(out, title)
    if meta_desc:
        out = update_meta_desc(out, meta_desc)
    out = update_canonical(out, dest_url)
    out = update_hreflang(out, it_url, lang_url(it_url, "en"), lang_url(it_url, "es"))
    if title or meta_desc:
        out = update_og_tags(out, title or "Rad Index", meta_desc, dest_url)

    # Asset paths (one level deeper)
    out = fix_asset_paths(out)

    # JSON-LD
    out = fix_jsonld_lang_and_url(out, dest_url, target_lang)

    # i18n content replacement
    out = replace_i18n_content(out, lang_data, target_lang)
    out = replace_i18n_placeholder(out, lang_data, target_lang)

    # JS IIFE: always initialize to target_lang
    out = fix_iife(out, target_lang)

    return out


# ── Sitemap update ────────────────────────────────────────────────────────────

def sitemap_entry(loc: str, it_url: str, priority: str) -> str:
    en_url_ = lang_url(it_url, "en")
    es_url_ = lang_url(it_url, "es")
    return (
        f'  <url><loc>{loc}</loc><lastmod>{TODAY}</lastmod>'
        f'<changefreq>monthly</changefreq><priority>{priority}</priority>\n'
        f'    <xhtml:link rel="alternate" hreflang="it" href="{it_url}"/>\n'
        f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url_}"/>\n'
        f'    <xhtml:link rel="alternate" hreflang="es" href="{es_url_}"/>\n'
        f'    <xhtml:link rel="alternate" hreflang="x-default" href="{it_url}"/>\n'
        f'  </url>'
    )


def update_sitemap(proj_urls: List[str], gloss_urls: List[str]) -> int:
    """
    Fix existing ?lang= hreflang in sitemap, then append /en/ and /es/ entries.
    """
    sitemap_path = SITE / "sitemap.xml"
    txt = sitemap_path.read_text(encoding="utf-8")

    # Fix ?lang=it → clean URL (no query param)
    txt = re.sub(r'href="(https://radindex\.app/[^"?]*)\?lang=it"', r'href="\1"', txt)
    # Fix ?lang=en → /en/...
    def fix_en(m):
        clean = m.group(1)
        return f'href="{lang_url(clean, "en")}"'
    txt = re.sub(r'href="(https://radindex\.app/[^"?]*)\?lang=en"', fix_en, txt)
    # Fix ?lang=es → /es/...
    def fix_es(m):
        clean = m.group(1)
        return f'href="{lang_url(clean, "es")}"'
    txt = re.sub(r'href="(https://radindex\.app/[^"?]*)\?lang=es"', fix_es, txt)

    # Build new /en/ and /es/ entries to append
    new_entries = []

    # Section index pages
    for section, it_sec_url, priority in [
        ("proiezioni-radiografiche", f"{BASE}/proiezioni-radiografiche/", "0.8"),
        ("glossario",                f"{BASE}/glossario/",                 "0.8"),
    ]:
        for lang in LANGS:
            dest = lang_url(it_sec_url, lang)
            new_entries.append(sitemap_entry(dest, it_sec_url, priority))

    # Detail pages
    for it_url in proj_urls:
        for lang in LANGS:
            new_entries.append(sitemap_entry(lang_url(it_url, lang), it_url, "0.7"))

    for it_url in gloss_urls:
        for lang in LANGS:
            new_entries.append(sitemap_entry(lang_url(it_url, lang), it_url, "0.6"))

    # Append before closing </urlset>
    txt = txt.replace("</urlset>", "\n".join(new_entries) + "\n</urlset>")
    sitemap_path.write_text(txt, encoding="utf-8")
    return len(new_entries)


# ── Directory processor ───────────────────────────────────────────────────────

def process_directory(section: str) -> List[str]:
    """
    Process all HTML files in /section/.
    Updates IT hreflang in-place and generates /en/section/ + /es/section/ copies.
    Returns list of IT canonical URLs (for sitemap update).
    """
    src_dir = SITE / section
    it_urls  = []
    skipped  = 0

    for src_file in sorted(src_dir.glob("*.html")):
        html_text = src_file.read_text(encoding="utf-8")
        lang_data = extract_lang_data(html_text)

        if not lang_data:
            print(f"  SKIP (no LANG_DATA): {src_file.name}")
            skipped += 1
            continue

        it_url = get_canonical(html_text)
        if not it_url:
            print(f"  SKIP (no canonical): {src_file.name}")
            skipped += 1
            continue

        # Determine page type
        if src_file.name == "index.html":
            page_type = "proj_index" if section == "proiezioni-radiografiche" else "gloss_index"
        elif section == "proiezioni-radiografiche":
            page_type = "proj_detail"
        else:
            page_type = "gloss_detail"

        # Update IT page: fix hreflang to point to static /en/ and /es/
        updated_it = update_it_page_hreflang(html_text, it_url)
        if updated_it != html_text:
            src_file.write_text(updated_it, encoding="utf-8")

        # Generate EN and ES static pages
        for lang in LANGS:
            if lang not in lang_data:
                print(f"  SKIP {lang}: {src_file.name} (missing in LANG_DATA)")
                continue

            out_dir  = SITE / lang / section
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / src_file.name

            translated = generate_lang_page(
                html_text, lang_data, it_url, lang, page_type, section
            )
            out_file.write_text(translated, encoding="utf-8")

        if src_file.name != "index.html":
            it_urls.append(it_url)

    return it_urls


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Static EN/ES page generator — radindex.app")
    print("=" * 60)

    print("\n[1/3] Proiezioni radiografiche …")
    proj_urls = process_directory("proiezioni-radiografiche")
    print(f"      {len(proj_urls)} detail pages processed")

    print("\n[2/3] Glossario …")
    gloss_urls = process_directory("glossario")
    print(f"      {len(gloss_urls)} detail pages processed")

    print("\n[3/3] Sitemap …")
    n = update_sitemap(proj_urls, gloss_urls)
    print(f"      {n} new sitemap entries added")

    total = (len(proj_urls) + len(gloss_urls)) * 2 + 4  # +4 = section index pages
    print(f"\nDone. {total} static pages generated in /en/ and /es/.")
    print("Next: git add en/ es/ && git commit && git push → GitHub Pages auto-deploys.")
