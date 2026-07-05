#!/usr/bin/env python3
"""Generatore glossario RadIndex TRILINGUE (IT/EN/ES) — pattern ?lang= come le proiezioni."""
import re, html, json, unicodedata, pathlib
from collections import Counter, OrderedDict

SITE = pathlib.Path("/Users/simonezen/radindex-site")
OUT = SITE / "glossario"
SITEMAP = SITE / "sitemap.xml"
I18N = pathlib.Path("/Users/simonezen/radindex-site/_glossario/glossario_i18n.json")
PROJ_DIR = SITE / "proiezioni-radiografiche"
LASTMOD = "2026-07-03"
APP_STORE = "https://apps.apple.com/it/app/rad-index/id6770671896"
PLAY_STORE = "https://play.google.com/store/apps/details?id=com.radindex.app"

MATCH_STOP = {'articolazione','obliqua','anteriore','posteriore','antero','postero','laterale','latero',
'mediale','distale','prossimale','craniale','caudale','cefalico','podalico','destra','destro',
'sinistra','sinistro','bilaterale','carico','trauma','assiale','tangenziale','funzionale','decubito',
'ulnare','radiale','proiezione','deviazione','esposizione','tempo','calcolo','inversi','quadrato',
'legge','secondo','milliampere','kilovolt','varianza','pediatrica','stress','monolatera'}

CAT_COLOR = {"tecnico": ("#E8F0FB", "#2D4E8A"), "anatomia": ("#FCEBEB", "#791F1F"), "formula": ("#FFF3E0", "#E65100")}
CAT_ORDER = ["tecnico", "anatomia", "formula"]

# etichette UI per lingua
UI = {
 "it": {"navHome":"Home","navProj":"Proiezioni","navGloss":"Glossario","navCta":"Scarica l'app",
   "uiRelated":"Termini correlati","uiProjRelated":"Proiezioni correlate","uiProjTag":"Proiezione",
   "ctaH":"Vai oltre la definizione","ctaP":"Con Rad Index studi con le flashcard, consulti le 147 proiezioni complete e la checklist ALARA — anche offline, in reparto.",
   "footerCopy":"© 2026 Rad Index · Sviluppato da un TSRM per i TSRM",
   "catLabel":{"tecnico":"Tecnico","anatomia":"Anatomia","formula":"Formula"},
   "catPlural":{"tecnico":"Tecnici","anatomia":"Anatomia","formula":"Formule"},
   "hubTitle":"Glossario di radiologia","hubSub":"94 termini tecnici, anatomici e formule spiegati in modo chiaro — per TSRM e studenti.",
   "search":"Cerca un termine…","noResult":"Nessun termine trovato.","titleSuffix":"Glossario di radiologia | Rad Index","hubTitleTag":"Glossario di radiologia — 94 termini tecnici e anatomici | Rad Index"},
 "en": {"navHome":"Home","navProj":"Projections","navGloss":"Glossary","navCta":"Download",
   "uiRelated":"Related terms","uiProjRelated":"Related projections","uiProjTag":"Projection",
   "ctaH":"Go beyond the definition","ctaP":"With Rad Index you study with flashcards, browse all 147 full projections and the ALARA checklist — even offline, on the ward.",
   "footerCopy":"© 2026 Rad Index · Built by a Radiographer for Radiographers",
   "catLabel":{"tecnico":"Technical","anatomia":"Anatomy","formula":"Formula"},
   "catPlural":{"tecnico":"Technical","anatomia":"Anatomy","formula":"Formulas"},
   "hubTitle":"Radiology glossary","hubSub":"94 technical, anatomical and formula terms explained clearly — for radiographers and students.",
   "search":"Search a term…","noResult":"No term found.","titleSuffix":"Radiology glossary | Rad Index","hubTitleTag":"Radiology glossary — 94 technical and anatomical terms | Rad Index"},
 "es": {"navHome":"Inicio","navProj":"Proyecciones","navGloss":"Glosario","navCta":"Descargar",
   "uiRelated":"Términos relacionados","uiProjRelated":"Proyecciones relacionadas","uiProjTag":"Proyección",
   "ctaH":"Más allá de la definición","ctaP":"Con Rad Index estudias con flashcards, consultas las 147 proyecciones completas y la checklist ALARA — incluso sin conexión, en el servicio.",
   "footerCopy":"© 2026 Rad Index · Desarrollado por un Técnico para Técnicos",
   "catLabel":{"tecnico":"Técnico","anatomia":"Anatomía","formula":"Fórmula"},
   "catPlural":{"tecnico":"Técnicos","anatomia":"Anatomía","formula":"Fórmulas"},
   "hubTitle":"Glosario de radiología","hubSub":"94 términos técnicos, anatómicos y fórmulas explicados de forma clara — para técnicos y estudiantes.",
   "search":"Buscar un término…","noResult":"Ningún término encontrado.","titleSuffix":"Glosario de radiología | Rad Index","hubTitleTag":"Glosario de radiología — 94 términos técnicos y anatómicos | Rad Index"},
}
LANGS = ["it", "en", "es"]

def strip_acc(s): return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
def esc(s): return html.escape(s)
def defhtml(s): return html.escape(s).replace("\n", "<br>")

def jstr(s):
    """Stringa JSON valida (con virgolette) — per i valori dentro JSON-LD.
    NON usare esc()/html.escape nei blocchi schema: produce &quot; nel JSON."""
    return json.dumps(s, ensure_ascii=False)

def load_projections():
    projs = []
    for p in sorted(PROJ_DIR.glob("rx-*.html")) + sorted(PROJ_DIR.glob("opt-*.html")):
        txt = p.read_text(encoding="utf-8")
        m = re.search(r'const LANG_DATA = (\{.*?\});', txt, re.DOTALL)
        names = {}
        if m:
            try:
                ld = json.loads(m.group(1))
                names = {l: ld.get(l, {}).get("projName", "") for l in LANGS}
            except Exception:
                pass
        it_name = names.get("it", p.stem)
        projs.append({"slug": p.stem, "names": names, "nametext": strip_acc(html.unescape(it_name))})
    dfc = Counter()
    for pr in projs:
        for w in set(re.findall(r"[a-z]+", pr["nametext"])): dfc[w] += 1
    return projs, dfc

def match_projections(term_it, projs, dfc, cap=4, maxdf=3):
    words = [w for w in re.findall(r"[a-z]+", strip_acc(term_it)) if len(w) >= 5 and w not in MATCH_STOP and 1 <= dfc.get(w,0) <= maxdf]
    if not words: return []
    return [pr for pr in projs if any(re.search(r"\b"+re.escape(w), pr["nametext"]) for w in words)][:cap]

CSS = (OUT / "kv-kilovolt.html").read_text(encoding="utf-8")  # riuso il CSS già in produzione
CSS = re.search(r"<style>(.*?)</style>", CSS, re.DOTALL).group(1)
# aggiungo stile lang switcher + colonne hub (se non presenti)
CSS += """
    .lang-switcher{display:flex;gap:2px;align-items:center;margin-left:8px;}
    .lang-btn{background:none;border:none;cursor:pointer;font-size:15px;padding:3px 4px;border-radius:6px;opacity:0.38;transition:opacity 0.15s;line-height:1;}
    .lang-btn:hover{opacity:0.75;}.lang-btn.active{opacity:1;}
    .hub-content{max-width:1080px;}
    .glossary-cols{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;align-items:start;}
    .gloss-col h2{display:flex;align-items:center;font-size:16px;font-weight:800;color:var(--text);margin-bottom:12px;}
    .col-dot{width:9px;height:9px;border-radius:50%;margin-right:8px;flex-shrink:0;}
    .col-count{font-size:12px;font-weight:600;color:var(--text3);margin-left:6px;}
    @media(max-width:820px){.glossary-cols{grid-template-columns:1fr;gap:28px;}}
    .gloss-search{position:relative;margin:0 0 24px;}
    .gloss-search input{width:100%;padding:13px 16px 13px 44px;font-size:15px;font-family:inherit;color:var(--text);background:var(--surface);border:1px solid var(--border);border-radius:12px;outline:none;transition:border-color 0.15s;}
    .gloss-search input:focus{border-color:var(--blue);}
    .gloss-search svg{position:absolute;left:15px;top:50%;transform:translateY(-50%);width:18px;height:18px;color:var(--text3);pointer-events:none;}
    .gloss-col.hidden,.related-item.hidden{display:none;}
    .gloss-noresult{display:none;text-align:center;color:var(--text3);font-size:14px;padding:24px;}"""

NAV = """<nav>
  <a href="/" class="nav-logo"><img src="../assets/logo_scuro.png" alt="Rad Index"></a>
  <button class="nav-hamburger" id="nav-toggle" aria-label="Menu" onclick="document.getElementById('nav-toggle').classList.toggle('open');document.getElementById('nav-menu').classList.toggle('open')">
    <svg width="22" height="22" viewBox="0 0 24 24"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
  </button>
  <div class="nav-links" id="nav-menu">
    <a href="/" data-i18n="navHome">Home</a>
    <a href="/proiezioni-radiografiche/" data-i18n="navProj">Proiezioni</a>
    <a href="/glossario/" data-i18n="navGloss">Glossario</a>
    <a href="/#pricing" class="nav-cta" data-i18n="navCta">Scarica l'app</a>
    <div class="lang-switcher">
      <button class="lang-btn" data-lang="it" onclick="setLang('it')" title="Italiano">🇮🇹</button>
      <button class="lang-btn" data-lang="en" onclick="setLang('en')" title="English">🇬🇧</button>
      <button class="lang-btn" data-lang="es" onclick="setLang('es')" title="Español">🇪🇸</button>
    </div>
  </div>
</nav>"""

FOOTER = """<footer>
  <a href="/">Rad Index</a> ·
  <a href="/proiezioni-radiografiche/" data-i18n="navProj">Proiezioni</a> ·
  <a href="/glossario/" data-i18n="navGloss">Glossario</a> ·
  <a href="/privacy.html">Privacy</a> ·
  <a href="mailto:info@radindex.app">info@radindex.app</a>
  <div class="footer-copy" data-i18n="footerCopy">© 2026 Rad Index · Sviluppato da un TSRM per i TSRM</div>
</footer>"""

SETLANG = """<script>
const LANG_DATA = %s;
function setLang(lang){
  if(!LANG_DATA[lang]) return;
  const d = LANG_DATA[lang];
  document.querySelectorAll('[data-i18n]').forEach(function(el){
    const k = el.getAttribute('data-i18n'); if(d[k]!==undefined) el.innerHTML = d[k];
  });
  document.querySelectorAll('[data-i18n-ph]').forEach(function(el){
    const k = el.getAttribute('data-i18n-ph'); if(d[k]!==undefined) el.setAttribute('placeholder', d[k]);
  });
  if(d.pageTitle) document.title = d.pageTitle;
  document.documentElement.lang = lang;
  document.querySelectorAll('.lang-btn').forEach(function(b){ b.classList.toggle('active', b.getAttribute('data-lang')===lang); });
  try{ localStorage.setItem('radindex-lang', lang); }catch(e){}
}
(function(){
  const p = new URLSearchParams(location.search).get('lang');
  if(p && LANG_DATA[p]){ setLang(p); return; }
  let s=null; try{ s=localStorage.getItem('radindex-lang'); }catch(e){}
  if(s && LANG_DATA[s]){ setLang(s); return; }
  const b=(navigator.language||'it').slice(0,2).toLowerCase();
  setLang(LANG_DATA[b]?b:'it');
})();
%s
</script>"""

HUB_SEARCH_JS = """
var _in=document.getElementById('gloss-filter');
if(_in){
  var items=[].slice.call(document.querySelectorAll('.related-item'));
  var cols=[].slice.call(document.querySelectorAll('.gloss-col'));
  var nres=document.getElementById('gloss-noresult');
  function _norm(s){return s.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');}
  _in.addEventListener('input',function(){
    var q=_norm(_in.value.trim()),t=0;
    items.forEach(function(it){var m=_norm(it.textContent).indexOf(q)!==-1;it.classList.toggle('hidden',!m);if(m)t++;});
    cols.forEach(function(c){c.classList.toggle('hidden',c.querySelectorAll('.related-item:not(.hidden)').length===0);});
    if(nres) nres.style.display=t===0?'block':'none';
  });
}"""

def head(canonical, title, desc, extra_schema):
    alts = "\n".join(f'  <link rel="alternate" hreflang="{l}" href="{canonical}?lang={l}"/>' for l in LANGS)
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="apple-itunes-app" content="app-id=6770671896">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="canonical" href="{canonical}">
{alts}
  <link rel="alternate" hreflang="x-default" href="{canonical}"/>
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:image" content="https://radindex.app/assets/og-image.png">
  <meta property="og:url" content="{canonical}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="https://radindex.app/assets/og-image.png">
  <link rel="icon" type="image/png" href="../assets/logo_icona.png">
  <link rel="preload" as="font" href="../assets/fonts/inter-latin.woff2" type="font/woff2" crossorigin>
{extra_schema}
  <style>{CSS}</style>
</head>"""

CTA = f"""<div class="app-cta">
    <h2 data-i18n="ctaH">Vai oltre la definizione</h2>
    <p data-i18n="ctaP">Con Rad Index studi con le flashcard, consulti le 147 proiezioni complete e la checklist ALARA — anche offline, in reparto.</p>
    <div class="cta-buttons">
      <a href="{APP_STORE}" class="badge-link"><img src="../assets/badges/app-store.svg" alt="App Store" class="badge-img" loading="lazy" width="124" height="48"></a>
      <a href="{PLAY_STORE}" class="badge-link"><img src="../assets/badges/google-play.png" alt="Google Play" class="badge-img" loading="lazy" width="124" height="48"></a>
    </div>
  </div>"""

def term_page(slug, v, data, projs, dfc):
    cat = v["categoria"]; cbg, cfg = CAT_COLOR[cat]
    canonical = f"https://radindex.app/glossario/{slug}.html"
    it = v["it"]
    # correlati per vicinanza tematica (stessa categoria)
    same = [s for s in data if data[s]["categoria"] == cat]
    idx = same.index(slug)
    related = sorted([s for s in same if s != slug], key=lambda s: abs(same.index(s)-idx))[:5]
    proj_matches = match_projections(it["termine"], projs, dfc)
    # LANG_DATA
    ld = {}
    for l in LANGS:
        u = UI[l]; tv = v[l]
        d = {"termName": esc(tv["termine"]), "definition": defhtml(tv["definizione"]),
             "catLabel": u["catLabel"][cat], "navHome":u["navHome"],"navProj":u["navProj"],
             "navGloss":u["navGloss"],"navCta":u["navCta"],"uiRelated":u["uiRelated"],
             "uiProjRelated":u["uiProjRelated"],"ctaH":u["ctaH"],"ctaP":u["ctaP"],
             "footerCopy":u["footerCopy"],"pageTitle":f"{tv['termine']} — {u['titleSuffix']}"}
        for rs in related:
            d[f"rel_{rs}"] = esc(data[rs][l]["termine"])
            d[f"relcat_{rs}"] = UI[l]["catLabel"][data[rs]["categoria"]]
        for pr in proj_matches:
            d[f"proj_{pr['slug']}"] = pr["names"].get(l) or pr["names"].get("it") or pr["slug"]
            d[f"projtag_{pr['slug']}"] = u["uiProjTag"]
        ld[l] = d
    # HTML (default IT)
    rel_html = "".join(
        f'<a href="{rs}.html" class="related-item"><span class="related-name" data-i18n="rel_{rs}">{esc(data[rs]["it"]["termine"])}</span>'
        f'<span class="related-cat" data-i18n="relcat_{rs}">{UI["it"]["catLabel"][data[rs]["categoria"]]}</span></a>' for rs in related)
    proj_section = ""
    if proj_matches:
        pit = "".join(
            f'<a href="/proiezioni-radiografiche/{pr["slug"]}.html" class="related-item"><span class="related-name" data-i18n="proj_{pr["slug"]}">{pr["names"].get("it")}</span>'
            f'<span class="related-cat" data-i18n="projtag_{pr["slug"]}">{UI["it"]["uiProjTag"]}</span></a>' for pr in proj_matches)
        proj_section = f'<div class="related" style="margin-bottom:24px;"><h2 data-i18n="uiProjRelated">Proiezioni correlate</h2><div class="related-list">{pit}</div></div>'
    schema = f'''  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"DefinedTerm","name":{jstr(it["termine"])},"description":{jstr(re.sub(chr(10)," ",it["definizione"])[:300])},"inDefinedTermSet":{{"@type":"DefinedTermSet","name":"Glossario di radiologia — Rad Index","url":"https://radindex.app/glossario/"}},"url":"{canonical}"}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"https://radindex.app/"}},{{"@type":"ListItem","position":2,"name":"Glossario","item":"https://radindex.app/glossario/"}},{{"@type":"ListItem","position":3,"name":{jstr(it["termine"])}}}]}}
  </script>'''
    desc = re.sub(r"\s+"," ", it["definizione"]).strip()
    desc = f"{it['termine']}: {desc[:150]}…" if len(desc) > 150 else f"{it['termine']}: {desc}"
    body = f"""{head(canonical, f"{it['termine']} — {UI['it']['titleSuffix']}", desc, schema)}
<body>
{NAV}
<div class="breadcrumb">
  <a href="/" data-i18n="navHome">Home</a><span>›</span>
  <a href="/glossario/" data-i18n="navGloss">Glossario</a><span>›</span>
  <span data-i18n="termName">{esc(it['termine'])}</span>
</div>
<main class="page-content">
  <div class="card">
    <div class="card-head">
      <h1 data-i18n="termName">{esc(it['termine'])}</h1>
      <span class="badge-cat" data-i18n="catLabel" style="background:{cbg};color:{cfg};">{UI['it']['catLabel'][cat]}</span>
    </div>
    <div class="term-body"><p data-i18n="definition">{defhtml(it['definizione'])}</p></div>
  </div>
  {CTA}
  {proj_section}
  <div class="related"><h2 data-i18n="uiRelated">Termini correlati</h2><div class="related-list">{rel_html}</div></div>
</main>
{FOOTER}
{SETLANG % (json.dumps(ld, ensure_ascii=False), "")}
</body>
</html>
"""
    return body

def hub_page(data):
    canonical = "https://radindex.app/glossario/"
    # colonne (default IT)
    cols = ""
    for cat in CAT_ORDER:
        terms = [s for s in data if data[s]["categoria"] == cat]
        cfg = CAT_COLOR[cat][1]
        items = "".join(f'<a href="{s}.html" class="related-item"><span class="related-name" data-i18n="term_{s}">{esc(data[s]["it"]["termine"])}</span></a>' for s in terms)
        cols += (f'<div class="gloss-col"><h2><span class="col-dot" style="background:{cfg};"></span>'
                 f'<span data-i18n="catPlural_{cat}">{UI["it"]["catPlural"][cat]}</span> <span class="col-count">{len(terms)}</span></h2>'
                 f'<div class="related-list">{items}</div></div>')
    ld = {}
    for l in LANGS:
        u = UI[l]
        d = {"navHome":u["navHome"],"navProj":u["navProj"],"navGloss":u["navGloss"],"navCta":u["navCta"],
             "footerCopy":u["footerCopy"],"ctaH":u["ctaH"],"ctaP":u["ctaP"],
             "hubTitle":u["hubTitle"],"hubSub":u["hubSub"],"noResult":u["noResult"],
             "search":u["search"],"pageTitle":u["hubTitleTag"]}
        for cat in CAT_ORDER: d[f"catPlural_{cat}"] = u["catPlural"][cat]
        for s in data: d[f"term_{s}"] = esc(data[s][l]["termine"])
        ld[l] = d
    schema = f'''  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"CollectionPage","name":"Glossario di radiologia — Rad Index","url":"{canonical}","description":"Glossario di 94 termini di radiologia per TSRM e studenti.","breadcrumb":{{"@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"https://radindex.app/"}},{{"@type":"ListItem","position":2,"name":"Glossario"}}]}}}}
  </script>'''
    body = f"""{head(canonical, UI['it']['hubTitleTag'], "Glossario di radiologia: 94 termini tecnici, anatomici e formule spiegati in modo chiaro. Per TSRM e studenti.", schema)}
<body>
{NAV}
<div class="breadcrumb"><a href="/" data-i18n="navHome">Home</a><span>›</span><span data-i18n="navGloss">Glossario</span></div>
<main class="page-content hub-content">
  <div class="card"><div class="card-head">
    <h1 data-i18n="hubTitle">Glossario di radiologia</h1>
    <p data-i18n="hubSub" style="font-size:14px;color:var(--text2);margin-top:4px;">94 termini tecnici, anatomici e formule spiegati in modo chiaro — per TSRM e studenti.</p>
  </div></div>
  {CTA}
  <div class="gloss-search">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <input type="text" id="gloss-filter" data-i18n-ph="search" placeholder="Cerca un termine…" autocomplete="off" aria-label="Cerca">
  </div>
  <div class="glossary-cols">{cols}</div>
  <div class="gloss-noresult" id="gloss-noresult" data-i18n="noResult">Nessun termine trovato.</div>
</main>
{FOOTER}
{SETLANG % (json.dumps(ld, ensure_ascii=False), HUB_SEARCH_JS)}
</body>
</html>
"""
    return body

def update_sitemap(data):
    txt = SITEMAP.read_text(encoding="utf-8")
    # rimuovi vecchie righe glossario (semplici)
    # re.S: le entry glossario sono multiriga (xhtml:link hreflang) — senza
    # DOTALL non verrebbero rimosse e la rigenerazione creerebbe duplicati.
    txt = re.sub(r'\n?\s*<url><loc>https://radindex\.app/glossario/[^<]*</loc>.*?</url>', '', txt, flags=re.S)
    def entry(loc):
        alts = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{l}" href="{loc}?lang={l}"/>' for l in LANGS)
        alts += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{loc}"/>'
        return f'  <url><loc>{loc}</loc><lastmod>{LASTMOD}</lastmod><changefreq>monthly</changefreq><priority>{"0.8" if loc.endswith("/glossario/") else "0.6"}</priority>{alts}\n  </url>'
    entries = [entry("https://radindex.app/glossario/")] + [entry(f"https://radindex.app/glossario/{s}.html") for s in data]
    txt = txt.replace("</urlset>", "\n".join(entries) + "\n</urlset>")
    SITEMAP.write_text(txt, encoding="utf-8")
    return len(entries)

if __name__ == "__main__":
    data = json.load(open(I18N, encoding="utf-8"))
    projs, dfc = load_projections()
    OUT.mkdir(exist_ok=True)
    nproj = 0
    for slug, v in data.items():
        (OUT / f"{slug}.html").write_text(term_page(slug, v, data, projs, dfc), encoding="utf-8")
        nproj += len(match_projections(v["it"]["termine"], projs, dfc))
    (OUT / "index.html").write_text(hub_page(data), encoding="utf-8")
    n = update_sitemap(data)
    print(f"Generati {len(data)} termini + hub TRILINGUE | cross-link proiezioni: {nproj} | sitemap: {n} URL glossario (con hreflang)")
