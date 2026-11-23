#!/usr/bin/env python3
"""
generate_home_i18n.py — static EN/ES copies of the home page (/en/ and /es/)
============================================================================

Why: the home used `?lang=` (same HTML, JS translates it), with a canonical
pointing to the root, so Google ignored the hreflang of the home and /en/, /es/
returned 404. This script produces real static pages, like generate_static_i18n.py
does for projections and glossary.

Source of truth: /index.html (Italian, with the `const T = {it, en, es}` dictionary).
Re-run after ANY change to the home, then commit en/index.html, es/index.html, sitemap.xml:

    cd /Users/simonezen/radindex-site
    python3 _i18n/generate_home_i18n.py

It does NOT touch glossary/projection pages (use ./build_glossario.sh and
_i18n/generate_static_i18n.py for those). Needs `node` to read the dictionary.
"""
import re, json, pathlib, subprocess, html as H
from datetime import date

SITE = pathlib.Path(__file__).parent.parent
BASE = "https://radindex.app"
TODAY = str(date.today())

META = {
    "en": {
        "desc": "147 radiographic projections with DR/CR parameters, positioning, quality criteria and common errors. The app for radiographers and radiology students.",
        "ogtitle": "Rad Index — The radiography manual for radiographers",
        "appdesc": "147 radiographic projections with separate DR/CR parameters, positioning, quality criteria, common errors, practical notes, flashcards and glossary. Works offline. For radiographers and radiology students.",
    },
    "es": {
        "desc": "147 proyecciones radiográficas con parámetros DR/CR, posicionamiento, criterios de calidad y errores comunes. La app para técnicos y estudiantes de radiología.",
        "ogtitle": "Rad Index — El manual de RX para técnicos",
        "appdesc": "147 proyecciones radiográficas con parámetros DR/CR separados, posicionamiento, criterios de calidad, errores comunes, notas prácticas, flashcards y glosario. Funciona sin conexión. Para técnicos y estudiantes de radiología.",
    },
}


def load_T(src: str) -> dict:
    a = src.index("const T = {")
    b = src.index("\n};", a) + 3
    block = src[a:b]
    js = block + "\nconsole.log(JSON.stringify(T));"
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def find_close(s: str, start: int, tag: str) -> int:
    """index of the '</tag>' that closes the element whose open tag ends at `start`."""
    depth, pos = 1, start
    pat = re.compile(r"<(/?)%s\b[^>]*>" % re.escape(tag), re.I)
    while depth:
        m = pat.search(s, pos)
        if not m:
            raise ValueError("unbalanced <%s>" % tag)
        depth += -1 if m.group(1) else 1
        pos = m.end()
        if depth == 0:
            return m.start()
    raise ValueError


def apply_i18n(s: str, t: dict) -> str:
    # textContent / innerHTML: process from the end so offsets stay valid
    pat = re.compile(r"<(?P<tag>[a-zA-Z0-9]+)(?P<attrs>[^>]*?\sdata-i18n(?P<html>-html)?=\"(?P<key>[^\"]+)\"[^>]*)>")
    for m in reversed(list(pat.finditer(s))):
        key = m.group("key")
        if key not in t or m.group("tag").lower() in ("img", "input", "br"):
            continue
        end = find_close(s, m.end(), m.group("tag"))
        val = t[key] if m.group("html") else H.escape(t[key], quote=False)
        s = s[: m.end()] + val + s[end:]
    # alt
    def alt(m):
        tag = m.group(0)
        key = re.search(r'data-i18n-alt="([^"]+)"', tag).group(1)
        if key in t:
            tag = re.sub(r'\salt="[^"]*"', ' alt="%s"' % H.escape(t[key], quote=True), tag, count=1)
        return tag
    s = re.sub(r'<img\b[^>]*data-i18n-alt="[^"]+"[^>]*>', alt, s)
    # placeholder
    def ph(m):
        key = m.group(1)
        if key in t:
            v = H.escape(t[key], quote=True)
            tag = re.sub(r'\splaceholder="[^"]*"', ' placeholder="%s"' % v, m.group(0), count=1)
            return re.sub(r'\saria-label="[^"]*"', ' aria-label="%s"' % v, tag, count=1)
        return m.group(0)
    s = re.sub(r'<(?:input|textarea)\b[^>]*data-i18n-placeholder="([^"]+)"[^>]*>', ph, s)
    return s


def strip_tags(x: str) -> str:
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", x))).strip()


def build(lang: str, src: str, T: dict) -> str:
    t, m = T[lang], META[lang]
    s = src
    # head
    s = s.replace('<html lang="it">', '<html lang="%s">' % lang, 1)
    s = re.sub(r"<title>.*?</title>", "<title>%s</title>" % H.escape(t["pageTitle"], quote=False), s, count=1, flags=re.S)
    s = re.sub(r'(<meta name="description" content=")[^"]*(")', lambda x: x.group(1) + H.escape(m["desc"]) + x.group(2), s, count=1)
    s = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s/%s/">' % (BASE, lang), s, count=1)
    s = re.sub(r'(<link rel="alternate" hreflang="it" href=")[^"]*(")', r"\g<1>%s/\2" % BASE, s, count=1)
    s = re.sub(r'(<link rel="alternate" hreflang="en" href=")[^"]*(")', r"\g<1>%s/en/\2" % BASE, s, count=1)
    s = re.sub(r'(<link rel="alternate" hreflang="es" href=")[^"]*(")', r"\g<1>%s/es/\2" % BASE, s, count=1)
    s = re.sub(r'(<meta property="og:title" content=")[^"]*(")', lambda x: x.group(1) + H.escape(m["ogtitle"]) + x.group(2), s, count=1)
    s = re.sub(r'(<meta property="og:description" content=")[^"]*(")', lambda x: x.group(1) + H.escape(m["desc"]) + x.group(2), s, count=1)
    s = re.sub(r'(<meta property="og:url" content=")[^"]*(")', r"\g<1>%s/%s/\2" % (BASE, lang), s, count=1)
    # body text from the dictionary (same keys the JS uses)
    s = apply_i18n(s, t)
    # json-ld
    def ld(mm):
        d = json.loads(mm.group(1))
        if d.get("@type") == "MobileApplication":
            d["inLanguage"] = lang
            d["url"] = "%s/%s/" % (BASE, lang)
            d["description"] = m["appdesc"]
        elif d.get("@type") == "FAQPage":
            qs = []
            for i in range(1, 10):
                if "faqQ%d" % i in t and "faqA%d" % i in t:
                    qs.append({"@type": "Question", "name": strip_tags(t["faqQ%d" % i]),
                               "acceptedAnswer": {"@type": "Answer", "text": strip_tags(t["faqA%d" % i])}})
            d["mainEntity"] = qs
        return '<script type="application/ld+json">\n  ' + json.dumps(d, ensure_ascii=False, indent=2).replace("\n", "\n  ") + "\n  </script>"
    s = re.sub(r'<script type="application/ld\+json">(.*?)</script>', ld, s, flags=re.S)
    # paths: the page now lives one level deeper
    s = re.sub(r'(href|src|poster)="assets/', r'\1="/assets/', s)
    s = s.replace("url(assets/", "url(/assets/")
    s = s.replace('href="/proiezioni-radiografiche/"', 'href="/%s/proiezioni-radiografiche/"' % lang)
    s = s.replace('href="/glossario/"', 'href="/%s/glossario/"' % lang)
    s = s.replace('href="/"', 'href="/%s/"' % lang)
    s = s.replace("/go/it/", "/go/%s/" % lang)
    # the language buttons: mark the right one as active in the static HTML
    s = re.sub(r'class="lang-btn active"', 'class="lang-btn"', s)
    s = re.sub(r'(class="lang-btn)(" data-lang="%s")' % lang, r"\1 active\2", s, count=1)
    return s


def update_sitemap():
    p = SITE / "sitemap.xml"
    x = p.read_text()
    x = re.sub(r"\n?  <url><loc>%s/(?:en|es)/</loc>.*?</url>" % re.escape(BASE), "", x, flags=re.S)
    home = re.compile(r"  <url><loc>%s/</loc>.*?</url>" % re.escape(BASE), re.S)
    def entry(loc):
        return (
            '  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>1.0</priority>\n'
            '    <xhtml:link rel="alternate" hreflang="it" href="%s/"/>\n'
            '    <xhtml:link rel="alternate" hreflang="en" href="%s/en/"/>\n'
            '    <xhtml:link rel="alternate" hreflang="es" href="%s/es/"/>\n'
            '    <xhtml:link rel="alternate" hreflang="x-default" href="%s/"/>\n'
            "  </url>" % (loc, TODAY, BASE, BASE, BASE, BASE)
        )
    new = "\n".join([entry(BASE + "/"), entry(BASE + "/en/"), entry(BASE + "/es/")])
    assert home.search(x), "home entry not found in sitemap.xml"
    x = home.sub(lambda _: new, x, count=1)
    p.write_text(x)


def main():
    src = (SITE / "index.html").read_text()
    T = load_T(src)
    for lang in ("en", "es"):
        out = build(lang, src, T)
        d = SITE / lang
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(out)
        print("wrote", d / "index.html", len(out), "bytes")
    update_sitemap()
    print("sitemap.xml updated")


if __name__ == "__main__":
    main()
