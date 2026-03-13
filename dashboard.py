import streamlit as st
# brapi.dev — cotações B3 em tempo real
try:
    import sys as _sys
    _sys.path.insert(0, "/opt/shipyard")
    import brapi_client as _brapi
    _HAS_BRAPI = True
except Exception as _be:
    _HAS_BRAPI = False

# brapi.dev — cotações B3 em tempo real
try:
    import sys as _sys
    _sys.path.insert(0, "/opt/shipyard")
    import brapi_client as _brapi
    _HAS_BRAPI = True
except Exception as _be:
    _HAS_BRAPI = False

try:
    from streamlit_autorefresh import st_autorefresh
    _HAS_AUTOREFRESH = True
except ImportError:
    _HAS_AUTOREFRESH = False
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json, math, base64, io, os
from pathlib import Path
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

SEGMENTOS_B3 = {
    "WEGE3.SA":"Novo Mercado","COGN3.SA":"Novo Mercado","PETR4.SA":"Nível 2",
    "VALE3.SA":"Novo Mercado","ABEV3.SA":"Nível 2","BBAS3.SA":"Novo Mercado",
    "ITUB4.SA":"Nível 1","PETR3.SA":"Nível 2","BBDC4.SA":"Nível 1",
    "SUZB3.SA":"Novo Mercado","EMBR3.SA":"Novo Mercado","RAIL3.SA":"Novo Mercado",
    "CPLE6.SA":"Nível 2","EGIE3.SA":"Novo Mercado","TAEE11.SA":"Nível 2",
    "CPFE3.SA":"Novo Mercado","EQTL3.SA":"Novo Mercado","SBSP3.SA":"Novo Mercado",
    "BRFS3.SA":"Novo Mercado","KLBN11.SA":"Novo Mercado","SLCE3.SA":"Novo Mercado",
    "YDUQ3.SA":"Novo Mercado","ANIM3.SA":"Novo Mercado","RADL3.SA":"Novo Mercado",
    "BBSE3.SA":"Novo Mercado","IRBR3.SA":"Novo Mercado","STBP3.SA":"Novo Mercado",
}

st.set_page_config(
    page_title="Shipyard | Vela Capital",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── PALETA VELA CAPITAL ───────────────────────────────────────────
C = {
    "bg":      "#141E31", "bg2":    "#0F1E30", "bg3":    "#2351FE",
    "bg4":     "#0a1624", "border": "#1a3a5c", "white":  "#FFFFFF",
    "gray":    "#9AC0E6", "gray2":  "#6a8fbf", "blue_lt":"#2351FE",
    "pos":     "#2ECC71", "neg":    "#E05555",
    "teal":    "#044D4D", "navy":   "#0F558B", "sky":    "#9AC0E6",
}

# ── LOGOS EMPRESAS — Clearbit runtime ────────────────────────────
CLEARBIT_DOMAINS = {
    "WEGE3.SA":  "weg.net",
    "COGN3.SA":  "cogna.com.br",
    "VALE3.SA":  "vale.com",
    "ITUB4.SA":  "itau.com.br",
    "RENT3.SA":  "localiza.com",
    "PETR4.SA":  "petrobras.com.br",
    "BBAS3.SA":  "bb.com.br",
    "ABEV3.SA":  "ambev.com.br",
    "MGLU3.SA":  "magazineluiza.com.br",
    "RADL3.SA":  "raia.com.br",
    "ABEV3.SA":  "ambev.com.br",
    "BRKM5.SA":  "braskem.com.br",
    "CPFE3.SA":  "cpfl.com.br",
    "ELET6.SA":  "eletrobras.com",
    "ELET3.SA":  "eletrobras.com",
    "ENGI11.SA": "energisa.com.br",
    "ISAE4.SA":  "isacteep.com.br",
    "TRPL4.SA":  "isacteep.com.br",
    "TAEE11.SA": "taesa.com.br",
    "VBBR3.SA":  "vibra.com.br",
    "VALE3.SA":  "vale.com",
    "MOVI3.SA":  "movida.com.br",
    "PETZ3.SA":  "cobasi.com.br",
    "PRIO3.SA":  "prio3.com.br",
    "MILS3.SA":  "mills.com.br",
    "LOGN3.SA":  "log-in.com.br",
    "PGMN3.SA":  "paguemenos.com.br",
    "OIBR3.SA":  "oi.com.br",
    "FLRY3.SA":  "fleury.com.br",
    "WEGE3.SA":  "weg.net",
    "COGN3.SA":  "cogna.com.br",
    "PETR4.SA":  "petrobras.com.br",
    "TAEE11.SA": "taesa.com.br",
    "ENGI11.SA": "energisa.com.br",
    "ISAE4.SA":  "isacteep.com.br",
    "LOGN3.SA":  "log-in.com.br",
    "PGMN3.SA":  "paguemenos.com.br",
    "VBBR3.SA":  "vibra.com.br",
    "MILS3.SA":  "mills.com.br",
    "MOVI3.SA":  "movida.com.br",
    "PRIO3.SA":  "prio3.com.br",
    "BRKM5.SA":  "braskem.com.br",
    "CPFE3.SA":  "cpfl.com.br",
    "ELET6.SA":  "eletrobras.com",
    "FLRY3.SA":  "fleury.com.br",
    "OIBR3.SA":  "oi.com.br",
}

@st.cache_data(ttl=86400)

def _brl(v, dec=0):
    """Formata valor em BRL: R$ 1.234.567,89"""
    try:
        v = float(v)
        s = f"{v:,.{dec}f}".replace(",","X").replace(".",",").replace("X",".")
        return f"R$ {s}"
    except: return "R$ —"


def _norm_setor(s):
    if not s: return "Outros"
    s2 = s.upper()
    MAP = {
        "Petróleo & Gás":    ["PETRO","OIL","GAS","COMBUST","REFIN"],
        "Mineração":         ["MINER","SIDER","META","AÇO","FERRO"],
        "Energia Elétrica":  ["ENERG","ELET","POWER","GERAÇ","TRANS","DISTRIB"],
        "Financeiro":        ["BANCO","FINANC","SEGUR","PREVIDÊN","CREDIT","LEASING"],
        "Consumo Básico":    ["ALIM","BEBID","SUPER","VAREJO ALIM","HIGIENE","COSM"],
        "Consumo Discrec.":  ["VAREJO","MODA","VEST","AUTOMOBI","CONCESSION","LOCAÇ"],
        "Saúde":             ["SAÚDE","FARM","HOSPIT","DIAGNÓST","MEDIC","LAB"],
        "Tecnologia":        ["TECNO","SOFTW","INFORM","DADOS","TI","DIGITAL"],
        "Telecomunicações":  ["TELEC","TELEFO","OPERADO","MÓVEL","BANDA"],
        "Educação":          ["EDUC","ENSINO","UNIVERS","ESCOLA","CURSOS"],
        "Saneamento":        ["SANEAM","ÁGUA","ESGOTO","RESIDUO"],
        "Transportes":       ["TRANSP","FERROVI","RODOVI","PORTO","LOGÍST","AÉREA"],
        "Agronegócio":       ["AGRO","SUCROAL","AÇÚCAR","ETANOL","PAPEL","CELULOSE","MADEIRA","GRÃO","SOJA"],
        "Construção Civil":  ["CONSTRU","IMOBIL","INCORPOR","CIMENTO","TINTA"],
        "Bens Industriais":  ["INDUST","MAQUIN","EQUIPAM","MECÂN","ELETRO","MOTOR"],
        "Seguros":           ["SEGUR","RESSEGUR","PREVIDÊN"],
    }
    for setor, kws in MAP.items():
        if any(k in s2 for k in kws): return setor
    return s if s and s != "DEFAULT" else "Outros"


def fetch_logo_b64(ticker: str) -> str | None:
    domain = CLEARBIT_DOMAINS.get(ticker)
    if not domain: return None
    urls = [
        f"https://logo.clearbit.com/{domain}",
        f"https://www.google.com/s2/favicons?domain={domain}&sz=128",
    ]
    try:
        import requests
        for url in urls:
            try:
                r = requests.get(url, timeout=4, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200 and len(r.content) > 500:
                    return base64.b64encode(r.content).decode()
            except Exception: continue
    except ImportError:
        import urllib.request
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = resp.read()
                    if len(data) > 500: return base64.b64encode(data).decode()
            except Exception: continue
    return None

def _svg_logo(sigla, bg, fg):
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="110" height="50">'
         f'<rect width="110" height="50" rx="5" fill="{bg}"/>'
         f'<text x="55" y="33" font-family="Helvetica,Arial" font-weight="700" '
         f'font-size="18" fill="{fg}" text-anchor="middle">{sigla}</text></svg>')
    return base64.b64encode(s.encode()).decode()

SVG_FALLBACKS = {
    "WEGE3.SA":  _svg_logo("WEG",   C["bg3"], C["white"]),
    "COGN3.SA":  _svg_logo("COGNA", C["bg4"], C["blue_lt"]),
    "VALE3.SA":  _svg_logo("VALE",  C["bg4"], C["gray"]),
    "ITUB4.SA":  _svg_logo("ITUB",  C["bg3"], C["white"]),
    "RENT3.SA":  _svg_logo("RENT3", C["bg2"], C["blue_lt"]),
    "ABEV3.SA":  _svg_logo("ABEV",  C["bg3"], C["white"]),
    "BRKM5.SA":  _svg_logo("BRKM",  C["bg4"], C["blue_lt"]),
    "CPFE3.SA":  _svg_logo("CPFL",  C["bg3"], C["white"]),
    "ELET6.SA":  _svg_logo("ELET",  C["bg4"], C["blue_lt"]),
    "ELET3.SA":  _svg_logo("ELET",  C["bg4"], C["blue_lt"]),
    "ENGI11.SA": _svg_logo("ENGI",  C["bg3"], C["white"]),
    "ISAE4.SA":  _svg_logo("ISAE",  C["bg4"], C["blue_lt"]),
    "TAEE11.SA": _svg_logo("TAEE",  C["bg3"], C["white"]),
    "VBBR3.SA":  _svg_logo("VIBR",  C["bg4"], C["blue_lt"]),
    "MOVI3.SA":  _svg_logo("MOVI",  C["bg3"], C["white"]),
    "PRIO3.SA":  _svg_logo("PRIO",  C["bg4"], C["blue_lt"]),
    "MILS3.SA":  _svg_logo("MILS",  C["bg3"], C["white"]),
    "LOGN3.SA":  _svg_logo("LOGN",  C["bg4"], C["blue_lt"]),
    "PGMN3.SA":  _svg_logo("PGMN",  C["bg3"], C["white"]),
    "RADL3.SA":  _svg_logo("RADL",  C["bg4"], C["blue_lt"]),
    "MGLU3.SA":  _svg_logo("MGLU",  C["bg3"], C["white"]),
    "PETR4.SA":  _svg_logo("PETR",  C["bg4"], C["blue_lt"]),
    "OIBR3.SA":  _svg_logo("OI",    C["bg3"], C["white"]),
    "FLRY3.SA":  _svg_logo("FLRY",  C["bg4"], C["blue_lt"]),
}

def logo_empresa_html(ticker, width=110):
    b64 = fetch_logo_b64(ticker)
    if b64:
        return f'<img src="data:image/png;base64,{b64}" width="{width}" style="border-radius:6px;background:#fff;padding:4px;display:block;"/>'
    fb = SVG_FALLBACKS.get(ticker, _svg_logo(ticker[:5], C["bg4"], C["blue_lt"]))
    return f'<img src="data:image/svg+xml;base64,{fb}" width="{width}" style="border-radius:5px;display:block;"/>'

# ── CSS ───────────────────────────────────────────────────────────
st.markdown(f"""<style>

    
* {{ font-family: Helvetica,"Helvetica Neue",Arial,sans-serif !important; }}
.stApp {{ background:{C['bg']}; color:{C['white']}; }}
[data-testid="stSidebar"] {{ background:{C['bg']} !important; border-right:1px solid {C['border']}; }}
[data-testid="metric-container"] {{ background:{C['bg2']}; border:1px solid {C['border']}; border-radius:6px; padding:14px 16px; }}
[data-testid="stMetricValue"] {{ color:{C['blue_lt']} !important; font-size:1.4rem !important; font-weight:700; }}
[data-testid="stMetricLabel"] {{ color:{C['gray2']} !important; font-size:0.68rem !important; text-transform:uppercase; letter-spacing:.1em; }}
h1 {{ color:{C['white']} !important; font-size:1.3rem !important; font-weight:700; }}
h2 {{ color:{C['white']} !important; font-size:1.0rem !important; font-weight:600;
      border-bottom:1px solid {C['border']}; padding-bottom:5px; margin-top:22px !important; }}
h3 {{ color:{C['gray2']} !important; font-size:.76rem !important; text-transform:uppercase; letter-spacing:.1em; }}
.stSelectbox>div>div {{ background:{C['bg2']}; border:1px solid {C['border']}; color:{C['white']}; border-radius:5px; font-weight:700; font-size:.95rem; }}
/* Tab labels em negrito */
[data-testid="stTab"] button p {{ font-weight:700 !important; }}
button[data-baseweb="tab"] {{ font-weight:700 !important; }}
/* ── DataFrames / tabelas ── */
.stDataFrame {{ border:1px solid {C['border']}; border-radius:6px; overflow:hidden; background:{C['bg2']}; }}
.stDataFrame > div {{ background:{C['bg2']} !important; }}
/* Novo componente Arrow (glide-data-grid) */
[data-testid="stDataFrame"] {{ background:{C['bg2']} !important; border:1px solid {C['border']}; border-radius:6px; }}
[data-testid="stDataFrame"] > div {{ background:{C['bg2']} !important; }}
/* Canvas do glide-data-grid fica em cima — forçar background do container */
.dvn-scroller {{ background:{C['bg2']} !important; }}
.stDataFrame canvas {{ filter: invert(0); }}
/* Fallback: tabelas HTML simples */
thead tr th {{ background:{C['bg4']} !important; color:{C['blue_lt']} !important; font-size:.72rem !important; text-transform:uppercase; }}
tbody tr {{ background:{C['bg2']} !important; color:{C['white']} !important; }}
tbody tr:nth-child(even) {{ background:rgba(15,85,139,.10) !important; }}
tbody tr:hover {{ background:rgba(35,81,254,.15) !important; }}
td, th {{ color:{C['white']} !important; border-color:{C['border']} !important; }}
/* st.table */
.stTable table {{ background:{C['bg2']} !important; color:{C['white']} !important; border-collapse:collapse; width:100%; }}
.stTable th {{ background:{C['bg4']} !important; color:{C['blue_lt']} !important; padding:8px; border:1px solid {C['border']}; }}
.stTable td {{ color:{C['white']} !important; padding:7px; border:1px solid {C['border']}; }}
.badge-c {{ background:#0a1a3a;color:#2351FE;border:1px solid #2351FE;border-radius:4px;padding:3px 12px;font-weight:700;font-size:.8rem;display:inline-block; }}
.badge-n {{ background:#1a1a0d;color:{C['gray']};border:1px solid {C['gray']};border-radius:4px;padding:3px 12px;font-weight:700;font-size:.8rem;display:inline-block; }}
.badge-v {{ background:#2a1010;color:{C['neg']};border:1px solid {C['neg']};border-radius:4px;padding:3px 12px;font-weight:700;font-size:.8rem;display:inline-block; }}
.emp-card {{ background:{C['bg2']};border:1px solid {C['border']};border-radius:8px;padding:18px;margin-bottom:10px; }}
.news-card {{ background:{C['bg2']};border:1px solid {C['border']};border-radius:8px;padding:14px 18px;margin-bottom:10px; }}
hr {{ border-color:{C['border']} !important; margin:10px 0 !important; }}
/* ── Sidebar sempre visível / sem collapse ── */
[data-testid="collapsedControl"] {{ display: none !important; pointer-events: none !important; }}
[data-testid="stSidebarCollapseButton"] {{ display: none !important; pointer-events: none !important; }}
button[data-testid="baseButton-headerNoPadding"] {{ display: none !important; pointer-events: none !important; }}
/* Força sidebar sempre aberto */
section[data-testid="stSidebar"] {{
    min-width: 240px !important; max-width: 240px !important;
    transform: none !important; visibility: visible !important;
    left: 0 !important; margin-left: 0 !important;
}}
section[data-testid="stSidebar"][aria-expanded="false"] {{
    transform: none !important; left: 0 !important; margin-left: 0 !important;
}}
.main .block-container {{ margin-left: 0 !important; }}
/* Barra rosa/decoração do topo */
[data-testid="stDecoration"] {{ display: none !important; }}
header[data-testid="stHeader"] {{ background:{C['bg']} !important; border-bottom: 1px solid {C['border']} !important; }}
header[data-testid="stHeader"] button {{ display: none !important; pointer-events: none !important; }}

    /* Todos os botões — sem vermelho */
.stButton > button {{
    background:{C['bg2']} !important; color:{C['white']} !important;
    border:1px solid {C['border']} !important; border-radius:5px !important;
    font-weight:600 !important; font-size:.85rem !important;
}}
.stButton > button:hover {{
    background:{C['bg3']} !important; border-color:{C['blue_lt']} !important; color:{C['white']} !important;
}}
/* Sliders — remove vermelho, usa azul Vela */
[data-testid="stSlider"] > div > div > div > div {{
    background:{C['blue_lt']} !important;
}}
[data-testid="stSlider"] > div > div > div > div > div {{
    background:{C['blue_lt']} !important; border-color:{C['blue_lt']} !important;
}}
div[data-baseweb="slider"] [role="slider"] {{
    background:{C['blue_lt']} !important; border-color:{C['blue_lt']} !important;
}}
/* Track do slider */
div[data-baseweb="slider"] > div {{ background:{C['border']} !important; }}
div[data-baseweb="slider"] > div > div {{ background:{C['blue_lt']} !important; }}
.sidebar-footer {{ position:fixed;bottom:18px;left:0;width:238px;text-align:center;font-size:.62rem;color:{C['gray2']};opacity:.4; }}
/* Checkboxes e Radio — sem vermelho */
[data-testid="stCheckbox"] label span, [data-testid="stRadio"] label span {{
    color:{C['white']} !important;
}}
input[type="checkbox"]:checked + div, input[type="radio"]:checked + div {{
    background:{C['blue_lt']} !important; border-color:{C['blue_lt']} !important;
}}
/* Multiselect tags — remove vermelho */
[data-baseweb="tag"] {{ background:{C['bg3']} !important; color:{C['white']} !important; }}
[data-baseweb="tag"] span {{ color:{C['white']} !important; }}
/* Text inputs */
.stTextInput > div > div > input {{ background:{C['bg2']} !important; color:{C['white']} !important; border:1px solid {C['border']} !important; }}
/* Progress/spinner color */
.stProgress > div > div > div > div {{ background:{C['blue_lt']} !important; }}

/* ── REMOVE VERMELHO STREAMLIT GLOBAL ── */
:root {{
    --primary-color: {C['blue_lt']} !important;
    --secondary-background-color: {C['bg2']} !important;
    --text-color: {C['white']} !important;
}}

/* Radio buttons — pontinho azul, não vermelho */
[data-baseweb="radio"] label > div:first-child {{
    border-color: {C['border']} !important;
    background-color: transparent !important;
}}
[data-baseweb="radio"] [aria-checked="true"] > div:first-child {{
    border-color: {C['blue_lt']} !important;
    background-color: {C['blue_lt']} !important;
}}
[data-baseweb="radio"] [aria-checked="true"] > div:first-child > div {{
    background-color: {C['white']} !important;
}}
[data-baseweb="radio"] label span {{
    color: {C['white']} !important;
}}

/* Checkbox — azul, não vermelho */
[data-baseweb="checkbox"] label > div:first-child {{
    border-color: {C['border']} !important;
    background-color: transparent !important;
}}
[data-baseweb="checkbox"] [aria-checked="true"] > div:first-child {{
    background-color: {C['blue_lt']} !important;
    border-color: {C['blue_lt']} !important;
}}
[data-baseweb="checkbox"] label span {{
    color: {C['white']} !important;
}}

/* Slider — linha e handle azul, não vermelho */
[data-testid="stSlider"] [role="slider"] {{
    background-color: {C['blue_lt']} !important;
    border-color: {C['blue_lt']} !important;
}}
div[data-baseweb="slider"] [data-testid="stTickBar"] {{
    color: {C['gray']} !important;
}}
/* Slider track preenchido */
div[data-baseweb="slider"] > div > div:nth-child(3) > div {{
    background: {C['blue_lt']} !important;
}}

/* Number input — remove vermelho nos botões +/- */
[data-testid="stNumberInput"] > div > div > div > button {{
    color: {C['white']} !important;
    border-color: {C['border']} !important;
}}
[data-testid="stNumberInput"] > div > div > div > button:hover {{
    background: {C['bg3']} !important;
    border-color: {C['blue_lt']} !important;
}}

/* Text do label de todos os widgets — branco, não cinza */
[data-testid="stSelectbox"] label p,
[data-testid="stMultiSelect"] label p,
[data-testid="stNumberInput"] label p,
[data-testid="stTextInput"] label p,
[data-testid="stSlider"] label p,
[data-testid="stRadio"] label p,
[data-testid="stCheckbox"] label p {{
    color: {C['white']} !important;
    font-size: .8rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: .5px !important;
}}

/* Caption / helper text — sky, não cinza escuro */
[data-testid="stCaptionContainer"] p {{
    color: {C['sky']} !important;
    opacity: .75 !important;
}}

/* Info/warning/success — bordas azuis */
[data-testid="stAlert"][data-baseweb="notification"] {{
    border-left-color: {C['blue_lt']} !important;
}}

/* Markdown default text — branco */
[data-testid="stMarkdownContainer"] p {{
    color: {C['white']} !important;
}}

/* h2/h3 em conteúdo — override mais específico */
.main h2, .main h3 {{
    color: {C['white']} !important;
}}

/* Multiselect tags — cor certa */
[data-baseweb="tag"] svg {{
    fill: {C['white']} !important;
}}

/* Remove borda roxa/vermelha de focus */
input:focus, textarea:focus, [data-baseweb="input"]:focus-within {{
    border-color: {C['blue_lt']} !important;
    box-shadow: 0 0 0 2px rgba(35,81,254,.25) !important;
    outline: none !important;
}}
[data-baseweb="select"]:focus-within > div {{
    border-color: {C['blue_lt']} !important;
    box-shadow: 0 0 0 2px rgba(35,81,254,.25) !important;
}}

/* ── CITADEL-STYLE: Métricas mais densas e profissionais ── */
[data-testid="metric-container"] {{
    background: {C['bg2']} !important;
    border: 1px solid {C['border']} !important;
    border-radius: 6px !important;
    padding: 12px 14px !important;
    position: relative !important;
}}
[data-testid="metric-container"]::before {{
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: {C['blue_lt']};
    border-radius: 6px 0 0 6px;
}}
[data-testid="stMetricValue"] {{
    color: {C['white']} !important;
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    font-variant-numeric: tabular-nums !important;
}}
[data-testid="stMetricLabel"] {{
    color: {C['sky']} !important;
    font-size: .65rem !important;
    text-transform: uppercase !important;
    letter-spacing: .8px !important;
    font-weight: 600 !important;
}}
[data-testid="stMetricDelta"] {{
    font-size: .78rem !important;
    font-weight: 700 !important;
}}

/* ── INPUT / SELECTBOX / MULTISELECT fundo dark ── */
[data-baseweb="select"] > div {{
    background:{C['bg2']} !important; border-color:{C['border']} !important;
    color:{C['white']} !important; border-radius:5px !important;
}}
[data-baseweb="select"] > div:hover {{ border-color:{C['blue_lt']} !important; }}
[data-baseweb="select"] svg {{ color:{C['gray']} !important; fill:{C['gray']} !important; }}
[data-baseweb="popover"] ul {{
    background:{C['bg2']} !important; border:1px solid {C['border']} !important;
}}
[data-baseweb="popover"] * {{ color:{C['white']} !important; }}
[data-baseweb="option"] {{ color:{C['white']} !important; background:{C['bg2']} !important; }}
[data-baseweb="option"]:hover {{ background:{C['bg3']} !important; color:{C['white']} !important; }}
[data-baseweb="option"][aria-selected="true"] {{ background:rgba(35,81,254,.18) !important; color:{C['blue_lt']} !important; }}
[data-baseweb="option"] span {{ color:{C['white']} !important; }}
[data-baseweb="option"] div {{ color:{C['white']} !important; }}
[data-baseweb="menu"] {{ background:{C['bg2']} !important; }}
[data-baseweb="menu"] * {{ color:{C['white']} !important; }}
ul[role="listbox"] {{ background:{C['bg2']} !important; }}
ul[role="listbox"] li {{ color:{C['white']} !important; background:{C['bg2']} !important; }}
ul[role="listbox"] li * {{ color:{C['white']} !important; }}

/* ── NUMBER INPUT ── */
[data-baseweb="base-input"] input {{
    background:{C['bg2']} !important; color:{C['white']} !important;
    border-color:{C['border']} !important;
}}
[data-testid="stNumberInput"] button {{
    background:{C['bg2']} !important; border-color:{C['border']} !important;
    color:{C['white']} !important;
}}
[data-testid="stNumberInput"] button:hover {{
    background:{C['bg3']} !important; border-color:{C['blue_lt']} !important;
}}

/* ── TEXTAREA ── */
textarea {{ background:{C['bg2']} !important; color:{C['white']} !important; border-color:{C['border']} !important; }}

/* ── MULTISELECT tag X button ── */
[data-baseweb="tag"] button {{ color:{C['white']} !important; }}

/* ── TABS — ativa usa azul, não vermelho ── */
[data-baseweb="tab-list"] {{ background:{C['bg']} !important; border-bottom:1px solid {C['border']} !important; gap:4px; }}
[data-baseweb="tab"] {{
    background:transparent !important; color:{C['gray']} !important;
    border-bottom:2px solid transparent !important;
    font-weight:600 !important; font-size:.82rem !important;
    padding:8px 16px !important;
    transition: color .15s, border-color .15s !important;
}}
[data-baseweb="tab"]:hover {{ color:{C['white']} !important; }}
[aria-selected="true"][data-baseweb="tab"] {{
    color:{C['blue_lt']} !important;
    border-bottom:2px solid {C['blue_lt']} !important;
    background:transparent !important;
}}

/* ── METRIC DELTA — positivo verde, negativo vermelho ── */
[data-testid="stMetricDelta"] > div[data-direction="up"] {{
    color:{C['pos']} !important;
}}
[data-testid="stMetricDelta"] > div[data-direction="down"] {{
    color:{C['neg']} !important;
}}
[data-testid="stMetricDelta"] svg {{ width:12px; height:12px; }}

/* ── EXPANDIR / EXPANDER ── */
[data-testid="stExpander"] {{ background:{C['bg2']} !important; border:1px solid {C['border']} !important; border-radius:6px !important; }}
[data-testid="stExpander"] summary {{ color:{C['white']} !important; font-weight:600 !important; }}

/* ── ALERT / INFO / WARNING / SUCCESS ── */
[data-testid="stAlert"] {{ border-radius:6px !important; border-left-width:4px !important; }}

/* ── MAIN BLOCK CONTAINER padding ── */
.main .block-container {{
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 1400px !important;
}}

/* ── SIDEBAR: espaçamento interno ── */
[data-testid="stSidebar"] > div:first-child {{
    padding-top: 1.2rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}}

/* ── SPINNER ── */
[data-testid="stSpinner"] {{ color:{C['blue_lt']} !important; }}

/* ── CAPTION / SMALL TEXT ── */
[data-testid="stCaptionContainer"] {{ color:{C['gray']} !important; }}

/* ── DIVIDER ── */
[data-testid="stMarkdownContainer"] hr {{
    border-color:{C['border']} !important; margin: 1.2rem 0 !important;
}}

/* ── SCROLLBAR ── */
::-webkit-scrollbar {{ width:6px; height:6px; }}
::-webkit-scrollbar-track {{ background:{C['bg']}; }}
::-webkit-scrollbar-thumb {{ background:{C['border']}; border-radius:3px; }}
::-webkit-scrollbar-thumb:hover {{ background:{C['blue_lt']}; }}

/* ── TOOLTIP ── */
[data-testid="stTooltipIcon"] {{ color:{C['gray']} !important; }}

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"] {{
    background:{C['bg2']} !important; border:1px dashed {C['border']} !important;
    border-radius:6px !important;
}}

/* ── REMOVE debug / developer menu ── */
#MainMenu {{ visibility: hidden !important; }}
footer {{ visibility: hidden !important; }}

/* ══ CITADEL-STYLE ENHANCEMENTS ══════════════════════════════════ */

/* Fontes tabulares em números — alinhamento profissional */
[data-testid="stMetricValue"],
.stDataFrame, td, th {{
    font-variant-numeric: tabular-nums !important;
    font-feature-settings: "tnum" !important;
}}

/* Section headers estilo Citadel — linha accent à esquerda */
.main h2 {{
    color: {C['white']} !important;
    font-size: 0.92rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
    border-left: 3px solid {C['blue_lt']} !important;
    padding-left: 10px !important;
    border-bottom: none !important;
    margin: 24px 0 12px !important;
}}

/* h3 — subtítulo discreto */
.main h3 {{
    color: {C['sky']} !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.2px !important;
    margin: 18px 0 8px !important;
}}

/* Plotly charts — sem fundo branco */
.js-plotly-plot .plotly, .js-plotly-plot .plotly .main-svg {{
    background: transparent !important;
}}

/* Linhas de separação HR — accent */
.main hr {{
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, {C['blue_lt']}60, {C['border']}, transparent) !important;
    margin: 20px 0 !important;
}}

/* Tab list — estilo Citadel (underline accent) */
[data-baseweb="tab-list"] {{
    background: transparent !important;
    border-bottom: 1px solid {C['border']} !important;
    gap: 0 !important;
}}
[data-baseweb="tab"] {{
    background: transparent !important;
    color: {C['sky']} !important;
    border-bottom: 3px solid transparent !important;
    font-weight: 600 !important;
    font-size: .78rem !important;
    text-transform: uppercase !important;
    letter-spacing: .8px !important;
    padding: 8px 18px !important;
    transition: all .15s !important;
}}
[data-baseweb="tab"]:hover {{
    color: {C['white']} !important;
    background: rgba(35,81,254,.06) !important;
}}
[aria-selected="true"][data-baseweb="tab"] {{
    color: {C['white']} !important;
    border-bottom: 3px solid {C['blue_lt']} !important;
    background: rgba(35,81,254,.08) !important;
}}

/* Selectbox valor selecionado — branco */
[data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
[data-baseweb="select"] > div > div > div {{
    color: {C['white']} !important;
}}

/* Spinner text */
.stSpinner p {{ color: {C['sky']} !important; }}

/* Sidebar nav item hover */
.sidebar-nav-item:hover {{ color: {C['white']} !important; }}

/* Sidebar footer */
.sidebar-footer {{
    position: fixed; bottom: 14px; left: 0; width: 238px;
    text-align: center; font-size: .58rem;
    color: {C['gray2']}; opacity: .35;
    letter-spacing: 1px; text-transform: uppercase;
}}
</style>""", unsafe_allow_html=True)

# JavaScript: desabilita botão de collapse da sidebar
st.markdown("""
<script>
(function keepSidebarOpen() {
    function disableCollapseBtn() {
        const btns = document.querySelectorAll(
            '[data-testid="collapsedControl"], [data-testid="stSidebarCollapseButton"], ' +
            'button[data-testid="baseButton-headerNoPadding"]'
        );
        btns.forEach(b => {
            b.style.display = 'none';
            b.style.pointerEvents = 'none';
            b.onclick = e => e.stopPropagation();
        });
        // Se sidebar foi colapsada, reabre
        const sidebar = document.querySelector('[data-testid="stSidebar"]');
        if (sidebar && sidebar.getAttribute('aria-expanded') === 'false') {
            const openBtn = document.querySelector('[data-testid="collapsedControl"] button');
            if (openBtn) openBtn.click();
        }
    }
    disableCollapseBtn();
    const obs = new MutationObserver(disableCollapseBtn);
    obs.observe(document.body, { childList: true, subtree: true, attributes: true });
    setInterval(disableCollapseBtn, 1000);
})();
</script>
""", unsafe_allow_html=True)

PL = dict(
    paper_bgcolor=C["bg"], plot_bgcolor=C["bg2"],
    font=dict(family="Helvetica,Arial", color=C["gray"], size=11),
    xaxis=dict(gridcolor=C["border"], zerolinecolor=C["border"], tickfont=dict(color=C["gray2"])),
    yaxis=dict(gridcolor=C["border"], zerolinecolor=C["border"], tickfont=dict(color=C["gray2"])),
    margin=dict(l=45, r=25, t=40, b=38),
    legend=dict(bgcolor=C["bg"], bordercolor=C["border"], font=dict(color=C["gray"])),
)

# ── AUTH ──────────────────────────────────────────────────────────
def load_auth():
    p = Path("dashboard_auth.yaml")
    if not p.exists():
        st.error(" dashboard_auth.yaml não encontrado. Execute: python setup_auth.py"); st.stop()
    with open(p) as f:
        return yaml.load(f, Loader=SafeLoader)

cfg = load_auth()
auth = stauth.Authenticate(cfg["credentials"], cfg["cookie"]["name"],
                           cfg["cookie"]["key"], cfg["cookie"]["expiry_days"])
try:
    result = auth.login(location="main")
    if isinstance(result, tuple):
        name, auth_status, username = result
    else:
        name = st.session_state.get("name")
        auth_status = st.session_state.get("authentication_status")
        username = st.session_state.get("username")
except Exception as e:
    st.error(f"Erro auth: {e}"); st.stop()

if auth_status is False:
    st.error("❌ Usuário ou senha incorretos."); st.stop()

if auth_status is None:
    # ── CSS fixo para tela de login ──────────────────────────
    st.markdown("""<style>
    /* Fixa largura do form de login e centraliza */
    [data-testid="stMainBlockContainer"] > div > div {
        max-width: 400px !important;
        margin: 0 auto !important;
        padding-top: 0 !important;
    }
    /* Esconde a sidebar no login */
    [data-testid="stSidebar"] { display: none !important; }
    section[data-testid="stMain"] > div > div > div > div > div > form {
        background: transparent !important;
    }
    /* Inputs do login — fundo dark */
    [data-testid="stMainBlockContainer"] input {
        background: #0F1E30 !important;
        color: #FFFFFF !important;
        border: 1px solid #1a3a5c !important;
        border-radius: 6px !important;
    }
    [data-testid="stMainBlockContainer"] button[kind="primary"] {
        background: #2351FE !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        width: 100% !important;
    }
    [data-testid="stMainBlockContainer"] label {
        color: #9AC0E6 !important;
        font-size: .8rem !important;
        font-weight: 600 !important;
    }
    </style>""", unsafe_allow_html=True)
    # ── Header do login ──────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center;margin:48px auto 28px;padding:32px 28px 24px;
                background:#0F1E30;border:1px solid #1a3a5c;border-radius:12px;
                max-width:400px;box-shadow:0 12px 40px rgba(0,0,0,.5);">
        <div style="margin-bottom:12px">
            <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120' width='72' height='72'>
  <rect width='120' height='120' fill='none'/>
  <!-- Casco -->
  <path d='M15 85 Q60 100 105 85 L98 75 Q60 88 22 75 Z' fill='#9AC0E6'/>
  <!-- Mastro principal -->
  <line x1='60' y1='20' x2='60' y2='80' stroke='#9AC0E6' stroke-width='2.5'/>
  <!-- Mastro proa -->
  <line x1='35' y1='38' x2='35' y2='78' stroke='#9AC0E6' stroke-width='2'/>
  <!-- Vela principal grande -->
  <path d='M60 22 L95 55 L60 78 Z' fill='#2351FE' opacity='.9'/>
  <!-- Vela secundária -->
  <path d='M60 22 L25 52 L60 78 Z' fill='#0F558B' opacity='.85'/>
  <!-- Vela proa -->
  <path d='M35 40 L62 60 L35 76 Z' fill='#2351FE' opacity='.7'/>
  <!-- Bandeira -->
  <path d='M60 20 L75 14 L60 26 Z' fill='#9AC0E6'/>
  <!-- Ondas -->
  <path d='M10 90 Q25 85 40 90 Q55 95 70 90 Q85 85 100 90 Q110 93 115 90' 
        stroke='#9AC0E6' stroke-width='1.5' fill='none' opacity='.5'/>
  <path d='M5 96 Q20 91 35 96 Q50 101 65 96 Q80 91 95 96 Q108 99 118 96' 
        stroke='#9AC0E6' stroke-width='1' fill='none' opacity='.35'/>
</svg>
        </div>
        <div style="color:#FFFFFF;font-size:1.45rem;font-weight:900;letter-spacing:3.5px;margin-bottom:6px">
            VELA CAPITAL
        </div>
        <div style="width:40px;height:2px;background:#2351FE;margin:0 auto 10px"></div>
        <div style="color:#9AC0E6;font-size:.7rem;letter-spacing:3px;text-transform:uppercase;opacity:.8">
            SHIPYARD &middot; Análise Fundamentalista</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── DADOS ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_results():
    for fname in ["valuation_results_combined.json", "valuation_results.json"]:
        p = Path(fname)
        if p.exists(): break
    if not p.exists(): return {}
    with open(p) as f: return json.load(f)

results = load_results()
if not results:
    st.error(" valuation_results.json não encontrado. Execute: python main.py"); st.stop()

# Precos atualizados via cron update_prices.py
_live_prices = {}

# ── SIDEBAR ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;padding:22px 0 12px;">
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120' width='72' height='72'>
          <rect x='57' y='18' width='3' height='72' rx='1.5' fill='#9AC0E6'/>
          <path d='M60 22 L95 55 L60 78 Z' fill='#2351FE' opacity='.9'/>
          <path d='M60 22 L25 52 L60 78 Z' fill='#0F558B' opacity='.85'/>
          <path d='M35 40 L62 60 L35 76 Z' fill='#2351FE' opacity='.7'/>
          <path d='M60 20 L75 14 L60 26 Z' fill='#9AC0E6'/>
          <path d='M10 90 Q25 85 40 90 Q55 95 70 90 Q85 85 100 90 Q110 93 115 90'
                stroke='#9AC0E6' stroke-width='1.5' fill='none' opacity='.5'/>
          <path d='M5 96 Q20 91 35 96 Q50 101 65 96 Q80 91 95 96 Q108 99 118 96'
                stroke='#9AC0E6' stroke-width='1' fill='none' opacity='.35'/>
          <path d='M15 85 Q60 100 105 85 L98 75 Q60 88 22 75 Z' fill='#9AC0E6' opacity='.18'/>
        </svg>
        <div style="color:#FFFFFF;font-size:1.1rem;font-weight:800;letter-spacing:.2em;margin-top:8px">VELA CAPITAL</div>
        <div style="width:36px;height:2px;background:#2351FE;margin:5px auto 6px"></div>
        <div style="color:{C['gray2']};font-size:.58rem;letter-spacing:.25em;opacity:.7">SHIPYARD</div>
    </div><hr>""", unsafe_allow_html=True)

    MASTER_USER = "Leonardo.Losi"
    is_master = (username == MASTER_USER)

    _pages_base = [
        "Visão Geral", "Empresa", "Cotações",
        "FCFF & Projeções", "Comparativo",
        "Sensibilidade", "Markowitz",
        "Notícias", "Carteira Endurance",
        "Exposição Geográfica",
        "Governança", "Grupo Econômico", "Setores Macro",
        "Gestoras", "ComDinheiro", "Valuation", "Cadastros"
    ]
    _pages = _pages_base + (["── Admin ──", "Gerenciar Usuários"] if is_master else [])

    pagina = st.selectbox("nav", _pages, label_visibility="collapsed",
                      index=_pages.index("Empresa") if st.session_state.get("_nav_empresa") else 0)

    st.markdown("<hr>", unsafe_allow_html=True)
    _role = "Master" if is_master else "Diretor"
    _c_gray2   = C["gray2"]
    _c_blue_lt = C["blue_lt"]
    st.markdown(f"<div style='color:{_c_gray2};font-size:.72rem;padding:4px 0;'> {name} <span style='color:{_c_blue_lt};font-size:.65rem;'>({_role})</span></div>", unsafe_allow_html=True)
    # Auto-refresh
    # Esconde o input numérico gerado pelo st_autorefresh

    if _HAS_AUTOREFRESH:
        st.sidebar.markdown("---")
        _ron = st.sidebar.checkbox(" Auto-refresh", value=False, key="refresh_on")
        if _ron:
            _rint = st.sidebar.select_slider("Intervalo", [30,60,300,600], value=60, key="refresh_int",
                format_func=lambda x: f"{x}s" if x<60 else f"{x//60}min")
            _cnt = st_autorefresh(interval=_rint*1000, limit=None, key="autorefresh_ctrl")
    auth.logout("Sair", location="sidebar")
    st.markdown(f"<div class='sidebar-footer'>Vela Capital © 2026</div>", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────
bi    = lambda v: f"R$ {float(v)/1e9:.2f}bi" if v not in (None,'') else "n/d"
pct   = lambda v: f"{float(v)*100:.1f}%" if v not in (None,'') else "n/d"
price = lambda v: f"R$ {float(v):.2f}" if v not in (None,'') else "n/d"
f_    = lambda v,fmt=".2f": format(float(v),fmt) if v not in (None,'') else "n/d"

def badge(rec):
    rec = str(rec)
    if "COMPRA" in rec: return '<span class="badge-c">▲ COMPRA</span>'
    if "NEUTRO" in rec: return '<span class="badge-n">● NEUTRO</span>'
    return '<span class="badge-v">▼ VENDA FORTE</span>'

empresas = list(results.keys())
tickers_map = {emp: results[emp].get("ticker", emp) for emp in empresas}

def dark_table(df, color_fn=None):
    """Renderiza DataFrame como tabela HTML dark compatível com Streamlit."""
    hdrs = "".join(f'<th style="background:#0a1624;color:#2351FE;padding:8px 12px;'
                   f'border:1px solid #1a3a5c;font-size:.72rem;text-transform:uppercase;'
                   f'letter-spacing:.08em;">{c}</th>' for c in df.columns)
    rows_html = ""
    for i, row in df.iterrows():
        bg = "rgba(15,85,139,.10)" if int(str(i).split(".")[-1] if "." in str(i) else i or 0) % 2 == 0 else "#0F1E30"
        cells = ""
        for j, (col, val) in enumerate(row.items()):
            style_extra = color_fn(val) if color_fn else ""
            cells += (f'<td style="padding:7px 12px;border:1px solid #1a3a5c;'
                      f'color:#FFFFFF;{style_extra}">{val}</td>')
        rows_html += f'<tr style="background:{bg};">{cells}</tr>'
    return (f'<div style="overflow-x:auto;border:1px solid #1a3a5c;border-radius:6px;margin:8px 0;">'
            f'<table style="width:100%;border-collapse:collapse;font-family:Helvetica,Arial;font-size:.83rem;">'
            f'<thead><tr>{hdrs}</tr></thead><tbody>{rows_html}</tbody></table></div>')

# ── HELPERS EXPORT (#20) ─────────────────────────────────────────
def export_buttons(df: "pd.DataFrame", nome_base: str = "shipyard_export"):
    """Botões de download: CSV e Excel para qualquer DataFrame."""
    import io
    c1, c2 = st.columns([1, 1])
    with c1:
        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇ Baixar CSV",
            data=csv_data,
            file_name=f"{nome_base}.csv",
            mime="text/csv",
            key=f"dl_csv_{nome_base}",
        )
    with c2:
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Dados")
            buf.seek(0)
            st.download_button(
                label="⬇ Baixar Excel",
                data=buf.read(),
                file_name=f"{nome_base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"dl_xlsx_{nome_base}",
            )
        except ImportError:
            st.caption("openpyxl não instalado — apenas CSV disponível.")

def page_to_pdf_btn(label: str = "Baixar página como PDF"):
    """Instrução para salvar página como PDF via browser."""
    _bg = "#0a1624"; _bd = "#1a3a5c"; _fg = "#9AC0E6"
    st.markdown(
        f'<div style="background:{_bg};border:1px solid {_bd};border-radius:6px;'
        f'padding:10px 16px;margin:6px 0;font-size:.8rem;color:{_fg};">'
        f'Salvar como PDF: Use Ctrl+P → Destino: Salvar como PDF → Confirmar.</div>',
        unsafe_allow_html=True
    )

# ══════════════════════════════════════════════════════════════════
# HELPER — COTAÇÃO YFINANCE
# ══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=600)
def get_price_history(ticker, period="6mo"):
    try:
        import yfinance as yf
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_ibov(period="1y"):
    try:
        import yfinance as yf
        df = yf.download("^BVSP", period=period, auto_adjust=True, progress=False)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_beta_data(tk, periodo="3y"):
    """Retorna DataFrame com retornos diários da ação e do IBOV."""
    try:
        import yfinance as yf
        df_s = yf.download(tk, period=periodo, auto_adjust=True, progress=False)
        df_b = yf.download("^BVSP", period=periodo, auto_adjust=True, progress=False)
        if df_s.empty or df_b.empty:
            return pd.DataFrame()
        cl_s = df_s["Close"].squeeze()
        cl_b = df_b["Close"].squeeze()
        df = pd.DataFrame({"stock": cl_s, "ibov": cl_b}).dropna()
        df["r_stock"] = df["stock"].pct_change()
        df["r_ibov"]  = df["ibov"].pct_change()
        return df.dropna()
    except Exception:
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════════════
# PÁG 1 — VISÃO GERAL
# ══════════════════════════════════════════════════════════════════
if pagina == "Visão Geral":
    # ── Filtros e ordenação ────────────────────────────────────
    f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
    with f1:
        ordem_por = st.selectbox("Ordenar por", [
            "Nome", "Upside ↑", "Upside ↓", "EV ↓", "EV ↑",
            "WACC ↑", "WACC ↓", "Beta ↑", "Beta ↓",
            "EV/EBITDA ↑", "P/E ↑", "Margem EBIT ↓",
        ], key="vg_ordem")
    with f2:
        filtro_rec = st.multiselect("Recomendação", ["COMPRA FORTE","COMPRA","NEUTRO","VENDA","VENDA FORTE"],
                                    default=[], key="vg_rec",
                                    placeholder="Todas")
    with f3:
        filtro_upside_min = st.number_input("Upside mín (%)", value=-100, step=5, key="vg_up_min")
    with f4:
        filtro_upside_max = st.number_input("Upside máx (%)", value=200, step=5, key="vg_up_max")

    # Aplica filtros
    empresas_vg = list(results.keys())
    if filtro_rec:
        empresas_vg = [e for e in empresas_vg if
                       any(r in (results[e].get("recomendacao") or "") for r in filtro_rec)]
    empresas_vg = [e for e in empresas_vg if
                   filtro_upside_min <= float(results[e].get("upside") or 0) <= filtro_upside_max]

    # Ordena
    _sort_key = {
        "Nome":          lambda e: results[e].get("ticker", e).replace(".SA",""),
        "Upside ↑":      lambda e: float(results[e].get("upside") or 0),
        "Upside ↓":      lambda e: -float(results[e].get("upside") or 0),
        "EV ↓":          lambda e: -float(results[e].get("enterprise_value") or 0),
        "EV ↑":          lambda e: float(results[e].get("enterprise_value") or 0),
        "WACC ↑":        lambda e: float(results[e].get("wacc") or 0),
        "WACC ↓":        lambda e: -float(results[e].get("wacc") or 0),
        "Beta ↑":        lambda e: float(results[e].get("beta") or 0),
        "Beta ↓":        lambda e: -float(results[e].get("beta") or 0),
        "EV/EBITDA ↑":   lambda e: float(results[e].get("ev_ebitda") or 0),
        "P/E ↑":         lambda e: float(results[e].get("pe") or 0),
        "Margem EBIT ↓": lambda e: -float(results[e].get("ebit_margin") or 0),
    }
    empresas_vg = sorted(empresas_vg, key=_sort_key.get(ordem_por, lambda e: e))
    # Deduplica por ticker — manual tem prioridade sobre B3
    _seen = {}
    for _e in empresas_vg:
        _t = results[_e].get("ticker", _e)
        if _t not in _seen or not results[_e].get("cvm_code"):
            _seen[_t] = _e
    empresas_vg = list(_seen.values())

    if not empresas_vg:
        st.info("Nenhuma empresa corresponde aos filtros aplicados.")
        st.stop()

    st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;margin:8px 0 12px">
        <span style="color:{C['white']};font-size:1.1rem;font-weight:700">Visão Geral da Cobertura</span>
        <span style="color:{C['gray']};font-size:.75rem;background:{C['bg2']};border:1px solid {C['border']};
            border-radius:4px;padding:2px 10px">{len(empresas_vg)} empresa(s)</span>
    </div>""", unsafe_allow_html=True)

    _ncols = 3
    for _row_start in range(0, len(empresas_vg), _ncols):
        _row_emps = empresas_vg[_row_start:_row_start+_ncols]
        cols = st.columns(_ncols, gap="small")
        for i, emp in enumerate(_row_emps):
            r = results[emp]; ticker = r.get("ticker", emp); upside = r.get("upside") or 0
            with cols[i]:
                _up  = (upside or 0) * 100
                _uc  = C["pos"] if _up >= 0 else C["neg"]
                _ud  = f"{_up:+.1f}%"
                _rec = r.get("recomendacao", "—")
                _bc  = C["pos"] if "COMPRA" in str(_rec).upper() else (C["neg"] if "VENDA" in str(_rec).upper() else C["gray"])
                _nome = r.get("empresa", ticker.replace(".SA",""))
                st.markdown(f'''<div style="background:{C['bg2']};border:1px solid {C['border']};border-radius:10px;padding:16px 14px;margin-bottom:4px;min-width:0">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;min-width:0">
                    ''' + logo_empresa_html(ticker, 40) + f'''
                    <div style="flex:1;min-width:0;overflow:hidden">
                        <div style="color:{C['blue_lt']};font-weight:800;font-size:.95rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{ticker.replace('.SA','')}</div>
                        <div style="color:{C['gray']};font-size:.65rem;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{_nome[:28]}</div>
                    </div>
                    <div style="background:{_bc}22;border:1px solid {_bc};border-radius:4px;padding:2px 6px;font-size:.62rem;font-weight:700;color:{_bc};white-space:nowrap;flex-shrink:0">{_rec}</div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:6px">
                    <div style="background:{C['bg']};border-radius:6px;padding:8px 10px">
                        <div style="color:{C['gray']};font-size:.58rem;text-transform:uppercase;letter-spacing:.5px">Preco Tela</div>
                        <div style="color:{C['white']};font-weight:700;font-size:.92rem;margin-top:2px">{price(r.get('price_now'))}</div>
                    </div>
                    <div style="background:{C['bg']};border-radius:6px;padding:8px 10px">
                        <div style="color:{C['gray']};font-size:.58rem;text-transform:uppercase;letter-spacing:.5px">Preco Justo</div>
                        <div style="font-weight:700;font-size:.92rem;margin-top:2px">
                            <span style="color:{C['blue_lt']}">{price(r.get('price_fair'))}</span>
                            <span style="color:{_uc};font-size:.70rem;margin-left:4px">{_ud}</span>
                        </div>
                    </div>
                    <div style="background:{C['bg']};border-radius:6px;padding:8px 10px">
                        <div style="color:{C['gray']};font-size:.58rem;text-transform:uppercase;letter-spacing:.5px">EV (DCF)</div>
                        <div style="color:{C['white']};font-weight:600;font-size:.85rem;margin-top:2px">{bi(r.get('enterprise_value'))}</div>
                    </div>
                    <div style="background:{C['bg']};border-radius:6px;padding:8px 10px">
                        <div style="color:{C['gray']};font-size:.58rem;text-transform:uppercase;letter-spacing:.5px">Net Debt</div>
                        <div style="color:{C['white']};font-weight:600;font-size:.85rem;margin-top:2px">{bi(r.get('net_debt'))}</div>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:4px">
                    <div style="background:{C['bg']};border-radius:4px;padding:5px 4px;text-align:center">
                        <div style="color:{C['gray']};font-size:.55rem;text-transform:uppercase">WACC</div>
                        <div style="color:{C['blue_lt']};font-weight:700;font-size:.78rem">{pct(r.get('wacc'))}</div>
                    </div>
                    <div style="background:{C['bg']};border-radius:4px;padding:5px 4px;text-align:center">
                        <div style="color:{C['gray']};font-size:.55rem;text-transform:uppercase">ROIC</div>
                        <div style="color:{C['blue_lt']};font-weight:700;font-size:.78rem">{pct(r.get('roic'))}</div>
                    </div>
                    <div style="background:{C['bg']};border-radius:4px;padding:5px 4px;text-align:center">
                        <div style="color:{C['gray']};font-size:.55rem;text-transform:uppercase">Mg EBIT</div>
                        <div style="color:{C['blue_lt']};font-weight:700;font-size:.78rem">{pct(r.get('ebit_margin'))}</div>
                    </div>
                    <div style="background:{C['bg']};border-radius:4px;padding:5px 4px;text-align:center">
                        <div style="color:{C['gray']};font-size:.55rem;text-transform:uppercase">Beta</div>
                        <div style="color:{C['blue_lt']};font-weight:700;font-size:.78rem">{f_(r.get('beta'))}</div>
                    </div>
                </div>
                </div>''', unsafe_allow_html=True)
                if st.button('Ver detalhes', key=f'vd_{emp}_{_row_start}', use_container_width=True):
                    st.session_state['_nav_empresa'] = emp
                    st.rerun()

    # Sparklines de cotação
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## Cotações Recentes (6 meses)")
    _scols = 6
    for _srow in range(0, len(empresas_vg), _scols):
        _semp = empresas_vg[_srow:_srow+_scols]
        spark_cols = st.columns(_scols)
        for i, emp in enumerate(_semp):
            r = results[emp]; ticker = r.get("ticker", emp)
            with spark_cols[i]:
                _tk = ticker.replace(".SA","")
                _pr_now = r.get("price_now") or 0
                _pr_str = f"R$ {_pr_now:.2f}" if _pr_now else "—"
                df_p = get_price_history(ticker, "6mo")
                if not df_p.empty:
                    closes = df_p["Close"].squeeze()
                    _v0 = float(closes.iloc[0]); _vf = float(closes.iloc[-1])
                    pct_chg = (_vf - _v0) / _v0 * 100 if _v0 else 0
                    _col = C["pos"] if pct_chg >= 0 else C["neg"]
                    _rv,_gv,_bv = int(_col[1:3],16),int(_col[3:5],16),int(_col[5:7],16)
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;align-items:baseline;padding:2px 0'>"
                        f"<span style='font-size:.78rem;font-weight:800;color:{C['blue_lt']}'>{_tk}</span>"
                        f"<span style='font-size:.74rem;font-weight:700;color:{_col}'>{pct_chg:+.1f}%</span>"
                        f"</div>"
                        f"<div style='font-size:.67rem;color:{C['gray2']};margin-bottom:3px'>{_pr_str}</div>",
                        unsafe_allow_html=True)
                    fig_sp = go.Figure(go.Scatter(
                        x=closes.index, y=closes.values,
                        mode="lines", line=dict(color=_col, width=1.5),
                        fill="tozeroy", fillcolor=f"rgba({_rv},{_gv},{_bv},.10)"))
                    fig_sp.update_layout(
                        paper_bgcolor=C["bg2"], plot_bgcolor=C["bg2"],
                        margin=dict(l=0,r=0,t=0,b=0), height=60,
                        xaxis=dict(visible=False), yaxis=dict(visible=False),
                        showlegend=False)
                    st.plotly_chart(fig_sp, use_container_width=True, key=f"sp_{ticker}_{_srow}_{i}")
                else:
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;align-items:baseline;padding:2px 0'>"
                        f"<span style='font-size:.78rem;font-weight:800;color:{C['blue_lt']}'>{_tk}</span>"
                        f"<span style='font-size:.72rem;color:{C['gray2']}'>—</span></div>"
                        f"<div style='font-size:.67rem;color:{C['gray2']};margin-bottom:3px'>{_pr_str}</div>"
                        f"<div style='color:{C['gray2']};font-size:.75rem;text-align:center;padding:18px 0'>Sem dados</div>",
                        unsafe_allow_html=True)
    st.markdown("## EV · Equity DCF · Market Cap")
    fig = go.Figure()
    for emp in empresas_vg:
        r = results[emp]; ticker = r.get("ticker",emp)
        ev = float(r.get("enterprise_value",0))/1e9
        eq = float(r.get("equity_value",0))/1e9
        wd = r.get("wacc_data") or {}
        mc = float(wd.get("market_cap") or r.get("equity_value") or 0)/1e9
        fig.add_trace(go.Bar(name=f"{ticker} EV",    x=[ticker],y=[ev],marker_color=C["bg3"],    width=.22))
        fig.add_trace(go.Bar(name=f"{ticker} Equity",x=[ticker],y=[eq],marker_color=C["blue_lt"],width=.22))
        fig.add_trace(go.Bar(name=f"{ticker} MktCap",x=[ticker],y=[mc],marker_color=C["gray"],   width=.22))
    fig.update_layout(**PL, barmode="group", title="R$ bilhões")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("## Radar — Qualidade Operacional")
    cats = ["Mg EBIT","ROIC","ROE","Mg Líquida","CAGR Receita"]
    fig_r = go.Figure()
    clrs = [C["blue_lt"],C["sky"],C["teal"],C["gray"],C["navy"],C["pos"],C["neg"]]
    for idx_r,emp in enumerate(empresas_vg):
        r=results[emp]; ticker=r.get("ticker",emp).replace(".SA","")
        vals=[min(abs(float(r.get(k) or 0))*100, lim) for k,lim in
              [("ebit_margin",60),("roic",40),("roe",60),("net_margin",60),("cagr_revenue",35)]]
        clr=clrs[idx_r % len(clrs)]
        rv,gv,bv=int(clr[1:3],16),int(clr[3:5],16),int(clr[5:7],16)
        fig_r.add_trace(go.Scatterpolar(
            r=vals+[vals[0]], theta=cats+[cats[0]],
            fill="toself", name=ticker, line_color=clr,
            fillcolor=f"rgba({rv},{gv},{bv},.12)"))
    fig_r.update_layout(
        paper_bgcolor=C["bg"], font=dict(family="Helvetica,Arial",color=C["gray"],size=11),
        polar=dict(bgcolor=C["bg2"],
                   radialaxis=dict(visible=True,gridcolor=C["border"],tickfont=dict(color=C["gray2"])),
                   angularaxis=dict(gridcolor=C["border"],color=C["gray2"])),
        margin=dict(l=40,r=40,t=30,b=30),
        legend=dict(bgcolor=C["bg"],bordercolor=C["border"]),
        title="Em % — quanto maior melhor")
    st.plotly_chart(fig_r, use_container_width=True, key="radar_vg")
    st.markdown("## Múltiplos Comparativos")
    def _fx(v, s="x"):
        try:
            fv = float(v)
            return f"{fv:.1f}{s}" if fv != 0 else "—"
        except (TypeError, ValueError): return "—"
    rows=[]; rows_html=[]
    for emp in empresas_vg:
        r=results[emp]
        _up   = (r.get("upside") or 0)*100
        _rec  = r.get("recomendacao","—")
        _uc   = C["pos"] if _up>=0 else C["neg"]
        _rc   = C["pos"] if "COMPRA" in str(_rec).upper() else (C["neg"] if "VENDA" in str(_rec).upper() else C["gray"])
        rows.append({
            "Ticker": r.get("ticker",emp).replace(".SA",""),
            "P. Tela": price(r.get("price_now")), "P. Justo": price(r.get("price_fair")),
            "Upside": f"{_up:+.1f}%", "EV/EBITDA": _fx(r.get("ev_ebitda")),
            "EV/EBIT": _fx(r.get("ev_ebit")), "P/E": _fx(r.get("pe")),
            "ROIC": pct(r.get("roic")), "Mg EBIT": pct(r.get("ebit_margin")),
            "WACC": pct(r.get("wacc")), "Beta": f_(r.get("beta")), "Rec.": _rec,
        })
        rows_html.append({
            "Ticker":    f'<b style="color:{C["blue_lt"]}">{r.get("ticker",emp).replace(".SA","")}</b>',
            "P. Tela":   price(r.get("price_now")),
            "P. Justo":  f'<span style="color:{C["blue_lt"]}">{price(r.get("price_fair"))}</span>',
            "Upside":    f'<span style="color:{_uc};font-weight:700">{_up:+.1f}%</span>',
            "EV/EBITDA": _fx(r.get("ev_ebitda")), "EV/EBIT": _fx(r.get("ev_ebit")),
            "P/E":       _fx(r.get("pe")), "ROIC": pct(r.get("roic")),
            "Mg EBIT":   pct(r.get("ebit_margin")), "WACC": pct(r.get("wacc")),
            "Beta":      f_(r.get("beta")),
            "Rec.":      f'<span style="color:{_rc};font-weight:700">{_rec}</span>',
        })
    st.markdown(dark_table(pd.DataFrame(rows_html)), unsafe_allow_html=True)
    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
    export_buttons(pd.DataFrame(rows), "visao_geral_multiplos")

# ══════════════════════════════════════════════════════════════════
# PÁG 2 — EMPRESA
# ══════════════════════════════════════════════════════════════════
elif pagina == "Empresa":
    _default_emp = st.session_state.pop("_nav_empresa", None)
    _default_idx = empresas.index(_default_emp) if _default_emp and _default_emp in empresas else 0
    emp_sel = st.selectbox("Empresa", empresas,
                           index=_default_idx,
                           format_func=lambda e: f"{results[e].get('ticker',e).replace('.SA','')} — {e}")
    r=results[emp_sel]; ticker=r.get("ticker",emp_sel); upside=r.get("upside") or 0

    cl,cr=st.columns([1,5])
    with cl: st.markdown(logo_empresa_html(ticker,110), unsafe_allow_html=True)
    with cr:
        _tk_clean = ticker.replace(".SA","")
        _up_str = f"{(upside or 0)*100:+.1f}%"
        st.markdown(f"""
        <div style="margin-top:8px;">
            <span style="color:{C['blue_lt']};font-size:1.15rem;font-weight:700;">{_tk_clean}</span>
            &nbsp;&nbsp;{badge(r.get('recomendacao',''))}
        </div>
        <div style="color:{C['gray2']};font-size:.8rem;margin-top:6px;">
            Preço tela: <b style="color:{C['white']};">{price(r.get('price_now'))}</b>
            &nbsp;|&nbsp; Preço justo: <b style="color:{C['blue_lt']};">{price(r.get('price_fair'))}</b>
            &nbsp;|&nbsp; Upside: <b style="color:{C['pos'] if upside>0 else C['neg']};">{_up_str}</b>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    wd=r.get("wacc_data") or {}
    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.metric("Market Cap",   bi(wd.get("market_cap") or r.get("equity_value")))
    c2.metric("EV (DCF)",     bi(r.get("enterprise_value")))
    c3.metric("Equity Value", bi(r.get("equity_value")))
    c4.metric("Net Debt",     bi(r.get("net_debt")))
    c5.metric("WACC",         pct(r.get("wacc")))
    c6.metric("Beta",         f_(r.get("beta")))
    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.metric("Margem EBIT",  pct(r.get("ebit_margin")))
    c2.metric("Margem Líq.",  pct(r.get("net_margin")))
    c3.metric("ROIC",         pct(r.get("roic")))
    c4.metric("ROE",          pct(r.get("roe")))
    c5.metric("CAGR Receita", pct(r.get("cagr_revenue")))
    c6.metric("FCF Yield",    pct(r.get("fcf_yield")))

    # ── Gráfico de Cotação ──────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## Cotação — Gráfico Interativo")
    per_col, ma_col = st.columns([1,2])
    with per_col:
        periodo = st.selectbox("Período", ["1mo","3mo","6mo","1y","2y","5y"], index=3, key="emp_period")
    with ma_col:
        show_ma = st.multiselect("Médias Móveis", ["MA20","MA50","MA200"], default=["MA20","MA50"], key="emp_ma")

    df_cot = get_price_history(ticker, periodo)
    if not df_cot.empty:
        fig_cot = go.Figure()
        # Candlestick
        fig_cot.add_trace(go.Candlestick(
            x=df_cot.index,
            open=df_cot["Open"].squeeze(), high=df_cot["High"].squeeze(),
            low=df_cot["Low"].squeeze(),   close=df_cot["Close"].squeeze(),
            name=ticker,
            increasing_line_color=C["pos"], decreasing_line_color=C["neg"],
            increasing_fillcolor=C["pos"],  decreasing_fillcolor=C["neg"],
        ))
        closes = df_cot["Close"].squeeze()
        ma_colors = {"MA20": C["blue_lt"], "MA50": "#FFD700", "MA200": C["gray"]}
        ma_windows = {"MA20": 20, "MA50": 50, "MA200": 200}
        for ma in show_ma:
            w = ma_windows[ma]
            if len(closes) >= w:
                fig_cot.add_trace(go.Scatter(
                    x=closes.index, y=closes.rolling(w).mean(),
                    mode="lines", name=ma,
                    line=dict(color=ma_colors[ma], width=1.5, dash="dot")
                ))
        # Linha preço justo
        pf = r.get("price_fair")
        if pf:
            fig_cot.add_hline(y=float(pf), line_dash="dash", line_color=C["blue_lt"],
                annotation_text=f"Justo R${float(pf):.2f}", annotation_font_color=C["blue_lt"])
        fig_cot.update_layout(
            **PL, title=f"{ticker} — Cotação",
            xaxis_rangeslider_visible=False, height=420,
            yaxis_title="R$/ação"
        )
        st.plotly_chart(fig_cot, use_container_width=True)

        # Volume
        fig_vol = go.Figure()
        vol = df_cot["Volume"].squeeze()
        closes_v = df_cot["Close"].squeeze()
        vol_colors = [C["pos"] if closes_v.iloc[i] >= closes_v.iloc[i-1] else C["neg"]
                      for i in range(len(closes_v))]
        fig_vol.add_trace(go.Bar(x=vol.index, y=vol.values, name="Volume",
                                  marker_color=vol_colors, opacity=0.7))
        fig_vol.update_layout(**{**PL, "margin": dict(l=45,r=25,t=25,b=30)}, title="Volume", height=160, yaxis_title="Volume")
        st.plotly_chart(fig_vol, use_container_width=True)
    else:
        st.info(f"Sem dados de cotação para {ticker}.")

    # ── DRE Histórica ───────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## DRE Histórica")

    hist = r.get("historical") or {}
    if hist:
        anos_h = sorted(hist.keys())
        dre_rows = []
        for ano in anos_h:
            d = hist[ano]
            dre_rows.append({
                "Ano": ano,
                "Receita (R$bi)": f"{float(d.get('revenue',0))/1e9:.2f}",
                "EBIT (R$bi)":    f"{float(d.get('ebit',0))/1e9:.2f}",
                "EBITDA (R$bi)":  f"{float(d.get('ebitda',0))/1e9:.2f}",
                "Lucro Líq.":     f"{float(d.get('net_income',0))/1e9:.2f}",
                "Mg EBIT":        f"{float(d.get('ebit_margin',0))*100:.1f}%",
                "CAPEX (R$bi)":   f"{float(d.get('capex',0))/1e9:.2f}",
                "FCFF (R$bi)":    f"{float(d.get('fcff',0))/1e9:.2f}",
            })
        st.markdown(dark_table(pd.DataFrame(dre_rows)), unsafe_allow_html=True)

        # Gráfico receita + EBIT
        anos_nums = [int(a) for a in anos_h]
        rev = [float(hist[a].get('revenue',0))/1e9 for a in anos_h]
        ebit = [float(hist[a].get('ebit',0))/1e9 for a in anos_h]
        ni   = [float(hist[a].get('net_income',0))/1e9 for a in anos_h]

        fig_dre = go.Figure()
        fig_dre.add_trace(go.Bar(x=anos_nums, y=rev, name="Receita", marker_color=C["bg3"]))
        fig_dre.add_trace(go.Bar(x=anos_nums, y=ebit, name="EBIT",   marker_color=C["blue_lt"]))
        fig_dre.add_trace(go.Scatter(x=anos_nums, y=ni, name="Lucro Líq.",
                                      mode="lines+markers", line=dict(color=C["pos"],width=2),
                                      marker=dict(size=7, color=C["pos"]), yaxis="y"))
        fig_dre.update_layout(**PL, barmode="group", title="R$ bilhões", yaxis_title="R$ bi")
        st.plotly_chart(fig_dre, use_container_width=True)
    else:
        # Fallback: usa fcff_series como proxy
        fcff = r.get("fcff_series") or {}
        last_h = int(r.get("last_historical_year") or 2024)
        if fcff:
            anos_fcff = [int(a) for a in sorted(fcff.keys()) if int(a) <= last_h]
            vals_fcff = [float(fcff[str(a)])/1e9 for a in anos_fcff]
            fig_fcff = go.Figure(go.Bar(
                x=anos_fcff, y=vals_fcff, marker_color=C["bg3"],
                text=[f"R${v:.2f}bi" for v in vals_fcff],
                textposition="outside", textfont=dict(color=C["white"],size=9)
            ))
            fig_fcff.update_layout(**PL, title="FCFF Histórico (R$ bi)", yaxis_title="R$ bi")
            st.plotly_chart(fig_fcff, use_container_width=True)
            # (debug msg removida)

    st.markdown("<hr>", unsafe_allow_html=True)
    cl2,cr2=st.columns(2)
    ev=float(r.get("enterprise_value",0))/1e9
    nd=float(r.get("net_debt",0))/1e9
    eq=float(r.get("equity_value",0))/1e9

    with cl2:
        st.markdown("## Waterfall EV → Equity")
        fig_wf=go.Figure(go.Waterfall(
            orientation="v", measure=["absolute","relative","total"],
            x=["Enterprise Value","(−) Dívida Líquida","Equity Value"],
            y=[ev,-nd,0],
            text=[f"R${ev:.1f}bi",f"R${-nd:+.1f}bi",f"R${eq:.1f}bi"],
            textposition="outside", textfont=dict(color=C["white"]),
            connector=dict(line=dict(color=C["border"],width=1,dash="dot")),
            increasing=dict(marker_color=C["blue_lt"]),
            decreasing=dict(marker_color=C["neg"]),
            totals=dict(marker_color=C["bg3"])))
        fig_wf.update_layout(**PL, showlegend=False, yaxis_title="R$ bilhões")
        st.plotly_chart(fig_wf, use_container_width=True)

    with cr2:
        st.markdown("## Composição do EV")
        dcf=r.get("dcf") or {}
        pv_fcf=float(dcf.get("pv_fcf",0))/1e9; pv_term=float(dcf.get("pv_terminal",0))/1e9
        if pv_fcf+pv_term>0:
            fig_pie=go.Figure(go.Pie(
                labels=["PV FCFs Explícitos","PV Valor Terminal"],
                values=[pv_fcf,pv_term], hole=.55,
                marker_colors=[C["bg3"],C["blue_lt"]],
                textfont=dict(color=C["white"],size=11)))
            fig_pie.update_layout(paper_bgcolor=C["bg"],
                font=dict(family="Helvetica,Arial",color=C["gray"]),
                legend=dict(bgcolor=C["bg"],bordercolor=C["border"]),
                margin=dict(l=20,r=20,t=30,b=20),
                annotations=[dict(text=f"EV<br><b>R${ev:.1f}bi</b>",
                    font=dict(size=12,color=C["white"]),showarrow=False)])
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.caption("Dados de composição do EV não disponíveis para esta empresa.")

    st.markdown("## Múltiplos EV")
    mult_ok={k:float(v) for k,v in
             [("EV/EBITDA",r.get("ev_ebitda")),("EV/EBIT",r.get("ev_ebit")),
              ("P/E",r.get("pe")),("EV/Receita",r.get("ev_revenue"))] if v}
    if mult_ok:
        fig_m=go.Figure(go.Bar(x=list(mult_ok.keys()),y=list(mult_ok.values()),
            marker_color=[C["bg3"],C["blue_lt"],C["gray"],C["bg4"]],
            text=[f"{v:.1f}x" for v in mult_ok.values()],
            textposition="outside", textfont=dict(color=C["white"])))
        fig_m.update_layout(**PL, yaxis_title="múltiplo (x)", showlegend=False)
        st.plotly_chart(fig_m, use_container_width=True)

    ovr=r.get("overrides") or {}
    if any(ovr.values()):
        st.warning(f"  Overrides — receita: {pct(ovr.get('revenue_growth'))} | EBIT: {pct(ovr.get('ebit_margin'))}")

    # ── #22 — Confronto de Preços: Tela vs DCF vs Consenso ──────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## Confronto de Preços — Tela · DCF · Consenso Diretors")

    p_tela = float(r.get("price_now") or 0)
    p_dcf  = float(r.get("price_fair") or 0)

    # Consenso analistas — busca via yfinance info()
    @st.cache_data(ttl=3600)
    def get_analyst_consensus(tk):
        try:
            import yfinance as yf
            info = yf.Ticker(tk).info
            tp   = info.get("targetMeanPrice") or info.get("targetMedianPrice")
            tl   = info.get("targetLowPrice")
            th   = info.get("targetHighPrice")
            nb   = info.get("numberOfAnalystOpinions") or 0
            rec  = info.get("recommendationMean")  # 1=Strong Buy … 5=Strong Sell
            rec_map = {1:"Compra Forte",1.5:"Compra Forte",2:"Compra",
                       2.5:"Compra",3:"Neutro",3.5:"Venda",4:"Venda",
                       4.5:"Venda Forte",5:"Venda Forte"}
            rec_str = rec_map.get(round(rec*2)/2, "—") if rec else "—"
            return {"target": tp, "low": tl, "high": th, "n": nb, "rec": rec_str, "rec_raw": rec}
        except Exception:
            return {}

    consensus = get_analyst_consensus(ticker)
    p_cons = consensus.get("target") or 0
    p_low  = consensus.get("low") or 0
    p_high = consensus.get("high") or 0
    n_anal = consensus.get("n", 0)
    rec_cons = consensus.get("rec", "—")

    # Cards de comparação
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1:
        st.markdown(f"""<div style="background:{C['bg2']};border:1px solid {C['border']};border-radius:8px;padding:16px;text-align:center;">
            <div style="color:{C['gray2']};font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;">Preço em Tela</div>
            <div style="color:{C['white']};font-size:1.6rem;font-weight:700;margin:6px 0;">R$ {p_tela:.2f}</div>
            <div style="color:{C['gray2']};font-size:.75rem;">Cotação atual</div>
        </div>""", unsafe_allow_html=True)
    with cc2:
        dcf_color = C["pos"] if p_dcf > p_tela else C["neg"]
        dcf_diff  = (p_dcf - p_tela)/p_tela*100 if p_tela else 0
        st.markdown(f"""<div style="background:{C['bg2']};border:1px solid {C['border']};border-radius:8px;padding:16px;text-align:center;">
            <div style="color:{C['gray2']};font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;">DCF (Vela)</div>
            <div style="color:{dcf_color};font-size:1.6rem;font-weight:700;margin:6px 0;">R$ {p_dcf:.2f}</div>
            <div style="color:{dcf_color};font-size:.75rem;">{dcf_diff:+.1f}% vs tela</div>
        </div>""", unsafe_allow_html=True)
    with cc3:
        cons_color = C["pos"] if p_cons > p_tela else (C["neg"] if p_cons > 0 else C["gray2"])
        cons_diff  = (p_cons - p_tela)/p_tela*100 if p_tela and p_cons else 0
        st.markdown(f"""<div style="background:{C['bg2']};border:1px solid {C['border']};border-radius:8px;padding:16px;text-align:center;">
            <div style="color:{C['gray2']};font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;">Consenso ({n_anal} analistas)</div>
            <div style="color:{cons_color};font-size:1.6rem;font-weight:700;margin:6px 0;">{"R$ "+f"{p_cons:.2f}" if p_cons else "—"}</div>
            <div style="color:{cons_color};font-size:.75rem;">{f"{cons_diff:+.1f}% vs tela" if p_cons else "Indisponível"}</div>
        </div>""", unsafe_allow_html=True)
    with cc4:
        st.markdown(f"""<div style="background:{C['bg2']};border:1px solid {C['border']};border-radius:8px;padding:16px;text-align:center;">
            <div style="color:{C['gray2']};font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;">Rec. Consenso</div>
            <div style="color:{C['blue_lt']};font-size:1.4rem;font-weight:700;margin:6px 0;">{rec_cons}</div>
            <div style="color:{C['gray2']};font-size:.75rem;">{"Range: R$"+f"{p_low:.0f}–{p_high:.0f}" if p_low and p_high else "—"}</div>
        </div>""", unsafe_allow_html=True)

    # Gráfico de barras comparativo + range analistas
    if p_tela or p_dcf or p_cons:
        fig_cp = go.Figure()
        labels = ["Preço Tela", "DCF Vela Capital"]
        values = [p_tela, p_dcf]
        colors = [C["sky"], C["blue_lt"]]
        if p_cons:
            labels.append(f"Consenso ({n_anal} anal.)")
            values.append(p_cons)
            colors.append(C["gray"])

        fig_cp.add_trace(go.Bar(
            x=labels, y=values,
            marker_color=colors,
            text=[f"R$ {v:.2f}" for v in values],
            textposition="outside", textfont=dict(color=C["white"], size=11),
            width=0.4
        ))

        # Range de analistas (low–high) como caixa
        if p_low and p_high:
            fig_cp.add_shape(type="rect",
                x0=-0.5, x1=len(labels)-0.5,
                y0=p_low, y1=p_high,
                fillcolor=f"rgba(154,192,230,.08)",
                line=dict(color=C["sky"], width=1, dash="dot")
            )
            fig_cp.add_annotation(
                x=len(labels)-0.5, y=(p_low+p_high)/2,
                text=f"Range analistas<br>R${p_low:.0f}–{p_high:.0f}",
                showarrow=False, xanchor="right",
                font=dict(color=C["sky"], size=10),
                bgcolor=C["bg2"], bordercolor=C["sky"]
            )

        fig_cp.update_layout(**PL,
            title="Comparação de Preço Alvo (R$/ação)",
            yaxis_title="R$/ação", showlegend=False, height=340
        )
        st.plotly_chart(fig_cp, use_container_width=True)

    st.caption("Consenso via Yahoo Finance (yfinance). Dados podem ter delay. "
               "Para cobertura completa, integre a API ComDinheiro (#19).")

    # ── #25 — Volatilidade Histórica ────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## Volatilidade Histórica")
    df_vol_hist = get_price_history(ticker, "2y")
    if not df_vol_hist.empty:
        closes_v2 = df_vol_hist["Close"].squeeze()
        rets_v = closes_v2.pct_change().dropna()
        vol21  = rets_v.rolling(21).std()  * (252**0.5) * 100
        vol63  = rets_v.rolling(63).std()  * (252**0.5) * 100
        vol252 = rets_v.rolling(252).std() * (252**0.5) * 100

        fig_vol_h = go.Figure()
        fig_vol_h.add_trace(go.Scatter(
            x=vol21.index, y=vol21.values, mode="lines", name="Vol 21d (mensal)",
            line=dict(color=C["blue_lt"], width=1.5)))
        fig_vol_h.add_trace(go.Scatter(
            x=vol63.index, y=vol63.values, mode="lines", name="Vol 63d (trimestral)",
            line=dict(color=C["sky"], width=2)))
        fig_vol_h.add_trace(go.Scatter(
            x=vol252.index, y=vol252.values, mode="lines", name="Vol 252d (anual)",
            line=dict(color=C["gray"], width=2, dash="dot")))
        # Faixa de referência
        fig_vol_h.add_hrect(y0=20, y1=40, fillcolor=C["navy"],
            opacity=0.1, layer="below", line_width=0,
            annotation_text="Zona Normal (20-40%)",
            annotation_font_color=C["gray2"], annotation_position="top left")
        fig_vol_h.update_layout(**PL,
            title=f"{ticker} — Volatilidade Anualizada (%)",
            yaxis_title="Vol. Anualizada (%)", height=320)
        st.plotly_chart(fig_vol_h, use_container_width=True)

        # Métricas de vol
        vc1,vc2,vc3,vc4 = st.columns(4)
        vc1.metric("Vol Atual (21d)",  f"{float(vol21.dropna().iloc[-1]):.1f}%")
        vc2.metric("Vol Atual (63d)",  f"{float(vol63.dropna().iloc[-1]):.1f}%")
        vc3.metric("Vol Máx (2a)",     f"{float(vol21.dropna().max()):.1f}%")
        vc4.metric("Vol Mín (2a)",     f"{float(vol21.dropna().min()):.1f}%")
    else:
        st.info("Sem dados para calcular volatilidade.")

    # ── #24 — Regressão do Beta (ação vs IBOV) ──────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## Regressão do Beta — Ação vs IBOV")
    try:
        df_beta = get_beta_data(ticker)
        if not df_beta.empty and len(df_beta) > 30:
            x = df_beta["r_ibov"].values
            y = df_beta["r_stock"].values
            # OLS manual
            beta_calc = float(np.cov(x, y)[0,1] / np.var(x))
            alpha_calc = float(np.mean(y) - beta_calc * np.mean(x))
            # R²
            y_pred = alpha_calc + beta_calc * x
            ss_res = np.sum((y - y_pred)**2)
            ss_tot = np.sum((y - np.mean(y))**2)
            r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0

            x_line = np.linspace(x.min(), x.max(), 100)
            y_line = alpha_calc + beta_calc * x_line

            fig_beta = go.Figure()
            # Scatter dos retornos diários
            colors_pts = [C["pos"] if yi >= 0 else C["neg"] for yi in y]
            fig_beta.add_trace(go.Scatter(
                x=x*100, y=y*100, mode="markers",
                marker=dict(size=4, color=colors_pts, opacity=0.5),
                name="Retornos diários",
                hovertemplate="IBOV: %{x:.2f}%<br>Ação: %{y:.2f}%<extra></extra>"
            ))
            # Linha de regressão
            fig_beta.add_trace(go.Scatter(
                x=x_line*100, y=y_line*100, mode="lines",
                line=dict(color=C["blue_lt"], width=2.5),
                name=f"β = {beta_calc:.2f}"
            ))
            # Linha horizontal y=0 e vertical x=0
            fig_beta.add_hline(y=0, line_color=C["border"], line_width=1)
            fig_beta.add_vline(x=0, line_color=C["border"], line_width=1)

            fig_beta.update_layout(**PL,
                title=f"β = {beta_calc:.2f} | α = {alpha_calc*100:.3f}%/dia | R² = {r2:.3f} | janela: 3 anos",
                xaxis_title="Retorno IBOV (%)",
                yaxis_title=f"Retorno {ticker} (%)",
                height=420
            )
            st.plotly_chart(fig_beta, use_container_width=True)

            # Métricas
            bc1,bc2,bc3,bc4 = st.columns(4)
            bc1.metric("Beta Calculado", f"{beta_calc:.3f}")
            bc2.metric("Beta Blume Adj.", f_(r.get("beta")))
            bc3.metric("Alpha (diário)", f"{alpha_calc*100:.4f}%")
            bc4.metric("R²", f"{r2:.3f}")
            st.caption(f"OLS sobre retornos diários — janela 3 anos ({len(df_beta)} observações) | "
                       f"Beta Blume = 0.33 + 0.67 × Beta Raw")
        else:
            st.info("Dados insuficientes para calcular a regressão do beta.")
    except Exception as e:
        st.warning(f"Erro ao calcular beta: {e}")

# ══════════════════════════════════════════════════════════════════
# PÁG 3 — COTAÇÕES
# ══════════════════════════════════════════════════════════════════
elif pagina == "Cotações":
    st.markdown("## Cotações em Tempo Real")

    col_t, col_p, col_m = st.columns([2,1,2])
    with col_t:
        all_tks = [r.get("ticker","") for r in results.values()]
        extras_str = st.text_input("Adicionar tickers", value="PETR4.SA, VALE3.SA, IBOV")
        extra_tks = [t.strip() for t in extras_str.split(",") if t.strip()]
        # Normaliza IBOV
        extra_tks_norm = ["^BVSP" if t.upper() in ("IBOV","^BVSP") else
                          (t if t.endswith(".SA") else t+".SA") for t in extra_tks]
        all_display = list(dict.fromkeys(all_tks + extra_tks_norm))
        selected_tk = st.selectbox("Ativo", all_display)
    with col_p:
        per_cot = st.selectbox("Período", [
            "5d","1mo","3mo","6mo","ytd","1y","2y","3y","5y","10y","max"
        ], index=6, format_func=lambda x: {
            "5d":"5 dias","1mo":"1 mês","3mo":"3 meses","6mo":"6 meses",
            "ytd":"Ano atual (YTD)","1y":"1 ano","2y":"2 anos","3y":"3 anos",
            "5y":"5 anos","10y":"10 anos","max":"Máximo disponível"
        }.get(x,x))
    with col_m:
        tipo_graf = st.radio("Tipo", ["Candlestick","Linha","OHLC"], horizontal=True)

    mas_cot = st.multiselect("Médias Móveis", ["MA9","MA20","MA50","MA100","MA200"], default=["MA20","MA50"])

    df_cot2 = get_price_history(selected_tk, per_cot)
    if not df_cot2.empty:
        closes2 = df_cot2["Close"].squeeze()
        v_ini = float(closes2.iloc[0]); v_fin = float(closes2.iloc[-1])
        pct_chg2 = (v_fin - v_ini) / v_ini * 100
        chg_color = C["pos"] if pct_chg2 >= 0 else C["neg"]

        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Último", f"{v_fin:.2f}", delta=f"{pct_chg2:+.2f}%")
        m2.metric("Máx Período", f"{float(df_cot2['High'].max()):.2f}")
        m3.metric("Mín Período", f"{float(df_cot2['Low'].min()):.2f}")
        vol_med = float(df_cot2["Volume"].mean()) if "Volume" in df_cot2.columns else 0
        m4.metric("Vol. Médio", f"{vol_med/1e6:.1f}M" if vol_med > 1e6 else f"{vol_med:.0f}")

        fig_cot2 = go.Figure()
        if tipo_graf == "Candlestick":
            fig_cot2.add_trace(go.Candlestick(
                x=df_cot2.index,
                open=df_cot2["Open"].squeeze(), high=df_cot2["High"].squeeze(),
                low=df_cot2["Low"].squeeze(),   close=closes2,
                name=selected_tk,
                increasing_line_color=C["pos"], decreasing_line_color=C["neg"],
                increasing_fillcolor=C["pos"],  decreasing_fillcolor=C["neg"],
            ))
        elif tipo_graf == "OHLC":
            fig_cot2.add_trace(go.Ohlc(
                x=df_cot2.index,
                open=df_cot2["Open"].squeeze(), high=df_cot2["High"].squeeze(),
                low=df_cot2["Low"].squeeze(),   close=closes2,
                name=selected_tk,
                increasing_line_color=C["pos"], decreasing_line_color=C["neg"],
            ))
        else:
            fig_cot2.add_trace(go.Scatter(
                x=df_cot2.index, y=closes2,
                mode="lines", name=selected_tk,
                line=dict(color=chg_color, width=2),
                fill="tozeroy",
                fillcolor=f"rgba({int(chg_color[1:3],16)},{int(chg_color[3:5],16)},{int(chg_color[5:7],16)},.07)"
            ))

        ma_colors2 = {"MA9":C["gray2"],"MA20":C["blue_lt"],"MA50":"#FFD700","MA100":"#FF8C00","MA200":C["gray"]}
        for ma in mas_cot:
            w = int(ma[2:])
            if len(closes2) >= w:
                fig_cot2.add_trace(go.Scatter(
                    x=closes2.index, y=closes2.rolling(w).mean(),
                    mode="lines", name=ma,
                    line=dict(color=ma_colors2.get(ma,C["gray"]), width=1.5, dash="dot")
                ))

        # Preço justo se for uma das empresas cobertas
        for emp, rv in results.items():
            if rv.get("ticker") == selected_tk and rv.get("price_fair"):
                pf2 = float(rv["price_fair"])
                fig_cot2.add_hline(y=pf2, line_dash="dash", line_color=C["blue_lt"],
                    annotation_text=f"Justo R${pf2:.2f}", annotation_font_color=C["blue_lt"])
                break

        fig_cot2.update_layout(**PL, title=f"{selected_tk}",
                                xaxis_rangeslider_visible=False, height=480,
                                yaxis_title="Preço")
        st.plotly_chart(fig_cot2, use_container_width=True)

        # Volume
        if "Volume" in df_cot2.columns:
            fig_v2 = go.Figure()
            vol2 = df_cot2["Volume"].squeeze()
            vcol = [C["pos"] if closes2.iloc[i] >= closes2.iloc[max(0,i-1)] else C["neg"]
                    for i in range(len(closes2))]
            fig_v2.add_trace(go.Bar(x=vol2.index, y=vol2.values, marker_color=vcol, opacity=.7, name="Volume"))
            fig_v2.update_layout(**{**PL, "margin": dict(l=45,r=25,t=25,b=30)}, title="Volume", height=150, yaxis_title="Volume")
            st.plotly_chart(fig_v2, use_container_width=True)

        # Retornos diários
        st.markdown("## Distribuição de Retornos Diários")
        rets = closes2.pct_change().dropna() * 100
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=rets.values, nbinsx=50, name="Retornos",
            marker_color=C["bg3"], opacity=0.8,
        ))
        fig_hist.add_vline(x=0, line_dash="dash", line_color=C["gray"])
        fig_hist.add_vline(x=float(rets.mean()), line_dash="dash", line_color=C["blue_lt"],
                            annotation_text=f"Média {rets.mean():.2f}%", annotation_font_color=C["blue_lt"])
        fig_hist.update_layout(**PL, title=f"Retornos diários — Vol anual: {rets.std()*np.sqrt(252):.1f}%",
                                xaxis_title="Retorno (%)", yaxis_title="Frequência", height=280)
        st.plotly_chart(fig_hist, use_container_width=True)

        # Estatísticas
        sc1,sc2,sc3,sc4,sc5 = st.columns(5)
        sc1.metric("Retorno Médio", f"{float(rets.mean()):.3f}%/dia")
        sc2.metric("Vol. Diária",   f"{float(rets.std()):.2f}%")
        sc3.metric("Vol. Anual",    f"{float(rets.std())*np.sqrt(252):.1f}%")
        sc4.metric("Sharpe (aprox)",f"{float(rets.mean())/float(rets.std())*np.sqrt(252):.2f}")
        sc5.metric("Observações",   f"{len(rets)}")
    else:
        st.warning(f"Não foi possível obter dados para {selected_tk}. Verifique o ticker.")

# ══════════════════════════════════════════════════════════════════
# PÁG 4 — FCFF & PROJEÇÕES
# ══════════════════════════════════════════════════════════════════
elif pagina == "FCFF & Projeções":
    emp_sel=st.selectbox("Empresa",empresas,
                         format_func=lambda e:f"{results[e].get('ticker',e)} — {e}")
    r=results[emp_sel]; ticker=r.get("ticker",emp_sel)
    fcff=r.get("fcff_series") or {}; last_h=int(r.get("last_historical_year") or 2024)
    st.markdown(f"## {ticker} — FCFF Histórico & Projetado")

    if fcff:
        anos=sorted([int(k) for k in fcff.keys()])
        vals=[float(fcff[str(a)])/1e9 for a in anos]
        cores=[C["gray2"] if a<=last_h else C["blue_lt"] for a in anos]
        fig_f=go.Figure()
        fig_f.add_trace(go.Bar(x=anos,y=vals,marker_color=cores,
            text=[f"R${v:.2f}bi" for v in vals],
            textposition="outside",textfont=dict(color=C["white"],size=9)))
        fig_f.add_vrect(x0=last_h+.5,x1=max(anos)+.5,
            fillcolor=C["bg3"],opacity=.05,layer="below",line_width=0,
            annotation_text="Projeção →",annotation_font_color=C["gray2"],
            annotation_position="top left")
        fig_f.update_layout(**PL,yaxis_title="R$ bilhões",
                             title="Cinza = histórico | Azul = projeção")
        st.plotly_chart(fig_f,use_container_width=True)

        anos_h=[a for a in anos if a<=last_h]; vals_h=[float(fcff[str(a)])/1e9 for a in anos_h]
        anos_p=[a for a in anos if a>last_h];  vals_p=[float(fcff[str(a)])/1e9 for a in anos_p]
        fig_l=go.Figure()
        fig_l.add_trace(go.Scatter(x=anos_h,y=vals_h,mode="lines+markers",name="Histórico",
            line=dict(color=C["gray"],width=2),marker=dict(size=7,color=C["gray"])))
        if anos_p:
            fig_l.add_trace(go.Scatter(x=[anos_h[-1]]+anos_p,y=[vals_h[-1]]+vals_p,
                mode="lines+markers",name="Projeção",
                line=dict(color=C["blue_lt"],width=2,dash="dot"),
                marker=dict(size=7,color=C["blue_lt"])))
            rv,gv,bv=int(C["blue_lt"][1:3],16),int(C["blue_lt"][3:5],16),int(C["blue_lt"][5:7],16)
            fig_l.add_trace(go.Scatter(
                x=anos_p+anos_p[::-1],
                y=[v*1.15 for v in vals_p]+[v*.85 for v in vals_p[::-1]],
                fill="toself",fillcolor=f"rgba({rv},{gv},{bv},.08)",
                line=dict(color="rgba(0,0,0,0)"),name="±15%"))
        fig_l.update_layout(**PL,title="Evolução com banda ±15%",yaxis_title="R$ bilhões")
        st.plotly_chart(fig_l,use_container_width=True)

        df_fcff=pd.DataFrame({"Ano":anos,"FCFF (R$ bi)":[f"{v:.3f}" for v in vals],
            "Tipo":["Histórico" if a<=last_h else "Projeção" for a in anos],
            "Var. %":["—"]+[f"{(vals[i]-vals[i-1])/abs(vals[i-1])*100:+.1f}%"
                            if vals[i-1]!=0 else "n/d" for i in range(1,len(vals))]})
        st.markdown(dark_table(df_fcff), unsafe_allow_html=True)
    else:
        st.info("FCFF série não disponível. Execute: python main.py")

# ══════════════════════════════════════════════════════════════════
# PÁG 5 — COMPARATIVO
# ══════════════════════════════════════════════════════════════════
elif pagina == "Comparativo":
    st.markdown("## Comparativo entre Empresas")
    # Filtra outliers — empresas com upside absurdo distorcem os gráficos
    empresas_comp = [e for e in empresas if abs((results[e].get("upside") or 0)) < 5]
    if not empresas_comp:
        empresas_comp = empresas

    st.markdown("## Dispersão: Upside × WACC")
    fig_sc=go.Figure()
    for emp in empresas:
        r=results[emp]; ticker=r.get("ticker",emp)
        up=float(r.get("upside") or 0)*100; wac=float(r.get("wacc") or 0)*100
        ev=float(r.get("enterprise_value") or 1)/1e9
        fig_sc.add_trace(go.Scatter(x=[wac],y=[up],mode="markers+text",
            marker=dict(size=max(8,abs(ev)*.5+14),color=C["blue_lt"],line=dict(width=2,color=C["bg3"])),
            text=[ticker],textposition="top center",
            textfont=dict(color=C["white"],size=11),name=ticker))
    fig_sc.add_hline(y=0,line_dash="dash",line_color=C["gray2"],opacity=.4)
    fig_sc.update_layout(**PL,title="Tamanho=EV | Acima=subavaliado",
                         xaxis_title="WACC (%)",yaxis_title="Upside (%)")
    st.plotly_chart(fig_sc,use_container_width=True)

    st.markdown("## Múltiplos: EV/EBITDA · EV/EBIT · P/E")
    fig_m=go.Figure()
    for i,(lbl,key) in enumerate([("EV/EBITDA","ev_ebitda"),("EV/EBIT","ev_ebit"),("P/E","pe")]):
        tks=[results[e].get("ticker",e) for e in empresas]
        vls=[float(results[e].get(key) or 0) for e in empresas]
        fig_m.add_trace(go.Bar(name=lbl,x=tks,y=vls,
            marker_color=[C["bg3"],C["blue_lt"],C["gray"]][i],
            text=[f"{v:.1f}x" for v in vls],textposition="outside",
            textfont=dict(color=C["white"])))
    fig_m.update_layout(**PL,barmode="group",yaxis_title="múltiplo (x)")
    st.plotly_chart(fig_m,use_container_width=True)

    st.markdown("## Composição do WACC")
    fig_wacc=go.Figure()
    for emp in empresas:
        r=results[emp]; ticker=r.get("ticker",emp); wd=r.get("wacc_data") or {}
        ke=float(wd.get("cost_of_equity") or r.get("wacc") or 0)*100
        kd=float(wd.get("after_tax_cost_of_debt") or .08)*100
        we=float(wd.get("equity_weight") or .5); dw=float(wd.get("debt_weight") or .5)
        fig_wacc.add_trace(go.Bar(name=f"{ticker} Ke×We",x=[ticker],y=[ke*we],marker_color=C["bg3"]))
        fig_wacc.add_trace(go.Bar(name=f"{ticker} Kd×Wd",x=[ticker],y=[kd*dw],marker_color=C["gray"]))
    fig_wacc.update_layout(**PL,barmode="stack",title="WACC=Ke×We+Kd×Wd (% a.a.)",yaxis_title="% a.a.")
    st.plotly_chart(fig_wacc,use_container_width=True)

    st.markdown("## ROIC · ROE · Margem EBIT")
    fig_op=go.Figure()
    for i,(lbl,key) in enumerate([("Margem EBIT","ebit_margin"),("ROIC","roic"),("ROE","roe")]):
        tks=[results[e].get("ticker",e) for e in empresas]
        vls=[float(results[e].get(key) or 0)*100 for e in empresas]
        fig_op.add_trace(go.Bar(name=lbl,x=tks,y=vls,
            marker_color=[C["bg3"],C["blue_lt"],C["gray"]][i],
            text=[f"{v:.1f}%" for v in vls],textposition="outside",
            textfont=dict(color=C["white"])))
    fig_op.update_layout(**PL,barmode="group",yaxis_title="% a.a.")
    st.plotly_chart(fig_op,use_container_width=True)

# ══════════════════════════════════════════════════════════════════
# PÁG 6 — SENSIBILIDADE
# ══════════════════════════════════════════════════════════════════
elif pagina == "Sensibilidade":
    st.markdown("## Sensibilidade: Preço Justo × WACC × Terminal Growth")
    emp_sel=st.selectbox("Empresa",empresas,
                         format_func=lambda e:f"{results[e].get('ticker',e)} — {e}")
    r=results[emp_sel]; ticker=r.get("ticker",emp_sel)
    ev_base=float(r.get("enterprise_value") or 0); nd_base=float(r.get("net_debt") or 0)
    shares=float(r.get("shares_out") or 1)
    pv_fcfs=float(r.get("dcf_pv_fcf") or ev_base*.48)
    # Calcula fcff_last_proj a partir da série (último ano projetado)
    fcff_series = r.get("fcff_series") or {}
    last_h = int(r.get("last_historical_year") or 2024)
    proj_anos = sorted([int(k) for k in fcff_series.keys() if int(k) > last_h])
    if proj_anos:
        fcff_l = float(fcff_series[str(proj_anos[-1])])
    else:
        fcff_l = float(r.get("dcf_pv_fcf") or ev_base) * 0.06
    price_now=float(r.get("price_now") or 0)

    waccs=[w/100 for w in range(10,21)]; growths=[g/100 for g in range(1,8)]  # WACC 10-20%, g 1-7%
    matrix=[]
    for g in growths:
        row=[]
        for w in waccs:
            if w<=g: row.append(None); continue
            tv=fcff_l*(1+g)/(w-g); pv_tv=tv/(1+w)**6
            row.append(round(((pv_fcfs+pv_tv)-nd_base)/shares,2))
        matrix.append(row)
    df_s=pd.DataFrame(matrix,index=[f"{g*100:.1f}%" for g in growths],  # growths já em decimal
                      columns=[f"{w*100:.1f}%" for w in waccs])  # wacc %

    st.markdown("### Heatmap: Preço Justo (R$/ação)")
    fig_h=go.Figure(go.Heatmap(
        z=df_s.values.tolist(), x=df_s.columns.tolist(), y=df_s.index.tolist(),
        colorscale=[[0,"#E8F4FD"],[.2,"#BEDAF2"],[.4,"#6EB5E8"],[.6,"#2B7EC2"],
                    [.8,"#0F558B"],[1,"#0a2340"]],
        text=[[f"R${v:.2f}" if v else "" for v in row] for row in df_s.values.tolist()],
        texttemplate="%{text}", textfont=dict(size=9,color="#0a1624"),
        colorbar=dict(title=dict(text="R$/ação",font=dict(color=C["gray"])),tickfont=dict(color=C["gray"]))))
    if price_now:
        fig_h.add_annotation(text=f"Preço atual: R${price_now:.2f}",
            xref="paper",yref="paper",x=.5,y=-.12,
            showarrow=False,font=dict(color=C["blue_lt"],size=11))
    fig_h.update_layout(paper_bgcolor=C["bg"],font=dict(family="Helvetica,Arial",color=C["gray"]),
        xaxis_title="WACC",yaxis_title="Terminal Growth",margin=dict(l=50,r=30,t=30,b=60))
    st.plotly_chart(fig_h,use_container_width=True)

    st.markdown("### Superfície 3D")
    z_vals=[[v if v else 0 for v in row] for row in matrix]
    fig_3d=go.Figure(go.Surface(z=z_vals,x=[w*100 for w in waccs],y=[g*100 for g in growths],
        colorscale=[[0,"#E8F4FD"],[.25,"#6EB5E8"],[.5,"#2B7EC2"],[.75,"#0F558B"],[1,"#071d36"]],
        contours=dict(z=dict(show=True,usecolormap=True,project_z=True))))
    if price_now:
        fig_3d.add_trace(go.Surface(z=[[price_now]*len(waccs)]*len(growths),
            x=[w*100 for w in waccs],y=[g*100 for g in growths],
            colorscale=[[0,C["gray"]],[1,C["gray"]]],opacity=.2,showscale=False))
    fig_3d.update_layout(paper_bgcolor=C["bg"],font=dict(family="Helvetica,Arial",color=C["gray"],size=10),
        scene=dict(xaxis=dict(title="WACC (%)",gridcolor=C["border"],color=C["gray2"]),
                   yaxis=dict(title="Growth (%)",gridcolor=C["border"],color=C["gray2"]),
                   zaxis=dict(title="R$/ação",gridcolor=C["border"],color=C["gray2"]),
                   bgcolor=C["bg2"]),
        margin=dict(l=0,r=0,t=30,b=0),height=500)
    st.plotly_chart(fig_3d,use_container_width=True)
    st.caption(f"Plano cinza = preço atual R${price_now:.2f} | Verde=subavaliado | Vermelho=sobreavaliado")

    def _c(v):
        if v is None or (isinstance(v,float) and math.isnan(v)): return f"color:{C['border']}"
        if price_now and v>=price_now*1.15: return f"color:{C['blue_lt']};font-weight:bold"
        if price_now and v<=price_now*.85: return f"color:{C['neg']}"
        return f"color:{C['gray']}"
    def _cell_color(val):
        try:
            v = float(val)
            if price_now and v >= price_now * 1.5:  return "color:#FFFFFF;font-weight:bold;background:#2351FE22"
            if price_now and v >= price_now * 1.15: return "color:#9AC0E6;font-weight:bold"
            if price_now and v >= price_now * 0.95: return "color:#0F558B"
            if price_now and v <= price_now * 0.85: return "color:#6a8fbf"
        except (ValueError, TypeError): pass
        return "color:#FFFFFF"
    df_s_fmt = df_s.copy()
    for col in df_s_fmt.columns:
        df_s_fmt[col] = df_s_fmt[col].apply(lambda v: f"{v:.2f}" if v is not None and not (isinstance(v,float) and math.isnan(v)) else "—")
    df_s_fmt.index.name = "g / WACC"
    df_s_fmt = df_s_fmt.reset_index()
    st.markdown(dark_table(df_s_fmt, lambda v: _cell_color(v)), unsafe_allow_html=True)
    export_buttons(df_s_fmt, f"sensibilidade_{ticker}")

# ══════════════════════════════════════════════════════════════════
# PÁG 7 — MARKOWITZ (com benchmark IBOV)
# ══════════════════════════════════════════════════════════════════
elif pagina == "Markowitz":
    st.markdown("## Otimização de Carteira — Fronteira Eficiente de Markowitz")

    all_tickers = [results[e].get("ticker",e) for e in empresas]
    st.markdown("### Configuração")
    col_a, col_b = st.columns(2)
    with col_a:
        # Import da Carteira Endurance
        import json as _jmk, pathlib as _pmk
        _efile = _pmk.Path("/opt/shipyard/data/endurance/carteira.json")
        _end_tks = []
        if _efile.exists():
            try:
                _end_cart = _jmk.loads(_efile.read_text())
                _end_tks = [p["ticker"] for p in _end_cart if p.get("ticker") and p["ticker"] != "CAIXA"]
            except: pass
        col_imp1, col_imp2 = st.columns([2,1])
        with col_imp1:
            extra = st.text_input("Tickers extras (separados por vírgula)",
                                  value="PETR4.SA, VALE3.SA, BBAS3.SA, ITUB4.SA")
        with col_imp2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(" Importar Endurance", use_container_width=True, key="mk_imp_end"):
                st.session_state["mk_end_imported"] = True
        extra_list = [t.strip() for t in extra.split(",") if t.strip()]
        base_tks = _end_tks if st.session_state.get("mk_end_imported") else []
        portfolio_tickers = list(dict.fromkeys(base_tks + all_tickers + extra_list))
        default_sel = _end_tks[:min(8,len(_end_tks))] if st.session_state.get("mk_end_imported") and _end_tks else portfolio_tickers[:min(5,len(portfolio_tickers))]
        if st.session_state.get("mk_end_imported") and _end_tks:
            st.success(f" {len(_end_tks)} ativos da Endurance importados")
        selected = st.multiselect("Ativos na carteira", portfolio_tickers, default=default_sel)
    with col_b:
        period    = st.selectbox("Período histórico", ["1y","2y","3y","5y"], index=1)
        n_sim     = st.slider("Portfólios simulados (Monte Carlo)", 1000, 10000, 3000, 500)
        risk_free = st.slider("Taxa livre de risco anual (%)", 5.0, 15.0, 11.7, 0.1) / 100
        perfil    = st.radio("Perfil de risco preferido",
                             ["Mínima Variância","Máximo Sharpe","Personalizado"],
                             horizontal=True)
        show_ibov = st.checkbox("Mostrar benchmark IBOV", value=True)

    if len(selected) < 2:
        st.warning("Selecione pelo menos 2 ativos."); st.stop()

    if st.button("  Calcular Fronteira Eficiente", type="primary"):
        with st.spinner("Baixando dados e calculando..."):
            try:
                import yfinance as yf
                from scipy.optimize import minimize

                @st.cache_data(ttl=3600)
                def get_prices(tickers, period):
                    data = yf.download(tickers, period=period, auto_adjust=True, progress=False)
                    if isinstance(data.columns, pd.MultiIndex):
                        prices = data["Close"]
                    else:
                        prices = data[["Close"]] if "Close" in data.columns else data
                    return prices.dropna(how="all")

                prices = get_prices(selected, period)
                prices = prices.dropna(axis=1, thresh=int(len(prices)*0.8))
                valid_tickers = list(prices.columns)
                if len(valid_tickers) < 2:
                    st.error("Dados insuficientes para os tickers selecionados."); st.stop()

                returns = prices.pct_change().dropna()
                mu      = returns.mean() * 252
                cov     = returns.cov() * 252
                n       = len(valid_tickers)

                # Benchmark IBOV
                ibov_ret = None
                ibov_vol = None
                if show_ibov:
                    try:
                        ibov_data = yf.download("^BVSP", period=period, auto_adjust=True, progress=False)
                        ibov_close = ibov_data["Close"].squeeze()
                        ibov_rets = ibov_close.pct_change().dropna()
                        ibov_ret = float(ibov_rets.mean() * 252)
                        ibov_vol = float(ibov_rets.std() * np.sqrt(252))
                    except Exception:
                        ibov_ret = None

                # Monte Carlo
                np.random.seed(42)
                sim_ret, sim_vol, sim_sharpe, sim_w = [], [], [], []
                for _ in range(n_sim):
                    w = np.random.dirichlet(np.ones(n))
                    r_p = float(w @ mu)
                    v_p = float(np.sqrt(w @ cov.values @ w))
                    s_p = (r_p - risk_free) / v_p if v_p > 0 else 0
                    sim_ret.append(r_p); sim_vol.append(v_p)
                    sim_sharpe.append(s_p); sim_w.append(w)

                sim_ret    = np.array(sim_ret)
                sim_vol    = np.array(sim_vol)
                sim_sharpe = np.array(sim_sharpe)

                def neg_sharpe(w):
                    rp = w @ mu; vp = np.sqrt(w @ cov.values @ w)
                    return -(rp - risk_free) / vp if vp>0 else 0
                def port_vol(w):
                    return np.sqrt(w @ cov.values @ w)

                bounds    = tuple((0,1) for _ in range(n))
                constraint = {"type":"eq","fun":lambda w: np.sum(w)-1}

                opt_sharpe = minimize(neg_sharpe, np.ones(n)/n, method="SLSQP",
                                      bounds=bounds, constraints=constraint)
                opt_minvar = minimize(port_vol, np.ones(n)/n, method="SLSQP",
                                      bounds=bounds, constraints=constraint)

                w_sharpe = opt_sharpe.x
                w_minvar = opt_minvar.x
                r_sharpe = float(w_sharpe @ mu); v_sharpe = float(np.sqrt(w_sharpe @ cov.values @ w_sharpe))
                r_minvar = float(w_minvar @ mu); v_minvar = float(np.sqrt(w_minvar @ cov.values @ w_minvar))

                target_rets = np.linspace(sim_ret.min(), sim_ret.max(), 60)
                ef_vols = []
                for tr in target_rets:
                    cons = [{"type":"eq","fun":lambda w: np.sum(w)-1},
                            {"type":"eq","fun":lambda w,t=tr: w@mu - t}]
                    try:
                        res = minimize(port_vol, np.ones(n)/n, method="SLSQP",
                                       bounds=bounds, constraints=cons)
                        ef_vols.append(float(res.fun) if res.success else None)
                    except Exception:
                        ef_vols.append(None)

                ef_pairs = [(v,r) for v,r in zip(ef_vols, target_rets) if v is not None]
                ef_vols_clean = [p[0] for p in ef_pairs]
                ef_rets_clean = [p[1] for p in ef_pairs]

                fig_mz = go.Figure()

                fig_mz.add_trace(go.Scatter(
                    x=sim_vol*100, y=sim_ret*100, mode="markers",
                    marker=dict(size=4, color=sim_sharpe,
                        colorscale=[[0,C["bg4"]],[0.5,C["bg3"]],[1,C["blue_lt"]]],
                        colorbar=dict(title=dict(text="Sharpe",font=dict(color=C["gray"])),
                                      tickfont=dict(color=C["gray"]),thickness=12,x=1.02),
                        opacity=0.5),
                    name="Portfólios MC",
                    hovertemplate="Vol: %{x:.1f}%<br>Ret: %{y:.1f}%<extra></extra>",
                ))

                fig_mz.add_trace(go.Scatter(
                    x=[v*100 for v in ef_vols_clean], y=[r*100 for r in ef_rets_clean],
                    mode="lines", line=dict(color=C["white"],width=2.5),
                    name="Fronteira Eficiente",
                ))

                vol_range = np.linspace(0, max(sim_vol)*100, 100)
                sharpe_opt = (r_sharpe - risk_free) / v_sharpe
                cml_ret = risk_free*100 + sharpe_opt * vol_range
                fig_mz.add_trace(go.Scatter(
                    x=vol_range, y=cml_ret, mode="lines",
                    line=dict(color=C["blue_lt"], width=1.5, dash="dot"),
                    name=f"Capital Market Line (Sharpe={sharpe_opt:.2f})",
                ))

                fig_mz.add_trace(go.Scatter(
                    x=[v_sharpe*100], y=[r_sharpe*100], mode="markers+text",
                    marker=dict(size=14, color=C["pos"], symbol="star",
                                line=dict(color=C["white"],width=1.5)),
                    text=[" Máx Sharpe"], textposition="top right",
                    textfont=dict(color=C["pos"], size=11),
                    name=f"Máx Sharpe ({sharpe_opt:.2f})",
                ))

                fig_mz.add_trace(go.Scatter(
                    x=[v_minvar*100], y=[r_minvar*100], mode="markers+text",
                    marker=dict(size=14, color=C["blue_lt"], symbol="diamond",
                                line=dict(color=C["white"],width=1.5)),
                    text=["◆ Mín Var"], textposition="top right",
                    textfont=dict(color=C["blue_lt"], size=11),
                    name="Mínima Variância",
                ))

                # Benchmark IBOV
                if show_ibov and ibov_ret is not None:
                    ibov_sharpe = (ibov_ret - risk_free) / ibov_vol
                    fig_mz.add_trace(go.Scatter(
                        x=[ibov_vol*100], y=[ibov_ret*100], mode="markers+text",
                        marker=dict(size=14, color="#FFD700", symbol="square",
                                    line=dict(color=C["white"],width=1.5)),
                        text=[" IBOV"], textposition="top left",
                        textfont=dict(color="#FFD700", size=11),
                        name=f"IBOV (Sharpe={ibov_sharpe:.2f})",
                    ))

                for i,t in enumerate(valid_tickers):
                    fig_mz.add_trace(go.Scatter(
                        x=[float(np.sqrt(cov.values[i,i]))*100],
                        y=[float(mu.iloc[i])*100], mode="markers+text",
                        marker=dict(size=10, color=C["gray"], symbol="circle-open",
                                    line=dict(color=C["gray"],width=2)),
                        text=[t], textposition="top center",
                        textfont=dict(color=C["gray2"],size=10),
                        name=t, showlegend=False,
                    ))

                fig_mz.update_layout(**PL,
                    title="Fronteira Eficiente | Nuvem = Monte Carlo |  Máx Sharpe |  IBOV",
                    xaxis_title="Volatilidade Anual (%)",
                    yaxis_title="Retorno Anual Esperado (%)",
                    height=580,
                )
                st.plotly_chart(fig_mz, use_container_width=True)

                if show_ibov and ibov_ret is not None:
                    st.info(f" IBOV — Retorno: {ibov_ret*100:.1f}% a.a. | Vol: {ibov_vol*100:.1f}% | Sharpe: {(ibov_ret-risk_free)/ibov_vol:.2f}")

                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown("### Alocações Ótimas")

                if perfil == "Máximo Sharpe":
                    w_sel = w_sharpe; label_sel = "Máximo Sharpe"
                    r_sel = r_sharpe; v_sel = v_sharpe
                elif perfil == "Mínima Variância":
                    w_sel = w_minvar; label_sel = "Mínima Variância"
                    r_sel = r_minvar; v_sel = v_minvar
                else:
                    w_sel = w_sharpe; label_sel = "Máximo Sharpe (base)"
                    r_sel = r_sharpe; v_sel = v_sharpe

                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    st.markdown(f"#### Portfólio — {label_sel}")
                    df_w = pd.DataFrame({
                        "Ativo": valid_tickers,
                        "Peso (%)": [f"{w*100:.1f}%" for w in w_sel],
                        "Retorno Esp.": [f"{float(mu.iloc[i])*100:.1f}%" for i in range(n)],
                        "Volatilidade": [f"{float(np.sqrt(cov.values[i,i]))*100:.1f}%" for i in range(n)],
                    })
                    st.markdown(dark_table(df_w), unsafe_allow_html=True)
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Retorno Esperado", f"{r_sel*100:.1f}%")
                    c2.metric("Volatilidade",     f"{v_sel*100:.1f}%")
                    c3.metric("Índice de Sharpe", f"{(r_sel-risk_free)/v_sel:.2f}")
                    if show_ibov and ibov_ret is not None:
                        st.markdown(f"<div style='color:{C['gray2']};font-size:.8rem;'>vs IBOV: Ret {ibov_ret*100:.1f}% | Vol {ibov_vol*100:.1f}% | Sharpe {(ibov_ret-risk_free)/ibov_vol:.2f}</div>", unsafe_allow_html=True)

                with col_p2:
                    fig_pizza = go.Figure(go.Pie(
                        labels=valid_tickers, values=w_sel*100, hole=.5,
                        marker_colors=[C["bg3"],C["blue_lt"],C["gray"],
                                       C["bg4"],C["gray2"],C["pos"],C["neg"]][:n],
                        textfont=dict(color=C["white"],size=11),
                    ))
                    fig_pizza.update_layout(
                        paper_bgcolor=C["bg"],
                        font=dict(family="Helvetica,Arial",color=C["gray"]),
                        legend=dict(bgcolor=C["bg"],bordercolor=C["border"]),
                        margin=dict(l=10,r=10,t=30,b=10),
                        title=f"Alocação — {label_sel}",
                        annotations=[dict(text=f"Sharpe<br><b>{(r_sel-risk_free)/v_sel:.2f}</b>",
                            font=dict(size=12,color=C["white"]),showarrow=False)],
                    )
                    st.plotly_chart(fig_pizza, use_container_width=True)

                st.markdown("#### Comparação: Mín Variância vs Máx Sharpe")
                compare_df = pd.DataFrame({
                    "Ativo": valid_tickers,
                    "Mín Variância (%)": [f"{w*100:.1f}%" for w in w_minvar],
                    "Máx Sharpe (%)":    [f"{w*100:.1f}%" for w in w_sharpe],
                })
                st.markdown(dark_table(compare_df), unsafe_allow_html=True)

                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Ret. Mín Var",   f"{r_minvar*100:.1f}%")
                mc2.metric("Vol. Mín Var",   f"{v_minvar*100:.1f}%")
                mc3.metric("Ret. Máx Sharpe", f"{r_sharpe*100:.1f}%")
                mc4.metric("Vol. Máx Sharpe", f"{v_sharpe*100:.1f}%")

                # Correlação entre ativos
                st.markdown("#### Matriz de Correlação")
                corr = returns.corr()
                fig_corr = go.Figure(go.Heatmap(
                    z=corr.values, x=list(corr.columns), y=list(corr.index),
                    colorscale=[
                        [0.0,"#E8F4FD"],[0.25,"#BEDAF2"],
                        [0.5,"#6EB5E8"],[0.75,"#2B7EC2"],
                        [1.0,"#071d36"]
                    ],
                    zmin=-1, zmax=1,
                    text=[[f"{v:.2f}" for v in row] for row in corr.values],
                    texttemplate="%{text}", textfont=dict(size=10,color="#0a1624"),
                    colorbar=dict(tickfont=dict(color=C["gray"]),bgcolor=C["bg2"],bordercolor=C["border"])
                ))
                fig_corr.update_layout(
                    paper_bgcolor=C["bg"],
                    font=dict(family="Helvetica,Arial",color=C["white"]),
                    margin=dict(l=80,r=30,t=30,b=80), height=380)
                st.plotly_chart(fig_corr, use_container_width=True)

            except ImportError as e:
                st.error(f"Biblioteca necessária não instalada: {e}")
                st.code("pip install yfinance scipy")
            except Exception as e:
                import traceback
                st.error(f"Erro ao calcular: {e}")
                st.code(traceback.format_exc())

# ══════════════════════════════════════════════════════════════════
# PÁG 8 — NOTÍCIAS
# ══════════════════════════════════════════════════════════════════
elif pagina == "Notícias":
    st.markdown("## Monitor de Notícias — Mercado Brasileiro")

    feeds = {
        "InfoMoney — Mercado":   "https://www.infomoney.com.br/feed/",
        "InfoMoney — Ações":     "https://www.infomoney.com.br/mercados/acoes/feed/",
        "Valor Econômico":       "https://valor.globo.com/rss/home/",
        "Exame — Investimentos": "https://exame.com/invest/feed/",
        "InvestNews":            "https://investnews.com.br/feed/",
        "Brazil Journal":        "https://braziljournal.com/feed/",
        "NeoFeed":               "https://neofeed.com.br/feed/",
        "MoneyTimes":            "https://www.moneytimes.com.br/feed/",
    }

    col_f, col_q = st.columns([2,2])
    with col_f:
        fonte = st.selectbox("Fonte de notícias", ["Todos"] + list(feeds.keys()))
    with col_q:
        query = st.text_input("Filtrar por palavra-chave", placeholder="ex: WEG, COGNA, Selic...")

    n_noticias = st.slider("Número de notícias", 5, 30, 12, 1)

    if st.button("Carregar Notícias", key="btn_noticias"):
        with st.spinner("Carregando notícias..."):
            try:
                import feedparser
                if fonte == "Todos":
                    entries = []
                    for _fn, _url in feeds.items():
                        try:
                            _f = feedparser.parse(_url)
                            for _e in _f.entries: _e["_fonte"] = _fn
                            entries.extend(_f.entries)
                        except: pass
                else:
                    feed = feedparser.parse(feeds[fonte])
                    entries = feed.entries

                if query:
                    q = query.lower()
                    entries = [e for e in entries if
                                q in e.get("title","").lower() or
                                q in e.get("summary","").lower()]

                entries = entries[:n_noticias]

                if not entries:
                    st.info("Nenhuma notícia encontrada. Tente outro filtro ou fonte.")
                else:
                    for entry in entries:
                        title = entry.get("title", "Sem título")
                        link  = entry.get("link", "#")
                        summ  = entry.get("summary", "")[:200].replace("<br>","").replace("<p>","").strip()
                        date  = entry.get("published", "")[:16] if entry.get("published") else ""

                        # Remove HTML tags simples
                        import re
                        summ = re.sub(r"<[^>]+>", "", summ)[:180]

                        st.markdown(f"""
                        <div class="news-card">
                            <div style="color:{C['blue_lt']};font-size:.72rem;font-weight:600;letter-spacing:.05em;margin-bottom:4px;">{date}</div>
                            <a href="{link}" target="_blank" style="color:{C['white']};font-size:.9rem;font-weight:600;text-decoration:none;">{title}</a>
                            <div style="color:{C['gray']};font-size:.78rem;margin-top:6px;">{summ}...</div>
                        </div>""", unsafe_allow_html=True)

            except ImportError:
                st.error("feedparser não instalado no VPS.")
                st.code("pip install feedparser --break-system-packages")
                st.info("Após instalar, reinicie o dashboard: `systemctl restart shipyard-dashboard`")

                # Fallback: links diretos
                st.markdown("### Links Diretos para Notícias")
                links = [
                    ("InfoMoney — Ações", "https://www.infomoney.com.br/mercados/acoes/"),
                    ("Valor Econômico", "https://valor.globo.com/financas/"),
                    ("B3 — Comunicados", "https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/empresas-listadas.htm"),
                    ("CVM — ITR/DFP", "https://dados.cvm.gov.br/"),
                    ("Broadcast — Tempo Real", "https://www.estadao.com.br/economia/"),
                ]
                for nome, url in links:
                    st.markdown(f" [{nome}]({url})")

            except Exception as e:
                st.error(f"Erro ao carregar notícias: {e}")
                st.info("Verifique a conexão do VPS com a internet.")

    # Calendário de eventos
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## Calendário de Resultados")

    # Calendário dinâmico — gera para todas as empresas cobertas
    def _cal_trimestre(ticker_clean):
        """Estima datas de resultado baseado no padrão B3"""
        import datetime
        hoje = datetime.date.today()
        ano  = hoje.year
        # Padrão: 4T divulgado em fev/mar; 1T em mai; 2T em ago; 3T em nov
        trimestres = [
            (f"4T{str(ano-1)[2:]}", f"Mar {ano}",  " Divulgado" if hoje.month>=3 else " Aguardando"),
            (f"1T{str(ano)[2:]}",   f"Mai {ano}",  " Divulgado" if hoje.month>=5 else " Aguardando"),
            (f"2T{str(ano)[2:]}",   f"Ago {ano}",  " Divulgado" if hoje.month>=8 else " Aguardando"),
            (f"3T{str(ano)[2:]}",   f"Nov {ano}",  " Divulgado" if hoje.month>=11 else " Aguardando"),
            (f"4T{str(ano)[2:]}",   f"Mar {ano+1}"," Previsto"),
        ]
        return trimestres

    MACRO_EVENTS = [
        {"Empresa":" Macro — COPOM", "Evento":"Reunião COPOM",    "Data":"Mai 2026","Status":" Macro"},
        {"Empresa":" Macro — COPOM", "Evento":"Reunião COPOM",    "Data":"Jun 2026","Status":" Macro"},
        {"Empresa":" Macro — IPCA",  "Evento":"IPCA mensal",      "Data":"Todo mês","Status":" Macro"},
        {"Empresa":" Macro — IGP-M", "Evento":"IGP-M mensal",     "Data":"Todo mês","Status":" Macro"},
        {"Empresa":" Macro — PIB",   "Evento":"PIB trimestral",   "Data":"Jun 2026","Status":" Macro"},
        {"Empresa":" Macro — Fed",   "Evento":"FOMC Meeting",     "Data":"Mai 2026","Status":" Macro"},
    ]

    cal_data = []
    for emp in empresas:
        tk = results[emp].get("ticker","").replace(".SA","")
        for trim, data, status in _cal_trimestre(tk):
            cal_data.append({"Ticker":tk,"Empresa":emp[:25],"Evento":f"Resultados {trim}","Data":data,"Status":status})
    cal_data.extend(MACRO_EVENTS)

    df_cal = pd.DataFrame(cal_data)

    # Filtros do calendário
    calfc1, calfc2, calfc3 = st.columns(3)
    with calfc1:
        cal_status = st.multiselect("Status", [" Divulgado"," Aguardando"," Previsto"," Macro"],
            default=[" Aguardando"," Previsto"," Macro"], key="cal_status")
    with calfc2:
        cal_emp = st.multiselect("Empresa", ["Todas"] + list(empresas),
            default=["Todas"], key="cal_emp")
    with calfc3:
        cal_meses = st.multiselect("Mês", sorted(df_cal["Data"].unique()),
            default=[], key="cal_mes")

    df_cal_f = df_cal.copy()
    if cal_status: df_cal_f = df_cal_f[df_cal_f["Status"].isin(cal_status)]
    if cal_emp and "Todas" not in cal_emp:
        df_cal_f = df_cal_f[df_cal_f["Empresa"].isin([e[:25] for e in cal_emp])]
    if cal_meses: df_cal_f = df_cal_f[df_cal_f["Data"].isin(cal_meses)]

    def _cal_color(v):
        if "" in str(v): return f"color:{C['pos']}"
        if "" in str(v): return f"color:#FFB347"
        if "" in str(v): return f"color:{C['sky']}"
        if "" in str(v): return f"color:{C['gray']}"
        return f"color:{C['white']}"
    st.markdown(dark_table(df_cal_f, _cal_color), unsafe_allow_html=True)
    export_buttons(df_cal_f, "calendario_resultados")

# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════
# PÁG 9 — CARTEIRA ENDURANCE + EXPOSIÇÃO SETORIAL (#15 e #27)
# ══════════════════════════════════════════════════════════════════
elif pagina == "Carteira Endurance":
    import json as _json
    from pathlib import Path as _Path
    from datetime import datetime as _dt, date as _date
    import numpy as _np

    _END_DIR  = _Path("/opt/shipyard/data/endurance")
    _END_DIR.mkdir(parents=True, exist_ok=True)
    _CART_FILE = _END_DIR / "carteira.json"
    _TR_FILE   = _END_DIR / "trackrecord.json"
    _CDI_AA    = 0.1075  # CDI aproximado a.a.

    # ── helpers ──────────────────────────────────────────────────
    def _load_carteira():
        if _CART_FILE.exists():
            return _json.loads(_CART_FILE.read_text())
        return []

    def _save_carteira(c):
        _CART_FILE.write_text(_json.dumps(c, indent=2, ensure_ascii=False))

    def _load_tr():
        if _TR_FILE.exists():
            return _json.loads(_TR_FILE.read_text())
        return []

    def _save_tr(t):
        _TR_FILE.write_text(_json.dumps(t, indent=2, ensure_ascii=False))

    @st.cache_data(ttl=300)
    def _get_hist(tickers_tuple, period="2y"):
        import yfinance as yf
        tks = [t for t in tickers_tuple if t != "CAIXA"]
        if not tks:
            return pd.DataFrame()
        try:
            raw = yf.download(tks + ["^BVSP","^GSPC","USDBRL=X"],
                              period=period, auto_adjust=True, progress=False)["Close"]
            if isinstance(raw, pd.Series):
                raw = raw.to_frame(tks[0])
            raw = raw.rename(columns={"^BVSP":"IBOV","^GSPC":"SPX","USDBRL=X":"USDBRL"})
            return raw.dropna(how="all")
        except Exception as e:
            st.warning(f"yfinance: {e}")
            return pd.DataFrame()

    def _portfolio_returns(df, carteira):
        rv  = [p for p in carteira if p["ticker"] != "CAIXA" and p["ticker"] in df.columns]
        if not rv: return None, None
        total_rv  = sum(p["peso"] for p in rv)
        total_cx  = sum(p["peso"] for p in carteira if p["ticker"] == "CAIXA")
        total_all = total_rv + total_cx
        if total_all == 0: return None, None
        w_rv = {p["ticker"]: p["peso"]/total_all for p in rv}
        w_cx = total_cx / total_all
        rets = df[[p["ticker"] for p in rv]].pct_change().dropna()
        port_ret = sum(rets[tk] * w for tk, w in w_rv.items())
        cdi_d = (1 + _CDI_AA)**(1/252) - 1
        port_ret += cdi_d * w_cx
        return port_ret, rets

    def _risk_metrics(port_ret, bench_ret=None):
        if port_ret is None or len(port_ret) < 5:
            return {}
        r = _np.array(port_ret.dropna())
        ann = 252
        cdi_d = (1 + _CDI_AA)**(1/252) - 1
        ret_aa  = float((1 + r).prod() ** (ann/len(r)) - 1)
        vol_aa  = float(r.std() * ann**0.5)
        sharpe  = (ret_aa - _CDI_AA) / vol_aa if vol_aa else 0
        neg     = r[r < 0]
        sortino_vol = float(neg.std() * ann**0.5) if len(neg) else vol_aa
        sortino = (ret_aa - _CDI_AA) / sortino_vol if sortino_vol else 0
        cum     = (1 + r).cumprod()
        roll_max= _np.maximum.accumulate(cum)
        dd      = (cum - roll_max) / roll_max
        max_dd  = float(dd.min())
        calmar  = ret_aa / abs(max_dd) if max_dd else 0
        var95   = float(_np.percentile(r, 5))
        cvar95  = float(r[r <= var95].mean()) if len(r[r <= var95]) else var95
        out = dict(ret_aa=ret_aa, vol_aa=vol_aa, sharpe=sharpe,
                   sortino=sortino, max_dd=max_dd, calmar=calmar,
                   var95=var95, cvar95=cvar95)
        if bench_ret is not None:
            br = _np.array(bench_ret.reindex(port_ret.index).dropna())
            pr = _np.array(port_ret.reindex(port_ret.index).dropna())
            n  = min(len(br), len(pr))
            if n > 5:
                cov   = _np.cov(pr[:n], br[:n])
                beta  = cov[0,1] / cov[1,1] if cov[1,1] else 1.0
                alpha = ret_aa - (_CDI_AA + beta * (float((1+br).prod()**(ann/n)-1) - _CDI_AA))
                corr  = _np.corrcoef(pr[:n], br[:n])[0,1]
                bench_aa = float((1+br).prod()**(ann/n)-1)
                out.update(beta=beta, alpha=alpha, corr=corr, bench_aa=bench_aa)
        return out

    # ── estado ───────────────────────────────────────────────────
    carteira = _load_carteira()
    tr_data  = _load_tr()

    # ── header ───────────────────────────────────────────────────
    st.markdown(f"""<div style="display:flex;align-items:center;gap:16px;margin-bottom:8px">
        <span style="color:{C['white']};font-size:1.3rem;font-weight:800"> Carteira Endurance</span>
        <span style="background:{C['bg2']};border:1px solid {C['border']};border-radius:4px;
            padding:2px 10px;font-size:.72rem;color:{C['gray']}">{len([p for p in carteira if p['ticker']!='CAIXA'])} posições · {sum(p['peso'] for p in carteira):.0f}% alocado</span>
    </div>""", unsafe_allow_html=True)

    # ── tabs ─────────────────────────────────────────────────────
    tab_port, tab_edit, tab_risk, tab_tr, tab_cota, tab_bt = st.tabs([
        " Visão da Carteira", " Gerenciar Posições", " Risco & KPIs", " Trackrecord", " Custos & Cota", " Backtest & Cenários"
    ])

    # ════════════════════════════════════════════════════════════
    # TAB 1 — VISÃO DA CARTEIRA
    # ════════════════════════════════════════════════════════════
    with tab_port:
        if not carteira:
            st.info("Carteira vazia. Adicione posições na aba ")
        else:
            tickers_rv = tuple(p["ticker"] for p in carteira if p["ticker"] != "CAIXA")
            _period_opt = st.select_slider("Período",["1mo","3mo","6mo","1y","2y","5y"], value="1y",
                                           key="end_period")
            with st.spinner("Carregando cotações..."):
                df_hist = _get_hist(tickers_rv, _period_opt)

            # Cotações atuais
            precos = {}
            if not df_hist.empty:
                for tk in tickers_rv:
                    if tk in df_hist.columns:
                        s = df_hist[tk].dropna()
                        precos[tk] = float(s.iloc[-1]) if not s.empty else 0.0

            # Tabela de posições
            rows = []
            total_pond = 0.0
            for p in carteira:
                tk = p["ticker"]
                pe = p.get("preco_entrada", 0)
                pa = precos.get(tk, 0.0)
                peso = p["peso"]
                if tk == "CAIXA":
                    ret = None; ret_s = "CDI"
                else:
                    ret = (pa - pe)/pe*100 if pe and pa else None
                    ret_s = f"{ret:+.1f}%" if ret is not None else "—"
                    if ret: total_pond += ret * peso/100
                rows.append({"Ticker": tk.replace(".SA",""),
                             "Empresa": p.get("empresa",""),
                             "Setor": p.get("setor",""),
                             "Peso": f"{peso:.1f}%",
                             "Entrada": f"R${pe:.2f}" if pe else "—",
                             "Atual": f"R${pa:.2f}" if pa else ("CDI" if tk=="CAIXA" else "—"),
                             "Retorno": ret_s})

            def _color(val):
                if "%" in str(val) and val not in ["CDI","—"]:
                    try:
                        v = float(str(val).replace("%","").replace("+",""))
                        if v > 15:  return f"color:{C['pos']};font-weight:bold"
                        if v > 0:   return f"color:{C['sky']}"
                        if v < -10: return f"color:{C['neg']};font-weight:bold"
                        if v < 0:   return f"color:{C['gray2']}"
                    except: pass
                return f"color:{C['white']}"

            st.markdown(dark_table(pd.DataFrame(rows), _color), unsafe_allow_html=True)

            # KPIs rápidos
            peso_cx = sum(p["peso"] for p in carteira if p["ticker"]=="CAIXA")
            k1,k2,k3,k4 = st.columns(4)
            k1.metric("Retorno Ponderado", f"{total_pond:+.2f}%")
            k2.metric("Posições RV", f"{len(tickers_rv)}")
            k3.metric("Caixa / RF", f"{peso_cx:.1f}%")
            k4.metric("Concentração Top3",
                f"{sum(sorted([p['peso'] for p in carteira if p['ticker']!='CAIXA'],reverse=True)[:3]):.1f}%")

            # Gráfico retorno acumulado
            if not df_hist.empty:
                port_ret, _ = _portfolio_returns(df_hist, carteira)
                if port_ret is not None:
                    port_acc = (1 + port_ret).cumprod() - 1
                    # Salva retorno acumulado real no session_state para uso em outras abas
                    st.session_state["end_ret_real_pct"] = float(port_acc.iloc[-1] * 100) if len(port_acc) else None
                    st.session_state["end_ret_periodo"] = "histórico"

                    # Comparativo configurável
                    bench_opts = {"IBOV":"IBOV","S&P 500":"SPX","CDI (proxy)":"CDI"}
                    bench_extra = st.multiselect("Comparar com", list(bench_opts.keys()),
                                                 default=["IBOV"], key="end_bench")

                    fig_port = go.Figure()
                    fig_port.add_trace(go.Scatter(
                        x=port_acc.index, y=port_acc.values*100,
                        mode="lines", name=" Endurance",
                        line=dict(color=C["blue_lt"], width=2.5)))

                    for b in bench_extra:
                        bk = bench_opts[b]
                        if bk == "CDI":
                            cdi_d = (1+_CDI_AA)**(1/252)-1
                            cdi_acc = pd.Series((1+cdi_d)**_np.arange(len(port_acc))-1,
                                                index=port_acc.index)
                            fig_port.add_trace(go.Scatter(
                                x=cdi_acc.index, y=cdi_acc.values*100,
                                mode="lines", name="CDI",
                                line=dict(color=C["teal"], width=1.5, dash="dot")))
                        elif bk in df_hist.columns:
                            s = df_hist[bk].dropna().pct_change().dropna()
                            s = s.reindex(port_ret.index).fillna(0)
                            acc = (1+s).cumprod()-1
                            fig_port.add_trace(go.Scatter(
                                x=acc.index, y=acc.values*100,
                                mode="lines", name=b,
                                line=dict(color=C["gray"], width=1.5, dash="dot")))

                    fig_port.add_hline(y=0, line_color=C["border"], line_width=1)
                    fig_port.update_layout(**PL,
                        title="Retorno Acumulado — base 0%",
                        yaxis_title="Retorno (%)", height=420)
                    st.plotly_chart(fig_port, use_container_width=True)

            # Pizza setorial
            st.markdown("### Exposição Setorial")
            setor_peso = {}
            for p in carteira:
                s = p.get("setor","Outros")
                setor_peso[s] = setor_peso.get(s,0) + p["peso"]
            sc1, sc2 = st.columns(2)
            cores_s = [C["blue_lt"],C["sky"],C["navy"],C["teal"],C["gray"],
                       C["bg3"],"#5EC8A0","#FFB347","#9B59B6","#E67E22",C["gray2"]]
            with sc1:
                fig_pie = go.Figure(go.Pie(
                    labels=list(setor_peso.keys()), values=list(setor_peso.values()),
                    hole=0.52, marker_colors=cores_s[:len(setor_peso)],
                    textfont=dict(color=C["white"],size=11), textinfo="label+percent"))
                fig_pie.update_layout(paper_bgcolor=C["bg"],
                    font=dict(family="Helvetica,Arial",color=C["white"]),
                    legend=dict(bgcolor=C["bg"],bordercolor=C["border"]),
                    margin=dict(l=10,r=10,t=20,b=10), height=300,
                    annotations=[dict(text="Setores",font=dict(size=11,color=C["white"]),showarrow=False)])
                st.plotly_chart(fig_pie, use_container_width=True)
            with sc2:
                # Heatmap de correlação
                if not df_hist.empty and len(tickers_rv) > 1:
                    corr_tks = [t for t in tickers_rv if t in df_hist.columns]
                    if len(corr_tks) > 1:
                        corr_df = df_hist[corr_tks].pct_change().dropna().corr()
                        labels = [t.replace(".SA","") for t in corr_tks]
                        fig_corr = go.Figure(go.Heatmap(
                            z=corr_df.values, x=labels, y=labels,
                            colorscale=[[0,C["neg"]],[0.5,C["bg2"]],[1,C["pos"]]],
                            zmin=-1, zmax=1, text=corr_df.round(2).values,
                            texttemplate="%{text}", textfont=dict(size=9)))
                        fig_corr.update_layout(**{**PL, "margin": dict(l=40,r=10,t=40,b=40)}, title="Correlação entre Ativos", height=300)
                        st.plotly_chart(fig_corr, use_container_width=True)

    # ════════════════════════════════════════════════════════════
    # TAB 2 — GERENCIAR POSIÇÕES
    # ════════════════════════════════════════════════════════════
    with tab_edit:
        st.markdown("###  Posições Atuais")

        # Editor de tabela
        df_edit = pd.DataFrame([{
            "ticker": p["ticker"], "empresa": p.get("empresa",""),
            "setor": p.get("setor",""), "peso": p["peso"],
            "preco_entrada": p.get("preco_entrada",0.0),
            "data_entrada": p.get("data_entrada","")
        } for p in carteira])

        edited = st.data_editor(
            df_edit,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "ticker": st.column_config.TextColumn("Ticker", help="Ex: PETR4.SA ou CAIXA"),
                "empresa": st.column_config.TextColumn("Empresa"),
                "setor": st.column_config.TextColumn("Setor"),
                "peso": st.column_config.NumberColumn("Peso (%)", min_value=0, max_value=100, step=0.5),
                "preco_entrada": st.column_config.NumberColumn("P. Entrada (R$)", min_value=0, step=0.01),
                "data_entrada": st.column_config.TextColumn("Data Entrada", help="AAAA-MM-DD"),
            },
            key="end_editor"
        )

        total_peso = edited["peso"].sum() if not edited.empty else 0
        _pcol = C["pos"] if 98 <= total_peso <= 102 else C["neg"]
        st.markdown(f"<span style='color:{_pcol};font-weight:700'>Total alocado: {total_peso:.1f}%</span>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**+ Adicionar posição manualmente**")
        if True:
            # Lista de tickers disponíveis no sistema para autocomplete
            _tickers_disponiveis = sorted([
                r.get("ticker","").replace(".SA","")
                for r in results.values()
                if r.get("ticker","")
            ])
            _setores_disponiveis = sorted(set([
                r.get("sector","") or r.get("setor","")
                for r in results.values()
                if r.get("sector","") or r.get("setor","")
            ]))
            _empresas_map = {
                r.get("ticker","").replace(".SA",""): r.get("name","") or r.get("empresa","")
                for r in results.values()
                if r.get("ticker","")
            }
            na1,na2,na3 = st.columns(3)
            with na1:
                new_ticker_sel = st.selectbox(
                    "Ticker (autocomplete)", 
                    [""] + _tickers_disponiveis + ["CAIXA","OUTRO"],
                    key="new_tk_sel",
                    help="Selecione um ticker da cobertura ou escolha OUTRO para digitar manualmente"
                )
                if new_ticker_sel == "OUTRO" or new_ticker_sel == "":
                    new_ticker = st.text_input("Ticker manual", placeholder="Ex: TOTS3", key="new_tk_manual")
                else:
                    new_ticker = new_ticker_sel
                # Preenche empresa automaticamente
                _emp_auto = _empresas_map.get(new_ticker.upper(), "")
                new_emp = st.text_input("Empresa", value=_emp_auto, key="new_emp")
            with na2:
                # Autocomplete de setor
                _setor_auto = ""
                if new_ticker.upper() in _empresas_map:
                    _r = results.get(next((k for k in results if results[k].get("ticker","").replace(".SA","").upper()==new_ticker.upper()), ""), {})
                    _setor_auto = _r.get("sector","") or _r.get("setor","")
                new_setor_sel = st.selectbox(
                    "Setor (autocomplete)",
                    [""] + _setores_disponiveis + ["Outro"],
                    index=(_setores_disponiveis.index(_setor_auto)+1) if _setor_auto in _setores_disponiveis else 0,
                    key="new_set_sel"
                )
                if new_setor_sel == "Outro" or new_setor_sel == "":
                    new_setor = st.text_input("Setor manual", key="new_set_manual")
                else:
                    new_setor = new_setor_sel
                new_peso = st.number_input("Peso (%)", min_value=0.0, max_value=100.0, step=0.5, key="new_peso")
            with na3:
                new_entrada = st.number_input("Preco de entrada (R$)", min_value=0.0, step=0.01, key="new_preco")
                new_data    = st.text_input("Data de entrada", placeholder="AAAA-MM-DD", key="new_data",
                    value=_dt.today().strftime("%Y-%m-%d"))
            if st.button("Adicionar a carteira", key="new_add", type="primary", use_container_width=True):
                if new_ticker.strip():
                    cart_atual = _load_carteira()
                    tk_novo = new_ticker.strip().upper()
                    if tk_novo != "CAIXA" and not tk_novo.endswith(".SA"):
                        tk_novo += ".SA"
                    if tk_novo in [p["ticker"].upper() for p in cart_atual]:
                        st.warning(f"{tk_novo} ja esta na carteira. Edite na tabela acima.")
                    else:
                        try:
                            cart_atual.append({"ticker":tk_novo,"empresa":new_emp.strip(),
                                "setor":new_setor.strip(),"peso":new_peso,
                                "preco_entrada":new_entrada,"data_entrada":new_data.strip()})
                            _save_carteira(cart_atual)
                            st.success(f"{tk_novo} adicionado com sucesso!")
                            st.cache_data.clear()
                            st.rerun()
                        except PermissionError:
                            st.error("Erro de permissao no arquivo. Execute no servidor: chmod 666 /opt/shipyard/data/endurance/carteira.json")
                else:
                    st.error("Informe o ticker.")
        col_save, col_imp = st.columns([1,1])
        with col_save:
            if st.button(" Salvar Carteira", use_container_width=True, type="primary"):
                nova = edited.to_dict("records")
                _save_carteira(nova)
                st.success("Carteira salva!")
                st.cache_data.clear()
                st.rerun()

        with col_imp:
            st.markdown("**Importar CSV ComDinheiro**")
            uploaded = st.file_uploader("Upload CSV", type=["csv","txt"], key="end_upload",
                                        label_visibility="collapsed")
            if uploaded:
                try:
                    df_imp = pd.read_csv(uploaded, sep=None, engine="python",
                                        encoding="latin1", dtype=str)
                    df_imp.columns = [c.strip().lower() for c in df_imp.columns]
                    # Tenta mapear colunas comuns do ComDinheiro
                    col_map = {}
                    for c in df_imp.columns:
                        if any(k in c for k in ["ticker","ativo","papel","cod"]): col_map["ticker"]=c
                        if any(k in c for k in ["peso","alocacao","%","participacao"]): col_map["peso"]=c
                        if any(k in c for k in ["preco","entrada","custo","pm"]): col_map["preco_entrada"]=c
                        if any(k in c for k in ["empresa","nome","emis"]): col_map["empresa"]=c
                    if "ticker" in col_map:
                        importados = []
                        for _, row in df_imp.iterrows():
                            tk = str(row[col_map["ticker"]]).strip().upper()
                            if not tk.endswith(".SA") and tk != "CAIXA":
                                tk += ".SA"
                            importados.append({
                                "ticker": tk,
                                "empresa": str(row.get(col_map.get("empresa",""), tk)).strip(),
                                "setor": "—",
                                "peso": float(str(row.get(col_map.get("peso","0"),"0")).replace(",",".").replace("%","") or 0),
                                "preco_entrada": float(str(row.get(col_map.get("preco_entrada","0"),"0")).replace(",",".") or 0),
                                "data_entrada": str(_date.today()),
                            })
                        _save_carteira(importados)
                        st.success(f"{len(importados)} posições importadas!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Não achei coluna 'ticker'. Colunas: {list(df_imp.columns)}")
                except Exception as e:
                    st.error(f"Erro ao importar: {e}")

    # ════════════════════════════════════════════════════════════
    # TAB 3 — RISCO & KPIs
    # ════════════════════════════════════════════════════════════
    with tab_risk:
        if not carteira:
            st.info("Carteira vazia.")
        else:
            tickers_rv = tuple(p["ticker"] for p in carteira if p["ticker"] != "CAIXA")
            _rp = st.select_slider("Janela de análise",
                ["6mo","1y","2y","3y","5y"], value="2y", key="end_risk_period")
            with st.spinner("Calculando métricas de risco..."):
                df_r = _get_hist(tickers_rv, _rp)

            if df_r.empty:
                st.warning("Sem dados históricos suficientes.")
            else:
                port_ret, ind_rets = _portfolio_returns(df_r, carteira)
                bench_ret = df_r["IBOV"].pct_change().dropna() if "IBOV" in df_r.columns else None
                m = _risk_metrics(port_ret, bench_ret)

                if m:
                    st.markdown("###  Métricas de Risco")
                    r1,r2,r3,r4 = st.columns(4)
                    r1.metric("Retorno a.a.", f"{m.get('ret_aa',0)*100:+.1f}%")
                    r2.metric("Volatilidade a.a.", f"{m.get('vol_aa',0)*100:.1f}%")
                    r3.metric("Sharpe", f"{m.get('sharpe',0):.2f}")
                    r4.metric("Sortino", f"{m.get('sortino',0):.2f}")

                    r5,r6,r7,r8 = st.columns(4)
                    r5.metric("Max Drawdown", f"{m.get('max_dd',0)*100:.1f}%",
                              delta_color="inverse")
                    r6.metric("Calmar", f"{m.get('calmar',0):.2f}")
                    r7.metric("VaR 95% (diário)", f"{m.get('var95',0)*100:.2f}%",
                              delta_color="inverse")
                    r8.metric("CVaR 95%", f"{m.get('cvar95',0)*100:.2f}%",
                              delta_color="inverse")

                    if "beta" in m:
                        st.markdown("<hr>", unsafe_allow_html=True)
                        rb1,rb2,rb3,rb4 = st.columns(4)
                        rb1.metric("Beta vs IBOV", f"{m['beta']:.2f}")
                        rb2.metric("Alpha (a.a.)", f"{m['alpha']*100:+.2f}%")
                        rb3.metric("Correlação IBOV", f"{m['corr']:.2f}")
                        rb4.metric("IBOV a.a.", f"{m.get('bench_aa',0)*100:+.1f}%")

                    # Drawdown chart
                    if port_ret is not None:
                        cum_r = (1 + port_ret).cumprod()
                        roll_max = cum_r.cummax()
                        dd_series = (cum_r - roll_max) / roll_max * 100

                        fig_dd = go.Figure()
                        fig_dd.add_trace(go.Scatter(
                            x=dd_series.index, y=dd_series.values,
                            mode="lines", fill="tozeroy",
                            fillcolor=f"rgba({int(C['neg'][1:3],16)},{int(C['neg'][3:5],16)},{int(C['neg'][5:7],16)},.2)",
                            line=dict(color=C["neg"], width=1.2), name="Drawdown"))
                        fig_dd.update_layout(**PL, title="Drawdown Histórico (%)",
                                             yaxis_title="%", height=280)
                        st.plotly_chart(fig_dd, use_container_width=True)

                    # Distribuição de retornos
                    if port_ret is not None:
                        fig_hist = go.Figure()
                        fig_hist.add_trace(go.Histogram(
                            x=port_ret.values*100, nbinsx=60,
                            marker_color=C["blue_lt"], opacity=0.8, name="Retornos diários"))
                        fig_hist.add_vline(x=m.get("var95",0)*100,
                                           line_color=C["neg"], line_dash="dash",
                                           annotation_text=f"VaR 95%: {m.get('var95',0)*100:.2f}%")
                        fig_hist.update_layout(**PL,
                                               title="Distribuição de Retornos Diários (%)",
                                               height=280)
                        st.plotly_chart(fig_hist, use_container_width=True)

                    # Risk per ativo
                    if ind_rets is not None and not ind_rets.empty:
                        st.markdown("### Risco por Ativo")
                        ativo_metrics = []
                        for tk in ind_rets.columns:
                            r_tk = ind_rets[tk].dropna()
                            if len(r_tk) < 20: continue
                            ret_aa_tk = float((1+r_tk).prod()**(252/len(r_tk))-1)
                            vol_tk    = float(r_tk.std()*252**0.5)
                            sh_tk     = (ret_aa_tk - _CDI_AA)/vol_tk if vol_tk else 0
                            cum_tk    = (1+r_tk).cumprod()
                            dd_tk     = float(((cum_tk - cum_tk.cummax())/cum_tk.cummax()).min())
                            ativo_metrics.append({
                                "Ativo": tk.replace(".SA",""),
                                "Ret. a.a.": f"{ret_aa_tk*100:+.1f}%",
                                "Vol. a.a.": f"{vol_tk*100:.1f}%",
                                "Sharpe": f"{sh_tk:.2f}",
                                "Max DD": f"{dd_tk*100:.1f}%",
                            })
                        if ativo_metrics:
                            st.markdown(dark_table(pd.DataFrame(ativo_metrics)), unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════
    # TAB 4 — TRACKRECORD
    # ════════════════════════════════════════════════════════════
    with tab_tr:
        st.markdown("###  Trackrecord Diário")

        col_snap, col_info = st.columns([1,3])
        with col_snap:
            if st.button("📸 Registrar NAV Hoje", use_container_width=True, type="primary"):
                tickers_rv_tr = tuple(p["ticker"] for p in carteira if p["ticker"] != "CAIXA")
                df_snap = _get_hist(tickers_rv_tr, "5d")
                if not df_snap.empty:
                    port_ret_snap, _ = _portfolio_returns(df_snap, carteira)
                    if port_ret_snap is not None:
                        today_str = str(_date.today())
                        cum_snap = float((1 + port_ret_snap).prod() - 1)
                        # Carrega TR e adiciona snapshot
                        tr_curr = _load_tr()
                        # Remove entrada de hoje se já existir
                        tr_curr = [x for x in tr_curr if x.get("date") != today_str]
                        tr_curr.append({"date": today_str, "nav_acc": round(cum_snap*100, 4)})
                        tr_curr.sort(key=lambda x: x["date"])
                        _save_tr(tr_curr)
                        st.success(f"NAV registrado: {cum_snap*100:+.2f}%")
                        st.rerun()

        with col_info:
            st.caption(f"{len(tr_data)} snapshots registrados. Clique para adicionar o NAV de hoje.")

        if tr_data:
            df_tr = pd.DataFrame(tr_data)
            df_tr["date"] = pd.to_datetime(df_tr["date"])
            df_tr = df_tr.sort_values("date")

            fig_tr = go.Figure()
            fig_tr.add_trace(go.Scatter(
                x=df_tr["date"], y=df_tr["nav_acc"],
                mode="lines+markers", name=" Endurance (NAV)",
                line=dict(color=C["blue_lt"], width=2.5),
                marker=dict(size=6, color=C["blue_lt"])))
            fig_tr.add_hline(y=0, line_color=C["border"], line_width=1)
            fig_tr.update_layout(**PL,
                title="Trackrecord — NAV Acumulado (%)",
                yaxis_title="Retorno acumulado (%)", height=400)
            st.plotly_chart(fig_tr, use_container_width=True)

            # Tabela de snapshots
            df_tr_show = df_tr.copy()
            df_tr_show["Variação Diária"] = df_tr_show["nav_acc"].diff().apply(
                lambda x: f"{x:+.2f}%" if pd.notna(x) else "—")
            df_tr_show["date"] = df_tr_show["date"].dt.strftime("%Y-%m-%d")
            df_tr_show = df_tr_show.rename(columns={"date":"Data","nav_acc":"NAV Acum. (%)"})
            st.dataframe(df_tr_show[["Data","NAV Acum. (%)","Variação Diária"]].tail(30),
                         use_container_width=True, hide_index=True)

            export_buttons(df_tr_show, "trackrecord_endurance")
        else:
            st.info("Nenhum snapshot registrado. Clique em 📸 Registrar NAV Hoje para iniciar o trackrecord.")




    with tab_cota:
        import json as _jcota
        _COTA_FILE = _END_DIR / "cota.json"
        def _load_cota():
            if _COTA_FILE.exists():
                return _jcota.loads(_COTA_FILE.read_text())
            return {"valor_inicial": 1000.0, "data_inicio": "2024-01-02",
                    "taxa_gestao_aa": 2.0, "taxa_perf": 20.0,
                    "hurdle": "CDI", "patrimonio": 10_000_000.0,
                    "despesas_fixas_mensais": 15_000.0, "historico": []}
        def _save_cota(c): _COTA_FILE.write_text(_jcota.dumps(c, indent=2, ensure_ascii=False))

        cfg_cota = _load_cota()

        st.markdown("###  Configuração do Fundo")
        cc1,cc2,cc3 = st.columns(3)
        with cc1:
            val_ini  = st.number_input("Valor inicial da cota (R$)", value=float(cfg_cota.get("valor_inicial",1000)), step=100.0, key="cota_ini")
            st.caption(f"= {_brl(val_ini,2)}")
            dt_ini   = st.text_input("Data de início", value=cfg_cota.get("data_inicio","2024-01-02"), key="cota_dt")
            patr     = st.number_input("Patrimônio líquido atual (R$)", value=float(cfg_cota.get("patrimonio",10e6)), step=100_000.0, key="cota_patr")
            st.caption(f"= {_brl(patr,2)}")
        with cc2:
            tg_aa    = st.slider("Taxa de gestão a.a. (%)", 0.0, 3.0, float(cfg_cota.get("taxa_gestao_aa",2.0)), 0.1, key="cota_tg")
            tp       = st.slider("Taxa de performance (%)", 0.0, 30.0, float(cfg_cota.get("taxa_perf",20.0)), 1.0, key="cota_tp")
            hurdle_tipo = st.selectbox("Hurdle rate", ["CDI","IBOV","IPCA + spread"], index=0, key="cota_hurdle")
            if hurdle_tipo == "IPCA + spread":
                _spread_default = float(cfg_cota.get("ipca_spread", 5.0))
                ipca_spread = st.slider("Spread sobre IPCA (%a.a.)", 0.0, 15.0, _spread_default, 0.5, key="cota_ipca_spread")
                hurdle = f"IPCA+{ipca_spread:.1f}%"
                st.caption(f"Ex: IPCA 5% + {ipca_spread:.1f}% = ~{5+ipca_spread:.1f}% a.a.")
            else:
                ipca_spread = 0.0
                hurdle = hurdle_tipo
        with cc3:
            desp_fix = st.number_input("Despesas fixas mensais (R$)", value=float(cfg_cota.get("despesas_fixas_mensais",15000)), step=1000.0, key="cota_desp")
            st.caption(f"= {_brl(desp_fix,2)}")
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(" Salvar e Aplicar", key="cota_save", type="primary", use_container_width=True):
                cfg_cota.update({"valor_inicial":val_ini,"data_inicio":dt_ini,
                    "taxa_gestao_aa":tg_aa,"taxa_perf":tp,"hurdle":hurdle,
                    "ipca_spread":ipca_spread,"patrimonio":patr,
                    "despesas_fixas_mensais":desp_fix})
                _save_cota(cfg_cota)
                st.success(" Configuração salva e aplicada!")
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("###  Demonstrativo de Custos")

        # Cálculos
        tg_mensal = patr * (tg_aa/100) / 12
        desp_total_mensal = tg_mensal + desp_fix
        desp_total_aa = desp_total_mensal * 12
        tx_efetiva_aa = desp_total_aa / patr * 100 if patr else 0

        # Cálculos adicionais
        tg_aa_valor    = patr * (tg_aa/100)
        desp_total_aa  = desp_total_mensal * 12

        dm1,dm2,dm3,dm4 = st.columns(4)
        dm1.metric("Gestao Mensal", _brl(tg_mensal,0),
            help=f"Taxa anual: {_brl(tg_aa_valor,0)} ({tg_aa:.1f}% a.a.)")
        dm2.metric("Despesas Fixas Mensais", _brl(desp_fix,0),
            help=f"Anual: {_brl(desp_fix*12,0)}")
        dm3.metric("Total Mensal", _brl(desp_total_mensal,0),
            help=f"Total anual: {_brl(desp_total_aa,0)}")
        dm4.metric("Encargos Totais a.a.", f"{tx_efetiva_aa:.2f}%")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("### Demonstrativo Anual Detalhado")
        da1,da2,da3 = st.columns(3)
        da1.metric("Taxa de Gestao a.a.", _brl(tg_aa_valor,0),
            help=f"{tg_aa:.1f}% sobre patrimonio de {_brl(patr,0)}")
        da2.metric("Despesas Operacionais a.a.", _brl(desp_fix*12,0))
        da3.metric("Custo Total a.a.", _brl(desp_total_aa,0))

        # Taxa de performance estimada
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("### Taxa de Performance")
        gp1,gp2,gp3,gp4 = st.columns(4)
        _ret_real = st.session_state.get("end_ret_real_pct", None)
        _periodo_real = st.session_state.get("end_ret_periodo", None)
        if _ret_real is not None:
            _ret_default = round(float(_ret_real), 2)
            gp1.markdown(f"<small style='color:#4CAF50'>Retorno real carregado da Visao da Carteira ({_periodo_real})</small>", unsafe_allow_html=True)
        else:
            _ret_default = 12.0
            gp1.markdown("<small style='color:#888'>Nenhum dado da Visao da Carteira — usando estimativa manual</small>", unsafe_allow_html=True)
        _ret_est = gp1.number_input("Retorno do fundo (%)", value=_ret_default, step=0.5, key="dem_ret_est")
        _bench_est = {"CDI": _CDI_AA*100, "IBOV": 10.0}.get(
            hurdle.split("+")[0].strip(), _CDI_AA*100 + float(hurdle.split("+")[1].replace("%","").strip()) if "+" in hurdle else _CDI_AA*100)
        gp2.metric("Hurdle Rate", f"{_bench_est:.2f}% a.a.", help=hurdle)
        _alpha_est = _ret_est - _bench_est
        _perf_fee_est = max(0, (_alpha_est/100) * patr * (tp/100)) if _alpha_est > 0 else 0.0
        gp3.metric("Alpha Estimado", f"{_alpha_est:+.2f}%",
            delta_color="normal" if _alpha_est>0 else "inverse")
        gp4.metric("Perf. Fee Estimada", _brl(_perf_fee_est,0),
            help=f"{tp:.0f}% sobre alpha de {_alpha_est:+.2f}%")

        # Gross up
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("### Gross Up — Resultado Liquido para a Gestora")
        gu1,gu2,gu3,gu4 = st.columns(4)
        with gu1:
            aliq_ir = st.number_input("Aliquota IR (%)", value=15.0, min_value=0.0, max_value=50.0, step=0.5, key="gu_ir")
        with gu2:
            aliq_pis_cofins = st.number_input("PIS/COFINS (%)", value=9.25, min_value=0.0, max_value=20.0, step=0.25, key="gu_pc")
        with gu3:
            aliq_csll = st.number_input("CSLL (%)", value=9.0, min_value=0.0, max_value=15.0, step=0.5, key="gu_csll")
        with gu4:
            aliq_iss = st.number_input("ISS (%)", value=5.0, min_value=0.0, max_value=10.0, step=0.5, key="gu_iss")

        receita_bruta_gu  = tg_aa_valor + _perf_fee_est
        total_aliq        = (aliq_ir + aliq_pis_cofins + aliq_csll + aliq_iss) / 100
        impostos_gu       = receita_bruta_gu * total_aliq
        resultado_liq_gu  = receita_bruta_gu - impostos_gu - desp_total_aa
        margem_liq_gu     = resultado_liq_gu / receita_bruta_gu * 100 if receita_bruta_gu else 0

        gr1,gr2,gr3,gr4,gr5 = st.columns(5)
        gr1.metric("Receita Bruta", _brl(receita_bruta_gu,0))
        gr2.metric("Impostos Totais", _brl(impostos_gu,0),
            help=f"IR {aliq_ir}% + PIS/COFINS {aliq_pis_cofins}% + CSLL {aliq_csll}% + ISS {aliq_iss}%")
        gr3.metric("Custos Operacionais", _brl(desp_total_aa,0))
        gr4.metric("Resultado Liquido", _brl(resultado_liq_gu,0),
            delta=f"{margem_liq_gu:.1f}% margem",
            delta_color="normal" if resultado_liq_gu>0 else "inverse")
        gr5.metric("Aliquota Efetiva Total", f"{total_aliq*100:.2f}%")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("###  Valor da Cota & Performance")

        # Usa trackrecord para calcular valor de cota
        tr_c = _load_tr()
        if tr_c:
            import pandas as _pdc
            df_cota = _pdc.DataFrame(tr_c)
            df_cota["data"] = _pdc.to_datetime(df_cota["date"])
            df_cota = df_cota.sort_values("data")
            df_cota["valor_cota_bruto"] = val_ini * (1 + df_cota["nav_acc"]/100)
            # Desconta TER diário
            ter_diario = (1 + tx_efetiva_aa/100)**(1/252) - 1
            n_dias = (df_cota["data"] - df_cota["data"].iloc[0]).dt.days
            df_cota["valor_cota_liq"] = df_cota["valor_cota_bruto"] * (1 - ter_diario)**n_dias

            # CDI acumulado como hurdle
            cdi_d = (1 + _CDI_AA)**(1/252) - 1
            df_cota["cdi_acc"] = val_ini * ((1+cdi_d)**n_dias)

            # Taxa de performance (semestral — aplica se acima do hurdle)
            ultima = df_cota.iloc[-1]
            ret_bruto   = float(ultima["nav_acc"])
            ret_cdi_per = float((1+_CDI_AA)**(n_dias.iloc[-1]/252)-1)*100 if len(n_dias) else 0
            alpha_pp    = ret_bruto - ret_cdi_per
            perf_fee    = max(0, alpha_pp/100 * patr * tp/100) if alpha_pp > 0 else 0.0

            cv1,cv2,cv3,cv4 = st.columns(4)
            cv1.metric("Cota Bruta Atual", _brl(float(ultima["valor_cota_bruto"]),4))
            cv2.metric("Cota Líquida (c/ TER)", _brl(float(ultima["valor_cota_liq"]),4))
            cv3.metric("Retorno s/ CDI (alpha)", f"{alpha_pp:+.2f}%",
                delta_color="normal" if alpha_pp>0 else "inverse")
            cv4.metric("Perf. Fee Estimada", _brl(perf_fee,0),
                help="Taxa de performance semestral sobre alpha vs CDI")

            # Gráfico cota bruta vs líquida vs CDI
            fig_cota = go.Figure()
            fig_cota.add_trace(go.Scatter(x=df_cota["data"], y=df_cota["valor_cota_bruto"],
                mode="lines", name="Cota Bruta", line=dict(color=C["blue_lt"],width=2)))
            fig_cota.add_trace(go.Scatter(x=df_cota["data"], y=df_cota["valor_cota_liq"],
                mode="lines", name="Cota Líquida (c/ TER)", line=dict(color=C["pos"],width=2)))
            fig_cota.add_trace(go.Scatter(x=df_cota["data"], y=df_cota["cdi_acc"],
                mode="lines", name=f"CDI ({_CDI_AA*100:.1f}% a.a.)", line=dict(color=C["gray"],width=1.5,dash="dot")))
            fig_cota.update_layout(**PL, title="Evolução do Valor da Cota (R$)",
                yaxis_title="R$", height=380)
            st.plotly_chart(fig_cota, use_container_width=True)
            st.dataframe(df_cota[["date","valor_cota_bruto","valor_cota_liq"]].tail(20).rename(
                columns={"date":"Data","valor_cota_bruto":"Cota Bruta","valor_cota_liq":"Cota Líquida"}),
                use_container_width=True, hide_index=True)
        else:
            st.info("Registre snapshots de NAV na aba  Trackrecord para calcular o valor da cota.")


    with tab_bt:
        import numpy as _npbt
        st.markdown("###  Backtest & Simulação de Cenários")

        btt1, btt2 = st.tabs([" Backtest Histórico", " Monte Carlo da Carteira"])

        with btt1:
            st.markdown("#### Backtest — Simula a carteira atual em períodos históricos")
            bc1,bc2,bc3 = st.columns(3)
            with bc1:
                bt_period = st.selectbox("Período", ["1y","2y","3y","5y"], index=1, key="bt_period")
            with bc2:
                bt_bench  = st.selectbox("Benchmark", ["IBOV","CDI","SPX"], index=0, key="bt_bench")
            with bc3:
                bt_rebal  = st.selectbox("Rebalanceamento", ["Nunca","Mensal","Trimestral","Semestral"], index=0, key="bt_rebal")

            if st.button(" Rodar Backtest", type="primary", key="bt_run"):
                tks_bt = tuple(p["ticker"] for p in carteira if p["ticker"] != "CAIXA")
                with st.spinner("Baixando dados históricos..."):
                    df_bt = _get_hist(tks_bt, bt_period)
                if df_bt.empty:
                    st.error("Sem dados suficientes.")
                else:
                    port_ret_bt, _ = _portfolio_returns(df_bt, carteira)
                    if port_ret_bt is not None:
                        port_acc_bt = (1 + port_ret_bt).cumprod() - 1

                        fig_bt = go.Figure()
                        fig_bt.add_trace(go.Scatter(x=port_acc_bt.index, y=port_acc_bt.values*100,
                            mode="lines", name=" Endurance",
                            line=dict(color=C["blue_lt"],width=2.5),
                            fill="tozeroy", fillcolor="rgba(30,100,200,0.08)"))

                        bench_map = {"IBOV":"IBOV","SPX":"SPX","CDI":"CDI"}
                        bk = bench_map[bt_bench]
                        if bk == "CDI":
                            cdi_d2 = (1+_CDI_AA)**(1/252)-1
                            bench_acc = pd.Series((1+cdi_d2)**_npbt.arange(len(port_acc_bt))-1, index=port_acc_bt.index)
                        elif bk in df_bt.columns:
                            bs = df_bt[bk].pct_change().dropna().reindex(port_ret_bt.index).fillna(0)
                            bench_acc = (1+bs).cumprod()-1
                        else: bench_acc = None

                        if bench_acc is not None:
                            fig_bt.add_trace(go.Scatter(x=bench_acc.index, y=bench_acc.values*100,
                                mode="lines", name=bt_bench,
                                line=dict(color=C["gray"],width=1.5,dash="dot")))

                        fig_bt.add_hline(y=0, line_color=C["border"], line_width=1)
                        fig_bt.update_layout(**PL, title=f"Backtest — {bt_period} | vs {bt_bench}",
                            yaxis_title="Retorno Acumulado (%)", height=420)
                        st.plotly_chart(fig_bt, use_container_width=True)

                        # Métricas
                        m_bt = _risk_metrics(port_ret_bt, bench_acc.pct_change().dropna() if bench_acc is not None else None)
                        if m_bt:
                            mb1,mb2,mb3,mb4,mb5,mb6 = st.columns(6)
                            mb1.metric("Retorno a.a.", f"{m_bt.get('ret_aa',0)*100:+.1f}%")
                            mb2.metric("Volatilidade", f"{m_bt.get('vol_aa',0)*100:.1f}%")
                            mb3.metric("Sharpe", f"{m_bt.get('sharpe',0):.2f}")
                            mb4.metric("Max Drawdown", f"{m_bt.get('max_dd',0)*100:.1f}%")
                            mb5.metric("Alpha", f"{m_bt.get('alpha',0)*100:+.2f}%" if "alpha" in m_bt else "—")
                            mb6.metric("Beta", f"{m_bt.get('beta',0):.2f}" if "beta" in m_bt else "—")

                        # Underwater chart
                        cum_bt = (1 + port_ret_bt).cumprod()
                        dd_bt  = (cum_bt - cum_bt.cummax()) / cum_bt.cummax() * 100
                        fig_uw = go.Figure()
                        fig_uw.add_trace(go.Scatter(x=dd_bt.index, y=dd_bt.values,
                            mode="lines", fill="tozeroy",
                            fillcolor="rgba(220,50,50,0.2)",
                            line=dict(color=C["neg"],width=1), name="Drawdown"))
                        fig_uw.update_layout(**PL, title="Underwater Chart (Drawdown %)",
                            yaxis_title="%", height=220)
                        st.plotly_chart(fig_uw, use_container_width=True)

        with btt2:
            st.markdown("#### Monte Carlo — Simulação de Cenários da Carteira")
            sc1,sc2,sc3 = st.columns(3)
            with sc1:
                mc_n     = st.selectbox("Simulações", [500,1000,5000], index=1, key="end_mc_n")
                mc_anos  = st.slider("Horizonte (anos)", 1, 10, 3, 1, key="end_mc_anos")
            with sc2:
                mc_ret   = st.slider("Retorno esperado a.a. (%)", 0.0, 40.0, 12.0, 0.5, key="end_mc_ret") / 100
                mc_vol   = st.slider("Volatilidade a.a. (%)", 5.0, 50.0, 18.0, 0.5, key="end_mc_vol") / 100
            with sc3:
                mc_patr  = st.number_input("Patrimônio inicial (R$)", value=10_000_000.0, step=500_000.0, key="end_mc_patr")
                mc_aporte= st.number_input("Aporte mensal (R$)", value=0.0, step=50_000.0, key="end_mc_aporte")

            if st.button(" Simular Cenários", type="primary", key="end_mc_run"):
                _npbt.random.seed(42)
                n_steps2 = mc_anos * 12
                mu_m2    = (1 + mc_ret)**(1/12) - 1
                sig_m2   = mc_vol / _npbt.sqrt(12)
                paths2   = _npbt.zeros((mc_n, n_steps2+1))
                paths2[:,0] = mc_patr
                for t2 in range(1, n_steps2+1):
                    r2 = _npbt.random.normal(mu_m2, sig_m2, mc_n)
                    paths2[:,t2] = paths2[:,t2-1] * (1+r2) + mc_aporte

                x2 = list(range(n_steps2+1))
                pc10b = _npbt.percentile(paths2,10,axis=0)
                pc50b = _npbt.percentile(paths2,50,axis=0)
                pc90b = _npbt.percentile(paths2,90,axis=0)

                fig_mc2 = go.Figure()
                fig_mc2.add_trace(go.Scatter(x=x2+x2[::-1],
                    y=list(pc90b)+list(pc10b[::-1]), fill="toself",
                    fillcolor="rgba(30,80,160,0.15)", line=dict(color="rgba(0,0,0,0)"), name="P10-P90"))
                fig_mc2.add_trace(go.Scatter(x=x2, y=pc50b, mode="lines",
                    line=dict(color=C["blue_lt"],width=2.5), name="Mediana"))
                fig_mc2.add_trace(go.Scatter(x=x2, y=pc10b, mode="lines",
                    line=dict(color=C["neg"],width=1.2,dash="dot"), name="Bear P10"))
                fig_mc2.add_trace(go.Scatter(x=x2, y=pc90b, mode="lines",
                    line=dict(color=C["pos"],width=1.2,dash="dot"), name="Bull P90"))

                # Amostra de caminhos
                for i2 in _npbt.random.choice(mc_n, min(50,mc_n), replace=False):
                    fig_mc2.add_trace(go.Scatter(x=x2, y=paths2[i2], mode="lines",
                        line=dict(color="rgba(100,180,255,0.18)",width=1.0),
                        showlegend=False, hoverinfo="skip"))

                tickv2 = list(range(0,n_steps2+1,3))
                tickt2 = [f"M{v}" for v in tickv2]
                _pl_mc2 = {**PL,
                    "xaxis":dict(tickvals=tickv2,ticktext=tickt2,
                        gridcolor="rgba(255,255,255,0.04)"),
                    "yaxis":dict(title="Patrimônio (R$)",
                        gridcolor="rgba(255,255,255,0.04)"),
                    "height":450,"legend":dict(orientation="h",y=-0.12)}
                fig_mc2.update_layout(**_pl_mc2,
                    title=f"Monte Carlo Carteira — {mc_n:,} cenários | {mc_anos} anos")
                st.plotly_chart(fig_mc2, use_container_width=True)

                # KPIs finais
                final_vals = paths2[:,-1]
                prob_dobrar = float((_npbt.array(final_vals) > mc_patr*2).mean()*100)
                k1,k2,k3,k4 = st.columns(4)
                k1.metric("Mediana final", _brl(float(_npbt.median(final_vals)),0))
                k2.metric("Bear (P10)", _brl(float(pc10b[-1]),0))
                k3.metric("Bull (P90)", _brl(float(pc90b[-1]),0))
                k4.metric("Prob. dobrar patrimônio", f"{prob_dobrar:.1f}%")


elif pagina == "Exposição Geográfica":
    st.markdown("##  Exposição Geográfica")

    GEO = {
        "WEGE3.SA": {"Brasil":42,"América do Norte":18,"Europa":20,"Ásia":12,"América Latina":6,"Outros":2},
        "COGN3.SA": {"Brasil":100},
        "PETR4.SA": {"Brasil":85,"América do Norte":8,"Europa":4,"Outros":3},
        "VALE3.SA": {"China":55,"Brasil":15,"Europa":12,"Japão":8,"Outros":10},
        "ABEV3.SA": {"Brasil":60,"América do Norte":20,"América Latina":15,"Europa":5},
        "SUZB3.SA": {"Europa":35,"China":25,"Brasil":20,"América do Norte":12,"Outros":8},
        "EMBR3.SA": {"América do Norte":45,"Europa":20,"Brasil":15,"Ásia":12,"Outros":8},
        "GERDAU":   {"Brasil":55,"América do Norte":30,"América Latina":10,"Outros":5},
    }
    COUNTRY_MAP = {
        "Brasil":"BRA","América do Norte":"USA","Europa":"DEU","China":"CHN",
        "Ásia":"CHN","América Latina":"ARG","Japão":"JPN","Outros":"RUS",
    }

    # Filtros
    fc1,fc2,fc3 = st.columns(3)
    with fc1:
        modo = st.radio("Visualização",["Mapa Coroplético","Barras por Empresa","Treemap"],horizontal=True)
    with fc2:
        setor_filter = st.multiselect("Filtrar por Setor",
            list(set(results[e].get("setor","Outros") for e in empresas)),
            default=[], key="geo_setor")
    with fc3:
        min_exp = st.slider("Exposição mínima (%)", 0, 50, 0, 5, key="geo_min")

    # Empresas filtradas
    emps_geo = [e for e in empresas
                if (not setor_filter or results[e].get("setor","") in setor_filter)]
    tk_sel = st.multiselect("Empresas",
        [e for e in emps_geo],
        default=emps_geo[:8],
        format_func=lambda e: results[e].get("ticker",e).replace(".SA",""),
        key="geo_emps")

    # Agrega exposição ponderada por EV
    all_countries = {}
    for e in (tk_sel or emps_geo):
        tk = results[e].get("ticker","")
        geo = GEO.get(tk, GEO.get(tk.replace(".SA",""), {"Brasil":100}))
        ev  = abs(float(results[e].get("enterprise_value") or 1e9))
        for pais, pct_v in geo.items():
            if pct_v >= min_exp:
                all_countries[pais] = all_countries.get(pais,0) + pct_v * ev/1e9

    if not all_countries:
        st.info("Nenhum dado para os filtros selecionados.")
    else:
        total = sum(all_countries.values())
        norm  = {k: v/total*100 for k,v in all_countries.items()}

        if modo == "Mapa Coroplético":
            import plotly.express as px
            df_map = pd.DataFrame([
                {"País": p, "Exposição (%)": round(v,1),
                 "iso": COUNTRY_MAP.get(p,"BRA")}
                for p,v in norm.items()])
            fig_geo = px.choropleth(df_map,
                locations="iso", color="Exposição (%)",
                hover_name="País",
                color_continuous_scale=[[0,"#0a1628"],[0.3,C["navy"]],[0.7,C["blue_lt"]],[1,C["pos"]]],
                range_color=(0, df_map["Exposição (%)"].max()))
            fig_geo.update_layout(
                paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
                font=dict(color=C["white"],family="Helvetica,Arial"),
                geo=dict(bgcolor=C["bg"], showframe=False,
                         showcoastlines=True, coastlinecolor=C["border"],
                         showland=True, landcolor=C["bg2"],
                         showocean=True, oceancolor=C["bg"],
                         showlakes=False, projection_type="natural earth"),
                coloraxis_colorbar=dict(
                    title=dict(text="Exp. (%)", font=dict(color=C["white"])),
                    tickfont=dict(color=C["white"])),
                margin=dict(l=0,r=0,t=30,b=0), height=480)
            st.plotly_chart(fig_geo, use_container_width=True)

        elif modo == "Barras por Empresa":
            rows_bar = []
            for e in (tk_sel or emps_geo):
                tk = results[e].get("ticker","")
                geo = GEO.get(tk, GEO.get(tk.replace(".SA",""), {"Brasil":100}))
                for pais, pct_v in geo.items():
                    if pct_v >= min_exp:
                        rows_bar.append({"Empresa": tk.replace(".SA",""), "País": pais, "Exp (%)": pct_v})
            if rows_bar:
                df_bar = pd.DataFrame(rows_bar)
                import plotly.express as px
                fig_bar = px.bar(df_bar, x="Empresa", y="Exp (%)", color="País",
                    barmode="stack",
                    color_discrete_sequence=[C["blue_lt"],C["sky"],C["teal"],C["pos"],
                                             C["gray"],C["navy"],"#FFB347","#9B59B6"])
                fig_bar.update_layout(**{**PL,"margin":dict(l=20,r=20,t=40,b=60)},
                    height=440, xaxis_tickangle=-30)
                st.plotly_chart(fig_bar, use_container_width=True)

        else:  # Treemap
            import plotly.express as px
            df_tree = pd.DataFrame([{"País":k,"Exposição":round(v,1)} for k,v in norm.items()])
            fig_tree = px.treemap(df_tree, path=["País"], values="Exposição",
                color="Exposição",
                color_continuous_scale=[[0,C["bg2"]],[0.5,C["navy"]],[1,C["blue_lt"]]])
            fig_tree.update_layout(paper_bgcolor=C["bg"],
                font=dict(color=C["white"]),
                margin=dict(l=0,r=0,t=30,b=0), height=440)
            st.plotly_chart(fig_tree, use_container_width=True)

        # Tabela resumo
        st.markdown("### Resumo por País")
        df_res = pd.DataFrame([{"País":k,"Exposição Ponderada (%)":f"{v:.1f}%"}
                                for k,v in sorted(norm.items(),key=lambda x:-x[1])])
        st.markdown(dark_table(df_res), unsafe_allow_html=True)
        export_buttons(df_res, "exposicao_geografica")


elif pagina == "Governança":
    st.markdown("## Governança Corporativa")
    emp_sel = st.selectbox("Empresa", empresas,
        format_func=lambda e: f"{results[e].get('ticker',e).replace('.SA','')} — {e}",
        key="gov_emp")
    r = results[emp_sel]; ticker = r.get("ticker", emp_sel)

    # Dados ricos hardcoded para cobertura principal
    GOVERNANCA = {
        "WEGE3.SA": {"segmento_b3":"Novo Mercado","tag_along":"100%","free_float":"~45%",
            "controlling":"Família Voigt / Fundação WEG","link_ri":"https://ri.weg.net",
            "conselho":[{"Nome":"Décio da Silva","Cargo":"Presidente CA","Independente":"Não"},
                {"Nome":"Sérgio Schwartz","Cargo":"Membro","Independente":"Sim"},
                {"Nome":"Nildemar Secches","Cargo":"Membro Ind.","Independente":"Sim"}],
            "diretoria":[{"Nome":"Harry Schmelzer Jr.","Cargo":"CEO","Desde":"2012"},
                {"Nome":"André Rodrigues","Cargo":"CFO/DRI","Desde":"2015"}]},
        "COGN3.SA": {"segmento_b3":"Novo Mercado","tag_along":"100%","free_float":"~65%",
            "controlling":"Saber (Kroton) / Free Float","link_ri":"https://ri.cogna.com.br",
            "conselho":[{"Nome":"Rodrigo Galindo","Cargo":"Presidente CA","Independente":"Não"},
                {"Nome":"Carlos Senna","Cargo":"Membro Ind.","Independente":"Sim"}],
            "diretoria":[{"Nome":"Roberto Valério","Cargo":"CEO","Desde":"2022"},
                {"Nome":"Bruno Ferrari","Cargo":"CFO/DRI","Desde":"2021"}]},
    }

    @st.cache_data(ttl=3600)
    def _gov_dynamic(tk):
        try:
            import yfinance as yf
            t = yf.Ticker(tk)
            info = t.info or {}
            holders = t.major_holders
            inst    = t.institutional_holders
            return info, holders, inst
        except: return {}, None, None

    gov = GOVERNANCA.get(ticker)
    with st.spinner("Buscando dados..."):
        info_yf, holders_yf, inst_yf = _gov_dynamic(ticker)

    # KPIs dinâmicos via yfinance
    g1,g2,g3,g4 = st.columns(4)
    seg = (gov or {}).get("segmento_b3") or info_yf.get("exchange","—")
    tag = (gov or {}).get("tag_along","—")
    ff  = (gov or {}).get("free_float") or (f"{info_yf.get('floatShares',0)/max(info_yf.get('sharesOutstanding',1),1)*100:.1f}%" if info_yf.get('floatShares') else "—")
    ctrl= (gov or {}).get("controlling") or info_yf.get("companyOfficers","—")
    g1.metric("Segmento B3", seg)
    g2.metric("Tag Along",   tag)
    g3.metric("Free Float",  ff)
    g4.metric("País", info_yf.get("country","BR"))

    tab_ca, tab_dir, tab_holders = st.tabs(["🏛️ Conselho","👔 Diretoria"," Acionistas"])

    with tab_ca:
        if gov and gov.get("conselho"):
            st.markdown(dark_table(pd.DataFrame(gov["conselho"])), unsafe_allow_html=True)
        else:
            officers = info_yf.get("companyOfficers",[])
            ca = [{"Nome":o.get("name","—"),"Cargo":o.get("title","—"),
                   "Remuneração":f"US$ {int(o.get('totalPay',0)):,}".replace(",",".") if o.get("totalPay") else "—"}
                  for o in officers if any(k in o.get("title","").lower() for k in ["board","chair","conselho","director","presidente"])]
            if ca: st.markdown(dark_table(pd.DataFrame(ca)), unsafe_allow_html=True)
            else: st.info("Dados do conselho não disponíveis via API. Consulte o site de RI.")

    with tab_dir:
        if gov and gov.get("diretoria"):
            st.markdown(dark_table(pd.DataFrame(gov["diretoria"])), unsafe_allow_html=True)
        else:
            officers = info_yf.get("companyOfficers",[])
            dirs = [{"Nome":o.get("name","—"),"Cargo":o.get("title","—"),
                     "Desde":str(o.get("yearBorn","—")),
                     "Remuneração":f"US$ {int(o.get('totalPay',0)):,}".replace(",",".") if o.get("totalPay") else "—"}
                    for o in officers if not any(k in o.get("title","").lower() for k in ["board","chair"])]
            if dirs: st.markdown(dark_table(pd.DataFrame(dirs)), unsafe_allow_html=True)
            else: st.info("Sem dados de diretoria via API.")

    with tab_holders:
        if holders_yf is not None and not holders_yf.empty:
            st.markdown("**Composição Acionária (Major Holders)**")
            st.dataframe(holders_yf, use_container_width=True, hide_index=True)
        if inst_yf is not None and not inst_yf.empty:
            st.markdown("**Detentores Institucionais ≥ 5%**")
            shares_out = float(info_yf.get("sharesOutstanding",1) or 1)
            df_inst5 = inst_yf.copy()
            if "% Out" in df_inst5.columns:
                df_inst5 = df_inst5[df_inst5["% Out"].apply(lambda x: float(x or 0)*100 >= 5)]
                df_inst5["% Capital"] = df_inst5["% Out"].apply(lambda x: f"{float(x)*100:.2f}%")
            st.markdown(dark_table(df_inst5.head(20)), unsafe_allow_html=True)
        ri = (gov or {}).get("link_ri") or info_yf.get("website","")
        if ri: st.markdown(f" [Site de Relações com Investidores]({ri})")


elif pagina == "Grupo Econômico":
    st.markdown("## Estrutura do Grupo Econômico")
    emp_sel = st.selectbox("Empresa", empresas,
        format_func=lambda e: f"{results[e].get('ticker',e).replace('.SA','')} — {e}",
        key="grp_emp")
    r = results[emp_sel]; ticker = r.get("ticker", emp_sel)

    GRUPO_ECONOMICO = {
        "WEGE3.SA": {
            "nos":[{"id":"FUNDACAO","label":"Fundação WEG\n33%","tipo":"controladora"},
                   {"id":"FAMILIA","label":"Família Voigt\n22%","tipo":"controladora"},
                   {"id":"FF","label":"Free Float\n45%","tipo":"mercado"},
                   {"id":"WEGE3","label":"WEG S.A.\nWEGE3","tipo":"listada"},
                   {"id":"WEG_IND","label":"WEG Ind. 100%","tipo":"subsidiaria"},
                   {"id":"WEG_INT","label":"WEG Intl. 100%","tipo":"subsidiaria"},
                   {"id":"WEG_EN","label":"WEG Energy 100%","tipo":"subsidiaria"},
                   {"id":"WEG_US","label":"WEG USA 100%","tipo":"subsidiaria"},
                   {"id":"WEG_DE","label":"WEG Europe 100%","tipo":"subsidiaria"}],
            "arestas":[("FUNDACAO","WEGE3"),("FAMILIA","WEGE3"),("FF","WEGE3"),
                       ("WEGE3","WEG_IND"),("WEGE3","WEG_INT"),("WEGE3","WEG_EN"),
                       ("WEG_INT","WEG_US"),("WEG_INT","WEG_DE")]},
        "COGN3.SA": {
            "nos":[{"id":"SABER","label":"Saber (Kroton)\n35%","tipo":"controladora"},
                   {"id":"FF","label":"Free Float\n65%","tipo":"mercado"},
                   {"id":"COGN3","label":"Cogna Ed.\nCOGN3","tipo":"listada"},
                   {"id":"KROTON","label":"Kroton 100%","tipo":"subsidiaria"},
                   {"id":"VASTA","label":"Vasta Plat. 73%","tipo":"subsidiaria"},
                   {"id":"SABER_ED","label":"Saber Educ. 100%","tipo":"subsidiaria"},
                   {"id":"AMPLI","label":"Ampli 100%","tipo":"subsidiaria"}],
            "arestas":[("SABER","COGN3"),("FF","COGN3"),
                       ("COGN3","KROTON"),("COGN3","VASTA"),
                       ("COGN3","SABER_ED"),("COGN3","AMPLI")]},
    }

    grupo = GRUPO_ECONOMICO.get(ticker)

    @st.cache_data(ttl=3600)
    def _grp_dynamic(tk):
        try:
            import yfinance as yf
            info = yf.Ticker(tk).info or {}
            return info
        except: return {}

    info_g = _grp_dynamic(ticker)

    if grupo:
        # Monta grafo com plotly
        nos = grupo["nos"]; arestas = grupo["arestas"]
        cores_tipo = {"controladora":C["blue_lt"],"listada":C["pos"],
                      "subsidiaria":C["sky"],"mercado":C["gray"]}
        import math
        n = len(nos)
        # Layout radial simples
        pos = {}
        listada = next((nd["id"] for nd in nos if nd["tipo"]=="listada"), nos[0]["id"])
        pos[listada] = (0,0)
        outros = [nd for nd in nos if nd["id"]!=listada]
        for i,nd in enumerate(outros):
            ang = 2*math.pi*i/len(outros)
            r_  = 1.8 if nd["tipo"] in ["controladora","mercado"] else 1.0
            pos[nd["id"]] = (r_*math.cos(ang), r_*math.sin(ang))

        edge_x=[]; edge_y=[]
        for a,b in arestas:
            if a in pos and b in pos:
                edge_x+=[pos[a][0],pos[b][0],None]
                edge_y+=[pos[a][1],pos[b][1],None]

        fig_grp = go.Figure()
        fig_grp.add_trace(go.Scatter(x=edge_x,y=edge_y,mode="lines",
            line=dict(color=C["border"],width=1.5),hoverinfo="none",showlegend=False))
        for nd in nos:
            x,y = pos.get(nd["id"],(0,0))
            cor = cores_tipo.get(nd["tipo"],C["gray"])
            fig_grp.add_trace(go.Scatter(
                x=[x],y=[y],mode="markers+text",
                marker=dict(size=38 if nd["tipo"]=="listada" else 28,
                            color=cor,line=dict(width=2,color=C["bg"])),
                text=[nd["label"]],textposition="bottom center",
                textfont=dict(color=C["white"],size=9),
                name=nd["tipo"],showlegend=False,
                hovertext=nd["label"],hoverinfo="text"))
        fig_grp.update_layout(**{**PL,"margin":dict(l=20,r=20,t=40,b=20)},
            title="Estrutura Societária",height=500,
            xaxis=dict(showgrid=False,zeroline=False,showticklabels=False),
            yaxis=dict(showgrid=False,zeroline=False,showticklabels=False))
        st.plotly_chart(fig_grp, use_container_width=True)

        # Legenda
        lc1,lc2,lc3,lc4 = st.columns(4)
        _c1=C["blue_lt"];_c2=C["pos"];_c3=C["sky"];_c4=C["gray"]
        lc1.markdown(f"<span style='color:{_c1}'>⬤</span> Controladora", unsafe_allow_html=True)
        lc2.markdown(f"<span style='color:{_c2}'>⬤</span> Listada (B3)", unsafe_allow_html=True)
        lc3.markdown(f"<span style='color:{_c3}'>⬤</span> Subsidiária", unsafe_allow_html=True)
        lc4.markdown(f"<span style='color:{_c4}'>⬤</span> Mercado", unsafe_allow_html=True)
    else:
        st.info(f"Estrutura societária detalhada de {ticker.replace('.SA','')} não cadastrada.")
        # Mostra o que temos via yfinance
        if info_g:
            st.markdown("**Dados disponíveis via Yahoo Finance:**")
            campos = ["longName","sector","industry","country","website",
                      "fullTimeEmployees","marketCap","enterpriseValue"]
            rows_g = [{"Campo": c, "Valor": str(info_g.get(c,"—"))} for c in campos if info_g.get(c)]
            if rows_g: st.dataframe(pd.DataFrame(rows_g),use_container_width=True,hide_index=True)
        st.markdown(" Para adicionar a estrutura completa, entre em contato com o administrador do sistema.")


elif pagina == "Setores Macro":
    st.markdown("## Teia de Empresas por Setor Macro")
    st.caption("Agrupa todas as empresas da cobertura + carteira Endurance por setor. "
               "Tamanho dos nós = EV ou peso na carteira.")

    # Mapa setor macro por ticker
    SETOR_MAP = {
        "WEGE3.SA": "Bens Industriais",
        "COGN3.SA": "Educação",
        "ITUB4.SA": "Financeiro",
        "BBAS3.SA": "Financeiro",
        "PETR4.SA": "Petróleo & Gás",
        "VALE3.SA": "Mineração",
        "RENT3.SA": "Consumo Discricionário",
        "MGLU3.SA": "Consumo Discricionário",
        "RADL3.SA": "Saúde",
        "ABEV3.SA": "Consumo Básico",
        "CAIXA":    "Renda Fixa",
    }
    SETOR_CORES = {
        "Bens Industriais":       C["blue_lt"],
        "Educação":               C["sky"],
        "Financeiro":             C["navy"],
        "Petróleo & Gás":         "#E67E22",
        "Mineração":              "#8E44AD",
        "Consumo Discricionário": C["teal"],
        "Consumo Básico":         "#27AE60",
        "Saúde":                  "#E74C3C",
        "Renda Fixa":             C["gray2"],
    }

    # Coleta empresas: cobertura Shipyard + Endurance
    todas_empresas = {}
    for emp in empresas:
        tk = results[emp].get("ticker", emp)
        ev = float(results[emp].get("enterprise_value") or 1e10)
        todas_empresas[tk] = {"ev": ev / 1e9, "fonte": "Cobertura Shipyard"}

    ENDURANCE_TICKERS = {
        "WEGE3.SA": 12.0, "ITUB4.SA": 10.5, "PETR4.SA": 9.0,
        "VALE3.SA": 8.5,  "BBAS3.SA": 7.5,  "RENT3.SA": 7.0,
        "MGLU3.SA": 5.5,  "RADL3.SA": 5.0,  "COGN3.SA": 4.5,
        "ABEV3.SA": 4.0,
    }
    for tk, peso in ENDURANCE_TICKERS.items():
        if tk not in todas_empresas:
            todas_empresas[tk] = {"ev": peso * 5, "fonte": "Endurance"}
        else:
            todas_empresas[tk]["fonte"] = "Ambos"

    # Agrupa por setor
    setores_dict = {}
    for tk, info in todas_empresas.items():
        s = SETOR_MAP.get(tk, "Outros")
        if s not in setores_dict: setores_dict[s] = []
        setores_dict[s].append({"ticker": tk, **info})

    setores_lista = sorted(setores_dict.keys())
    n_setores = len(setores_lista)

    # Posições: setores em círculo maior, empresas em satélites
    import math as _math
    pos_nos = {}
    for i_s, setor in enumerate(setores_lista):
        ang_s = 2 * _math.pi * i_s / n_setores
        cx, cy = 3.5 * _math.cos(ang_s), 3.5 * _math.sin(ang_s)
        pos_nos[f"_S_{setor}"] = (cx, cy)
        empresas_setor = setores_dict[setor]
        n_e = len(empresas_setor)
        for i_e, emp_data in enumerate(empresas_setor):
            ang_e = ang_s + (i_e - (n_e-1)/2) * 0.4
            r_e = 1.8
            pos_nos[emp_data["ticker"]] = (cx + r_e * _math.cos(ang_e),
                                            cy + r_e * _math.sin(ang_e))

    fig_teia = go.Figure()

    # Arestas setor → empresa
    for setor, emps in setores_dict.items():
        if f"_S_{setor}" not in pos_nos: continue
        sx, sy = pos_nos[f"_S_{setor}"]
        cor = SETOR_CORES.get(setor, C["gray"])
        for emp_data in emps:
            tk = emp_data["ticker"]
            if tk not in pos_nos: continue
            ex, ey = pos_nos[tk]
            fig_teia.add_trace(go.Scatter(
                x=[sx, ex, None], y=[sy, ey, None],
                mode="lines",
                line=dict(color=cor, width=1.5, dash="dot"),
                hoverinfo="none", showlegend=False
            ))

    # Nós de setor
    for setor in setores_lista:
        if f"_S_{setor}" not in pos_nos: continue
        sx, sy = pos_nos[f"_S_{setor}"]
        cor = SETOR_CORES.get(setor, C["gray"])
        fig_teia.add_trace(go.Scatter(
            x=[sx], y=[sy], mode="markers+text",
            marker=dict(size=30, color=cor, line=dict(width=2, color=C["bg"])),
            text=[setor], textposition="top center",
            textfont=dict(color=C["white"], size=9, family="Helvetica"),
            name=setor, showlegend=True,
            hovertemplate=f"<b>{setor}</b><br>{len(setores_dict[setor])} empresa(s)<extra></extra>",
        ))

    # Nós de empresa
    fonte_cor = {"Cobertura Shipyard": C["blue_lt"], "Endurance": C["sky"], "Ambos": C["pos"]}
    for tk, info in todas_empresas.items():
        if tk not in pos_nos: continue
        ex, ey = pos_nos[tk]
        ev_v = max(info["ev"], 1)
        sz = min(max(int(ev_v ** 0.4 * 4), 12), 36)
        cor = fonte_cor.get(info["fonte"], C["gray"])
        fig_teia.add_trace(go.Scatter(
            x=[ex], y=[ey], mode="markers+text",
            marker=dict(size=sz, color=cor, opacity=0.85,
                        line=dict(width=1.5, color=C["bg"])),
            text=[tk.replace(".SA","")],
            textposition="bottom center",
            textfont=dict(color=C["white"], size=8),
            showlegend=False,
            hovertemplate=f"<b>{tk}</b><br>EV: R${ev_v:.1f}bi<br>Fonte: {info['fonte']}<extra></extra>",
        ))

    fig_teia.update_layout(
        paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
        font=dict(family="Helvetica,Arial", color=C["white"]),
        xaxis=dict(visible=False, range=[-6.5, 6.5]),
        yaxis=dict(visible=False, range=[-6.5, 6.5]),
        legend=dict(bgcolor=C["bg2"], bordercolor=C["border"],
                    font=dict(color=C["white"], size=9),
                    orientation="v", x=1.0, y=1.0),
        margin=dict(l=10, r=140, t=40, b=10), height=620,
        title=dict(text="Teia Setorial — Cobertura Shipyard + Carteira Endurance",
                   font=dict(color=C["white"]))
    )
    st.plotly_chart(fig_teia, use_container_width=True)

    # Tabela resumo por setor
    st.markdown("## Resumo por Setor")
    rows_set = []
    for setor in setores_lista:
        emps = setores_dict[setor]
        tks  = ", ".join(e["ticker"].replace(".SA","") for e in emps)
        ev_t = sum(e["ev"] for e in emps)
        rows_set.append({
            "Setor": setor,
            "Empresas": tks,
            "EV Total (R$bi)": f"{ev_t:.1f}",
            "Qtd": len(emps),
        })
    df_set_macro = pd.DataFrame(rows_set)
    st.markdown(dark_table(df_set_macro), unsafe_allow_html=True)
    export_buttons(df_set_macro, "setores_macro")

# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════
# PÁG ADMIN — GERENCIAR USUÁRIOS (somente master)
# ══════════════════════════════════════════════════════════════════
elif pagina == "── Admin ──":
    st.info("Selecione uma opção do menu.")

elif pagina == "Gerenciar Usuários":
    if username != "Leonardo.Losi":
        st.error("Acesso restrito ao usuário master.")
        st.stop()

    st.markdown("## Gerenciar Usuários — Painel Master")
    st.caption("Apenas o usuário master (Leonardo.Losi) tem acesso a esta página.")

    AUTH_PATH = Path("dashboard_auth.yaml")

    def _load_cfg():
        with open(AUTH_PATH) as f:
            return yaml.load(f, Loader=SafeLoader)

    def _save_cfg(cfg_data):
        with open(AUTH_PATH, "w") as f:
            yaml.dump(cfg_data, f, allow_unicode=True, default_flow_style=False)

    cfg_data = _load_cfg()
    users_dict = cfg_data.get("credentials", {}).get("usernames", {})

    # ── Tabela de usuários existentes ───────────────────────────
    st.markdown("### Usuários cadastrados")
    if users_dict:
        rows_u = []
        for uname, udata in users_dict.items():
            rows_u.append({
                "Login":  uname,
                "Nome":   udata.get("name", "—"),
                "E-mail": udata.get("email", "—"),
                "Master": "" if uname == "Leonardo.Losi" else "—",
            })
        st.markdown(dark_table(pd.DataFrame(rows_u)), unsafe_allow_html=True)
    else:
        st.info("Nenhum usuário cadastrado.")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Abas: Criar / Alterar senha / Remover ───────────────────
    tab_criar, tab_senha, tab_remover = st.tabs(["Criar usuário", "Alterar senha", "Remover usuário"])

    with tab_criar:
        st.markdown("#### Novo usuário")
        nc1, nc2 = st.columns(2)
        with nc1:
            new_login  = st.text_input("Login (sem espaços)", key="nu_login",
                                        placeholder="ex: joao.silva")
            new_nome   = st.text_input("Nome completo", key="nu_nome",
                                        placeholder="ex: João Silva")
        with nc2:
            new_email  = st.text_input("E-mail", key="nu_email",
                                        placeholder="ex: joao@velacapital.com.br")
            new_senha  = st.text_input("Senha inicial", key="nu_senha",
                                        type="password", placeholder="mínimo 6 caracteres")
            new_senha2 = st.text_input("Confirmar senha", key="nu_senha2",
                                        type="password")

        if st.button("Criar usuário", key="btn_criar_user"):
            erros = []
            if not new_login:  erros.append("Login obrigatório.")
            if " " in (new_login or ""):  erros.append("Login não pode ter espaços.")
            if new_login in users_dict:  erros.append(f"Login '{new_login}' já existe.")
            if not new_nome:   erros.append("Nome obrigatório.")
            if not new_email:  erros.append("E-mail obrigatório.")
            if len(new_senha or "") < 6:  erros.append("Senha mínimo 6 caracteres.")
            if new_senha != new_senha2:   erros.append("Senhas não coincidem.")

            if erros:
                for e in erros: st.error(e)
            else:
                hashed = stauth.Hasher([new_senha]).generate()[0]
                cfg_data["credentials"]["usernames"][new_login] = {
                    "name":     new_nome,
                    "email":    new_email,
                    "password": hashed,
                }
                _save_cfg(cfg_data)
                st.success(f" Usuário '{new_login}' criado com sucesso!")
                st.rerun()

    with tab_senha:
        st.markdown("#### Alterar senha de um usuário")
        logins_edit = [u for u in users_dict.keys()]
        sel_user = st.selectbox("Usuário", logins_edit, key="sel_user_senha")
        ps1, ps2 = st.columns(2)
        with ps1:
            nova_senha  = st.text_input("Nova senha", key="ns1", type="password")
        with ps2:
            nova_senha2 = st.text_input("Confirmar nova senha", key="ns2", type="password")

        if st.button("Alterar senha", key="btn_alt_senha"):
            if len(nova_senha or "") < 6:
                st.error("Senha mínimo 6 caracteres.")
            elif nova_senha != nova_senha2:
                st.error("Senhas não coincidem.")
            else:
                hashed = stauth.Hasher([nova_senha]).generate()[0]
                cfg_data["credentials"]["usernames"][sel_user]["password"] = hashed
                _save_cfg(cfg_data)
                st.success(f" Senha de '{sel_user}' alterada com sucesso!")

    with tab_remover:
        st.markdown("#### Remover usuário")
        st.warning(" Esta ação é irreversível. O usuário master não pode ser removido.")
        logins_del = [u for u in users_dict.keys() if u != "Leonardo.Losi"]
        if logins_del:
            del_user = st.selectbox("Usuário a remover", logins_del, key="sel_del_user")
            confirmar = st.text_input(f"Digite **{del_user}** para confirmar a remoção",
                                       key="del_confirm")
            if st.button("Remover usuário", key="btn_del_user"):
                if confirmar != del_user:
                    st.error("Confirmação incorreta. Digite exatamente o login do usuário.")
                else:
                    del cfg_data["credentials"]["usernames"][del_user]
                    _save_cfg(cfg_data)
                    st.success(f" Usuário '{del_user}' removido.")
                    st.rerun()
        else:
            st.info("Não há outros usuários para remover.")


# ══════════════════════════════════════════════════════════════════
# PÁG — GESTORAS (Posições em Carteira via CVM / Yahoo)
# ══════════════════════════════════════════════════════════════════
elif pagina == "Gestoras":
    st.markdown("##  Gestoras com Posição Relevante (≥5%)")
    st.caption("Fonte: CVM Dados Abertos — Composição Acionária (FRE) e Yahoo Finance institutional holders")

    emp_g = st.selectbox("Empresa", empresas,
        format_func=lambda e: f"{results[e].get('ticker','').replace('.SA','')} — {e}",
        key="gest_emp")
    r_g  = results[emp_g]
    tk_g = r_g.get("ticker","")
    cvm_g= str(r_g.get("cvm_code","") or "")

    tab_cvm_g, tab_yf_g, tab_map_g = st.tabs([" CVM — Composição Acionária"," Yahoo Finance","🗺️ Mapa de Acionistas"])

    # ── CVM Dados Abertos ─────────────────────────────────────────
    with tab_cvm_g:
        @st.cache_data(ttl=86400)
        def _get_cvm_acionistas(cvm_code):
            try:
                import requests, zipfile, io
                results_rows = []
                for ano in [2024, 2023, 2022]:
                    url = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FRE/DADOS/fre_cia_aberta_composicao_capital_{ano}.zip"
                    try:
                        r = requests.get(url, timeout=20)
                        if r.status_code != 200: continue
                        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                            fname = [f for f in z.namelist() if f.endswith(".csv")][0]
                            import csv, io as _io
                            txt = z.read(fname).decode("latin1")
                            reader = csv.DictReader(_io.StringIO(txt), delimiter=";")
                            for row in reader:
                                if str(row.get("CD_CVM","")).zfill(6) == cvm_code.zfill(6):
                                    pct = float((row.get("PCT_PART_ACOES_CAPITAL","0") or "0").replace(",","."))
                                    if pct >= 5.0:
                                        results_rows.append({
                                            "Acionista": row.get("NOME_ACIONISTA","—"),
                                            "Tipo":      row.get("TP_ACIONISTA","—"),
                                            "Ações ON":  row.get("QT_ACOES_ORDINARIAS","—"),
                                            "Ações PN":  row.get("QT_ACOES_PREFERENCIAIS","—"),
                                            "% Capital": f"{pct:.2f}%",
                                            "Ano":       str(ano),
                                        })
                    except: continue
                return results_rows
            except Exception as e:
                return []

        if not cvm_g:
            st.warning("Código CVM não disponível para esta empresa.")
        else:
            with st.spinner("Consultando CVM Dados Abertos..."):
                acionistas = _get_cvm_acionistas(cvm_g)

            if acionistas:
                df_ac = pd.DataFrame(acionistas)
                st.markdown(f"**{len(df_ac)} acionistas com participação ≥ 5%**")
                def _ac_color(v):
                    if "%" in str(v):
                        try:
                            vv = float(str(v).replace("%",""))
                            if vv >= 25: return f"color:{C['blue_lt']};font-weight:bold"
                            if vv >= 10: return f"color:{C['sky']}"
                            return f"color:{C['white']}"
                        except: pass
                    return f"color:{C['white']}"
                st.markdown(dark_table(df_ac, _ac_color), unsafe_allow_html=True)

                # Gráfico pizza
                df_pie_ac = df_ac.copy()
                df_pie_ac["pct_num"] = df_pie_ac["% Capital"].str.replace("%","").astype(float)
                outros = max(0, 100 - df_pie_ac["pct_num"].sum())
                if outros > 0:
                    df_pie_ac = pd.concat([df_pie_ac, pd.DataFrame([{"Acionista":"Free Float","pct_num":outros,"% Capital":f"{outros:.1f}%","Ano":"—","Tipo":"—","Ações ON":"—","Ações PN":"—"}])])
                fig_ac = go.Figure(go.Pie(
                    labels=df_pie_ac["Acionista"], values=df_pie_ac["pct_num"],
                    hole=0.45,
                    marker_colors=[C["blue_lt"],C["sky"],C["teal"],C["pos"],C["gray"],C["navy"],"#FFB347"],
                    textfont=dict(color=C["white"],size=10), textinfo="label+percent"))
                fig_ac.update_layout(paper_bgcolor=C["bg"],
                    font=dict(color=C["white"],family="Helvetica,Arial"),
                    legend=dict(bgcolor=C["bg"],bordercolor=C["border"]),
                    margin=dict(l=10,r=10,t=30,b=10), height=320)
                st.plotly_chart(fig_ac, use_container_width=True)
                export_buttons(df_ac, "acionistas_cvm")
            else:
                st.info("Nenhum acionista com ≥5% encontrado no FRE da CVM para esta empresa. Pode ser que o FRE mais recente ainda não tenha sido publicado.")
                st.markdown(f" [Consultar no CVM Dados Abertos](https://dados.cvm.gov.br/dataset/cia_aberta-doc-fre)")

    # ── Yahoo Finance ─────────────────────────────────────────────
    with tab_yf_g:
        @st.cache_data(ttl=3600)
        def _get_yf_holders(tk):
            try:
                import yfinance as yf
                t = yf.Ticker(tk)
                return t.institutional_holders, t.major_holders, t.mutualfund_holders
            except: return None, None, None

        with st.spinner("Buscando via Yahoo Finance..."):
            df_inst, df_major, df_mf = _get_yf_holders(tk_g)

        st.caption(" Yahoo Finance tem cobertura limitada para ações brasileiras. Para dados completos, use a aba CVM.")
        if df_major is not None and not df_major.empty:
            st.markdown("**Resumo de Participações**")
            st.dataframe(df_major, use_container_width=True, hide_index=True)

        if df_inst is not None and not df_inst.empty:
            shares_out = float(r_g.get("shares_out",1) or 1)
            df_i = df_inst.copy()
            if "% Out" in df_i.columns:
                df_i["% Capital"] = df_i["% Out"].apply(lambda x: f"{float(x or 0)*100:.2f}%")
                df_i = df_i[df_i["% Out"].apply(lambda x: float(x or 0)*100 >= 5)]
            if "Shares" in df_i.columns:
                df_i["Ações (M)"] = df_i["Shares"].apply(lambda x: f"{int(x)/1e6:.1f}M" if x else "—")
            if "Value" in df_i.columns:
                df_i["Valor"] = df_i["Value"].apply(lambda x: f"US${int(x)/1e6:.1f}M" if x else "—")
            rename = {"Holder":"Gestora","Date Reported":"Data"}
            df_i = df_i.rename(columns={k:v for k,v in rename.items() if k in df_i.columns})
            if not df_i.empty:
                st.markdown("**Institucionais ≥ 5%**")
                st.markdown(dark_table(df_i.head(20)), unsafe_allow_html=True)

                if "Shares" in df_inst.columns:
                    top = df_inst.nlargest(10,"Shares")
                    fig_yf = go.Figure(go.Bar(
                        x=top["Shares"]/1e6, y=top["Holder"], orientation="h",
                        marker_color=C["blue_lt"],
                        text=[f"{v/1e6:.1f}M" for v in top["Shares"]],
                        textposition="outside", textfont=dict(color=C["white"],size=10)))
                    fig_yf.update_layout(**{**PL,"yaxis":dict(autorange="reversed",tickfont=dict(color=C["white"]))},
                        title="Top 10 Institucionais", xaxis_title="Milhões de ações", height=350)
                    st.plotly_chart(fig_yf, use_container_width=True)
            else:
                st.info("Nenhum institucional com ≥5% encontrado via Yahoo Finance.")
        else:
            st.info("Dados institucionais não disponíveis via Yahoo Finance para este ticker.")

    # ── Mapa de Acionistas ────────────────────────────────────────
    with tab_map_g:
        st.markdown("### 🗺️ Estrutura de Controle")
        if not cvm_g:
            st.warning("Código CVM necessário.")
        else:
            with st.spinner("Carregando..."):
                acs = _get_cvm_acionistas(cvm_g)
            if acs:
                import math as _math
                nos_m = [{"id":"EMPRESA","label":tk_g.replace(".SA",""),"tipo":"listada"}]
                arestas_m = []
                for i,ac in enumerate(acs[:8]):
                    nid = f"AC_{i}"
                    pct_v = float(ac["% Capital"].replace("%",""))
                    tipo_m = "controladora" if pct_v >= 50 else ("relevante" if pct_v >= 20 else "minoritario")
                    nos_m.append({"id":nid,"label":f"{ac['Acionista'][:20]}\n{ac['% Capital']}","tipo":tipo_m})
                    arestas_m.append((nid,"EMPRESA"))
                ff = max(0,100-sum(float(a["% Capital"].replace("%","")) for a in acs))
                if ff > 0:
                    nos_m.append({"id":"FF","label":f"Free Float\n{ff:.1f}%","tipo":"mercado"})
                    arestas_m.append(("FF","EMPRESA"))
                cores_m = {"listada":C["pos"],"controladora":C["blue_lt"],"relevante":C["sky"],"minoritario":C["teal"],"mercado":C["gray"]}
                pos_m = {"EMPRESA":(0,0)}
                outros_m = [n for n in nos_m if n["id"]!="EMPRESA"]
                for i,n in enumerate(outros_m):
                    ang = 2*_math.pi*i/len(outros_m)
                    pos_m[n["id"]] = (2.0*_math.cos(ang), 2.0*_math.sin(ang))
                ex,ey=[],[]
                for a,b in arestas_m:
                    if a in pos_m and b in pos_m:
                        ex+=[pos_m[a][0],pos_m[b][0],None]
                        ey+=[pos_m[a][1],pos_m[b][1],None]
                fig_map = go.Figure()
                fig_map.add_trace(go.Scatter(x=ex,y=ey,mode="lines",
                    line=dict(color=C["border"],width=1.5),hoverinfo="none",showlegend=False))
                for n in nos_m:
                    x,y=pos_m.get(n["id"],(0,0))
                    fig_map.add_trace(go.Scatter(x=[x],y=[y],mode="markers+text",
                        marker=dict(size=40 if n["tipo"]=="listada" else 30,
                            color=cores_m.get(n["tipo"],C["gray"]),
                            line=dict(width=2,color=C["bg"])),
                        text=[n["label"]],textposition="bottom center",
                        textfont=dict(color=C["white"],size=9),
                        showlegend=False,hovertext=n["label"],hoverinfo="text"))
                fig_map.update_layout(**{**PL,"margin":dict(l=20,r=20,t=40,b=20)},
                    title="Mapa de Controle Acionário",height=480,
                    xaxis=dict(showgrid=False,zeroline=False,showticklabels=False),
                    yaxis=dict(showgrid=False,zeroline=False,showticklabels=False))
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.info("Carregue dados na aba CVM primeiro.")


elif pagina == "ComDinheiro":
    st.markdown("## ComDinheiro — Dados Fundamentalistas")

    @st.cache_resource
    def _load_cd_client():
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "comdinheiro_client", Path(__file__).parent / "comdinheiro_client.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    try:
        cd = _load_cd_client()
        @st.cache_data(ttl=600)
        def _cd_test(): return cd.test_connection()
        conn = _cd_test()
        _c_s = C["pos"] if conn["ok"] else C["neg"]
        st.markdown(
            f'<div style="background:{_c_s}22;border-left:4px solid {_c_s};padding:8px 16px;'
            f'border-radius:4px;color:{C["white"]};font-size:13px">'
            f'{"ComDinheiro conectado" if conn["ok"] else "Problema: " + conn["msg"]}</div>',
            unsafe_allow_html=True
        )
        st.markdown("")
    except Exception as e:
        st.error(f"Erro ao carregar comdinheiro_client.py: {e}")
        st.stop()

    emp_cd = st.selectbox(
        "Empresa", empresas,
        format_func=lambda e: f"{results[e].get('ticker',e).replace('.SA','')} — {e}",
        key="cd_emp"
    )
    papel       = results[emp_cd].get("ticker", emp_cd).replace(".SA", "")
    ticker_full = results[emp_cd].get("ticker", emp_cd)
    p_tela      = float(results[emp_cd].get("price_now") or 0)

    tab_kpi, tab_dre, tab_cons, tab_prov = st.tabs([
        "KPIs Fundamentalistas", "DRE / Balanço", "Consenso Analistas", "Proventos"
    ])

    # ═══════════════════════════════════════════════════════════════════
    # TAB 1 — KPIs (espelho completo da página Fundamentalista ComDinheiro)
    # ═══════════════════════════════════════════════════════════════════
    with tab_kpi:
        @st.cache_data(ttl=1800)
        def _cd_kpi(p, tk): return cd.get_fundamentalista(p, tk)
        with st.spinner("Carregando indicadores..."):
            kpi = _cd_kpi(papel, ticker_full)

        # ── Helpers de formatação ───────────────────────────────
        def _fm(v, d=2):
            """R$ mil → string legível (bi/mi/mil)"""
            if v is None: return "—"
            try:
                fv = float(v) * 1_000   # base R$ mil → R$
                neg = fv < 0; fv = abs(fv)
                s = f"-" if neg else ""
                if fv >= 1e12: return f"{s}R${fv/1e12:.{d}f} tri"
                if fv >= 1e9:  return f"{s}R${fv/1e9:.{d}f} bi"
                if fv >= 1e6:  return f"{s}R${fv/1e6:.{d}f} mi"
                if fv >= 1e3:  return f"{s}R${fv/1e3:.{d}f} mil"
                return f"{s}R${fv:.{d}f}"
            except: return "—"

        def _pct(v, d=2):
            if v is None: return "—"
            try: return f"{float(v):.{d}f}%"
            except: return "—"

        def _num(v, d=2, suffix="x"):
            if v is None: return "—"
            try: return f"{float(v):.{d}f}{suffix}"
            except: return "—"



        def _section(title, color=None):
            _c = color or C["blue_lt"]
            st.markdown(
                f'<div style="background:{C["bg2"]};border-left:3px solid {_c};'
                f'padding:6px 14px;margin:18px 0 8px;border-radius:2px;'
                f'color:{_c};font-size:11px;font-weight:700;letter-spacing:1px">'
                f'{title}</div>', unsafe_allow_html=True
            )

        # ── CABEÇALHO ───────────────────────────────────────────
        nome = kpi.get("nome_empresa", papel)
        setor = kpi.get("setor","—"); ind = kpi.get("industria","—")
        h1, h2, h3 = st.columns([3,2,2])
        h1.markdown(f"### {nome}")
        _gray = C["gray"]
        h2.markdown(f"<span style='color:{_gray};font-size:12px'>{setor}</span>",
                    unsafe_allow_html=True)
        h3.markdown(f"<span style='color:{_gray};font-size:12px'>{ind}</span>",
                    unsafe_allow_html=True)

        # ── 1. VISÃO MACRO BP e DRE ─────────────────────────────
        _section("VISÃO MACRO — BP E DRE")
        r1 = st.columns(5)
        r1[0].metric("Ativo Total",        _fm(kpi.get("AT")))
        r1[1].metric("Disponibilidades",   _fm(kpi.get("DISP")))
        r1[2].metric("Patrimônio Líquido", _fm(kpi.get("PL")))
        r1[3].metric("Receita Líquida",    _fm(kpi.get("RL")))
        r1[4].metric("Custo",              _fm(kpi.get("CUSTO")))

        r2 = st.columns(5)
        r2[0].metric("Lucro Bruto",        _fm(kpi.get("LB")))
        r2[1].metric("EBITDA",             _fm(kpi.get("EBITDA")))
        r2[2].metric("Depr. e Amor.",      _fm(kpi.get("DA")))
        r2[3].metric("EBIT (L.Oper.)",     _fm(kpi.get("EBIT")))
        r2[4].metric("Lucro Líquido",      _fm(kpi.get("LL")))

        # ── 2. RENTABILIDADE ────────────────────────────────────
        _section("RENTABILIDADE")
        r3 = st.columns(5)
        r3[0].metric("ROE (%)",            _pct(kpi.get("ROE")))
        r3[1].metric("ROIC (%)",           _pct(kpi.get("ROIC")))
        r3[2].metric("Margem Líq. (%)",    _pct(kpi.get("ML")))
        r3[3].metric("Margem EBITDA (%)",  _pct(kpi.get("MEBITDA")))
        r3[4].metric("Margem Oper. (%)",   _pct(kpi.get("MO")))

        r4 = st.columns(5)
        r4[0].metric("Margem Bruta (%)",   _pct(kpi.get("MB")))
        r4[1].metric("LPA (R$)",           _brl(kpi.get("LPA")))
        r4[2].metric("VPA (R$)",           _brl(kpi.get("VPA")))
        r4[3].metric("FCO (R$)",           _fm(kpi.get("FCO")))
        r4[4].metric("FCO/EBITDA (%)",     _pct(kpi.get("FCO_EBITDA"), d=1))

        # ── 3. MÚLTIPLOS DE MERCADO ─────────────────────────────
        _section("MÚLTIPLOS DE MERCADO")
        r5 = st.columns(5)
        _pl_d = f"{(kpi.get('PL_mult') - kpi.get('trailing_pe',0)):.1f}x vs trailing" if kpi.get("PL_mult") and kpi.get("trailing_pe") else None
        r5[0].metric("P/L",                _num(kpi.get("PL_mult")))
        r5[1].metric("P/VPA",              _num(kpi.get("PVP")))
        r5[2].metric("EV/EBITDA",          _num(kpi.get("EV_EBITDA")))
        r5[3].metric("P/S (P/Receita)",    _num(kpi.get("ps_ratio")))
        r5[4].metric("PEG Ratio",          _num(kpi.get("peg")))

        r6 = st.columns(5)
        r6[0].metric("Div. Yield (%)",     _pct(kpi.get("DY")))
        r6[1].metric("Preço Tela",         _brl(p_tela))
        r6[2].metric("52w Máx",            _brl(kpi.get("52w_high")))
        r6[3].metric("52w Mín",            _brl(kpi.get("52w_low")))
        _up = ((kpi.get("52w_high",0) or 0) - p_tela) / p_tela * 100 if p_tela and kpi.get("52w_high") else None
        r6[4].metric("Dist. 52w Máx",      _pct(_up) if _up else "—")

        # ── 4. ESTRUTURA DE CAPITAL E ENDIVIDAMENTO ─────────────
        _section("ESTRUTURA DE CAPITAL E ENDIVIDAMENTO")
        r7 = st.columns(5)
        r7[0].metric("Dívida Bruta",       _fm(kpi.get("DB")))
        r7[1].metric("Dívida Líquida",     _fm(kpi.get("DL")))
        r7[2].metric("Dív.Líq/EBITDA",     _num(kpi.get("DL_EBITDA")))
        r7[3].metric("Cob. Juros",         _num(kpi.get("ICJ")))
        r7[4].metric("Alavancagem AT/PL",  _num(kpi.get("ALAV")))

        r8 = st.columns(5)
        r8[0].metric("CT/AT (%)",          _pct(kpi.get("CT_AT")))
        r8[1].metric("Rec. Financeira",    _fm(kpi.get("RF")))
        r8[2].metric("Desp. Financeira",   _fm(kpi.get("DF")))
        r8[3].metric("Ativo Circulante",   _fm(kpi.get("AC")))
        r8[4].metric("Passivo Circulante", _fm(kpi.get("PC")))

        # ── 5. LIQUIDEZ ─────────────────────────────────────────
        _section("LIQUIDEZ")
        r9 = st.columns(5)
        r9[0].metric("Liq. Corrente",      _num(kpi.get("liq_corrente")))
        r9[1].metric("Liq. Seca",          _num(kpi.get("liq_seca")))
        r9[2].metric("Cap. Circ. Líq.",    _fm(kpi.get("CCL")))
        r9[3].metric("Estoques",           _fm(kpi.get("EST")))
        r9[4].metric("Imobilizado",        _fm(kpi.get("IMOB")))

        # ── 6. RISCO E MERCADO ──────────────────────────────────
        _section("RISCO E MERCADO")
        r10 = st.columns(5)
        r10[0].metric("Beta",              _num(kpi.get("beta")))
        r10[1].metric("Market Cap",
                      _fm(kpi.get("MKTCAP")/1_000_000) if kpi.get("MKTCAP") else "—")
        r10[2].metric("Preço-Alvo",
                      f"R$ {kpi['preco_alvo']:.2f}" if kpi.get("preco_alvo") else "—",
                      delta=f"{(kpi['preco_alvo']-p_tela)/p_tela*100:+.1f}%"
                            if kpi.get("preco_alvo") and p_tela else None)
        r10[3].metric("Recomendação",      kpi.get("recomendacao","—"))
        r10[4].metric("Nº Analistas",      str(kpi.get("n_analistas","—")))

        r11 = st.columns(5)
        r11[0].metric("Vol. Médio 3m",
                      f"{kpi['vol_medio']/1e6:.1f} mi" if kpi.get("vol_medio") else "—")
        r11[1].metric("Alvo Mín",          _brl(kpi.get("preco_min")))
        r11[2].metric("Alvo Máx",          _brl(kpi.get("preco_max")))
        r11[3].metric("Forward P/L",       _num(kpi.get("forward_pe")))
        r11[4].metric("Trailing P/L",      _num(kpi.get("trailing_pe")))

        # ── 7. FLUXO DE CAIXA ───────────────────────────────────
        _section("FLUXO DE CAIXA")
        r12 = st.columns(5)
        r12[0].metric("FCO (Operações)",   _fm(kpi.get("FCO")))
        r12[1].metric("FCI (Investim.)",   _fm(kpi.get("FCI")))
        r12[2].metric("FCF (Financiam.)",  _fm(kpi.get("FCF")))
        r12[3].metric("FCO/EBITDA (%)",    _pct(kpi.get("FCO_EBITDA")))
        _fcl = (kpi.get("FCO") or 0) + (kpi.get("FCI") or 0)
        r12[4].metric("FCL (FCO+FCI)",     _fm(_fcl) if _fcl else "—")

        # ── 8. FONTE E DATA ─────────────────────────────────────
        st.markdown("")
        fa, fb, fc = st.columns(3)
        fa.caption(f"Data demonstração: {kpi.get('data_dem','—')}")
        fb.caption(f"Convenção: {kpi.get('convencao','—')} · {kpi.get('tipo','—')}")
        fc.caption("Fonte: ComDinheiro + Yahoo Finance · Cache 30min")

        # ── 9. GRÁFICOS: SÉRIES HISTÓRICAS + RADAR ──────────────
        _section("HISTÓRICO — RECEITA, EBIT E LUCRO LÍQUIDO")
        serie_rl   = kpi.get("serie_rl",{})
        serie_ll   = kpi.get("serie_ll",{})
        serie_ebit = kpi.get("serie_ebit",{})

        if serie_rl:
            _datas = list(serie_rl.keys())
            fig_h = go.Figure()
            for _lbl, _serie, _cor in [
                ("Receita Líquida", serie_rl, C["sky"]),
                ("EBIT", serie_ebit, C["blue_lt"]),
                ("Lucro Líquido", serie_ll, C["pos"]),
            ]:
                _vals = [_serie.get(d) for d in _datas]
                fig_h.add_trace(go.Bar(
                    name=_lbl, x=_datas, y=_vals, marker_color=_cor,
                    text=[f"R${v/1e3:.1f}bi" if v else "" for v in _vals],
                    textposition="outside", textfont=dict(color=C["white"], size=9)
                ))
            fig_h.update_layout(**{**PL, "margin": dict(l=40,r=40,t=40,b=80)},
                title=f"Evolução Financeira — {papel} (R$ mil base)",
                barmode="group", height=400)
            fig_h.update_xaxes(tickangle=-45)
            st.plotly_chart(fig_h, use_container_width=True)

        _section("RADAR — QUALIDADE FUNDAMENTALISTA")
        _cats = ["ROE","ROIC","Mg EBITDA","Mg Líq.","DY","Cob. Juros"]
        def _norm(v, vmin, vmax):
            try: return max(0, min(10, (float(str(v or 0).replace(",",".")) - vmin) / (vmax - vmin) * 10))
            except: return 0
        _vals = [
            _norm(kpi.get("ROE"),     0, 50),
            _norm(kpi.get("ROIC"),    0, 40),
            _norm(kpi.get("MEBITDA"), 0, 50),
            _norm(kpi.get("ML"),      0, 40),
            _norm(kpi.get("DY"),      0,  8),
            _norm(kpi.get("ICJ"),     0, 15),
        ]
        fig_r = go.Figure(go.Scatterpolar(
            r=_vals+[_vals[0]], theta=_cats+[_cats[0]],
            fill="toself", fillcolor="rgba(35,81,254,.2)",
            line=dict(color=C["blue_lt"], width=2), name=papel,
        ))
        fig_r.update_layout(
            paper_bgcolor=C["bg"],
            font=dict(family="Helvetica,Arial", color=C["white"]),
            polar=dict(
                bgcolor=C["bg2"],
                radialaxis=dict(visible=True, range=[0,10], color=C["gray"],
                                gridcolor=C["border"], tickfont=dict(size=9)),
                angularaxis=dict(color=C["gray"], gridcolor=C["border"],
                                 tickfont=dict(size=11)),
            ),
            showlegend=False, margin=dict(l=70,r=70,t=30,b=30), height=380,
        )
        st.plotly_chart(fig_r, use_container_width=True)

        if kpi.get("erro_balanco"): st.warning(f"Aviso balanço: {kpi['erro_balanco']}")
        if kpi.get("erro_yf"):      st.caption(f"Aviso yfinance: {kpi['erro_yf']}")

    # ═══════════════════════════════════════════════════════════════════
    # TAB 2 — DRE / BALANÇO
    # ═══════════════════════════════════════════════════════════════════
    with tab_dre:
        st.markdown(f"### Demonstrações Financeiras — {papel}")
        anos_dre = st.slider("Período (anos)", 1, 10, 5, key="cd_anos_dre")

        @st.cache_data(ttl=3600)
        def _cd_dre(p, a): return cd.get_dre(p, a)

        with st.spinner("Carregando DRE via ComDinheiro..."):
            df_dre = _cd_dre(papel, anos_dre)

        if "Erro" in df_dre.columns:
            st.warning(f"Erro: {df_dre['Erro'].iloc[0]}")
        elif df_dre.empty:
            st.info("Sem dados disponíveis.")
        else:
            _col0 = df_dre.columns[0]
            _skip = ["Tipo", "Convenção", "Meses"]
            df_show = df_dre[~df_dre[_col0].isin(_skip)].reset_index(drop=True)
            st.markdown(dark_table(df_show), unsafe_allow_html=True)
            export_buttons(df_show, f"dre_{papel}")

            _row_map = {"Receita Líquida": C["sky"],
                        "Lucro Operacional (EBIT)": C["blue_lt"],
                        "Lucro Líquido": C["pos"]}
            _datas = [c for c in df_dre.columns[1:] if c and str(c).strip()]
            fig_dre = go.Figure()
            for _ind, _cor in _row_map.items():
                _row = df_dre[df_dre[_col0] == _ind]
                if not _row.empty:
                    _vals = [pd.to_numeric(str(_row.iloc[0].get(d,"") or "").replace(",","."),
                                           errors="coerce") for d in _datas]
                    fig_dre.add_trace(go.Bar(
                        name=_ind, x=_datas, y=_vals, marker_color=_cor,
                        text=[f"R${v/1e3:.1f}bi" if pd.notna(v) and v else "" for v in _vals],
                        textposition="outside", textfont=dict(color=C["white"], size=10)
                    ))
            fig_dre.update_layout(**{**PL, "margin": dict(l=40,r=40,t=50,b=80)},
                title=f"Receita, EBIT e Lucro — {papel} (R$ mil)",
                barmode="group", height=420)
            fig_dre.update_xaxes(tickangle=-45)
            st.plotly_chart(fig_dre, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════
    # TAB 3 — CONSENSO
    # ═══════════════════════════════════════════════════════════════════
    with tab_cons:
        st.markdown(f"### Consenso de Analistas — {papel}")

        @st.cache_data(ttl=3600)
        def _cd_consenso(tk): return cd.get_consenso(tk)
        with st.spinner("Carregando..."):
            cons = _cd_consenso(ticker_full)

        if not cons or "erro" in cons:
            st.warning("Consenso não disponível.")
        else:
            p_alvo = cons.get("preco_alvo") or 0
            p_min  = cons.get("preco_min")  or 0
            p_max  = cons.get("preco_max")  or 0
            cc1,cc2,cc3,cc4 = st.columns(4)
            cc1.metric("Preço Tela",   f"R$ {p_tela:.2f}")
            cc2.metric("Preço-Alvo",   f"R$ {p_alvo:.2f}" if p_alvo else "—",
                       delta=f"{(p_alvo-p_tela)/p_tela*100:+.1f}%" if p_alvo and p_tela else None)
            cc3.metric("Mín / Máx",    f"R${p_min:.0f} / R${p_max:.0f}" if p_min else "—")
            cc4.metric("Recomendação", cons.get("recomendacao","—"))
            st.caption(f"{cons.get('n_analistas',0)} analistas · Fonte: Yahoo Finance")
            if p_alvo and p_tela:
                _rlo = min(p_min or p_tela, p_tela) * 0.85
                _rhi = max(p_max or p_tela, p_tela) * 1.15
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number+delta", value=p_alvo,
                    delta={"reference": p_tela, "valueformat": ".2f",
                           "increasing": {"color": C["pos"]}, "decreasing": {"color": C["neg"]}},
                    number={"prefix": "R$ ","valueformat": ".2f","font": {"color": C["white"]}},
                    gauge={"axis": {"range": [_rlo, _rhi], "tickcolor": C["gray"]},
                           "bar": {"color": C["blue_lt"]}, "bgcolor": C["bg2"],
                           "bordercolor": C["border"],
                           "steps": [{"range": [_rlo, p_tela], "color": "rgba(224,85,85,.12)"},
                                     {"range": [p_tela, _rhi], "color": "rgba(46,204,113,.08)"}],
                           "threshold": {"line": {"color": C["sky"],"width": 3},
                                         "thickness": 0.85, "value": p_tela}},
                    title={"text": f"Preço-Alvo vs Tela — {papel}", "font": {"color": C["gray"]}},
                ))
                fig_g.update_layout(paper_bgcolor=C["bg"],
                    font=dict(family="Helvetica,Arial",color=C["white"]),
                    margin=dict(l=30,r=30,t=60,b=20), height=300)
                st.plotly_chart(fig_g, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════
    # TAB 4 — PROVENTOS
    # ═══════════════════════════════════════════════════════════════════
    with tab_prov:
        st.markdown(f"### Histórico de Proventos — {papel}")
        anos_prov = st.slider("Período (anos)", 1, 10, 5, key="cd_anos_prov")

        @st.cache_data(ttl=3600)
        def _cd_proventos(tk, a): return cd.get_proventos(tk, a)
        with st.spinner("Carregando proventos..."):
            df_prov = _cd_proventos(ticker_full, anos_prov)

        if df_prov.empty or "Erro" in df_prov.columns or "Aviso" in df_prov.columns:
            st.info("Sem proventos no período.")
        else:
            _vc = "Valor (R$)"
            pm1,pm2,pm3 = st.columns(3)
            pm1.metric("Total no período", f"R$ {df_prov[_vc].sum():.4f}/ação")
            pm2.metric("Média por evento", f"R$ {df_prov[_vc].mean():.4f}/ação")
            pm3.metric("Nº de eventos",    str(len(df_prov)))
            st.markdown(dark_table(df_prov), unsafe_allow_html=True)
            export_buttons(df_prov, f"proventos_{papel}")
            fig_prov = go.Figure(go.Bar(
                x=df_prov["Data"], y=df_prov[_vc], marker_color=C["blue_lt"],
                text=[f"R${v:.4f}" for v in df_prov[_vc]],
                textposition="outside", textfont=dict(color=C["white"], size=9)
            ))
            fig_prov.update_layout(**{**PL, "margin": dict(l=40,r=40,t=50,b=80)},
                title=f"Proventos por Evento — {papel}",
                yaxis_title="R$ por ação", height=380)
            fig_prov.update_xaxes(tickangle=-45)
            st.plotly_chart(fig_prov, use_container_width=True)
            st.caption("Fonte: Yahoo Finance")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.caption("ComDinheiro (BalancosSinteticos001) + Yahoo Finance · Cache: KPIs 30min · DRE/Proventos 1h")


# ══════════════════════════════════════════════════════════════════
# PÁG 10 — PREMISSAS
# ══════════════════════════════════════════════════════════════════
elif pagina == "Valuation":
    st.markdown("##  Valuation Interativo")
    emp_sel = st.selectbox("Empresa", empresas,
        format_func=lambda e: f"{results[e].get('ticker',e).replace('.SA','')} — {e}",
        key="val_emp")
    r = results[emp_sel]; ticker = r.get("ticker", emp_sel)
    wd = r.get("wacc_data") or {}
    ovr = r.get("overrides") or {}

    col_logo, col_title = st.columns([1,5])
    with col_logo: st.markdown(logo_empresa_html(ticker,80), unsafe_allow_html=True)
    with col_title:
        pn = float(r.get("price_now") or 0)
        pf = float(r.get("price_fair") or 0)
        up = float(r.get("upside") or 0)
        cor_up = C["pos"] if up > 0 else C["neg"]
        st.markdown(f"""<div style='margin-top:10px'>
            <span style='color:{C["blue_lt"]};font-size:1.2rem;font-weight:800'>{ticker.replace(".SA","")}</span>
            &nbsp;{badge(r.get("recomendacao",""))}
            <span style='color:{C["gray2"]};font-size:.85rem;margin-left:12px'>
            Tela: <b style='color:{C["white"]}'>{price(pn)}</b> &nbsp;|&nbsp;
            Justo: <b style='color:{C["blue_lt"]}'>{price(pf)}</b> &nbsp;|&nbsp;
            Upside: <b style='color:{cor_up}'>{up*100:+.1f}%</b>
            </span></div>""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    tab_prem, tab_sim, tab_cmp = st.tabs([" Premissas & WACC", " Simulador DCF", " Comparar Valuations"])

    # ── Tab 1: Premissas ───────────────────────────────────────────
    with tab_prem:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### DCF")
            tg  = st.slider("Terminal Growth (%)", 0.0, 8.0,
                float((r.get("terminal_growth") or 0.04)*100), 0.25, key="val_tg") / 100
            kd  = st.slider("Custo da Dívida Bruto (%)", 5.0, 25.0,
                float((r.get("cost_of_debt") or 0.12)*100), 0.25, key="val_kd") / 100
            tax = st.slider("Tax Rate (%)", 10.0, 45.0, 34.0, 1.0, key="val_tax") / 100
            anos= st.slider("Anos de projeção", 3, 10, 6, 1, key="val_anos")
        with c2:
            st.markdown("#### Crescimento & Margem")
            rev_g = st.slider("CAGR Receita (%)", -10.0, 40.0,
                float((ovr.get("revenue_growth") or r.get("cagr_receita") or 0.10)*100), 0.5, key="val_rev") / 100
            ebit_m= st.slider("Margem EBIT (%)", 0.0, 60.0,
                float((ovr.get("ebit_margin") or r.get("ebit_margin") or 0.15)*100), 0.5, key="val_ebit") / 100
            beta_v= st.slider("Beta", 0.3, 2.5,
                float(r.get("beta") or 1.0), 0.05, key="val_beta")
            rf_v  = st.slider("Risk-free nominal (%)", 5.0, 18.0,
                float((wd.get("risk_free_nominal") or 0.13)*100), 0.25, key="val_rf") / 100
            erp_v = st.slider("ERP (%)", 3.0, 10.0,
                float((wd.get("equity_risk_premium") or 0.055)*100), 0.25, key="val_erp") / 100

        # Recalcula WACC e preço justo simplificado
        ke_v    = rf_v + beta_v * erp_v
        kd_liq  = kd * (1 - tax)
        ew      = float(wd.get("equity_weight") or 0.7)
        dw      = 1 - ew
        wacc_v  = ke_v * ew + kd_liq * dw

        # DCF simplificado (FCFF atual como base)
        ebit_base = float(r.get("ebit_last") or r.get("revenue_last",1e9) * ebit_m)
        fcff_base = ebit_base * (1-tax) * 0.65  # proxy FCFF
        shares    = float(r.get("shares_out") or 1)
        net_debt  = float(r.get("net_debt") or 0)

        pv = 0.0
        fcff_i = fcff_base
        for i in range(1, anos+1):
            fcff_i *= (1 + rev_g)
            pv += fcff_i / (1 + wacc_v)**i
        tv = fcff_i * (1 + tg) / (wacc_v - tg) / (1 + wacc_v)**anos if wacc_v > tg else 0
        ev_sim   = pv + tv
        eq_sim   = ev_sim - net_debt
        pj_sim   = eq_sim / shares if shares else 0
        up_sim   = (pj_sim - pn) / pn if pn else 0

        st.markdown("<hr>", unsafe_allow_html=True)
        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("WACC estimado", f"{wacc_v*100:.2f}%")
        m2.metric("Ke", f"{ke_v*100:.2f}%")
        m3.metric("Kd líq.", f"{kd_liq*100:.2f}%")
        m4.metric("Preço Justo Simulado", f"R$ {pj_sim:.2f}")
        m5.metric("Upside Simulado", f"{up_sim*100:+.1f}%",
                  delta_color="normal" if up_sim>0 else "inverse")

        # Gauge
        if pn and pj_sim > 0:
            maximo = max(pn, pj_sim) * 1.4
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number+delta", value=pn,
                delta=dict(reference=pj_sim, valueformat=".2f",
                    increasing=dict(color=C["neg"]), decreasing=dict(color=C["pos"])),
                number=dict(prefix="R$ ", font=dict(color=C["white"], size=28)),
                gauge=dict(
                    axis=dict(range=[0,maximo], tickcolor=C["gray2"]),
                    bar=dict(color=C["bg3"]), bgcolor=C["bg2"], bordercolor=C["border"],
                    steps=[dict(range=[0,pj_sim*.85], color="#0a1e14"),
                           dict(range=[pj_sim*.85,pj_sim*1.15], color=C["bg4"]),
                           dict(range=[pj_sim*1.15,maximo], color="#1e0a0a")],
                    threshold=dict(line=dict(color=C["blue_lt"],width=3), value=pj_sim)),
                title=dict(text=f"Linha azul = justo simulado R${pj_sim:.2f}",
                           font=dict(color=C["gray2"],size=11))))
            fig_g.update_layout(paper_bgcolor=C["bg"],
                font=dict(family="Helvetica,Arial",color=C["gray"]),
                margin=dict(l=30,r=30,t=50,b=20), height=260)
            st.plotly_chart(fig_g, use_container_width=True)

    # ── Tab 2: Simulador Monte Carlo ──────────────────────────────
    with tab_sim:
        st.markdown("###  Monte Carlo — Distribuição de Preço Justo")
        mc1, mc2 = st.columns(2)
        with mc1:
            n_sim   = st.selectbox("Simulações", [500,1000,2000,5000,10000], index=2, key="val_mc_n")
            std_rev = st.slider("Desvio padrão CAGR (%)", 1.0, 15.0, 5.0, 0.5, key="val_mc_sr") / 100
        with mc2:
            std_ebit= st.slider("Desvio padrão Margem EBIT (%)", 1.0, 10.0, 3.0, 0.5, key="val_mc_se") / 100
            std_wacc= st.slider("Desvio padrão WACC (%)", 0.5, 5.0, 1.5, 0.25, key="val_mc_sw") / 100

        if st.button(" Rodar Simulação", type="primary", key="val_mc_run"):
            import numpy as _np2
            _np2.random.seed(42)
            rev_sims  = _np2.random.normal(rev_g,  std_rev,  n_sim)
            ebit_sims = _np2.random.normal(ebit_m, std_ebit, n_sim)
            wacc_sims = _np2.random.normal(wacc_v, std_wacc, n_sim)
            wacc_sims = _np2.clip(wacc_sims, 0.04, 0.35)

            pj_sims = []
            for rg_i, em_i, wc_i in zip(rev_sims, ebit_sims, wacc_sims):
                if wc_i <= tg: continue
                eb_i = float(r.get("revenue_last",1e9) or 1e9) * em_i
                fc_i = eb_i * (1-tax) * 0.65
                pv_i = 0.0; fc_j = fc_i
                for j in range(1, anos+1):
                    fc_j *= (1+rg_i)
                    pv_i += fc_j/(1+wc_i)**j
                tv_i = fc_j*(1+tg)/(wc_i-tg)/(1+wc_i)**anos
                eq_i = (pv_i+tv_i) - net_debt
                pj_i = eq_i/shares if shares else 0
                if -500 < pj_i < 5000: pj_sims.append(pj_i)

            if pj_sims:
                arr = _np2.array(pj_sims)
                p10,p25,p50,p75,p90 = _np2.percentile(arr,[10,25,50,75,90])
                prob_up = float((_np2.array(arr) > pn).mean()*100) if pn else 50.0

                # Histograma destacado
                import numpy as _np3
                # ── Fan chart estilo TradingView ──────────────────
                # Simula caminhos de preço ao longo de N períodos
                n_steps = anos * 12  # mensal
                mu_m  = (1 + rev_g)**(1/12) - 1
                sig_m = std_rev / _np3.sqrt(12)
                _np3.random.seed(42)
                n_paths = min(n_sim, 2000)
                paths = _np3.zeros((n_paths, n_steps+1))
                paths[:,0] = pn if pn else p50
                for t in range(1, n_steps+1):
                    shocks = _np3.random.normal(mu_m, sig_m, n_paths)
                    paths[:,t] = paths[:,t-1] * (1 + shocks)
                paths = _np3.clip(paths, 0, paths[:,0].max()*10)
                x_axis = list(range(n_steps+1))

                # Percentis por passo
                pc10 = _np3.percentile(paths, 10, axis=0)
                pc25 = _np3.percentile(paths, 25, axis=0)
                pc50 = _np3.percentile(paths, 50, axis=0)
                pc75 = _np3.percentile(paths, 75, axis=0)
                pc90 = _np3.percentile(paths, 90, axis=0)

                fig_mc = go.Figure()
                # Fan P10-P90 (zona vermelha)
                fig_mc.add_trace(go.Scatter(x=x_axis+x_axis[::-1],
                    y=list(pc90)+list(pc10[::-1]), fill="toself",
                    fillcolor="rgba(30,80,160,0.15)", line=dict(color="rgba(0,0,0,0)"),
                    name="P10-P90", showlegend=True))
                # Fan P25-P75 (zona azul)
                fig_mc.add_trace(go.Scatter(x=x_axis+x_axis[::-1],
                    y=list(pc75)+list(pc25[::-1]), fill="toself",
                    fillcolor="rgba(30,80,160,0.30)", line=dict(color="rgba(0,0,0,0)"),
                    name="P25-P75", showlegend=True))
                # Mediana
                fig_mc.add_trace(go.Scatter(x=x_axis, y=pc50, mode="lines",
                    line=dict(color=C["blue_lt"], width=2.5), name="Mediana (P50)"))
                # Bear e Bull
                fig_mc.add_trace(go.Scatter(x=x_axis, y=pc10, mode="lines",
                    line=dict(color=C["neg"], width=1.2, dash="dot"), name="Bear (P10)"))
                fig_mc.add_trace(go.Scatter(x=x_axis, y=pc90, mode="lines",
                    line=dict(color=C["pos"], width=1.2, dash="dot"), name="Bull (P90)"))
                # Preço atual (linha horizontal)
                if pn:
                    fig_mc.add_hline(y=pn, line_color=C["sky"], line_dash="dash", line_width=1.5,
                        annotation_text=f"Preço atual R${pn:.2f}",
                        annotation_font_color=C["sky"], annotation_position="top left")
                # Amostra de 30 caminhos aleatórios
                for i in _np3.random.choice(n_paths, min(50,n_paths), replace=False):
                    fig_mc.add_trace(go.Scatter(x=x_axis, y=paths[i], mode="lines",
                        line=dict(color="rgba(100,180,255,0.18)", width=1.0),
                        showlegend=False, hoverinfo="skip"))
                # Histograma lateral (distribuição final)
                fig_mc.add_trace(go.Violin(x=paths[:,-1], side="positive",
                    line_color=C["blue_lt"], fillcolor="rgba(30,80,160,0.3)",
                    opacity=0.6, name="Dist. final", showlegend=False,
                    yaxis="y2"))

                # Labels no eixo X — meses
                tickvals = list(range(0, n_steps+1, 6))
                ticktext = [f"Mês {v}" for v in tickvals]

                _pl2 = {**PL,
                    "xaxis":dict(tickvals=tickvals,ticktext=ticktext,
                        tickfont=dict(color=C["gray2"]),
                        gridcolor="rgba(255,255,255,0.04)", showgrid=True),
                    "yaxis":dict(title="Preço (R$)",
                        gridcolor="rgba(255,255,255,0.04)", showgrid=True),
                    "yaxis2":dict(overlaying="y",side="right",showgrid=False,showticklabels=False),
                    "height":480,"legend":dict(orientation="h",y=-0.12)}
                fig_mc.update_layout(**_pl2,
                    title=f"Monte Carlo — {n_paths:,} caminhos | {anos} anos | Prob. upside: {prob_up:.1f}%")
                st.plotly_chart(fig_mc, use_container_width=True)

                # Histograma de distribuição final separado
                fig_hist2 = go.Figure()
                fig_hist2.add_trace(go.Histogram(x=paths[:,-1], nbinsx=80,
                    marker_color=C["blue_lt"], opacity=0.8, name="Preço final"))
                for pv2,lb2,cl2 in [(p10,"P10",C["neg"]),(p50,"P50",C["white"]),(p90,"P90",C["pos"])]:
                    fig_hist2.add_vline(x=pv2, line_color=cl2, line_dash="dash",
                        annotation_text=f"{lb2}: R${pv2:.2f}", annotation_font_color=cl2)
                if pn:
                    fig_hist2.add_vline(x=pn, line_color=C["sky"], line_width=2,
                        annotation_text=f"Tela: R${pn:.2f}", annotation_font_color=C["sky"])
                fig_hist2.update_layout(**PL,
                    title="Distribuição de Preços no Final do Período",
                    xaxis_title="Preço Justo (R$)", height=300)
                st.plotly_chart(fig_hist2, use_container_width=True)

                r1,r2,r3,r4,r5 = st.columns(5)
                r1.metric("P10 (Bear)", f"R$ {p10:.2f}")
                r2.metric("P25", f"R$ {p25:.2f}")
                r3.metric("P50 (Base)", f"R$ {p50:.2f}")
                r4.metric("P75", f"R$ {p75:.2f}")
                r5.metric("P90 (Bull)", f"R$ {p90:.2f}")
                st.metric("Probabilidade de Upside", f"{prob_up:.1f}%",
                    delta_color="normal" if prob_up>50 else "inverse")

    # ── Tab 3: Comparar Valuations ─────────────────────────────────
    with tab_cmp:
        st.markdown("###  Comparar com outras empresas")
        emps_cmp = st.multiselect("Empresas para comparar", empresas,
            default=[emp_sel] + [e for e in empresas if e!=emp_sel][:3], key="val_cmp")
        if emps_cmp:
            rows_cmp = []
            for ec in emps_cmp:
                rc = results[ec]
                rows_cmp.append({
                    "Empresa": ec[:25],
                    "Ticker": rc.get("ticker","").replace(".SA",""),
                    "P. Tela": price(rc.get("price_now")),
                    "P. Justo": price(rc.get("price_fair")),
                    "Upside": f"{float(rc.get('upside') or 0)*100:+.1f}%",
                    "WACC": pct(rc.get("wacc")),
                    "Mg EBIT": pct(rc.get("ebit_margin")),
                    "ROIC": pct(rc.get("roic")),
                    "Rec.": rc.get("recomendacao","—"),
                })
            def _cmp_color(v):
                if "%" in str(v):
                    try:
                        vv = float(str(v).replace("%","").replace("+",""))
                        if vv>20: return f"color:{C['pos']};font-weight:bold"
                        if vv>0:  return f"color:{C['sky']}"
                        if vv<0:  return f"color:{C['neg']}"
                    except: pass
                return f"color:{C['white']}"
            st.markdown(dark_table(pd.DataFrame(rows_cmp), _cmp_color), unsafe_allow_html=True)

            # Scatter upside vs WACC
            fig_sc2 = go.Figure()
            for row in rows_cmp:
                up2  = float(str(row["Upside"]).replace("%","").replace("+","") or 0)
                wc2  = float(str(row["WACC"]).replace("%","") or 0)
                rc2  = results.get(next((e for e in emps_cmp if results[e].get("ticker","").replace(".SA","")==row["Ticker"]), emps_cmp[0]), {})
                ev2  = abs(float(rc2.get("enterprise_value") or 1e9))/1e9
                fig_sc2.add_trace(go.Scatter(
                    x=[wc2], y=[up2], mode="markers+text",
                    marker=dict(size=max(8,ev2*.5+14), color=C["blue_lt"],
                                line=dict(width=2,color=C["bg3"])),
                    text=[row["Ticker"]], textposition="top center",
                    textfont=dict(color=C["white"],size=11), name=row["Ticker"]))
            fig_sc2.add_hline(y=0, line_dash="dash", line_color=C["gray2"], opacity=.4)
            fig_sc2.update_layout(**PL, title="Upside vs WACC (tamanho = EV)",
                xaxis_title="WACC (%)", yaxis_title="Upside (%)", height=420)
            st.plotly_chart(fig_sc2, use_container_width=True)


elif pagina == "Cadastros":
    import json as _jc, hashlib as _hc
    _USERS_FILE = "/opt/shipyard/data/users.json"
    import os as _os
    def _load_users():
        if _os.path.exists(_USERS_FILE):
            return _jc.loads(open(_USERS_FILE).read())
        return {"Leonardo Losi": {"senha": _hc.md5(b"velacapital@2025").hexdigest(), "perfil": "Diretor"}}
    def _save_users(u):
        open(_USERS_FILE,"w").write(_jc.dumps(u, indent=2, ensure_ascii=False))

    users = _load_users()
    st.markdown("##  Gestão de Usuários")
    tab_list, tab_new = st.tabs([" Usuários Cadastrados", " Novo Usuário"])
    with tab_list:
        rows_u = [{"Nome": n, "Perfil": v.get("perfil","Analista")} for n,v in users.items()]
        st.dataframe(pd.DataFrame(rows_u), use_container_width=True, hide_index=True)
        st.markdown("### Excluir Usuário")
        del_user = st.selectbox("Selecione", [n for n in users if n != "Leonardo Losi"], key="del_u")
        if del_user and st.button(" Excluir", type="secondary"):
            users.pop(del_user, None)
            _save_users(users)
            st.success(f"{del_user} excluído.")
            st.rerun()
    with tab_new:
        with st.form("form_new_user"):
            nu_nome  = st.text_input("Nome completo")
            nu_senha = st.text_input("Senha", type="password")
            nu_perf  = st.selectbox("Perfil", ["Analista","Gestor","Diretor"])
            if st.form_submit_button("Criar Usuário", type="primary"):
                if nu_nome and nu_senha:
                    users[nu_nome] = {"senha": _hc.md5(nu_senha.encode()).hexdigest(), "perfil": nu_perf}
                    _save_users(users)
                    st.success(f"Usuário '{nu_nome}' criado!")
                    st.rerun()
                else:
                    st.warning("Preencha nome e senha.")

