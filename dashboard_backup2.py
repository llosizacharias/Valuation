import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json, math, base64, io
from pathlib import Path
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

st.set_page_config(
    page_title="Shipyard | Vela Capital",
    page_icon="⛵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── PALETA VELA CAPITAL ───────────────────────────────────────────
C = {
    "bg":      "#0D1520", "bg2":    "#0F1E30", "bg3":    "#0F558B",
    "bg4":     "#0a1624", "border": "#1a3a5c", "white":  "#E8EFF7",
    "gray":    "#7A9BBF", "gray2":  "#4a6a8f", "blue_lt":"#5EC8A0",
    "pos":     "#5EC8A0", "neg":    "#E05555",
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
    "WEGE3.SA": _svg_logo("WEG",   C["bg3"], C["white"]),
    "COGN3.SA": _svg_logo("COGNA", C["bg4"], C["blue_lt"]),
    "VALE3.SA": _svg_logo("VALE",  C["bg4"], C["gray"]),
    "ITUB4.SA": _svg_logo("ITUB",  C["bg3"], C["white"]),
    "RENT3.SA": _svg_logo("RENT3", C["bg2"], C["blue_lt"]),
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
.stSelectbox>div>div {{ background:{C['bg2']}; border:1px solid {C['border']}; color:{C['white']}; border-radius:5px; }}
.stDataFrame {{ border:1px solid {C['border']}; border-radius:6px; overflow:hidden; }}
thead tr th {{ background:{C['bg4']} !important; color:{C['blue_lt']} !important; font-size:.72rem !important; text-transform:uppercase; }}
tbody tr:nth-child(even) {{ background:rgba(15,85,139,.07) !important; }}
tbody tr:hover {{ background:rgba(154,192,230,.07) !important; }}
.badge-c {{ background:#0a2e1a;color:#5EC8A0;border:1px solid #5EC8A0;border-radius:4px;padding:3px 12px;font-weight:700;font-size:.8rem;display:inline-block; }}
.badge-n {{ background:#1a1a0d;color:{C['gray']};border:1px solid {C['gray']};border-radius:4px;padding:3px 12px;font-weight:700;font-size:.8rem;display:inline-block; }}
.badge-v {{ background:#2a1010;color:{C['neg']};border:1px solid {C['neg']};border-radius:4px;padding:3px 12px;font-weight:700;font-size:.8rem;display:inline-block; }}
.emp-card {{ background:{C['bg2']};border:1px solid {C['border']};border-radius:8px;padding:18px;margin-bottom:10px; }}
.news-card {{ background:{C['bg2']};border:1px solid {C['border']};border-radius:8px;padding:14px 18px;margin-bottom:10px; }}
hr {{ border-color:{C['border']} !important; margin:10px 0 !important; }}
button[kind="secondary"] {{ background:{C['bg2']} !important; color:{C['gray']} !important; border:1px solid {C['border']} !important; }}
.sidebar-footer {{ position:fixed;bottom:18px;left:0;width:238px;text-align:center;font-size:.62rem;color:{C['gray2']};opacity:.4; }}
</style>""", unsafe_allow_html=True)

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
    st.markdown(f"""
    <div style="text-align:center;margin:80px auto;padding:40px;background:{C['bg2']};
                border:1px solid {C['border']};border-radius:10px;max-width:400px;">
        <div style="color:{C['blue_lt']};font-size:2rem;font-weight:700;letter-spacing:.1em;">⛵ VELA CAPITAL</div>
        <div style="color:{C['gray2']};font-size:.78rem;letter-spacing:.2em;text-transform:uppercase;margin-top:8px;">
            SHIPYARD — Análise Fundamentalista</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── DADOS ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_results():
    p = Path("valuation_results.json")
    if not p.exists(): return {}
    with open(p) as f: return json.load(f)

results = load_results()
if not results:
    st.error("⚠️ valuation_results.json não encontrado. Execute: python main.py"); st.stop()

# ── SIDEBAR ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;padding:20px 0 10px;">
        <div style="color:{C['blue_lt']};font-size:1.1rem;font-weight:700;letter-spacing:.15em;">⛵ VELA CAPITAL</div>
        <div style="color:{C['gray2']};font-size:.6rem;letter-spacing:.2em;margin-top:4px;opacity:.7;">SHIPYARD</div>
    </div><hr>""", unsafe_allow_html=True)

    pagina = st.selectbox("nav", [
        "🏠  Visão Geral", "🔍  Empresa", "📊  Cotações",
        "📈  FCFF & Projeções", "🔀  Comparativo",
        "📉  Sensibilidade", "📐  Markowitz",
        "📰  Notícias", "⚙️  Premissas"
    ], label_visibility="collapsed")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:{C['gray2']};font-size:.72rem;padding:4px 0;'>👤 {name}</div>", unsafe_allow_html=True)
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

# ══════════════════════════════════════════════════════════════════
# PÁG 1 — VISÃO GERAL
# ══════════════════════════════════════════════════════════════════
if pagina == "🏠  Visão Geral":
    st.markdown("## Visão Geral da Cobertura")

    cols = st.columns(len(empresas))
    for i, emp in enumerate(empresas):
        r = results[emp]; ticker = r.get("ticker", emp); upside = r.get("upside") or 0
        with cols[i]:
            st.markdown(f"""<div class="emp-card">
                {logo_empresa_html(ticker,100)}<br>
                <span style="color:{C['blue_lt']};font-weight:700;font-size:1.0rem;">{ticker}</span>
            </div>""", unsafe_allow_html=True)
            st.metric("Preço Tela",   price(r.get("price_now")))
            st.metric("Preço Justo",  price(r.get("price_fair")),
                      delta=f"{upside*100:+.1f}%", delta_color="normal" if upside>0 else "inverse")
            st.metric("EV",           bi(r.get("enterprise_value")))
            st.metric("Equity Value", bi(r.get("equity_value")))
            st.metric("Net Debt",     bi(r.get("net_debt")))
            st.metric("WACC",         pct(r.get("wacc")))
            st.metric("Beta",         f_(r.get("beta")))
            st.markdown(badge(r.get("recomendacao","")), unsafe_allow_html=True)

    # Sparklines de cotação
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## Cotações Recentes (6 meses)")
    spark_cols = st.columns(len(empresas))
    for i, emp in enumerate(empresas):
        r = results[emp]; ticker = r.get("ticker", emp)
        with spark_cols[i]:
            df_p = get_price_history(ticker, "6mo")
            if not df_p.empty:
                closes = df_p["Close"].squeeze()
                pct_chg = (closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0] * 100
                color = C["pos"] if pct_chg >= 0 else C["neg"]
                fig_sp = go.Figure()
                fig_sp.add_trace(go.Scatter(
                    x=closes.index, y=closes.values,
                    mode="lines", line=dict(color=color, width=1.5),
                    fill="tozeroy", fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},.08)"
                ))
                fig_sp.update_layout(
                    paper_bgcolor=C["bg2"], plot_bgcolor=C["bg2"],
                    margin=dict(l=0,r=0,t=5,b=0), height=80,
                    xaxis=dict(visible=False), yaxis=dict(visible=False),
                    showlegend=False
                )
                st.plotly_chart(fig_sp, use_container_width=True)
                st.markdown(f"<div style='text-align:center;color:{color};font-size:.82rem;font-weight:700;'>{pct_chg:+.1f}% (6m)</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:{C['gray2']};font-size:.8rem;text-align:center;'>Sem dados</div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("## EV · Equity DCF · Market Cap")
    fig = go.Figure()
    for emp in empresas:
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
    cats = ["Margem EBIT","ROIC","ROE","FCF Yield","CAGR Receita"]
    fig_r = go.Figure()
    clrs = [C["blue_lt"], C["gray"]]
    for i,emp in enumerate(empresas):
        r=results[emp]; ticker=r.get("ticker",emp)
        vals=[min(abs(float(r.get(k) or 0))*100,lim) for k,lim in
              [("ebit_margin",40),("roic",40),("roe",60),("fcf_yield",30),("cagr_revenue",35)]]
        clr=clrs[i%2]; rv,gv,bv=int(clr[1:3],16),int(clr[3:5],16),int(clr[5:7],16)
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
    st.plotly_chart(fig_r, use_container_width=True)

    st.markdown("## Múltiplos Comparativos")
    rows=[]
    for emp in empresas:
        r=results[emp]
        rows.append({"Ticker":r.get("ticker",emp),"Preço Tela":price(r.get("price_now")),
            "Preço Justo":price(r.get("price_fair")),
            "Upside":f"{(r.get('upside') or 0)*100:+.1f}%",
            "EV":bi(r.get("enterprise_value")),"Net Debt":bi(r.get("net_debt")),
            "WACC":pct(r.get("wacc")),"Beta":f_(r.get("beta")),
            "EV/EBITDA":f"{float(r.get('ev_ebitda') or 0):.1f}x" if r.get("ev_ebitda") else "n/d",
            "EV/EBIT":f"{float(r.get('ev_ebit') or 0):.1f}x" if r.get("ev_ebit") else "n/d",
            "P/E":f"{float(r.get('pe') or 0):.1f}x" if r.get("pe") else "n/d",
            "ROIC":pct(r.get("roic")),"ROE":pct(r.get("roe")),
            "Rec.":r.get("recomendacao","—")})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════
# PÁG 2 — EMPRESA
# ══════════════════════════════════════════════════════════════════
elif pagina == "🔍  Empresa":
    emp_sel = st.selectbox("Empresa", empresas,
                           format_func=lambda e: f"{results[e].get('ticker',e)} — {e}")
    r=results[emp_sel]; ticker=r.get("ticker",emp_sel); upside=r.get("upside") or 0

    cl,cr=st.columns([1,5])
    with cl: st.markdown(logo_empresa_html(ticker,120), unsafe_allow_html=True)
    with cr:
        st.markdown(f"""
        <div style="margin-top:8px;">
            <span style="color:{C['blue_lt']};font-size:1.15rem;font-weight:700;">{ticker}</span>
            &nbsp;&nbsp;{badge(r.get('recomendacao',''))}
        </div>
        <div style="color:{C['gray2']};font-size:.8rem;margin-top:6px;">
            Preço tela: <b style="color:{C['white']};">{price(r.get('price_now'))}</b>
            &nbsp;|&nbsp; Preço justo: <b style="color:{C['blue_lt']};">{price(r.get('price_fair'))}</b>
            &nbsp;|&nbsp; Upside: <b style="color:{C['pos'] if upside>0 else C['neg']};">{upside*100:+.1f}%</b>
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
        fig_vol.update_layout(**PL, title="Volume", height=160,
                               yaxis_title="Volume", margin=dict(l=45,r=25,t=25,b=30))
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
        st.dataframe(pd.DataFrame(dre_rows), use_container_width=True, hide_index=True)

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
            st.caption("Para DRE completa, atualize main.py para exportar historical_data.")

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
            st.info("Execute python main.py para atualizar dados DCF.")

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

# ══════════════════════════════════════════════════════════════════
# PÁG 3 — COTAÇÕES
# ══════════════════════════════════════════════════════════════════
elif pagina == "📊  Cotações":
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
        per_cot = st.selectbox("Período", ["5d","1mo","3mo","6mo","1y","2y","5y"], index=4)
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
            fig_v2.update_layout(**PL, title="Volume", height=150,
                                  margin=dict(l=45,r=25,t=25,b=30), yaxis_title="Volume")
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
elif pagina == "📈  FCFF & Projeções":
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
        st.dataframe(df_fcff,use_container_width=True,hide_index=True)
    else:
        st.info("FCFF série não disponível. Execute: python main.py")

# ══════════════════════════════════════════════════════════════════
# PÁG 5 — COMPARATIVO
# ══════════════════════════════════════════════════════════════════
elif pagina == "🔀  Comparativo":
    st.markdown("## Comparativo entre Empresas")

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
elif pagina == "📉  Sensibilidade":
    st.markdown("## Sensibilidade: Preço Justo × WACC × Terminal Growth")
    emp_sel=st.selectbox("Empresa",empresas,
                         format_func=lambda e:f"{results[e].get('ticker',e)} — {e}")
    r=results[emp_sel]; ticker=r.get("ticker",emp_sel)
    ev_base=float(r.get("enterprise_value") or 0); nd_base=float(r.get("net_debt") or 0)
    shares=float(r.get("shares_out") or 1)
    pv_fcfs=float(r.get("dcf_pv_fcf") or ev_base*.48)
    fcff_l=float(r.get("fcff_last_proj") or ev_base*.06)
    price_now=float(r.get("price_now") or 0)

    waccs=[w/100 for w in range(13,22)]; growths=[g/100 for g in range(20,55,5)]
    matrix=[]
    for g in growths:
        row=[]
        for w in waccs:
            if w<=g: row.append(None); continue
            tv=fcff_l*(1+g)/(w-g); pv_tv=tv/(1+w)**6
            row.append(round(((pv_fcfs+pv_tv)-nd_base)/shares,2))
        matrix.append(row)
    df_s=pd.DataFrame(matrix,index=[f"{g*100:.1f}%" for g in growths],
                      columns=[f"{w*100:.1f}%" for w in waccs])

    st.markdown("### Heatmap: Preço Justo (R$/ação)")
    fig_h=go.Figure(go.Heatmap(
        z=df_s.values.tolist(), x=df_s.columns.tolist(), y=df_s.index.tolist(),
        colorscale=[[0,"#2d0000"],[.3,C["neg"]],[.48,C["bg4"]],[.52,C["bg4"]],
                    [.7,C["bg3"]],[1,C["pos"]]],
        text=[[f"R${v:.2f}" if v else "" for v in row] for row in df_s.values.tolist()],
        texttemplate="%{text}", textfont=dict(size=9,color=C["white"]),
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
        colorscale=[[0,"#2d0000"],[.35,C["neg"]],[.5,C["bg3"]],[.65,C["blue_lt"]],[1,C["pos"]]],
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
    st.dataframe(df_s.style.applymap(_c).format("{:.2f}",na_rep="—"),use_container_width=True)

# ══════════════════════════════════════════════════════════════════
# PÁG 7 — MARKOWITZ (com benchmark IBOV)
# ══════════════════════════════════════════════════════════════════
elif pagina == "📐  Markowitz":
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
                    st.dataframe(df_w, use_container_width=True, hide_index=True)
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
                st.dataframe(compare_df, use_container_width=True, hide_index=True)

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
                    colorscale=[[0,C["neg"]],[0.5,C["bg2"]],[1,C["pos"]]],
                    zmin=-1, zmax=1,
                    text=[[f"{v:.2f}" for v in row] for row in corr.values],
                    texttemplate="%{text}", textfont=dict(size=10,color=C["white"]),
                    colorbar=dict(tickfont=dict(color=C["gray"]))
                ))
                fig_corr.update_layout(paper_bgcolor=C["bg"],
                    font=dict(family="Helvetica,Arial",color=C["gray"]),
                    margin=dict(l=80,r=30,t=30,b=80), height=350)
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
elif pagina == "📰  Notícias":
    st.markdown("## Monitor de Notícias — Mercado Brasileiro")

    feeds = {
        "InfoMoney — Mercado": "https://www.infomoney.com.br/feed/",
        "InfoMoney — Ações":   "https://www.infomoney.com.br/mercados/acoes/feed/",
        "Valor Econômico":     "https://valor.globo.com/rss/home/",
        "Exame — Investimentos": "https://exame.com/invest/feed/",
    }

    col_f, col_q = st.columns([2,2])
    with col_f:
        fonte = st.selectbox("Fonte de notícias", list(feeds.keys()))
    with col_q:
        query = st.text_input("Filtrar por palavra-chave", placeholder="ex: WEG, COGNA, Selic...")

    n_noticias = st.slider("Número de notícias", 5, 30, 12, 1)

    if st.button("🔄  Carregar Notícias", type="primary") or True:
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
        {"Empresa": "WEG (WEGE3)",   "Evento": "Resultados 1T25",   "Data": "Mai 2025",  "Status": "⏳ Aguardando"},
        {"Empresa": "COGNA (COGN3)", "Evento": "Resultados 1T25",   "Data": "Mai 2025",  "Status": "⏳ Aguardando"},
        {"Empresa": "WEG (WEGE3)",   "Evento": "Dividendos",        "Data": "Ago 2025",  "Status": "📅 Previsto"},
        {"Empresa": "COGNA (COGN3)", "Evento": "Assembleia Geral",  "Data": "Abr 2025",  "Status": "📅 Previsto"},
        {"Empresa": "B3",            "Evento": "Reunião COPOM",     "Data": "Mai 2025",  "Status": "🏦 Macro"},
        {"Empresa": "B3",            "Evento": "IPCA",              "Data": "Todo mês",  "Status": "🏦 Macro"},
    ]
    st.dataframe(pd.DataFrame(cal_data), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════
# PÁG 9 — PREMISSAS
# ══════════════════════════════════════════════════════════════════
elif pagina == "⚙️  Premissas":
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