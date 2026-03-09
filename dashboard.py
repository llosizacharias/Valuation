"""
dashboard.py — Valuation Dashboard
Estilo dark Bloomberg | Autenticação streamlit-authenticator
Uso: streamlit run dashboard.py
"""

import json
import math
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import yaml
import streamlit_authenticator as stauth
from yaml.loader import SafeLoader
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# CONFIG PÁGINA
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Valuation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# CSS DARK BLOOMBERG
# ─────────────────────────────────────────────────────────────
DARK_CSS = """
<style>
    /* Fundo geral */
    .stApp { background-color: #0a0e1a; color: #e0e6f0; }
    [data-testid="stSidebar"] { background-color: #0d1220; border-right: 1px solid #1e2d45; }
    
    /* Cards de métricas */
    [data-testid="metric-container"] {
        background: #0f1929;
        border: 1px solid #1e2d45;
        border-radius: 6px;
        padding: 16px;
    }
    [data-testid="stMetricValue"] { color: #00d4ff; font-size: 1.6rem !important; font-weight: 700; }
    [data-testid="stMetricLabel"] { color: #7a8fa8 !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
    [data-testid="stMetricDelta"] { font-size: 0.85rem !important; }

    /* Títulos */
    h1 { color: #00d4ff !important; font-size: 1.5rem !important; font-weight: 700; letter-spacing: 0.05em; }
    h2 { color: #c8d8e8 !important; font-size: 1.15rem !important; font-weight: 600; border-bottom: 1px solid #1e2d45; padding-bottom: 6px; }
    h3 { color: #7a8fa8 !important; font-size: 0.9rem !important; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em; }

    /* Selectbox e inputs */
    .stSelectbox > div > div { background: #0f1929; border: 1px solid #1e2d45; color: #e0e6f0; }
    .stTextInput > div > div > input { background: #0f1929; border: 1px solid #1e2d45; color: #e0e6f0; }
    
    /* Tabelas */
    .stDataFrame { background: #0f1929; }
    thead tr th { background: #0d1a2d !important; color: #00d4ff !important; font-size: 0.78rem !important; text-transform: uppercase; }
    tbody tr:nth-child(even) { background: #0d1a2d !important; }
    tbody tr:hover { background: #1a2a40 !important; }

    /* Dividers */
    hr { border-color: #1e2d45; }

    /* Tag de recomendação */
    .rec-compra   { background:#0d3320; color:#00e676; border:1px solid #00e676; border-radius:4px; padding:4px 12px; font-weight:700; font-size:0.9rem; }
    .rec-neutro   { background:#2d2a0d; color:#ffd740; border:1px solid #ffd740; border-radius:4px; padding:4px 12px; font-weight:700; font-size:0.9rem; }
    .rec-venda    { background:#2d1a0d; color:#ff9100; border:1px solid #ff9100; border-radius:4px; padding:4px 12px; font-weight:700; font-size:0.9rem; }
    .rec-venda-f  { background:#2d0d0d; color:#ff1744; border:1px solid #ff1744; border-radius:4px; padding:4px 12px; font-weight:700; font-size:0.9rem; }

    /* Sidebar items */
    [data-testid="stSidebarNav"] { padding-top: 1rem; }
    .sidebar-title { color: #00d4ff; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.12em; padding: 0.5rem 1rem; opacity: 0.7; }
    
    /* Botão logout */
    button[kind="secondary"] { background: #1e2d45 !important; color: #c8d8e8 !important; border: 1px solid #2a3f5f !important; }
    
    /* Login form */
    .login-box { max-width: 380px; margin: 80px auto; padding: 40px; background: #0f1929; border: 1px solid #1e2d45; border-radius: 8px; }
</style>
"""
st.markdown(DARK_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# AUTENTICAÇÃO
# ─────────────────────────────────────────────────────────────

def load_auth_config():
    config_path = Path("dashboard_auth.yaml")
    if not config_path.exists():
        st.error("⚠️ Arquivo dashboard_auth.yaml não encontrado. Execute setup_auth.py primeiro.")
        st.stop()
    with open(config_path) as f:
        return yaml.load(f, Loader=SafeLoader)

config = load_auth_config()

# Compatível com streamlit-authenticator 0.2.x e 0.3.x
try:
    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )
    login_result = authenticator.login(location="main")
    if isinstance(login_result, tuple):
        name, auth_status, username = login_result
    else:
        name         = st.session_state.get("name")
        auth_status  = st.session_state.get("authentication_status")
        username     = st.session_state.get("username")
except Exception as e:
    st.error(f"Erro de autenticação: {e}")
    st.info("Tente: pip install streamlit-authenticator==0.2.3")
    st.stop()

if auth_status is False:
    st.error("❌ Usuário ou senha incorretos.")
    st.stop()

if auth_status is None:
    st.markdown("""
    <div style='text-align:center; margin-top:60px;'>
        <div style='color:#00d4ff; font-size:2rem; font-weight:700; letter-spacing:0.1em;'>📊 VALUATION</div>
        <div style='color:#7a8fa8; font-size:0.85rem; margin-top:6px;'>Sistema de Análise Fundamentalista</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────
# DADOS
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_results():
    path = Path("valuation_results.json")
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)

results = load_results()

if not results:
    st.error("⚠️ valuation_results.json não encontrado. Execute python main.py primeiro.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:20px 0 10px;'>
        <div style='color:#00d4ff; font-size:1.1rem; font-weight:700; letter-spacing:0.1em;'>📊 VALUATION</div>
        <div style='color:#7a8fa8; font-size:0.7rem; margin-top:2px;'>ANÁLISE FUNDAMENTALISTA</div>
    </div>
    <hr style='border-color:#1e2d45; margin:0 0 16px;'>
    """, unsafe_allow_html=True)

    pagina = st.selectbox(
        "NAVEGAÇÃO",
        ["🏠 Visão Geral", "🔍 Empresa", "📉 Sensibilidade WACC"],
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border-color:#1e2d45;'>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:#7a8fa8; font-size:0.72rem;'>👤 {name}</div>", unsafe_allow_html=True)
    authenticator.logout("Sair", location="sidebar")

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def fmt_bi(v):
    try: return f"R$ {float(v)/1e9:.1f}bi"
    except: return "n/d"

def fmt_pct(v):
    try: return f"{float(v)*100:.1f}%"
    except: return "n/d"

def fmt_price(v):
    try: return f"R$ {float(v):.2f}"
    except: return "n/d"

def rec_badge(rec):
    rec = str(rec)
    if "COMPRA" in rec and "FORTE" not in rec:
        return f'<span class="rec-compra">🟢 COMPRA</span>'
    elif "NEUTRO" in rec:
        return f'<span class="rec-neutro">🟡 NEUTRO</span>'
    elif "FORTE" in rec:
        return f'<span class="rec-venda-f">🔴 VENDA FORTE</span>'
    elif "VENDA" in rec:
        return f'<span class="rec-venda">🟠 VENDA</span>'
    return f'<span class="rec-neutro">{rec}</span>'

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#0a0e1a",
    plot_bgcolor="#0f1929",
    font=dict(color="#c8d8e8", size=11),
    xaxis=dict(gridcolor="#1e2d45", zerolinecolor="#1e2d45"),
    yaxis=dict(gridcolor="#1e2d45", zerolinecolor="#1e2d45"),
    margin=dict(l=40, r=20, t=40, b=40),
)

# ─────────────────────────────────────────────────────────────
# PÁGINA 1 — VISÃO GERAL
# ─────────────────────────────────────────────────────────────

if pagina == "🏠 Visão Geral":
    st.markdown("## Visão Geral da Cobertura")

    empresas = list(results.keys())

    # Cards por empresa
    cols = st.columns(len(empresas))
    for i, emp in enumerate(empresas):
        r = results[emp]
        upside = r.get("upside") or 0
        delta_color = "normal" if upside > 0 else "inverse"
        with cols[i]:
            st.markdown(f"### {r.get('ticker','')}")
            st.metric("Preço Tela",    fmt_price(r.get("price_now")))
            st.metric("Preço Justo",   fmt_price(r.get("price_fair")),
                      delta=f"{upside*100:+.1f}%", delta_color=delta_color)
            st.metric("Enterprise Value", fmt_bi(r.get("enterprise_value")))
            st.metric("Equity Value",     fmt_bi(r.get("equity_value")))
            st.metric("Net Debt",         fmt_bi(r.get("net_debt")))
            st.metric("WACC",             fmt_pct(r.get("wacc")))
            st.markdown(rec_badge(r.get("recomendacao","")), unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Gráfico comparativo — EV e Equity Value
    st.markdown("## Enterprise Value vs Equity Value")
    fig = go.Figure()
    for emp in empresas:
        r = results[emp]
        ticker = r.get("ticker", emp)
        ev = float(r.get("enterprise_value", 0)) / 1e9
        eq = float(r.get("equity_value", 0)) / 1e9
        nd = float(r.get("net_debt", 0)) / 1e9
        fig.add_trace(go.Bar(name=f"{ticker} EV",     x=[ticker], y=[ev], marker_color="#00d4ff", width=0.25))
        fig.add_trace(go.Bar(name=f"{ticker} Equity", x=[ticker], y=[eq], marker_color="#00e676", width=0.25,
                             base=[0] if eq >= 0 else None))
    fig.update_layout(**PLOTLY_LAYOUT, title="Valores em R$ bilhões", barmode="group",
                      showlegend=True, legend=dict(bgcolor="#0f1929", bordercolor="#1e2d45"))
    st.plotly_chart(fig, use_container_width=True)

    # Tabela comparativa de múltiplos
    st.markdown("## Múltiplos Comparativos")
    rows = []
    for emp in empresas:
        r = results[emp]
        overrides = r.get("overrides", {})
        rows.append({
            "Empresa":      r.get("ticker", emp),
            "Preço Tela":   fmt_price(r.get("price_now")),
            "Preço Justo":  fmt_price(r.get("price_fair")),
            "Upside":       f"{(r.get('upside') or 0)*100:+.1f}%",
            "EV":           fmt_bi(r.get("enterprise_value")),
            "Dívida Líq.":  fmt_bi(r.get("net_debt")),
            "WACC":         fmt_pct(r.get("wacc")),
            "Beta":         f"{float(r.get('beta',0)):.2f}",
            "Overrides":    "✅ Ativos" if any(overrides.values()) else "—",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────
# PÁGINA 2 — EMPRESA
# ─────────────────────────────────────────────────────────────

elif pagina == "🔍 Empresa":
    empresa_sel = st.selectbox("Selecione a empresa", list(results.keys()),
                               format_func=lambda e: f"{results[e].get('ticker',e)} — {e}")
    r = results[empresa_sel]

    ticker = r.get("ticker", empresa_sel)
    upside = r.get("upside") or 0

    st.markdown(f"## {ticker}")
    st.markdown(rec_badge(r.get("recomendacao", "")), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # KPIs linha 1
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Preço Tela",    fmt_price(r.get("price_now")))
    c2.metric("Preço Justo",   fmt_price(r.get("price_fair")),
              delta=f"{upside*100:+.1f}%", delta_color="normal" if upside > 0 else "inverse")
    c3.metric("Market Cap",    fmt_bi(r.get("wacc_data", {}).get("market_cap") if isinstance(r.get("wacc_data"), dict) else r.get("equity_value")))
    c4.metric("Enterprise Value", fmt_bi(r.get("enterprise_value")))
    c5.metric("Equity Value",     fmt_bi(r.get("equity_value")))

    # KPIs linha 2
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Net Debt",  fmt_bi(r.get("net_debt")))
    c2.metric("WACC",      fmt_pct(r.get("wacc")))
    c3.metric("Beta",      f"{float(r.get('beta',0)):.2f}")
    c4.metric("PV FCFs",   fmt_bi(r.get("dcf", {}).get("pv_fcf") if isinstance(r.get("dcf"), dict) else None))
    c5.metric("PV Terminal", fmt_bi(r.get("dcf", {}).get("pv_terminal") if isinstance(r.get("dcf"), dict) else None))

    st.markdown("<hr>", unsafe_allow_html=True)

    # Waterfall EV → Equity
    st.markdown("## Waterfall: EV → Equity Value")
    ev  = float(r.get("enterprise_value", 0)) / 1e9
    nd  = float(r.get("net_debt", 0)) / 1e9
    eq  = float(r.get("equity_value", 0)) / 1e9

    fig_wf = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "total"],
        x=["Enterprise Value", "(−) Dívida Líquida", "Equity Value"],
        y=[ev, -nd, 0],
        text=[f"R${ev:.1f}bi", f"R${-nd:.1f}bi", f"R${eq:.1f}bi"],
        textposition="outside",
        connector=dict(line=dict(color="#1e2d45", width=1)),
        increasing=dict(marker_color="#00e676"),
        decreasing=dict(marker_color="#ff1744"),
        totals=dict(marker_color="#00d4ff"),
    ))
    fig_wf.update_layout(**PLOTLY_LAYOUT, title="Valores em R$ bilhões", showlegend=False)
    st.plotly_chart(fig_wf, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # FCFF histórico + projeção
    st.markdown("## FCFF: Histórico e Projeção")
    fcff_data = r.get("fcff_series", {})

    if fcff_data:
        anos   = [int(k) for k in fcff_data.keys()]
        valores = [float(v) / 1e9 for v in fcff_data.values()]
        last_hist = r.get("last_historical_year", 2024)
        cores = ["#7a8fa8" if a <= last_hist else "#00d4ff" for a in anos]

        fig_fcff = go.Figure()
        fig_fcff.add_trace(go.Bar(
            x=anos, y=valores,
            marker_color=cores,
            text=[f"R${v:.2f}bi" for v in valores],
            textposition="outside",
            name="FCFF",
        ))
        fig_fcff.add_vline(x=last_hist + 0.5, line_dash="dash",
                           line_color="#1e2d45", annotation_text="projeção →",
                           annotation_font_color="#7a8fa8")
        fig_fcff.update_layout(**PLOTLY_LAYOUT, title="R$ bilhões | cinza = histórico | azul = projeção")
        st.plotly_chart(fig_fcff, use_container_width=True)
    else:
        st.info("FCFF série não disponível no JSON. Reexecute python main.py para atualizar.")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Overrides e premissas
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("## Premissas DCF")
        premissas = r.get("premissas", {})
        rows_p = [
            ("Terminal Growth",  fmt_pct(r.get("terminal_growth"))),
            ("Tax Rate",         "34%"),
            ("Kd bruto",         fmt_pct(r.get("cost_of_debt"))),
            ("Shares Out",       f"{int(r.get('shares_out',0))//1_000_000:,} mi" if r.get("shares_out") else "n/d"),
        ]
        st.table(pd.DataFrame(rows_p, columns=["Premissa", "Valor"]))

    with col_b:
        st.markdown("## Overrides Ativos")
        ovr = r.get("overrides", {})
        if any(ovr.values()):
            rows_o = []
            if ovr.get("revenue_growth"):
                rows_o.append(("Crescimento Receita", fmt_pct(ovr["revenue_growth"]), "forward override"))
            if ovr.get("ebit_margin"):
                rows_o.append(("Margem EBIT", fmt_pct(ovr["ebit_margin"]), "forward override"))
            st.table(pd.DataFrame(rows_o, columns=["Parâmetro", "Valor", "Fonte"]))
            st.warning("⚠️ Overrides ativos — premissas manuais substituem cálculo histórico.")
        else:
            st.success("✅ Nenhum override — todas as premissas calculadas automaticamente.")

# ─────────────────────────────────────────────────────────────
# PÁGINA 3 — SENSIBILIDADE WACC
# ─────────────────────────────────────────────────────────────

elif pagina == "📉 Sensibilidade WACC":
    st.markdown("## Análise de Sensibilidade")
    st.markdown("### Preço Justo por WACC × Terminal Growth")

    empresa_sel = st.selectbox("Empresa", list(results.keys()),
                               format_func=lambda e: f"{results[e].get('ticker',e)} — {e}")
    r = results[empresa_sel]

    ev_base   = float(r.get("enterprise_value", 0))
    nd_base   = float(r.get("net_debt", 0))
    shares    = float(r.get("shares_out") or 1)
    fcff_last = r.get("fcff_last_proj") or (ev_base * 0.08)  # estimativa se não tiver

    waccs  = [w/100 for w in range(13, 22)]   # 13% a 21%
    growths = [g/100 for g in range(20, 55, 5)]  # 2.0% a 5.0%

    # Recalcula EV simplificado: TV = FCFF_último * (1+g) / (WACC - g)
    # EV = PV_FCFs_base (fixo) + PV_TV recalculado
    pv_fcfs_base = float(r.get("dcf_pv_fcf") or ev_base * 0.50)

    price_matrix = []
    for g in growths:
        row = []
        for w in waccs:
            if w <= g:
                row.append(None)
                continue
            # Terminal value recalculado
            fcff_t = fcff_last * (1 + g) if fcff_last else ev_base * 0.06
            tv = fcff_t / (w - g)
            # PV do terminal (desconta ~6 anos)
            pv_tv = tv / (1 + w) ** 6
            ev_new = pv_fcfs_base + pv_tv
            equity = ev_new - nd_base
            price  = equity / shares
            row.append(round(price, 2))
        price_matrix.append(row)

    df_sens = pd.DataFrame(
        price_matrix,
        index=[f"{g*100:.1f}%" for g in growths],
        columns=[f"{w*100:.1f}%" for w in waccs],
    )

    price_now = float(r.get("price_now") or 0)

    # Heatmap
    fig_heat = go.Figure(data=go.Heatmap(
        z=df_sens.values.tolist(),
        x=df_sens.columns.tolist(),
        y=df_sens.index.tolist(),
        colorscale=[
            [0.0,  "#7b0000"],
            [0.35, "#d32f2f"],
            [0.5,  "#1e2d45"],
            [0.65, "#00695c"],
            [1.0,  "#00e676"],
        ],
        text=[[f"R${v:.2f}" if v is not None else "n/d" for v in row] for row in df_sens.values.tolist()],
        texttemplate="%{text}",
        textfont=dict(size=10),
        colorbar=dict(title="Preço R$", tickfont=dict(color="#c8d8e8"), titlefont=dict(color="#c8d8e8")),
    ))

    # Linha do preço atual
    if price_now:
        fig_heat.add_annotation(
            text=f"Preço tela: R${price_now:.2f}",
            xref="paper", yref="paper",
            x=1.0, y=-0.08,
            showarrow=False,
            font=dict(color="#ffd740", size=11),
        )

    fig_heat.update_layout(
        **PLOTLY_LAYOUT,
        title=f"Preço Justo R$/ação — {r.get('ticker','')} | Eixo X: WACC | Eixo Y: Terminal Growth",
        xaxis_title="WACC",
        yaxis_title="Terminal Growth",
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # Tabela legível
    st.markdown("### Tabela de Sensibilidade (R$/ação)")
    def color_cell(val):
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return "color: #3a4a5a"
        if price_now and val >= price_now * 1.15:
            return "color: #00e676; font-weight:bold"
        elif price_now and val <= price_now * 0.85:
            return "color: #ff1744"
        return "color: #ffd740"

    styled = df_sens.style.applymap(color_cell).format("{:.2f}", na_rep="n/d")
    st.dataframe(styled, use_container_width=True)

    st.markdown(f"""
    <div style='font-size:0.78rem; color:#7a8fa8; margin-top:8px;'>
        🟢 Verde = acima de +15% do preço atual (R${price_now:.2f}) &nbsp;|&nbsp;
        🔴 Vermelho = abaixo de -15% &nbsp;|&nbsp;
        🟡 Amarelo = dentro da banda ±15%
    </div>
    """, unsafe_allow_html=True)