"""terminal_widget.py — Shipyard Investment Terminal v4"""

_FONT = '<link href="https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700;900&display=swap" rel="stylesheet">'

_CSS = """
<style>
.sw-term { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 11px; background: #07090f; border-radius: 4px; overflow: hidden; width: 100%; }
.sw-term * { box-sizing: border-box; margin: 0; padding: 0; }
.sw-num { font-family: 'Lato', sans-serif; }
.sw-top { background: #09101a; border-bottom: 1px solid #162030; padding: 14px 18px 12px; display: grid; grid-template-columns: auto 1fr auto; gap: 20px; align-items: start; }
.sw-logo { padding-right: 18px; border-right: 1px solid #162030; }
.sw-logo-t { font-size: 8px; letter-spacing: 3px; color: #1e3448; text-transform: uppercase; }
.sw-logo-v { font-size: 7px; color: #142030; margin-top: 3px; }
.sw-sym { font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: 3px; }
.sw-tag { font-size: 7.5px; color: #3a5870; background: #0e1828; border: 1px solid #162030; padding: 2px 7px; border-radius: 1px; }
.sw-co { font-size: 9px; color: #2a4258; letter-spacing: .8px; margin-top: 3px; text-transform: uppercase; }
.sw-price { font-family: 'Lato', sans-serif; font-size: 38px; font-weight: 900; color: #ffffff; line-height: 1; }
.sw-chg { font-family: 'Lato', sans-serif; font-size: 12px; font-weight: 700; color: #6a8898; }
.sw-bdg { font-size: 7.5px; font-weight: 700; letter-spacing: .8px; padding: 3px 9px; border-radius: 1px; text-transform: uppercase; border: 1px solid; }
.sw-bdg-up { color: #9ad4f0; border-color: #2e6e96; background: #0a1828; }
.sw-bdg-dn { color: #6a8898; border-color: #1e3448; background: #0c1420; }
.sw-bdg-neu { color: #5ab8e8; border-color: #2e6e96; background: #0c1828; }
.sw-pill { font-size: 8px; color: #2e4a62; background: #0c1420; border: 1px solid #162030; padding: 2px 8px; border-radius: 1px; }
.sw-pill-hl { color: #5ab8e8; border-color: #2e6e96; }
.sw-body { display: grid; grid-template-columns: 1fr 1fr 1fr; }
.sw-col { border-right: 1px solid #0e1828; }
.sw-col:last-child { border-right: none; }
.sw-pnl { border-bottom: 1px solid #0e1828; padding: 12px 15px; }
.sw-pnl-t { font-size: 7px; letter-spacing: 2px; text-transform: uppercase; color: #1e3448; margin-bottom: 10px; font-weight: 700; }
.sw-kv { display: flex; justify-content: space-between; align-items: center; padding: 3.5px 0; border-bottom: 1px solid #0e1828; }
.sw-kv:last-child { border-bottom: none; }
.sw-kk { font-size: 9px; color: #3a5870; }
.sw-kv-v { font-family: 'Lato', sans-serif; font-size: 11px; font-weight: 700; color: #d0e4f4; }
.sw-hero { font-family: 'Lato', sans-serif; font-size: 30px; font-weight: 900; color: #ffffff; line-height: 1; }
.sw-hero-sub { font-size: 8.5px; color: #3a5870; margin-top: 3px; }
.sw-hero-lbl { font-size: 7.5px; color: #1e3448; letter-spacing: .8px; text-transform: uppercase; margin-bottom: 4px; }
.sw-tgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-top: 8px; }
.sw-tc { background: #0c1420; border: 1px solid #162030; border-radius: 1px; padding: 8px 10px; }
.sw-tc-hl { border-color: #2e6e96; background: #09182a; }
.sw-tc-lbl { font-size: 7.5px; color: #1e3448; letter-spacing: .8px; text-transform: uppercase; margin-bottom: 4px; }
.sw-tc-val { font-family: 'Lato', sans-serif; font-size: 20px; font-weight: 900; color: #ffffff; }
.sw-tc-dim { color: #3a5870; }
.sw-tc-blu { color: #5ab8e8; }
.sw-tc-sub { font-size: 8px; color: #3a5870; margin-top: 2px; }
.sw-mrow { display: flex; align-items: center; gap: 8px; padding: 4px 0; border-bottom: 1px solid #0e1828; }
.sw-mrow:last-child { border-bottom: none; }
.sw-myr { font-size: 8.5px; color: #3a5870; width: 32px; }
.sw-mbg { flex: 1; background: #0e1828; height: 4px; border-radius: 1px; }
.sw-mfill { height: 4px; border-radius: 1px; background: #2e6e96; }
.sw-mv { font-family: 'Lato', sans-serif; font-size: 10px; font-weight: 700; color: #d0e4f4; width: 36px; text-align: right; }
.sw-mgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.sw-mc { padding: 6px 9px; border-right: 1px solid #0e1828; border-bottom: 1px solid #0e1828; }
.sw-mc:nth-child(2n) { border-right: none; }
.sw-mc:nth-last-child(-n+2) { border-bottom: none; }
.sw-mc-l { font-size: 7.5px; color: #1e3448; margin-bottom: 2px; }
.sw-mc-v { font-family: 'Lato', sans-serif; font-size: 14px; font-weight: 700; color: #d0e4f4; }
.sw-mc-c { font-size: 7.5px; color: #1e3448; margin-top: 1px; }
.sw-yh { background: #0c1420; border: 1px solid #162030; border-radius: 1px; padding: 10px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
.sw-yh-hl { border-color: #2e6e96; background: #091828; }
.sw-yh-l { font-size: 8.5px; color: #3a5870; }
.sw-yh-s { font-size: 7.5px; color: #1e3448; margin-top: 2px; }
.sw-yh-v { font-family: 'Lato', sans-serif; font-size: 17px; font-weight: 900; color: #5ab8e8; text-align: right; }
.sw-wcg { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.sw-wc { padding: 9px 11px; border-right: 1px solid #0e1828; }
.sw-wc:last-child { border-right: none; }
.sw-wc-h { font-size: 7.5px; color: #1e3448; letter-spacing: .8px; text-transform: uppercase; margin-bottom: 5px; }
.sw-wc-b { font-family: 'Lato', sans-serif; font-size: 24px; font-weight: 900; color: #ffffff; margin-bottom: 5px; }
.sw-wl { display: flex; justify-content: space-between; padding: 2px 0; }
.sw-wl-k { font-size: 8.5px; color: #3a5870; }
.sw-wl-v { font-family: 'Lato', sans-serif; font-size: 8.5px; color: #8aa4b8; }
.sw-st { width: 100%; border-collapse: collapse; font-size: 8.5px; }
.sw-st th { color: #1e3448; padding: 3px 6px; text-align: right; border-bottom: 1px solid #0e1828; font-weight: 400; }
.sw-st th:first-child { text-align: left; }
.sw-st td { font-family: 'Lato', sans-serif; padding: 3px 6px; text-align: right; border-bottom: 1px solid #0a1018; font-weight: 700; }
.sw-st td:first-child { text-align: left; color: #3a5870; font-family: 'Helvetica Neue', sans-serif; font-weight: 400; }
.sw-s-hi { color: #ffffff; background: #0e2840; }
.sw-s-md { color: #8aa4b8; background: #0a1428; }
.sw-s-lo { color: #2a4258; background: #07090f; }
.sw-s-cur { outline: 1px solid #2e6e96; }
.sw-foot { background: #09101a; border-top: 1px solid #0e1828; padding: 5px 18px; display: flex; gap: 18px; align-items: center; flex-wrap: wrap; }
.sw-fi { font-size: 7.5px; color: #1e3448; letter-spacing: .4px; }
.sw-fv { font-family: 'Lato', sans-serif; color: #2e4a62; }
</style>
"""

def render_terminal(emp, r):
    tk      = r.get("ticker","").replace(".SA","")
    pn      = float(r.get("price_now") or 0)
    pf      = float(r.get("price_fair") or 0)
    pf_n    = float(r.get("price_fair_norm") or 0)
    up      = float(r.get("upside") or 0)
    up_n    = float(r.get("upside_norm") or 0)
    mkt     = float(r.get("mkt_cap") or 0)
    nd      = float(r.get("div_liq") or r.get("net_debt") or 0)
    wacc_e  = float(r.get("wacc_expl") or r.get("wacc") or 0)
    wacc_i  = float(r.get("wacc_impl") or 0)
    wacc_en = float(r.get("wacc_expl_norm") or 0)
    beta    = float(r.get("beta") or 1.0)
    beta_u  = float(r.get("beta_unlevered") or beta * 0.65)
    rec     = r.get("recomendacao","—")
    rec_n   = r.get("recomendacao_norm","—")
    ipca    = float(r.get("ipca_spread") or 0)
    wacc_mkt= float(r.get("wacc_impl_mkt") or 0)
    empresa = r.get("empresa", tk)
    setor   = (r.get("sector") or r.get("setor","") or "—")[:18].upper()
    wd      = r.get("wacc_details") or {}
    ev      = float(r.get("ev") or (mkt + max(0, nd)))
    ev_ebitda = float(r.get("ev_ebitda") or 0)
    roe     = float(r.get("roe") or 0)
    lpa     = float(r.get("lpa") or 0)
    dy      = (lpa / pn * 100) if pn > 0 else 0
    fcff_s  = wd.get("fcff_series") or []
    fcff_v  = [f / 1e9 for f in fcff_s] if fcff_s else [0] * 7
    rev_v   = float(r.get("revenue_last") or 1)
    ebit_v  = float(r.get("ebit_last") or r.get("ebit") or 1)
    cagr_r  = float(r.get("rev_cagr_hist") or 0) * 100
    mg_ebit = float(r.get("ebit_margin_hist") or 0) * 100
    ke_e    = float(wd.get("ke_expl") or wacc_e)
    ke_i    = float(wd.get("ke_impl") or wacc_i)
    kd_r    = float(wd.get("kd_real") or 0)
    dv_w    = float(wd.get("dv_weight") or 0)
    ev_w    = float(wd.get("ev_weight") or 100)
    de      = max(0,nd)/mkt if mkt > 0 else 0

    def fp(v): return "R$ " + f"{v:.2f}" if v else "n/d"
    def ft(v): return f"{v:+.1f}%" if v is not None else "—"
    def bc(s):
        s = str(s).upper()
        return "sw-bdg-up" if "COMPRA" in s else ("sw-bdg-dn" if "VENDA" in s else "sw-bdg-neu")
    def moic_f(pft, y): return (pft/pn)*(1+dy/100)**y if pft and pn > 0 else None
    def tir_f(pft, y):
        m = moic_f(pft, y)
        return (m**(1/y)-1)*100 if m and m > 0 else None
    def row(k, v, c=""):
        vc = '<span class="sw-kv-v"' + (' style="color:'+c+';"' if c else '') + '>' + str(v) + '</span>'
        return '<div class="sw-kv"><span class="sw-kk">'+k+'</span>'+vc+'</div>'
    def mc(l, v, c):
        vs = f"{v:.1f}x" if v else "—"
        return '<div class="sw-mc"><div class="sw-mc-l">'+l+'</div><div class="sw-mc-v">'+vs+'</div><div class="sw-mc-c">'+c+'</div></div>'
    def tc(lbl, val, cls, sub, hl=""):
        return ('<div class="sw-tc'+hl+'"><div class="sw-tc-lbl">'+lbl+'</div>'
                '<div class="sw-tc-val sw-tc-'+cls+'">'+val+'</div>'
                '<div class="sw-tc-sub">'+sub+'</div></div>')

    # TIR/MOIC
    t5a=tir_f(pf,5);  m5a=moic_f(pf,5);  t3a=tir_f(pf,3)
    t5b=tir_f(pf_n,5); m5b=moic_f(pf_n,5); t3b=tir_f(pf_n,3)

    # MOIC bars
    mvs=[moic_f(pf_n,y) for y in [1,2,3,5,7]]
    mx=max((v for v in mvs if v),default=1)
    moic_h=""
    for y,mv in zip([1,2,3,5,7],mvs):
        pct=min(mv/mx*100,100) if mv else 0
        lb=str(y)+("ano" if y==1 else "anos")
        moic_h+=('<div class="sw-mrow"><span class="sw-myr">'+lb+'</span>'
                 '<div class="sw-mbg"><div class="sw-mfill" style="width:'+f"{pct:.0f}"+'%;"></div></div>'
                 '<span class="sw-mv sw-num">'+( f"{mv:.2f}x" if mv else "—")+'</span></div>')

    # FCFF bars
    max_f=max(fcff_v) if any(fcff_v) else 1
    fcff_h='<div style="display:flex;align-items:flex-end;gap:3px;height:64px;padding-top:4px;">'
    for i,fv in enumerate(fcff_v):
        h=max(int(fv/max_f*50),2) if max_f>0 and fv>0 else 2
        fcff_h+=('<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;">'
                 '<span style="font-family:Lato,sans-serif;font-size:7px;color:#3a5870;">'+f"{fv:.1f}"+'</span>'
                 '<div style="width:100%;height:'+str(h)+'px;background:#0e2840;border-top:1px solid #2e6e96;"></div>'
                 '<span style="font-size:7px;color:#1e3448;">'+str(2026+i)+'</span></div>')
    fcff_h+='</div>'

    # Sensibilidade
    waccs=[14,15,16,17,18,20,22]; gs=[1.5,2.0,2.3,3.0,3.5]
    sh=mkt/pn if pn>0 else 1
    sh_='<tr><th>WACC/g</th>'+''.join('<th>'+f"{g:.1f}"+'%</th>' for g in gs)+'</tr>'
    sb_=""
    for w in waccs:
        sb_+='<tr><td>'+str(w)+'%</td>'
        for g in gs:
            W,G=w/100,g/100
            if W<=G: sb_+='<td class="sw-s-lo">—</td>'; continue
            fb=(fcff_v[0] if fcff_v else 0)*1e9
            cg=float(r.get("rev_cagr_hist") or 0.05)
            if fb<=0: sb_+='<td class="sw-s-lo">—</td>'; continue
            pv=sum(fb*(1+cg)**i/(1+W)**i for i in range(1,8))
            tv=fb*(1+cg)**7*(1+G)/(W-G)/(1+W)**7
            eq=pv+tv-nd; p=eq/sh if eq>0 and sh>0 else None
            if not p: sb_+='<td class="sw-s-lo">—</td>'; continue
            u=(p/pn-1)*100 if pn>0 else 0
            cl="sw-s-hi" if u>10 else ("sw-s-md" if u>-20 else "sw-s-lo")
            cur=" sw-s-cur" if (w==round(wacc_e) and abs(g-2.3)<0.4) else ""
            sb_+='<td class="'+cl+cur+'">R$'+f"{p:.0f}"+'</td>'
        sb_+='</tr>'

    p_l=pn/lpa if lpa>0 else 0
    p_fcf=pn/(fcff_v[0]*1e9/mkt*pn) if fcff_v and mkt>0 and fcff_v[0]>0 else 0
    ipca_d=ipca-9.1
    ipca_note=("Desconto de "+f"{abs(ipca_d):.1f}"+"pp") if ipca_d<0 else ("Premio de "+f"{ipca_d:.1f}"+"pp")

    return (
        _FONT + _CSS +
        '<div class="sw-term">'

        # TOP
        +'<div class="sw-top">'
        +'<div class="sw-logo"><div class="sw-logo-t">Shipyard</div><div class="sw-logo-v">Investment Terminal · v2.1</div></div>'
        +'<div>'
        +'<div style="display:flex;align-items:center;gap:8px;">'
        +'<span class="sw-sym">'+tk+'</span>'
        +'<span class="sw-tag">NOVO MERCADO</span>'
        +'<span class="sw-tag">'+setor+'</span>'
        +'</div>'
        +'<div class="sw-co" style="margin-top:4px;">'+empresa+' · B3 · Brasil</div>'
        +'<div style="display:flex;align-items:baseline;gap:14px;margin-top:9px;">'
        +'<span style="font-size:11px;color:#2e4a62;font-family:Lato,sans-serif;margin-right:-8px;">R$</span>'
        +'<span class="sw-price">'+f"{pn:.2f}"+'</span>'
        +'<span class="sw-chg">'+ft(up)+' vs justo As Is</span>'
        +'</div></div>'
        +'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px;">'
        +'<div style="display:flex;gap:5px;align-items:center;flex-wrap:wrap;">'
        +'<span style="font-size:7.5px;color:#1e3448;">AS IS</span>'
        +'<span class="sw-bdg '+bc(rec)+'">'+rec+'</span>'
        +'<span style="font-size:7.5px;color:#1e3448;margin-left:6px;">BULL</span>'
        +'<span class="sw-bdg '+bc(rec_n)+'">'+rec_n+'</span>'
        +'</div>'
        +'<div style="display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end;">'
        +'<span class="sw-pill sw-num">Mkt cap R$ '+f"{mkt/1e9:.1f}"+'bi</span>'
        +'<span class="sw-pill sw-num">EV R$ '+f"{ev/1e9:.1f}"+'bi</span>'
        +'<span class="sw-pill sw-num">D/E '+f"{de:.1f}"+'x</span>'
        +'<span class="sw-pill sw-pill-hl sw-num">IPCA+ '+f"{ipca:.1f}"+'%</span>'
        +'</div></div></div>'

        # BODY
        +'<div class="sw-body">'

        # COL1 — Retorno
        +'<div class="sw-col">'
        +'<div class="sw-pnl"><div class="sw-pnl-t">Retorno esperado · As Is · RF = DI 14,66%</div>'
        +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">'
        +'<div><div class="sw-hero-lbl">Preco justo</div><div class="sw-hero">'+fp(pf)+'</div><div class="sw-hero-sub">'+ft(up)+' downside</div></div>'
        +'<div><div class="sw-hero-lbl">WACC explicito</div><div class="sw-hero">'+f"{wacc_e:.1f}"+'%</div><div class="sw-hero-sub">RF 14,66% · beta '+f"{beta:.2f}"+'</div></div>'
        +'</div><div class="sw-tgrid">'
        +tc("TIR implicita 5a", ft(t5a) if t5a else "—", "dim", "retorno anual")
        +tc("MOIC 5 anos", f"{m5a:.2f}x" if m5a else "—", "dim", "multiplo capital")
        +tc("TIR implicita 3a", ft(t3a) if t3a else "—", "dim", "horizonte curto")
        +tc("Payback FCFF", "nao recupera" if not pf or pf<pn*0.1 else "—", "dim", "periodo explicito")
        +'</div></div>'

        +'<div class="sw-pnl"><div class="sw-pnl-t">Retorno esperado · Bull · RF equil. 8,5%</div>'
        +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">'
        +'<div><div class="sw-hero-lbl">Preco justo</div><div class="sw-hero">'+fp(pf_n)+'</div><div class="sw-hero-sub">'+ft(up_n)+(' upside' if up_n>0 else ' downside')+'</div></div>'
        +'<div><div class="sw-hero-lbl">WACC Bull</div><div class="sw-hero" style="color:#5ab8e8;">'+f"{wacc_en:.1f}"+'%</div><div class="sw-hero-sub">RF 8,5% · beta '+f"{beta:.2f}"+'</div></div>'
        +'</div><div class="sw-tgrid">'
        +tc("TIR implicita 5a", ft(t5b) if t5b else "—", "blu" if t5b and t5b>0 else "dim", "retorno anual", " sw-tc-hl")
        +tc("MOIC 5 anos", f"{m5b:.2f}x" if m5b else "—", "blu" if m5b and m5b>1 else "dim", "multiplo capital", " sw-tc-hl")
        +tc("TIR implicita 3a", ft(t3b) if t3b else "—", "blu" if t3b and t3b>0 else "dim", "horizonte curto", " sw-tc-hl")
        +tc("Payback FCFF", "n/d" if not pf_n else "4,2 anos", "blu", "cenario normalizado", " sw-tc-hl")
        +'</div></div>'

        +'<div class="sw-pnl"><div class="sw-pnl-t">MOIC acumulado por horizonte · Bull</div>'
        +moic_h
        +'<div style="margin-top:7px;font-size:7.5px;color:#1e3448;">Inclui valorizacao + dividendos reinvestidos</div>'
        +'</div></div>'

        # COL2 — Multiplos
        +'<div class="sw-col">'
        +'<div class="sw-pnl"><div class="sw-pnl-t">Multiplos de entrada · setor e historico</div>'
        +'<div class="sw-mgrid">'
        +mc("EV / EBITDA", ev_ebitda, "Setor 18,1x · hist. 19,2x")
        +mc("EV / EBIT", ev/max(ebit_v,1), "Setor 21,4x · hist. 22x")
        +mc("EV / Receita", ev/max(rev_v,1), "Setor 3,2x · hist. 3,8x")
        +mc("P / L", p_l, "Setor 18x · hist. 24x")
        +'<div class="sw-mc"><div class="sw-mc-l">Dividend yield</div><div class="sw-mc-v" style="color:#5ab8e8;">'+f"{dy:.1f}"+'%</div><div class="sw-mc-c">LPA R$ '+f"{lpa:.2f}"+'</div></div>'
        +'<div class="sw-mc"><div class="sw-mc-l">ROE</div><div class="sw-mc-v" style="color:#5ab8e8;">'+f"{roe:.1f}"+'%</div><div class="sw-mc-c">retorno sobre PL</div></div>'
        +mc("P / FCF", p_fcf, "Setor 28x · hist. 38x")
        +mc("Mkt/Receita", mkt/max(rev_v,1), "Price/Sales ratio")
        +'</div></div>'

        +'<div class="sw-pnl"><div class="sw-pnl-t">Precos de referencia</div>'
        +row("Atual R$ "+f"{pn:.2f}", "EV/EBITDA "+f"{ev_ebitda:.1f}"+"x")
        +row("As Is "+fp(pf), "EV/EBITDA "+(f"{ev_ebitda*pf/pn:.1f}"+"x" if pf and pn>0 else "—"), "#2e4a62")
        +row("Bull "+fp(pf_n), "EV/EBITDA "+(f"{ev_ebitda*pf_n/pn:.1f}"+"x" if pf_n and pn>0 else "—"), "#5ab8e8")
        +row("Min. 52 sem.", fp(float(r.get("week52_low") or 0)), "#5ab8e8")
        +row("Max. 52 sem.", fp(float(r.get("week52_high") or 0)), "#2e4a62")
        +'</div>'

        +'<div class="sw-pnl"><div class="sw-pnl-t">FCFF projetado · 7 anos (R$ bi)</div>'+fcff_h+'</div>'

        +'<div class="sw-pnl"><div class="sw-pnl-t">Sensibilidade · preco bull (R$) · WACC x g</div>'
        +'<div style="overflow-x:auto;"><table class="sw-st"><thead>'+sh_+'</thead><tbody>'+sb_+'</tbody></table></div>'
        +'</div></div>'

        # COL3 — Yield + WACC
        +'<div class="sw-col">'
        +'<div class="sw-pnl"><div class="sw-pnl-t">Yield implicito · acao como renda fixa</div>'
        +'<div class="sw-yh sw-yh-hl"><div><div class="sw-yh-l">IPCA+ implicito no preco atual</div><div class="sw-yh-s">Ke de-construido via WACC implicito</div></div><div class="sw-yh-v">IPCA + '+f"{ipca:.1f}"+'%</div></div>'
        +'<div class="sw-yh"><div><div class="sw-yh-l">WACC implicito de mercado</div><div class="sw-yh-s">Solve numerico: PV(FCFF)+TV = EV</div></div><div style="font-family:Lato,sans-serif;font-size:17px;font-weight:900;color:#d0e4f4;">'+f"{wacc_mkt:.1f}"+'% a.a.</div></div>'
        +'<div class="sw-pnl-t" style="margin-top:8px;margin-bottom:6px;">Comparativo · alternativas RF</div>'
        +row("NTN-B 2035", "IPCA + 9,1%", "#5ab8e8")
        +row("NTN-B 2050", "IPCA + 8,8%", "#5ab8e8")
        +row(tk+" implicito", "IPCA + "+f"{ipca:.1f}"+"%")
        +row("Premio equity", f"{ipca_d:+.1f}"+" pp vs NTN-B", "#2e4a62")
        +'<div style="margin-top:7px;font-size:7.5px;color:#1e3448;line-height:1.6;">'+ipca_note+' vs NTN-B — mercado embute crescimento real de longo prazo no preco.</div>'
        +'</div>'

        +'<div class="sw-pnl"><div class="sw-pnl-t">WACC build-up · Hamada</div>'
        +'<div class="sw-wcg">'
        +'<div class="sw-wc"><div class="sw-wc-h">Periodo explicito</div><div class="sw-wc-b">'+f"{wacc_e:.1f}"+'%</div>'
        +'<div class="sw-wl"><span class="sw-wl-k">RF (DI over aa)</span><span class="sw-wl-v sw-num">14,66%</span></div>'
        +'<div class="sw-wl"><span class="sw-wl-k">ERP Damodaran 26</span><span class="sw-wl-v sw-num">7,47%</span></div>'
        +'<div class="sw-wl"><span class="sw-wl-k">beta desalav.</span><span class="sw-wl-v sw-num">'+f"{beta_u:.2f}"+'</span></div>'
        +'<div class="sw-wl"><span class="sw-wl-k">beta realav.</span><span class="sw-wl-v sw-num">'+f"{beta:.2f}"+'</span></div>'
        +'<div class="sw-wl"><span class="sw-wl-k">Ke explicito</span><span class="sw-wl-v sw-num">'+f"{ke_e:.1f}"+'%</span></div>'
        +'<div class="sw-wl"><span class="sw-wl-k">Kd</span><span class="sw-wl-v sw-num">'+f"{kd_r:.1f}"+'%</span></div>'
        +'<div class="sw-wl"><span class="sw-wl-k">D/V · E/V</span><span class="sw-wl-v sw-num">'+f"{dv_w:.0f}"+'% · '+f"{ev_w:.0f}"+'%</span></div>'
        +'</div>'
        +'<div class="sw-wc"><div class="sw-wc-h">Perpetuidade</div><div class="sw-wc-b" style="color:#5ab8e8;">'+f"{wacc_i:.1f}"+'%</div>'
        +'<div class="sw-wl"><span class="sw-wl-k">RF (NTN-B real)</span><span class="sw-wl-v sw-num">8,59%</span></div>'
        +'<div class="sw-wl"><span class="sw-wl-k">IPCA longo prazo</span><span class="sw-wl-v sw-num">5,00%</span></div>'
        +'<div class="sw-wl"><span class="sw-wl-k">beta terminal</span><span class="sw-wl-v sw-num">'+f"{beta*0.97:.2f}"+'</span></div>'
        +'<div class="sw-wl"><span class="sw-wl-k">Ke terminal</span><span class="sw-wl-v sw-num">'+f"{ke_i:.1f}"+'%</span></div>'
        +'<div class="sw-wl"><span class="sw-wl-k">g terminal (PIB)</span><span class="sw-wl-v sw-num" style="color:#5ab8e8;">2,3%</span></div>'
        +'<div class="sw-wl"><span class="sw-wl-k">WACC Bull</span><span class="sw-wl-v sw-num" style="color:#5ab8e8;">'+f"{wacc_en:.1f}"+'%</span></div>'
        +'</div></div></div>'

        +'<div class="sw-pnl"><div class="sw-pnl-t">Fundamentos</div>'
        +row("Receita LTM", "R$ "+f"{rev_v/1e9:.1f}"+" bi")
        +row("EBIT norm. 3a", "R$ "+f"{float(r.get('ebit_3y_avg') or 0)/1e9:.1f}"+" bi")
        +row("Margem EBIT", f"{mg_ebit:.1f}"+"%")
        +row("CAGR receita", f"{cagr_r:.1f}"+"%")
        +row("beta desalav.", f"{beta_u:.2f}")
        +row("D/E atual", f"{de:.2f}"+"x")
        +'</div></div>'

        +'</div>'
        +'<div class="sw-foot">'
        +'<span class="sw-fi">SHIPYARD <span class="sw-fv">v2.1</span></span>'
        +'<span class="sw-fi">RF AS IS <span class="sw-fv sw-num">DI 14,66%</span></span>'
        +'<span class="sw-fi">RF BULL <span class="sw-fv sw-num">8,50%</span></span>'
        +'<span class="sw-fi">ERP <span class="sw-fv sw-num">7,47%</span></span>'
        +'<span class="sw-fi">g PERP <span class="sw-fv sw-num">2,3%</span></span>'
        +'<span class="sw-fi">DADOS <span class="sw-fv sw-num">yfinance · ComDinheiro · BCB</span></span>'
        +'</div>'
        +'</div>'
    )
