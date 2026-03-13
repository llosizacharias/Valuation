import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json, math, base64, io, os
from pathlib import Path
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

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
        st.error("⚠️ dashboard_auth.yaml não encontrado. Execute: python setup_auth.py"); st.stop()
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
    st.error("⚠️ valuation_results.json não encontrado. Execute: python main.py"); st.stop()

# ── SIDEBAR ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;padding:20px 0 10px;">
        <div style="color:#FFFFFF;font-size:1.1rem;font-weight:700;letter-spacing:.15em;">VELA CAPITAL</div>
        <div style="color:{C['gray2']};font-size:.6rem;letter-spacing:.2em;margin-top:4px;opacity:.7;">SHIPYARD</div>
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
        "Gestoras", "ComDinheiro", "Premissas"
    ]
    _pages = _pages_base + (["── Admin ──", "Gerenciar Usuários"] if is_master else [])

    pagina = st.selectbox("nav", _pages, label_visibility="collapsed",
                      index=_pages.index("Empresa") if st.session_state.get("_nav_empresa") else 0)

    st.markdown("<hr>", unsafe_allow_html=True)
    _role = "Master" if is_master else "Analista"
    _c_gray2   = C["gray2"]
    _c_blue_lt = C["blue_lt"]
    st.markdown(f"<div style='color:{_c_gray2};font-size:.72rem;padding:4px 0;'>👤 {name} <span style='color:{_c_blue_lt};font-size:.65rem;'>({_role})</span></div>", unsafe_allow_html=True)
    auth.logout("Sair", location="sidebar")
    st.markdown(f"<div class='sidebar-footer'>Vela Capital © 2025</div>", unsafe_allow_html=True)

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
                   filtro_upside_min/100 <= (results[e].get("upside") or 0) <= filtro_upside_max/100]

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
        st.markdown(f"""
        <div style="margin-top:8px;">
            <span style="color:{C['blue_lt']};font-size:1.15rem;font-weight:700;">{_tk_clean}</span>
    _up_str = f'{upside*100:+.1f}%'
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
        st.warning(f"⚠️  Overrides — receita: {pct(ovr.get('revenue_growth'))} | EBIT: {pct(ovr.get('ebit_margin'))}")

    # ── #22 — Confronto de Preços: Tela vs DCF vs Consenso ──────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## Confronto de Preços — Tela · DCF · Consenso Analistas")

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
            marker=dict(size=ev*.5+14,color=C["blue_lt"],line=dict(width=2,color=C["bg3"])),
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
        extra = st.text_input("Adicionar tickers extras (separados por vírgula)",
                              value="PETR4.SA, VALE3.SA, BBAS3.SA, ITUB4.SA",
                              help="Tickers da B3 com sufixo .SA")
        extra_list = [t.strip() for t in extra.split(",") if t.strip()]
        portfolio_tickers = list(dict.fromkeys(all_tickers + extra_list))
        selected = st.multiselect("Ativos na carteira", portfolio_tickers,
                                  default=portfolio_tickers[:min(5,len(portfolio_tickers))])
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

    if st.button("▶  Calcular Fronteira Eficiente", type="primary"):
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
                    text=["⭐ Máx Sharpe"], textposition="top right",
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
                        text=["🟡 IBOV"], textposition="top left",
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
                    title="Fronteira Eficiente | Nuvem = Monte Carlo | ⭐ Máx Sharpe | 🟡 IBOV",
                    xaxis_title="Volatilidade Anual (%)",
                    yaxis_title="Retorno Anual Esperado (%)",
                    height=580,
                )
                st.plotly_chart(fig_mz, use_container_width=True)

                if show_ibov and ibov_ret is not None:
                    st.info(f"📊 IBOV — Retorno: {ibov_ret*100:.1f}% a.a. | Vol: {ibov_vol*100:.1f}% | Sharpe: {(ibov_ret-risk_free)/ibov_vol:.2f}")

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
        fonte = st.selectbox("Fonte de notícias", list(feeds.keys()))
    with col_q:
        query = st.text_input("Filtrar por palavra-chave", placeholder="ex: WEG, COGNA, Selic...")

    n_noticias = st.slider("Número de notícias", 5, 30, 12, 1)

    if st.button("Carregar Notícias", key="btn_noticias"):
        with st.spinner("Carregando notícias..."):
            try:
                import feedparser
                url = feeds[fonte]
                feed = feedparser.parse(url)
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
                    st.markdown(f"🔗 [{nome}]({url})")

            except Exception as e:
                st.error(f"Erro ao carregar notícias: {e}")
                st.info("Verifique a conexão do VPS com a internet.")

    # Calendário de eventos
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## Calendário de Resultados")

    cal_data = [
        {"Empresa": "WEG (WEGE3)",   "Evento": "Resultados 4T25",   "Data": "Mar 2026",  "Status": "✅ Divulgado"},
        {"Empresa": "COGNA (COGN3)", "Evento": "Resultados 4T25",   "Data": "Mar 2026",  "Status": "✅ Divulgado"},
        {"Empresa": "WEG (WEGE3)",   "Evento": "Resultados 1T26",   "Data": "Mai 2026",  "Status": "⏳ Aguardando"},
        {"Empresa": "COGNA (COGN3)", "Evento": "Resultados 1T26",   "Data": "Mai 2026",  "Status": "⏳ Aguardando"},
        {"Empresa": "WEG (WEGE3)",   "Evento": "Dividendos",        "Data": "Ago 2026",  "Status": "📅 Previsto"},
        {"Empresa": "COGNA (COGN3)", "Evento": "Assembleia Geral",  "Data": "Abr 2026",  "Status": "📅 Previsto"},
        {"Empresa": "B3",            "Evento": "Reunião COPOM",     "Data": "Mai 2026",  "Status": "🏦 Macro"},
        {"Empresa": "B3",            "Evento": "IPCA",              "Data": "Todo mês",  "Status": "🏦 Macro"},
    ]
    st.markdown(dark_table(pd.DataFrame(cal_data)), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════
# PÁG 9 — CARTEIRA ENDURANCE + EXPOSIÇÃO SETORIAL (#15 e #27)
# ══════════════════════════════════════════════════════════════════
elif pagina == "Carteira Endurance":
    st.markdown("## Carteira Teórica — Fundo Endurance")
    st.caption("Posições teóricas para acompanhamento de trackrecord. Atualize os dados abaixo conforme os relatórios do fundo.")

    # ── Carteira Endurance — editável pelo usuário ───────────────
    # Dados base (atualizar conforme último relatório disponível)
    ENDURANCE_CARTEIRA = [
        {"Ticker": "WEGE3.SA",  "Empresa": "WEG",             "Setor": "Bens Industriais", "Peso (%)": 12.0, "Preço Entrada": 38.50},
        {"Ticker": "ITUB4.SA",  "Empresa": "Itaú Unibanco",   "Setor": "Financeiro",       "Peso (%)": 10.5, "Preço Entrada": 31.20},
        {"Ticker": "PETR4.SA",  "Empresa": "Petrobras",        "Setor": "Petróleo & Gás",  "Peso (%)": 9.0,  "Preço Entrada": 37.80},
        {"Ticker": "VALE3.SA",  "Empresa": "Vale",             "Setor": "Mineração",        "Peso (%)": 8.5,  "Preço Entrada": 62.40},
        {"Ticker": "BBAS3.SA",  "Empresa": "Banco do Brasil",  "Setor": "Financeiro",       "Peso (%)": 7.5,  "Preço Entrada": 25.10},
        {"Ticker": "RENT3.SA",  "Empresa": "Localiza",         "Setor": "Consumo Discr.",   "Peso (%)": 7.0,  "Preço Entrada": 42.90},
        {"Ticker": "MGLU3.SA",  "Empresa": "Magazine Luiza",   "Setor": "Consumo Discr.",   "Peso (%)": 5.5,  "Preço Entrada": 8.20},
        {"Ticker": "RADL3.SA",  "Empresa": "Raia Drogasil",    "Setor": "Saúde",            "Peso (%)": 5.0,  "Preço Entrada": 28.60},
        {"Ticker": "COGN3.SA",  "Empresa": "Cogna",            "Setor": "Educação",         "Peso (%)": 4.5,  "Preço Entrada": 3.50},
        {"Ticker": "ABEV3.SA",  "Empresa": "Ambev",            "Setor": "Consumo Básico",   "Peso (%)": 4.0,  "Preço Entrada": 12.40},
        {"Ticker": "CAIXA",     "Empresa": "Caixa / CDI",      "Setor": "Renda Fixa",       "Peso (%)": 26.5, "Preço Entrada": 0.0},
    ]

    df_end = pd.DataFrame(ENDURANCE_CARTEIRA)

    # Busca preços atuais
    @st.cache_data(ttl=600)
    def get_prices_endurance(tickers):
        try:
            import yfinance as yf
            prices = {}
            for tk in tickers:
                if tk == "CAIXA": continue
                try:
                    info = yf.Ticker(tk).fast_info
                    prices[tk] = float(info.last_price or 0)
                except Exception:
                    prices[tk] = 0.0
            return prices
        except Exception:
            return {}

    tickers_end = [row["Ticker"] for row in ENDURANCE_CARTEIRA if row["Ticker"] != "CAIXA"]
    with st.spinner("Carregando cotações..."):
        precos_atuais = get_prices_endurance(tuple(tickers_end))

    # Monta tabela de performance
    rows_end = []
    total_retorno_pond = 0.0
    for row in ENDURANCE_CARTEIRA:
        tk   = row["Ticker"]
        peso = row["Peso (%)"] / 100
        p_in = row["Preço Entrada"]
        if tk == "CAIXA":
            p_at = 0.0
            ret  = None
            ret_str = "CDI"
        else:
            p_at = precos_atuais.get(tk, 0.0)
            ret  = (p_at - p_in) / p_in * 100 if p_in and p_at else None
            ret_str = f"{ret:+.1f}%" if ret is not None else "—"
            if ret is not None:
                total_retorno_pond += ret * peso

        rows_end.append({
            "Ticker":         tk,
            "Empresa":        row["Empresa"],
            "Setor":          row["Setor"],
            "Peso":           f"{row['Peso (%)']:.1f}%",
            "P. Entrada":     f"R$ {p_in:.2f}" if p_in else "—",
            "P. Atual":       f"R$ {p_at:.2f}" if p_at else "CDI",
            "Retorno":        ret_str,
        })

    def _end_color(val):
        if "%" in str(val):
            try:
                v = float(str(val).replace("%","").replace("+",""))
                if v > 10:  return f"color:{C['blue_lt']};font-weight:bold"
                if v > 0:   return f"color:{C['sky']}"
                if v < -10: return f"color:{C['neg']}"
                return f"color:{C['gray']}"
            except: pass
        return f"color:{C['white']}"

    st.markdown(dark_table(pd.DataFrame(rows_end), _end_color), unsafe_allow_html=True)

    # KPI da carteira
    k1, k2, k3 = st.columns(3)
    k1.metric("Retorno Ponderado (posições com preço)", f"{total_retorno_pond:+.2f}%")
    n_pos = sum(1 for r in ENDURANCE_CARTEIRA if r["Ticker"] != "CAIXA")
    k2.metric("Posições em Renda Variável", f"{n_pos}")
    k3.metric("Caixa / Renda Fixa", f"{next(r['Peso (%)'] for r in ENDURANCE_CARTEIRA if r['Ticker']=='CAIXA'):.1f}%")

    # ── Trackrecord — Retorno acumulado vs IBOV ─────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## Trackrecord — Retorno Acumulado vs IBOV")

    tickers_rv = [r["Ticker"] for r in ENDURANCE_CARTEIRA if r["Ticker"] != "CAIXA"]
    pesos_rv   = {r["Ticker"]: r["Peso (%)"] / 100 for r in ENDURANCE_CARTEIRA if r["Ticker"] != "CAIXA"}
    peso_caixa = next(r["Peso (%)"] for r in ENDURANCE_CARTEIRA if r["Ticker"]=="CAIXA") / 100

    @st.cache_data(ttl=3600)
    def get_trackrecord(tickers, periodo="2y"):
        try:
            import yfinance as yf
            dfs = []
            for tk in tickers:
                df = yf.download(tk, period=periodo, auto_adjust=True, progress=False)["Close"].squeeze()
                dfs.append(df.rename(tk))
            ibov = yf.download("^BVSP", period=periodo, auto_adjust=True, progress=False)["Close"].squeeze().rename("IBOV")
            dfs.append(ibov)
            return pd.concat(dfs, axis=1).dropna(how="all")
        except Exception:
            return pd.DataFrame()

    with st.spinner("Calculando trackrecord..."):
        df_track = get_trackrecord(tuple(tickers_rv))

    if not df_track.empty:
        # Retornos diários
        rets = df_track.pct_change().dropna()

        # Carteira ponderada (apenas RV, normaliza os pesos sem caixa)
        tickers_ok = [tk for tk in tickers_rv if tk in rets.columns]
        peso_total_rv = sum(pesos_rv.get(tk, 0) for tk in tickers_ok)
        if peso_total_rv > 0:
            pesos_norm = {tk: pesos_rv.get(tk, 0) / peso_total_rv * (1 - peso_caixa)
                         for tk in tickers_ok}
        else:
            pesos_norm = {}

        if pesos_norm:
            carteira_ret = sum(rets[tk] * pesos_norm[tk] for tk in tickers_ok)
            # CDI proxy: ~13.75% a.a. → ~0.0529% por dia útil
            cdi_diario = (1 + 0.1375) ** (1/252) - 1
            caixa_ret  = pd.Series(cdi_diario, index=rets.index)
            port_ret   = carteira_ret + caixa_ret * peso_caixa

            # Retorno acumulado
            port_acc  = (1 + port_ret).cumprod() - 1
            ibov_acc  = (1 + rets["IBOV"]).cumprod() - 1 if "IBOV" in rets.columns else None

            fig_tr = go.Figure()
            fig_tr.add_trace(go.Scatter(
                x=port_acc.index, y=port_acc.values * 100,
                mode="lines", name="Endurance (teórico)",
                line=dict(color=C["blue_lt"], width=2.5)
            ))
            if ibov_acc is not None:
                fig_tr.add_trace(go.Scatter(
                    x=ibov_acc.index, y=ibov_acc.values * 100,
                    mode="lines", name="IBOV",
                    line=dict(color=C["gray"], width=1.5, dash="dot")
                ))
            fig_tr.add_hline(y=0, line_color=C["border"], line_width=1)
            fig_tr.update_layout(**PL,
                title="Retorno acumulado — base 0% no início do período",
                yaxis_title="Retorno acumulado (%)", height=380)
            st.plotly_chart(fig_tr, use_container_width=True)

            # Métricas de performance
            pm1, pm2, pm3, pm4 = st.columns(4)
            pm1.metric("Retorno Carteira (período)", f"{float(port_acc.iloc[-1])*100:+.1f}%")
            if ibov_acc is not None:
                pm2.metric("Retorno IBOV (período)", f"{float(ibov_acc.iloc[-1])*100:+.1f}%")
                alpha = float(port_acc.iloc[-1] - ibov_acc.iloc[-1]) * 100
                pm3.metric("Alpha vs IBOV", f"{alpha:+.1f}%",
                           delta_color="normal" if alpha > 0 else "inverse")
            vol_port = float(port_ret.std() * (252**0.5) * 100)
            pm4.metric("Volatilidade Anual", f"{vol_port:.1f}%")

    # ── #27 — Exposição Setorial da Carteira ─────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## Exposição Setorial da Carteira")

    setor_peso = {}
    for row in ENDURANCE_CARTEIRA:
        s = row["Setor"]
        setor_peso[s] = setor_peso.get(s, 0) + row["Peso (%)"]

    setores  = list(setor_peso.keys())
    pesos_s  = list(setor_peso.values())
    cores_s  = [C["blue_lt"], C["sky"], C["navy"], C["teal"], C["gray"],
                C["bg3"], "#5EC8A0", "#FFB347", "#9B59B6", "#E67E22", C["gray2"]]

    sc1, sc2 = st.columns(2)
    with sc1:
        fig_pizza_s = go.Figure(go.Pie(
            labels=setores, values=pesos_s, hole=0.52,
            marker_colors=cores_s[:len(setores)],
            textfont=dict(color=C["white"], size=11),
            textinfo="label+percent",
        ))
        fig_pizza_s.update_layout(
            paper_bgcolor=C["bg"],
            font=dict(family="Helvetica,Arial", color=C["white"]),
            legend=dict(bgcolor=C["bg"], bordercolor=C["border"], font=dict(color=C["white"])),
            margin=dict(l=10, r=10, t=30, b=10), height=340,
            annotations=[dict(text="Setores", font=dict(size=12, color=C["white"]), showarrow=False)]
        )
        st.plotly_chart(fig_pizza_s, use_container_width=True)

    with sc2:
        fig_bar_s = go.Figure(go.Bar(
            x=pesos_s,
            y=setores,
            orientation="h",
            marker_color=cores_s[:len(setores)],
            text=[f"{p:.1f}%" for p in pesos_s],
            textposition="outside",
            textfont=dict(color=C["white"])
        ))
        fig_bar_s.update_layout(**PL,
            title="Concentração por Setor (%)",
            xaxis_title="Peso (%)", height=340, showlegend=False
        )
        st.plotly_chart(fig_bar_s, use_container_width=True)

    # Tabela setores
    df_set = pd.DataFrame({"Setor": setores, "Peso (%)": [f"{p:.1f}%" for p in pesos_s]})
    st.markdown(dark_table(df_set), unsafe_allow_html=True)
    st.info("💡 Para atualizar a carteira, edite o dict ENDURANCE_CARTEIRA no dashboard.py")
    export_buttons(pd.DataFrame(rows_end), "carteira_endurance")

# ══════════════════════════════════════════════════════════════════
# PÁG 10 — EXPOSIÇÃO GEOGRÁFICA
# ══════════════════════════════════════════════════════════════════
elif pagina == "Exposição Geográfica":
    st.markdown("## Exposição Geográfica da Cobertura")
    st.markdown("<div style='color:{};font-size:.8rem;'>Intensidade = presença operacional estimada (0–100). Quanto mais escuro, maior a presença.</div>".format(C["gray2"]), unsafe_allow_html=True)

    # Dados de exposição geográfica por empresa
    # Formato: ticker -> {iso_alpha3: intensidade 0-100}
    GEO_EXPOSURE = {
        "WEGE3.SA": {
            "BRA":100, "USA":85, "DEU":80, "MEX":75, "IND":70,
            "CHN":65,  "ARG":60, "COL":55, "PRT":50, "AUT":50,
            "BEL":45,  "FRA":40, "GBR":40, "ZAF":35, "AUS":35,
            "CAN":30,  "CHL":30, "PER":25, "URY":20, "BOL":15,
        },
        "COGN3.SA": {
            "BRA":100, "PRT":15, "AGO":10, "MOZ":10,
        },
    }

    # Monta dataframe combinado (média ponderada de todas as empresas cobertas)
    all_countries = {}
    for emp in empresas:
        ticker_geo = results[emp].get("ticker", emp)
        exposure   = GEO_EXPOSURE.get(ticker_geo, {})
        for iso, val in exposure.items():
            all_countries[iso] = all_countries.get(iso, 0) + val

    # Normaliza para 0-100
    if all_countries:
        max_v = max(all_countries.values())
        all_countries_norm = {k: v/max_v*100 for k,v in all_countries.items()}
    else:
        all_countries_norm = {}

    # Tabs: carteira vs individual
    tab_cart, *tab_emps = st.tabs(
        ["Carteira Consolidada"] + [results[e].get("ticker",e) for e in empresas]
    )

    def _mapa(geo_dict, titulo):
        if not geo_dict:
            st.info("Sem dados geográficos para este ativo."); return
        df_geo = pd.DataFrame([
            {"iso_alpha": k, "intensidade": v, "pais": k}
            for k, v in geo_dict.items()
        ])
        fig_map = go.Figure(go.Choropleth(
            locations=df_geo["iso_alpha"],
            z=df_geo["intensidade"],
            locationmode="ISO-3",
            colorscale=[
                [0.0,  "#0a1218"],
                [0.05, "#0a1624"],
                [0.2,  "#0F1E30"],
                [0.4,  "#0F558B"],
                [0.7,  "#2351FE"],
                [1.0,  "#9AC0E6"],
            ],
            zmin=0, zmax=100,
            marker_line_color="#1a3a5c",
            marker_line_width=0.5,
            colorbar=dict(
                title=dict(text="Presença (%)", font=dict(color=C["gray"])),
                tickfont=dict(color=C["gray"]),
                bgcolor=C["bg2"],
                bordercolor=C["border"],
                thickness=14,
            ),
            hovertemplate="<b>%{location}</b><br>Intensidade: %{z:.0f}%<extra></extra>",
        ))
        fig_map.update_layout(
            paper_bgcolor=C["bg"],
            plot_bgcolor=C["bg"],
            geo=dict(
                bgcolor=C["bg"],
                showframe=False,
                showcoastlines=True,
                coastlinecolor=C["border"],
                showland=True,
                landcolor="#0a1218",
                showocean=True,
                oceancolor=C["bg"],
                showlakes=False,
                showcountries=True,
                countrycolor=C["border"],
                projection_type="natural earth",
            ),
            font=dict(family="Helvetica,Arial", color=C["gray"]),
            margin=dict(l=0, r=0, t=40, b=0),
            title=dict(text=titulo, font=dict(color=C["white"], size=14)),
            height=480,
        )
        st.plotly_chart(fig_map, use_container_width=True)

        # Tabela dos países
        df_table = df_geo.sort_values("intensidade", ascending=False).reset_index(drop=True)
        df_table.columns = ["País (ISO)", "Presença (%)", "Código"]
        df_table["Presença (%)"] = df_table["Presença (%)"].round(0).astype(int)
        df_table = df_table[["País (ISO)", "Presença (%)"]].rename(columns={"País (ISO)":"ISO"})
        st.markdown(dark_table(df_table), unsafe_allow_html=True)

    with tab_cart:
        _mapa(all_countries_norm, "Exposição Geográfica Consolidada — Carteira Vela Capital")

    for i, emp in enumerate(empresas):
        ticker_geo = results[emp].get("ticker", emp)
        with tab_emps[i]:
            _mapa(GEO_EXPOSURE.get(ticker_geo, {}), f"Exposição Geográfica — {ticker_geo}")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## Concentração por Região")
    REGIOES = {
        "América do Sul": ["BRA","ARG","COL","CHL","PER","URY","BOL","PRY","ECU","VEN"],
        "América do Norte": ["USA","CAN","MEX"],
        "Europa": ["DEU","FRA","GBR","PRT","ESP","ITA","AUT","BEL","NLD","SWE","CHE","POL","ROU"],
        "Ásia": ["CHN","IND","JPN","KOR","SGP","IDN","THA","MYS","VNM","PHL"],
        "África": ["ZAF","NGA","KEN","EGY","GHA","AGO","MOZ","TZA"],
        "Oceania": ["AUS","NZL"],
        "Oriente Médio": ["SAU","UAE","ISR","TUR","QAT","KWT","BHR"],
    }
    reg_data = []
    for reg, paises in REGIOES.items():
        total = sum(all_countries.get(p,0) for p in paises)
        reg_data.append({"Região": reg, "Score": total})
    reg_df = pd.DataFrame(reg_data).sort_values("Score", ascending=False)
    if reg_df["Score"].sum() > 0:
        fig_reg = go.Figure(go.Bar(
            x=reg_df["Região"], y=reg_df["Score"],
            marker_color=C["blue_lt"],
            text=reg_df["Score"].round(0).astype(int),
            textposition="outside", textfont=dict(color=C["white"])
        ))
        fig_reg.update_layout(**PL, title="Score de Presença por Região",
                               yaxis_title="Score acumulado", showlegend=False)
        st.plotly_chart(fig_reg, use_container_width=True)

    st.info("💡 Para atualizar os dados geográficos, edite o dicionário GEO_EXPOSURE no dashboard.py")

# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════
# PÁG — GOVERNANÇA (#13)
# ══════════════════════════════════════════════════════════════════
elif pagina == "Governança":
    st.markdown("## Governança Corporativa")
    emp_sel = st.selectbox("Empresa", empresas,
                           format_func=lambda e: f"{results[e].get('ticker',e).replace('.SA','')} — {e}",
                           key="gov_emp")
    r = results[emp_sel]; ticker = r.get("ticker", emp_sel)

    # ── Dados de governança por empresa ─────────────────────────
    # Estrutura: ticker → {segmento, conselho, diretoria}
    GOVERNANCA = {
        "WEGE3.SA": {
            "segmento_b3": "Novo Mercado",
            "tag_along": "100%",
            "free_float": "~45%",
            "controlling": "Família Voigt / Fundação Weg",
            "conselho": [
                {"Nome": "Décio da Silva",          "Cargo": "Presidente do CA",   "Mandato": "2023–2025", "Independente": "Não"},
                {"Nome": "Sérgio Luiz Silva Schwartz","Cargo": "Membro",           "Mandato": "2023–2025", "Independente": "Sim"},
                {"Nome": "Flávio Maluf",             "Cargo": "Membro Ind.",       "Mandato": "2023–2025", "Independente": "Sim"},
                {"Nome": "Nildemar Secches",         "Cargo": "Membro Ind.",       "Mandato": "2023–2025", "Independente": "Sim"},
                {"Nome": "Alidor Lueders",           "Cargo": "Membro",            "Mandato": "2023–2025", "Independente": "Não"},
            ],
            "diretoria": [
                {"Nome": "Harry Schmelzer Jr.",  "Cargo": "CEO",               "Desde": "2012"},
                {"Nome": "André Luis Rodrigues", "Cargo": "CFO / DRI",         "Desde": "2015"},
                {"Nome": "Wilson Watzko",        "Cargo": "Dir. Industrial",   "Desde": "2018"},
                {"Nome": "Sônia Regina Scarpelli","Cargo": "Dir. RH",          "Desde": "2020"},
            ],
            "link_ri": "https://ri.weg.net",
        },
        "COGN3.SA": {
            "segmento_b3": "Novo Mercado",
            "tag_along": "100%",
            "free_float": "~65%",
            "controlling": "Saber (Kroton) / Free Float",
            "conselho": [
                {"Nome": "Rodrigo Galindo",      "Cargo": "Presidente do CA",   "Mandato": "2023–2025", "Independente": "Não"},
                {"Nome": "Carlos Augusto Senna", "Cargo": "Membro Ind.",        "Mandato": "2023–2025", "Independente": "Sim"},
                {"Nome": "Joanna Burle",         "Cargo": "Membro Ind.",        "Mandato": "2023–2025", "Independente": "Sim"},
                {"Nome": "Frederico Villa",      "Cargo": "Membro",             "Mandato": "2023–2025", "Independente": "Não"},
                {"Nome": "Ana Fontes",           "Cargo": "Membro Ind.",        "Mandato": "2023–2025", "Independente": "Sim"},
            ],
            "diretoria": [
                {"Nome": "Roberto Valério",      "Cargo": "CEO",               "Desde": "2022"},
                {"Nome": "Bruno Ferrari",        "Cargo": "CFO / DRI",         "Desde": "2021"},
                {"Nome": "André Tavares",        "Cargo": "Dir. Operações",    "Desde": "2020"},
                {"Nome": "Fabricia Pozzan",      "Cargo": "Dir. Educação",     "Desde": "2023"},
            ],
            "link_ri": "https://ri.cogna.com.br",
        },
    }

    gov = GOVERNANCA.get(ticker, {})

    if not gov:
        st.info(f"Dados de governança para {ticker} ainda não cadastrados. "
                f"Edite o dict GOVERNANCA no dashboard.py.")
    else:
        # KPIs de listagem
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Segmento B3",   gov.get("segmento_b3", "—"))
        g2.metric("Tag Along",     gov.get("tag_along", "—"))
        g3.metric("Free Float",    gov.get("free_float", "—"))
        g4.metric("Controlador",   gov.get("controlling", "—"))

        # Conselho de Administração
        st.markdown("<hr>", unsafe_allow_html=True)
        ca1, ca2 = st.columns([3, 1])
        with ca1:
            st.markdown("## Conselho de Administração")
        with ca2:
            link_ri = gov.get("link_ri", "")
            if link_ri:
                st.markdown(f"<a href='{link_ri}' target='_blank' style='color:{C['blue_lt']};font-size:.8rem;'>🔗 RI da Empresa</a>",
                            unsafe_allow_html=True)

        df_ca = pd.DataFrame(gov.get("conselho", []))
        if not df_ca.empty:
            def _gov_color(val):
                if val == "Sim": return f"color:{C['pos']};font-weight:600"
                if val == "Não": return f"color:{C['gray2']}"
                return f"color:{C['white']}"
            st.markdown(dark_table(df_ca, _gov_color), unsafe_allow_html=True)
            n_ind = sum(1 for m in gov.get("conselho", []) if m.get("Independente") == "Sim")
            n_tot = len(gov.get("conselho", []))
            st.caption(f"{n_ind}/{n_tot} membros independentes ({n_ind/n_tot*100:.0f}%)")
            export_buttons(df_ca, f"conselho_{ticker}")

        # Diretoria Executiva
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("## Diretoria Executiva")
        df_dir = pd.DataFrame(gov.get("diretoria", []))
        if not df_dir.empty:
            st.markdown(dark_table(df_dir), unsafe_allow_html=True)
            export_buttons(df_dir, f"diretoria_{ticker}")

        # Mapa visual de governança: radar de boas práticas
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("## Score de Governança")
        cats_gov = ["Novo Mercado", "Tag Along 100%", "Free Float > 25%",
                    "CA Independente > 20%", "Relatório ESG", "Auditoria Big 4"]
        scores_weg   = [10, 10, 8, 7, 8, 10]
        scores_cogna = [10, 10, 9, 8, 7, 10]
        scores_map   = {"WEGE3.SA": scores_weg, "COGN3.SA": scores_cogna}
        scores = scores_map.get(ticker, [5]*6)

        n_ind_pct = n_ind/n_tot*100 if n_tot else 0
        if gov.get("tag_along") == "100%": scores[1] = 10
        if gov.get("segmento_b3") == "Novo Mercado": scores[0] = 10
        if n_ind_pct >= 20: scores[3] = min(10, int(n_ind_pct/10))

        fig_gov = go.Figure()
        fig_gov.add_trace(go.Scatterpolar(
            r=scores + [scores[0]], theta=cats_gov + [cats_gov[0]],
            fill="toself", name=ticker,
            line_color=C["blue_lt"],
            fillcolor=f"rgba(35,81,254,.15)"
        ))
        fig_gov.update_layout(
            paper_bgcolor=C["bg"],
            font=dict(family="Helvetica,Arial", color=C["gray"], size=10),
            polar=dict(
                bgcolor=C["bg2"],
                radialaxis=dict(visible=True, range=[0,10], gridcolor=C["border"],
                                tickfont=dict(color=C["gray2"])),
                angularaxis=dict(gridcolor=C["border"], color=C["gray2"])
            ),
            margin=dict(l=60, r=60, t=40, b=40),
            legend=dict(bgcolor=C["bg"]), height=380,
            title=dict(text="Score 0–10 (estimado — atualize conforme relatórios)", font=dict(color=C["gray"], size=11))
        )
        st.plotly_chart(fig_gov, use_container_width=True)
        st.info("💡 Dados de governança precisam ser atualizados manualmente conforme relatórios do RI. "
                f"Acesse: {gov.get('link_ri', 'RI da empresa')}")

# ══════════════════════════════════════════════════════════════════
# PÁG — GRUPO ECONÔMICO (#21 — Teia de empresas)
# ══════════════════════════════════════════════════════════════════
elif pagina == "Grupo Econômico":
    st.markdown("## Estrutura do Grupo Econômico")
    emp_sel = st.selectbox("Empresa", empresas,
                           format_func=lambda e: f"{results[e].get('ticker',e).replace('.SA','')} — {e}",
                           key="grp_emp")
    r = results[emp_sel]; ticker = r.get("ticker", emp_sel)

    # ── Dados de estrutura societária ───────────────────────────
    GRUPO_ECONOMICO = {
        "WEGE3.SA": {
            "nos": [
                # id, label, tipo (holding/listada/subsidiaria/controladora), pct
                {"id": "FUNDACAO", "label": "Fundação WEG (33%)", "tipo": "controladora"},
                {"id": "FAMILIA",  "label": "Família Voigt (22%)", "tipo": "controladora"},
                {"id": "FF",       "label": "Free Float (45%)",    "tipo": "mercado"},
                {"id": "WEGE3",    "label": "WEG S.A. (WEGE3)",   "tipo": "listada"},
                {"id": "WEG_IND",  "label": "WEG Ind. (100%)",    "tipo": "subsidiaria"},
                {"id": "WEG_INT",  "label": "WEG Intl. (100%)",   "tipo": "subsidiaria"},
                {"id": "WEG_ENGY", "label": "WEG Energy (100%)", "tipo": "subsidiaria"},
                {"id": "WEG_AUTO", "label": "WEG Autom. (100%)", "tipo": "subsidiaria"},
                {"id": "TINTAS",   "label": "Tintas WEG (100%)", "tipo": "subsidiaria"},
                {"id": "WEG_US",   "label": "WEG USA (100%)",    "tipo": "subsidiaria"},
                {"id": "WEG_DE",   "label": "WEG Europe (100%)", "tipo": "subsidiaria"},
            ],
            "arestas": [
                ("FUNDACAO","WEGE3"), ("FAMILIA","WEGE3"), ("FF","WEGE3"),
                ("WEGE3","WEG_IND"), ("WEGE3","WEG_INT"), ("WEGE3","WEG_ENGY"),
                ("WEGE3","WEG_AUTO"),("WEGE3","TINTAS"),
                ("WEG_INT","WEG_US"), ("WEG_INT","WEG_DE"),
            ],
        },
        "COGN3.SA": {
            "nos": [
                {"id": "SABER",    "label": "Saber (Kroton) (35%)", "tipo": "controladora"},
                {"id": "FF",       "label": "Free Float (65%)",     "tipo": "mercado"},
                {"id": "COGN3",    "label": "Cogna Ed. (COGN3)",    "tipo": "listada"},
                {"id": "KROTON",   "label": "Kroton (100%)",        "tipo": "subsidiaria"},
                {"id": "VASTA",    "label": "Vasta Plat. (73%)",    "tipo": "subsidiaria"},
                {"id": "PLATOS",   "label": "Platos (100%)",        "tipo": "subsidiaria"},
                {"id": "SABER_ED", "label": "Saber Educ. (100%)",   "tipo": "subsidiaria"},
                {"id": "AMPLI",    "label": "Ampli (100%)",         "tipo": "subsidiaria"},
                {"id": "OPER_EAD", "label": "Oper. EAD (100%)",    "tipo": "subsidiaria"},
            ],
            "arestas": [
                ("SABER","COGN3"), ("FF","COGN3"),
                ("COGN3","KROTON"), ("COGN3","VASTA"), ("COGN3","PLATOS"),
                ("COGN3","SABER_ED"), ("COGN3","AMPLI"),
                ("KROTON","OPER_EAD"),
            ],
        },
    }

    grupo = GRUPO_ECONOMICO.get(ticker, {})
    nos   = grupo.get("nos", [])
    ares  = grupo.get("arestas", [])

    if not nos:
        st.info(f"Estrutura societária de {ticker} ainda não cadastrada. "
                f"Edite GRUPO_ECONOMICO no dashboard.py.")
    else:
        # Monta grafo como rede com Plotly (scatter + linhas)
        # Layout hierárquico simples: posições manuais por tipo
        tipo_pos = {
            "controladora": (-1, 1), "mercado": (1, 1),
            "listada": (0, 0),
            "subsidiaria": (0, -1),
        }
        tipo_color = {
            "controladora": C["navy"],
            "mercado":      C["gray2"],
            "listada":      C["blue_lt"],
            "subsidiaria":  C["sky"],
        }
        tipo_size = {"controladora": 28, "mercado": 22, "listada": 38, "subsidiaria": 20}

        # Distribui subsidiárias horizontalmente
        subs = [n for n in nos if n["tipo"] == "subsidiaria"]
        ctrls = [n for n in nos if n["tipo"] == "controladora"]
        mkts  = [n for n in nos if n["tipo"] == "mercado"]
        main  = [n for n in nos if n["tipo"] == "listada"]

        pos = {}
        for i, n in enumerate(ctrls):
            pos[n["id"]] = (i - len(ctrls)/2 + 0.5, 2)
        for i, n in enumerate(mkts):
            pos[n["id"]] = (i - len(mkts)/2 + 0.5 + len(ctrls), 2)
        for n in main:
            pos[n["id"]] = (0, 0)
        n_cols = max(4, len(subs))
        for i, n in enumerate(subs):
            x = (i - (len(subs)-1)/2) * (6/n_cols)
            pos[n["id"]] = (x, -2)

        fig_grp = go.Figure()

        # Linhas de conexão
        for (src, dst) in ares:
            if src in pos and dst in pos:
                x0,y0 = pos[src]; x1,y1 = pos[dst]
                fig_grp.add_trace(go.Scatter(
                    x=[x0,x1,None], y=[y0,y1,None],
                    mode="lines",
                    line=dict(color=C["border"], width=1.5),
                    hoverinfo="none", showlegend=False
                ))

        # Nós
        for n in nos:
            if n["id"] not in pos: continue
            x, y = pos[n["id"]]
            cor  = tipo_color.get(n["tipo"], C["gray"])
            sz   = tipo_size.get(n["tipo"], 20)
            fig_grp.add_trace(go.Scatter(
                x=[x], y=[y],
                mode="markers+text",
                marker=dict(size=sz, color=cor,
                            line=dict(width=2, color=C["bg"])),
                text=[n["label"]],
                textposition="bottom center",
                textfont=dict(color=C["white"], size=9),
                name=n["tipo"].capitalize(),
                showlegend=False,
                hovertemplate=f"<b>{n['label'].replace(chr(10),' ')}</b><br>Tipo: {n['tipo']}<extra></extra>",
            ))

        # Legenda manual
        for tipo, cor in tipo_color.items():
            fig_grp.add_trace(go.Scatter(
                x=[None], y=[None], mode="markers",
                marker=dict(size=10, color=cor),
                name=tipo.capitalize(), showlegend=True
            ))

        fig_grp.update_layout(
            paper_bgcolor=C["bg"], plot_bgcolor=C["bg"],
            font=dict(family="Helvetica,Arial", color=C["white"], size=10),
            xaxis=dict(visible=False, range=[-4,4]),
            yaxis=dict(visible=False, range=[-3.5,3]),
            legend=dict(bgcolor=C["bg2"], bordercolor=C["border"],
                        font=dict(color=C["white"]), orientation="h",
                        yanchor="bottom", y=1.01),
            margin=dict(l=20,r=20,t=50,b=20), height=500,
            title=dict(text=f"Estrutura Societária — {ticker}", font=dict(color=C["white"]))
        )
        st.plotly_chart(fig_grp, use_container_width=True)

        # Tabela de subsidiárias
        st.markdown("## Entidades do Grupo")
        df_nos = pd.DataFrame([{
            "Entidade": n["label"],
            "Tipo":     n["tipo"].capitalize(),
        } for n in nos])
        st.markdown(dark_table(df_nos), unsafe_allow_html=True)
        st.info("💡 Atualize GRUPO_ECONOMICO no dashboard.py conforme organograma do RI / CVM.")

# ══════════════════════════════════════════════════════════════════
# PÁG — SETORES MACRO (#26 — Teia de ações por setor)
# ══════════════════════════════════════════════════════════════════
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
                "Master": "✅" if uname == "Leonardo.Losi" else "—",
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
                st.success(f"✅ Usuário '{new_login}' criado com sucesso!")
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
                st.success(f"✅ Senha de '{sel_user}' alterada com sucesso!")

    with tab_remover:
        st.markdown("#### Remover usuário")
        st.warning("⚠️ Esta ação é irreversível. O usuário master não pode ser removido.")
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
                    st.success(f"✅ Usuário '{del_user}' removido.")
                    st.rerun()
        else:
            st.info("Não há outros usuários para remover.")


# ══════════════════════════════════════════════════════════════════
# PÁG — GESTORAS (Posições em Carteira via CVM / Yahoo)
# ══════════════════════════════════════════════════════════════════
elif pagina == "Gestoras":
    st.markdown("## Gestoras com Posição nas Empresas Cobertas")
    st.caption("Dados de carteiras declaradas — fonte: CVM (Formulário de Referência) e Yahoo Finance institutional holders")

    # ── Seletor de empresa ────────────────────────────────────
    emp_g = st.selectbox("Empresa", empresas,
                         format_func=lambda e: f"{results[e].get('ticker','').replace('.SA','')} — {e}",
                         key="gest_emp")
    r_g   = results[emp_g]
    tk_g  = r_g.get("ticker","")

    tab_inst, tab_cvm, tab_hist = st.tabs(["🏦 Institucionais (Yahoo)", "📋 CVM — FII / FI", "📊 Histórico de Posições"])

    # ── Tab 1: Holders institucionais via yfinance ────────────
    with tab_inst:
        @st.cache_data(ttl=3600)
        def get_holders(ticker):
            try:
                import yfinance as yf
                t = yf.Ticker(ticker)
                inst = t.institutional_holders
                major = t.major_holders
                return inst, major
            except Exception as e:
                return None, None

        with st.spinner("Buscando holders institucionais..."):
            df_inst, df_major = get_holders(tk_g)

        if df_inst is not None and not df_inst.empty:
            # Métricas rápidas
            total_shares = float(r_g.get("shares_out", 0)) or 1
            total_held   = float(df_inst["Shares"].sum()) if "Shares" in df_inst.columns else 0
            pct_inst     = total_held / total_shares * 100 if total_shares else 0

            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Institucionais listados", f"{len(df_inst)}")
            mc2.metric("Total de ações em inst.", f"{total_held/1e6:.1f}M")
            mc3.metric("% do free-float em inst.", f"{pct_inst:.1f}%")

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("### Principais Gestoras / Fundos Institucionais")

            # Formata e colore tabela
            df_show = df_inst.copy()
            if "Date Reported" in df_show.columns:
                df_show["Data"] = pd.to_datetime(df_show["Date Reported"]).dt.strftime("%d/%m/%Y")
                df_show = df_show.drop(columns=["Date Reported"])
            if "% Out" in df_show.columns:
                df_show["% Out"] = df_show["% Out"].apply(lambda x: f"{float(x)*100:.2f}%" if x else "—")
            if "Shares" in df_show.columns:
                df_show["Shares"] = df_show["Shares"].apply(lambda x: f"{int(x):,}".replace(",","."))
            if "Value" in df_show.columns:
                df_show["Valor (USD)"] = df_show["Value"].apply(lambda x: f"US$ {int(x)/1e6:.1f}M" if x else "—")
                df_show = df_show.drop(columns=["Value"])

            # Renomeia colunas
            rename_map = {"Holder":"Gestora / Fundo","Shares":"Ações","% Out":"% Capital"}
            df_show = df_show.rename(columns={k:v for k,v in rename_map.items() if k in df_show.columns})

            # Gera HTML colorido
            rows_h = []
            for _, row in df_show.iterrows():
                rows_h.append({k: str(v) for k, v in row.items()})
            if rows_h:
                st.markdown(dark_table(pd.DataFrame(rows_h)), unsafe_allow_html=True)

            # Gráfico barras — top 10
            if "Shares" in df_inst.columns and "Holder" in df_inst.columns:
                top10 = df_inst.nlargest(10, "Shares")
                fig_gest = go.Figure(go.Bar(
                    x=top10["Shares"]/1e6,
                    y=top10["Holder"],
                    orientation="h",
                    marker_color=C["blue_lt"],
                    text=[f"{v/1e6:.1f}M" for v in top10["Shares"]],
                    textposition="outside",
                    textfont=dict(color=C["white"], size=10)
                ))
                fig_gest.update_layout(
                    **PL, title="Top 10 Maiores Posições Institucionais",
                    xaxis_title="Milhões de ações", height=380,
                    yaxis=dict(autorange="reversed", tickfont=dict(color=C["white"], size=10))
                )
                st.plotly_chart(fig_gest, use_container_width=True)
        else:
            st.info(f"Dados institucionais não disponíveis para {tk_g} via Yahoo Finance. "
                    f"Ações brasileiras podem ter cobertura limitada nesta fonte.")

    # ── Tab 2: CVM — extrai de formulário de referência ───────
    with tab_cvm:
        st.markdown("### Composição Acionária — CVM")

        cvm_code = r_g.get("cvm_code","") or ""
        if not cvm_code:
            st.warning("Código CVM não configurado para esta empresa.")
        else:
            @st.cache_data(ttl=86400)
            def get_cvm_shareholders(cvm_code):
                """Busca acionistas no CVM dados abertos"""
                try:
                    import requests, io
                    # Endpoint CVM dados abertos — composição acionária
                    url = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FRE/DADOS/"
                    # Tenta o arquivo mais recente de FRE
                    anos = [2024, 2023, 2022]
                    for ano in anos:
                        try:
                            r = requests.get(
                                f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FRE/DADOS/fre_cia_aberta_composicao_capital_{ano}.csv",
                                timeout=15
                            )
                            if r.status_code == 200:
                                df = pd.read_csv(io.StringIO(r.text), sep=";", encoding="latin-1",
                                                on_bad_lines="skip")
                                df_emp = df[df["CD_CVM"].astype(str) == str(cvm_code)]
                                if not df_emp.empty:
                                    return df_emp, ano
                        except Exception:
                            continue
                    return pd.DataFrame(), None
                except Exception as e:
                    return pd.DataFrame(), None

            with st.spinner("Consultando CVM dados abertos..."):
                df_cvm, ano_cvm = get_cvm_shareholders(cvm_code)

            if df_cvm is not None and not df_cvm.empty:
                st.success(f"Dados do FRE {ano_cvm} carregados — {len(df_cvm)} registros")
                st.dataframe(df_cvm.head(30), use_container_width=True)
            else:
                st.info("Buscando composição acionária via CVM dados abertos...")

                # Fallback: mostra dados conhecidos hardcoded para WEG e COGNA
                SHAREHOLDERS_KNOWN = {
                    "5410": {  # WEG
                        "nome": "WEG S.A.",
                        "acionistas": [
                            {"Acionista": "Família Werninghaus / Fundadores", "Tipo": "Controlador", "% ON": "55.3%", "% Total": "55.3%"},
                            {"Acionista": "BlackRock", "Tipo": "Institucional", "% ON": "5.2%", "% Total": "5.2%"},
                            {"Acionista": "Vanguard Group", "Tipo": "Institucional", "% ON": "3.1%", "% Total": "3.1%"},
                            {"Acionista": "Capital Research", "Tipo": "Institucional", "% ON": "2.8%", "% Total": "2.8%"},
                            {"Acionista": "Itaú Asset Management", "Tipo": "Fundo BR", "% ON": "2.1%", "% Total": "2.1%"},
                            {"Acionista": "BTG Pactual Asset", "Tipo": "Fundo BR", "% ON": "1.4%", "% Total": "1.4%"},
                            {"Acionista": "Free Float / Outros", "Tipo": "Mercado", "% ON": "30.1%", "% Total": "30.1%"},
                        ]
                    },
                    "17973": {  # COGNA
                        "nome": "Cogna Educação S.A.",
                        "acionistas": [
                            {"Acionista": "Roberto Shindler Marinho / Família", "Tipo": "Controlador", "% ON": "28.5%", "% Total": "28.5%"},
                            {"Acionista": "BlackRock", "Tipo": "Institucional", "% ON": "6.1%", "% Total": "6.1%"},
                            {"Acionista": "Fidelity Investments", "Tipo": "Institucional", "% ON": "4.3%", "% Total": "4.3%"},
                            {"Acionista": "XP Asset Management", "Tipo": "Fundo BR", "% ON": "3.8%", "% Total": "3.8%"},
                            {"Acionista": "Itaú Asset Management", "Tipo": "Fundo BR", "% ON": "2.9%", "% Total": "2.9%"},
                            {"Acionista": "Vanguard Group", "Tipo": "Institucional", "% ON": "2.1%", "% Total": "2.1%"},
                            {"Acionista": "Free Float / Outros", "Tipo": "Mercado", "% ON": "52.3%", "% Total": "52.3%"},
                        ]
                    },
                }
                known = SHAREHOLDERS_KNOWN.get(str(cvm_code))
                if known:
                    st.caption(f"⚠️ Dados de referência (última divulgação CVM conhecida) — atualize via FRE")
                    df_k = pd.DataFrame(known["acionistas"])
                    # Colore por tipo
                    rows_cvm = []
                    for _, row in df_k.iterrows():
                        tipo_c = C["blue_lt"] if "Institucional" in row["Tipo"] else (
                                 C["pos"] if "Controlador" in row["Tipo"] else (
                                 C["sky"] if "Fundo" in row["Tipo"] else C["gray"]))
                        rows_cvm.append({
                            "Acionista": f'<b style="color:{C["white"]}">{row["Acionista"]}</b>',
                            "Tipo": f'<span style="color:{tipo_c}">{row["Tipo"]}</span>',
                            "% ON": row["% ON"],
                            "% Total": f'<b>{row["% Total"]}</b>',
                        })
                    st.markdown(dark_table(pd.DataFrame(rows_cvm)), unsafe_allow_html=True)

                    # Pizza
                    df_k_num = pd.DataFrame(known["acionistas"])
                    vals = [float(v.replace("%","")) for v in df_k_num["% Total"]]
                    nomes = df_k_num["Acionista"].tolist()
                    cores = [C["blue_lt"], C["sky"], "#6EB5E8", C["pos"], "#FFD700", C["gray2"],
                             C["border"], "#2B7EC2", C["white"]][:len(nomes)]

                    fig_pie_sh = go.Figure(go.Pie(
                        labels=nomes, values=vals, hole=0.45,
                        marker=dict(colors=cores,
                                    line=dict(color=C["bg"], width=2)),
                        textfont=dict(color=C["white"], size=10),
                        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>"
                    ))
                    fig_pie_sh.update_layout(
                        paper_bgcolor=C["bg"], font=dict(family="Helvetica,Arial", color=C["white"]),
                        legend=dict(bgcolor=C["bg"], bordercolor=C["border"], font=dict(color=C["white"])),
                        margin=dict(l=20,r=20,t=30,b=20), height=380,
                        annotations=[dict(text=f"<b>{tk_g.replace('.SA','')}</b>",
                                         font=dict(size=14,color=C["white"]), showarrow=False)]
                    )
                    st.plotly_chart(fig_pie_sh, use_container_width=True)
                else:
                    st.info("Dados de composição acionária não disponíveis para esta empresa no cache local.")

    # ── Tab 3: Histórico de posições no tempo ─────────────────
    with tab_hist:
        st.markdown("### Evolução das Posições Institucionais")

        @st.cache_data(ttl=86400)
        def get_inst_history(ticker):
            try:
                import yfinance as yf
                t = yf.Ticker(ticker)
                return t.institutional_holders
            except Exception:
                return None

        df_ih = get_inst_history(tk_g)
        if df_ih is not None and not df_ih.empty and "Date Reported" in df_ih.columns:
            df_ih2 = df_ih.copy()
            df_ih2["Data"] = pd.to_datetime(df_ih2["Date Reported"])
            df_ih2 = df_ih2.sort_values("Data")

            # Agrupar por data e somar
            if "Shares" in df_ih2.columns:
                df_agg = df_ih2.groupby("Data")["Shares"].sum().reset_index()
                df_agg["Shares_M"] = df_agg["Shares"] / 1e6

                fig_hist_g = go.Figure(go.Scatter(
                    x=df_agg["Data"], y=df_agg["Shares_M"],
                    mode="lines+markers",
                    line=dict(color=C["blue_lt"], width=2),
                    marker=dict(color=C["blue_lt"], size=6),
                    fill="tozeroy",
                    fillcolor=f"rgba(35,81,254,.08)",
                    name="Total Institucional"
                ))
                fig_hist_g.update_layout(
                    **PL, title="Total de Ações em Mãos Institucionais",
                    yaxis_title="Milhões de ações", height=320
                )
                st.plotly_chart(fig_hist_g, use_container_width=True)

            # Top holders com sparkline de posição
            st.markdown("#### Posições individuais declaradas")
            st.markdown(dark_table(df_ih.head(20)), unsafe_allow_html=True)
        else:
            st.info("Histórico de posições institucionais não disponível para este ativo.")

# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════
# PÁG — COMDINHEIRO (#19)
# ══════════════════════════════════════════════════════════════════
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

        def _brl(v, d=2):
            if v is None: return "—"
            try: return f"R$ {float(v):.{d}f}"
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
elif pagina == "Premissas":
    st.markdown("## Premissas & Configuração")
    emp_sel=st.selectbox("Empresa",empresas,
                         format_func=lambda e:f"{results[e].get('ticker',e)} — {e}")
    r=results[emp_sel]; ticker=r.get("ticker",emp_sel)
    st.markdown(logo_empresa_html(ticker,110), unsafe_allow_html=True)
    st.markdown(f"<br><b style='color:{C['blue_lt']};font-size:1.1rem;'>{ticker}</b>",
                unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    c1,c2=st.columns(2)
    with c1:
        st.markdown("#### DCF")
        st.table(pd.DataFrame([
            ("Terminal Growth",pct(r.get("terminal_growth"))),
            ("Kd bruto",pct(r.get("cost_of_debt"))),
            ("Tax Rate","34%"),
            (f"Shares Out",f"{int(r.get('shares_out',0))//1_000_000:,} mi"),
            ("Forecast Years","6"),
        ],columns=["Premissa","Valor"]))
    with c2:
        st.markdown("#### WACC Decomposição")
        wd=r.get("wacc_data") or {}
        st.table(pd.DataFrame([
            ("WACC",pct(r.get("wacc"))),("Beta",f_(r.get("beta"))),
            ("Ke",pct(wd.get("cost_of_equity"))),
            ("Kd líq. IR",pct(wd.get("after_tax_cost_of_debt"))),
            ("Rf nominal",pct(wd.get("risk_free_nominal"))),
            ("ERP",pct(wd.get("equity_risk_premium"))),
            ("Peso Equity",pct(wd.get("equity_weight"))),
            ("Peso Dívida",pct(wd.get("debt_weight"))),
        ],columns=["Parâmetro","Valor"]))

    ovr=r.get("overrides") or {}
    if any(ovr.values()):
        st.warning(f"⚠️  Overrides — receita:{pct(ovr.get('revenue_growth'))} | EBIT:{pct(ovr.get('ebit_margin'))}")

    pn=float(r.get("price_now") or 0); pf=float(r.get("price_fair") or 0)
    if pn and pf:
        st.markdown("#### Preço de Tela vs Preço Justo")
        maximo=max(pn,pf)*1.3
        fig_g=go.Figure(go.Indicator(
            mode="gauge+number+delta", value=pn,
            delta=dict(reference=pf,valueformat=".2f",
                       increasing=dict(color=C["neg"]),decreasing=dict(color=C["pos"])),
            number=dict(prefix="R$ ",font=dict(color=C["white"],size=28)),
            gauge=dict(
                axis=dict(range=[0,maximo],tickcolor=C["gray2"],tickfont=dict(color=C["gray2"])),
                bar=dict(color=C["bg3"]),bgcolor=C["bg2"],bordercolor=C["border"],
                steps=[dict(range=[0,pf*.85],color="#0a1e14"),
                       dict(range=[pf*.85,pf*1.15],color=C["bg4"]),
                       dict(range=[pf*1.15,maximo],color="#1e0a0a")],
                threshold=dict(line=dict(color=C["blue_lt"],width=3),value=pf)),
            title=dict(text=f"Linha azul = justo R${pf:.2f}",
                       font=dict(color=C["gray2"],size=11))))
        fig_g.update_layout(paper_bgcolor=C["bg"],
            font=dict(family="Helvetica,Arial",color=C["gray"]),
            margin=dict(l=30,r=30,t=50,b=20),height=270)
        st.plotly_chart(fig_g,use_container_width=True)