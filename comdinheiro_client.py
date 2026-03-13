"""
comdinheiro_client.py — Shipyard | Vela Capital v4
Estratégia:
  ✅ BalancosSinteticos001  — BP + DRE + DFC completo (colunas = datas, linhas = indicadores)
  ✅ HistoricoCotacao002    — cotações históricas
  ✅ yfinance               — Beta, liquidez, múltiplos de mercado, consenso, proventos
  ⛔ ComparaEmpresas001     — SEMPRE ignora parâmetro indic, retorna só cols padrão
"""
import os, requests, pandas as pd
from datetime import datetime, timedelta
from urllib.parse import quote

API_URL  = "https://api.comdinheiro.com.br/v1/ep1/import-data"
CD_USER  = os.getenv("COMDINHEIRO_USER", "vela.capital")
CD_PASS  = os.getenv("COMDINHEIRO_PASS", "Vela.capital1!")
HEADERS  = {"Content-Type": "application/x-www-form-urlencoded"}


# ─────────────────────────────────────────────────────────────────
# INTERNOS
# ─────────────────────────────────────────────────────────────────
def _request(url_consulta, timeout=45):
    url_enc = quote(url_consulta + "&format=json3", safe="=&?/+")
    payload = f"username={CD_USER}&password={CD_PASS}&URL={url_enc}"
    r = requests.post(API_URL, data=payload, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _parse(data):
    """JSON3 → DataFrame. col0='Data'/label, col1..N = datas dos períodos."""
    try:
        tab  = list(data.get("tables", {}).values())[0]
        lin0 = tab.get("lin0", {})
        cols = [lin0[k] for k in sorted(lin0, key=lambda x: int(x.replace("col", "")))]
        rows, i = [], 1
        while f"lin{i}" in tab:
            lin = tab[f"lin{i}"]
            rows.append({cols[j]: lin.get(f"col{j}") for j in range(len(cols))})
            i += 1
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=cols)
    except Exception as e:
        return pd.DataFrame({"parse_erro": [str(e)]})


def _fmt(d):
    return d.strftime("%d%m%Y")


def _to_f(v):
    """Converte string para float, tolerante a vírgula decimal."""
    if v is None or str(v).strip() in ("", "-", "—"): return None
    try:   return float(str(v).replace(",", ".").strip())
    except: return None


def _row_val(df, label):
    """
    Extrai o primeiro valor numérico não-vazio de uma linha do BalancosSinteticos.
    ATENÇÃO: col0 = label, col1 = data mais recente (pode ser parcial/vazia),
    col2 = último período fechado. Percorre todas até achar valor.
    """
    col0 = df.columns[0]
    mask = df[col0].astype(str).str.strip() == label
    if not mask.any(): return None
    row = df[mask].iloc[0]
    for c in df.columns[1:]:
        fv = _to_f(row.get(c))
        if fv is not None and fv != 0.0:
            return fv
    # aceita zero se todos forem zero
    for c in df.columns[1:]:
        fv = _to_f(row.get(c))
        if fv is not None:
            return fv
    return None


def _row_series(df, label, max_periods=8):
    """Retorna dict {data: valor} para plotar série histórica."""
    col0 = df.columns[0]
    mask = df[col0].astype(str).str.strip() == label
    if not mask.any(): return {}
    row = df[mask].iloc[0]
    result = {}
    for c in df.columns[1:max_periods+1]:
        fv = _to_f(row.get(c))
        if fv is not None:
            result[str(c)] = fv
    return result


def _last_date(df):
    """Retorna a data do período mais recente com dado preenchido."""
    if len(df.columns) < 2: return "—"
    for c in df.columns[1:]:
        # Verifica se alguma linha nessa coluna tem valor
        vals = df[c].apply(_to_f).dropna()
        if len(vals) > 0:
            return str(c)
    return "—"


# ─────────────────────────────────────────────────────────────────
# 1. CONEXÃO
# ─────────────────────────────────────────────────────────────────
def test_connection():
    try:
        hoje = datetime.today()
        url = (f"HistoricoCotacao002.php?&x=WEGE3"
               f"&data_ini={_fmt(hoje-timedelta(days=5))}"
               f"&data_fim={_fmt(hoje)}&pagina=1&cabecalho_excel=modo1")
        _request(url, timeout=15)
        return {"ok": True, "msg": "Conexao OK"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


# ─────────────────────────────────────────────────────────────────
# 2. DRE + BP COMPLETO  (BalancosSinteticos001)
# ─────────────────────────────────────────────────────────────────
def get_dre(papel, anos=5):
    hoje = datetime.today()
    url = (f"BalancosSinteticos001.php?&papel={papel}"
           f"&data_ini={_fmt(hoje-timedelta(days=365*anos))}"
           f"&data_fim={_fmt(hoje)}"
           f"&tipo=dre&periodicidade=anual&cabecalho_excel=modo1")
    try: return _parse(_request(url))
    except Exception as e: return pd.DataFrame({"Erro": [str(e)]})


def get_balanco(papel, anos=5):
    hoje = datetime.today()
    url = (f"BalancosSinteticos001.php?&papel={papel}"
           f"&data_ini={_fmt(hoje-timedelta(days=365*anos))}"
           f"&data_fim={_fmt(hoje)}"
           f"&tipo=bp&periodicidade=anual&cabecalho_excel=modo1")
    try: return _parse(_request(url))
    except Exception as e: return pd.DataFrame({"Erro": [str(e)]})


def get_cotacao(papel, dias=365):
    hoje = datetime.today()
    url = (f"HistoricoCotacao002.php?&x={papel}"
           f"&data_ini={_fmt(hoje-timedelta(days=dias))}"
           f"&data_fim={_fmt(hoje)}&pagina=1&cabecalho_excel=modo1")
    try: return _parse(_request(url))
    except Exception as e: return pd.DataFrame({"Erro": [str(e)]})


# ─────────────────────────────────────────────────────────────────
# 3. KPIs FUNDAMENTALISTAS — TODOS os indicadores da página ComDinheiro
#    Fonte primária: BalancosSinteticos001 (BP+DRE+DFC)
#    Complemento: yfinance (Beta, liquidez, consenso, múltiplos)
# ─────────────────────────────────────────────────────────────────
def get_fundamentalista(papel, ticker_sa=None):
    if ticker_sa is None:
        ticker_sa = papel + ".SA"
    res = {}

    # ── 3a. DADOS CONTÁBEIS DO BALANÇO ──────────────────────────
    try:
        df = get_dre(papel, anos=3)
        if not df.empty and "Erro" not in df.columns and "parse_erro" not in df.columns:

            def v(lbl): return _row_val(df, lbl)

            # Demonstração de resultados
            rl   = v("Receita Líquida")
            custo= v("(-) Custo")
            lb   = v("Lucro Bruto")
            desp = v("(-) Despesas Operacionais")
            ebit = v("Lucro Operacional (EBIT)")
            rf   = v("(+) Receita Financeira")
            df_  = v("(-) Despesa Financeira")
            ll   = v("Lucro Líquido")
            ir   = v("(-) Tributos sobre o Lucro")

            # Fluxo de caixa
            fco  = v("(+) Fluxo Caixa das Operações")
            fci  = v("(+) Fluxo Caixa dos Investimentos")
            fcf  = v("(+) Fluxo Caixa dos Financiamentos")

            # Balanço patrimonial (dentro do mesmo DF do BalancosSinteticos)
            at   = v("Ativo Total")
            ac   = v("Ativo Circulante")
            disp = v("Disponibilidades")
            est  = v("Estoques")
            anc  = v("Ativo Não Circulante")
            imob = v("Imobilizado")
            intg = v("Intangível")
            pl   = v("Patrimônio Líquido")
            pc   = v("Passivo Circulante")
            pnc  = v("Passivo Não Circulante")
            cap  = v("Capital Social Realizado")

            # Dívida — duas linhas "Empréstimos e Financiamentos" (CP e LP)
            emp_rows = df[df.iloc[:,0].astype(str).str.strip() == "Empréstimos e Financiamentos"]
            emp_cp = _to_f(emp_rows.iloc[0, 1]) if len(emp_rows) >= 1 else None
            # se col1 vazio, pega col2
            if emp_cp is None or emp_cp == 0:
                for c in df.columns[1:]:
                    v2 = _to_f(emp_rows.iloc[0].get(c))
                    if v2 and v2 != 0: emp_cp = v2; break
            emp_nc = None
            if len(emp_rows) >= 2:
                for c in df.columns[1:]:
                    v2 = _to_f(emp_rows.iloc[1].get(c))
                    if v2 and v2 != 0: emp_nc = v2; break

            db   = (emp_cp or 0) + (emp_nc or 0) if (emp_cp or emp_nc) else None
            dl   = (db - disp) if (db is not None and disp is not None) else None
            ccl  = (ac - pc) if (ac and pc) else None

            # EBITDA ≈ EBIT + D&A  (D&A não vem explícito do BalancosSinteticos,
            # mas FCO ≈ LL + D&A + variações. Usamos referência: EBITDA do yfinance
            # ou aproximamos EBITDA = EBIT * 1.12 como fallback)
            ebitda = None  # preenchido pelo yfinance abaixo

            # Metadados
            data_dem  = _last_date(df)
            col0      = df.columns[0]
            conv_row  = df[df[col0].astype(str).str.strip() == "Convenção"]
            tipo_row  = df[df[col0].astype(str).str.strip() == "Tipo"]
            convencao = str(conv_row.iloc[0, 1]).strip() if not conv_row.empty else "IFRS"
            tipo      = str(tipo_row.iloc[0, 1]).strip() if not tipo_row.empty else "—"
            # corrige: se convencao e tipo estão vazios na col1, pega col2
            if convencao in ("", "None"):
                for c in df.columns[1:]:
                    v2 = str(conv_row.iloc[0].get(c,"")).strip()
                    if v2 and v2 != "None": convencao = v2; break
            if tipo in ("", "None"):
                for c in df.columns[1:]:
                    v2 = str(tipo_row.iloc[0].get(c,"")).strip()
                    if v2 and v2 != "None": tipo = v2; break

            # Qtd ações
            acao_row = df[df[col0].astype(str).str.strip() == "Quant Ações Emitidas"]
            shares_cd = None
            if not acao_row.empty:
                for c in df.columns[1:]:
                    v2 = str(acao_row.iloc[0].get(c,"")).replace(",",".").strip()
                    try:
                        shares_cd = float(v2) * 1_000_000  # em milhões → unidades
                        if shares_cd > 0: break
                    except: pass

            res.update({
                "AT": at, "AC": ac, "ANC": anc, "DISP": disp, "EST": est,
                "IMOB": imob, "INTG": intg, "PC": pc, "PNC": pnc, "PL": pl,
                "CAP": cap, "CCL": ccl,
                "RL": rl, "CUSTO": custo, "LB": lb, "DESP_OP": desp,
                "EBIT": ebit, "RF": rf, "DF": df_, "LL": ll, "IR": ir,
                "FCO": fco, "FCI": fci, "FCF": fcf,
                "DB": db, "DL": dl,
                "shares_cd": shares_cd,
                "data_dem": data_dem, "convencao": convencao, "tipo": tipo,
                # Séries históricas para gráfico
                "serie_rl":  _row_series(df, "Receita Líquida"),
                "serie_ll":  _row_series(df, "Lucro Líquido"),
                "serie_ebit":_row_series(df, "Lucro Operacional (EBIT)"),
                "serie_fco": _row_series(df, "(+) Fluxo Caixa das Operações"),
            })

            # Margens (RL em R$ mil, base consistente)
            if rl and rl != 0:
                res["ML"]      = ll   / rl * 100 if ll      else None
                res["MO"]      = ebit / rl * 100 if ebit    else None
                res["MB"]      = lb   / rl * 100 if lb      else None

            # Alavancagem / estrutura
            if at and at != 0:
                res["ALAV"]  = at / pl if pl else None
                res["CT_AT"] = (at - (pl or 0)) / at * 100

            res["ICJ"] = (ebit / abs(df_)) if (ebit and df_ and df_ != 0) else None

    except Exception as e:
        res["erro_balanco"] = str(e)

    # ── 3b. YFINANCE — múltiplos, risco, liquidez, consenso ─────
    try:
        import yfinance as yf
        tk     = yf.Ticker(ticker_sa)
        info   = tk.info
        fi     = tk.fast_info

        preco  = getattr(fi, "last_price", None) or info.get("currentPrice")
        shares = getattr(fi, "shares", None) or info.get("sharesOutstanding")
        mktcap = getattr(fi, "market_cap", None) or info.get("marketCap")
        ev     = info.get("enterpriseValue")
        ebitda_yf = info.get("ebitda")

        res["PRECO"]  = preco
        res["MKTCAP"] = mktcap
        res["EV"]     = ev

        # EBITDA: prioridade yfinance (mais preciso, inclui D&A real)
        ebitda = ebitda_yf / 1_000_000 if ebitda_yf else None  # converte para R$ mil
        if ebitda:
            res["EBITDA"] = ebitda
            ebit = res.get("EBIT")
            if ebit and ebitda:
                res["DA"]      = ebitda - ebit  # Depr. e Amort.
                res["MEBITDA"] = ebitda / res["RL"] * 100 if res.get("RL") else None
            if res.get("RL"):
                res["MEBITDA"] = ebitda / res["RL"] * 100

        # LPA e VPA por ação
        ll  = res.get("LL")
        pl  = res.get("PL")
        shares_cd = res.get("shares_cd")
        _shares = shares_cd or shares

        if _shares and _shares > 0 and ll:
            res["LPA"] = ll * 1_000_000 / _shares  # LL em R$ mil → R$ por ação
        else:
            res["LPA"] = info.get("trailingEps") or info.get("epsTrailingTwelveMonths")

        if _shares and _shares > 0 and pl:
            res["VPA"] = pl * 1_000_000 / _shares
        else:
            res["VPA"] = info.get("bookValue")

        # Múltiplos de mercado
        lpa = res.get("LPA"); vpa = res.get("VPA")
        if preco and lpa and lpa != 0: res["PL_mult"] = preco / lpa
        if preco and vpa and vpa != 0: res["PVP"]     = preco / vpa

        # EV/EBITDA
        if ev and ebitda_yf and ebitda_yf != 0:
            res["EV_EBITDA"] = ev / ebitda_yf

        # DL/EBITDA e FCO/EBITDA
        dl = res.get("DL"); fco = res.get("FCO")
        if dl is not None and ebitda and ebitda != 0:
            res["DL_EBITDA"] = dl / ebitda
        if fco and ebitda and ebitda != 0:
            res["FCO_EBITDA"] = fco / ebitda * 100

        # DY
        dy = info.get("dividendYield")
        res["DY"] = dy * 100 if dy else None

        # ROE e ROIC
        if ll and pl and pl != 0:
            res["ROE"] = ll / pl * 100
        at = res.get("AT"); ebit = res.get("EBIT")
        if ebit and at and at != 0:
            # ROIC ≈ EBIT(1-t) / (AT - PC)  | t ≈ 34% Brasil
            pc  = res.get("PC") or 0
            nopat = ebit * 0.66
            ic    = at - pc
            res["ROIC"] = nopat / ic * 100 if ic != 0 else None

        # Liquidez e risco (yfinance tem esses direto)
        res["liq_corrente"] = info.get("currentRatio")
        res["liq_seca"]     = info.get("quickRatio")
        res["beta"]         = info.get("beta")
        res["52w_high"]     = getattr(fi, "year_high", None) or info.get("fiftyTwoWeekHigh")
        res["52w_low"]      = getattr(fi, "year_low",  None) or info.get("fiftyTwoWeekLow")
        res["vol_medio"]    = getattr(fi, "three_month_average_volume", None) or info.get("averageVolume")
        res["peg"]          = info.get("pegRatio")
        res["trailing_pe"]  = info.get("trailingPE")
        res["forward_pe"]   = info.get("forwardPE")
        res["ps_ratio"]     = info.get("priceToSalesTrailing12Months")
        res["pb_ratio"]     = info.get("priceToBook")

        # Consenso analistas
        res["preco_alvo"]   = info.get("targetMeanPrice")
        res["preco_min"]    = info.get("targetLowPrice")
        res["preco_max"]    = info.get("targetHighPrice")
        res["recomendacao"] = (info.get("recommendationKey") or "—").upper()
        res["n_analistas"]  = info.get("numberOfAnalystOpinions", 0)

        # Dados empresa
        res["nome_empresa"] = info.get("longName") or info.get("shortName")
        res["setor"]        = info.get("sector")
        res["industria"]    = info.get("industry")
        res["pais"]         = info.get("country")

    except Exception as e:
        res["erro_yf"] = str(e)

    return res


# ─────────────────────────────────────────────────────────────────
# 4. PROVENTOS — yfinance
# ─────────────────────────────────────────────────────────────────
def get_proventos(ticker_sa, anos=5):
    try:
        import yfinance as yf
        divs = yf.Ticker(ticker_sa).dividends
        if divs.empty: return pd.DataFrame({"Aviso": ["Sem proventos"]})
        cutoff = pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(years=anos)
        divs   = divs[divs.index >= cutoff].reset_index()
        divs.columns = ["Data", "Valor (R$)"]
        divs["Data"] = divs["Data"].dt.strftime("%d/%m/%Y")
        divs["Valor (R$)"] = divs["Valor (R$)"].round(4)
        return divs
    except Exception as e:
        return pd.DataFrame({"Erro": [str(e)]})


# ─────────────────────────────────────────────────────────────────
# 5. CONSENSO — yfinance
# ─────────────────────────────────────────────────────────────────
def get_consenso(ticker_sa):
    try:
        import yfinance as yf
        info = yf.Ticker(ticker_sa).info
        return {
            "preco_alvo":   info.get("targetMeanPrice"),
            "preco_min":    info.get("targetLowPrice"),
            "preco_max":    info.get("targetHighPrice"),
            "recomendacao": (info.get("recommendationKey") or "—").upper(),
            "n_analistas":  info.get("numberOfAnalystOpinions", 0),
            "fonte":        "Yahoo Finance",
        }
    except Exception as e:
        return {"erro": str(e)}


# ─────────────────────────────────────────────────────────────────
# TESTE
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Teste comdinheiro_client v4 ===\n")
    c = test_connection()
    print(f"1. Conexão: {'OK' if c['ok'] else 'ERRO'} — {c['msg']}\n")

    print("2. KPIs WEGE3:")
    kpi = get_fundamentalista("WEGE3", "WEGE3.SA")
    for k, v in sorted(kpi.items()):
        if k.startswith("serie_"): continue
        if v is not None:
            print(f"   {k:20s}: {v:.4f}" if isinstance(v, float) else f"   {k:20s}: {v}")

    print("\n3. Proventos WEGE3 (2 anos):")
    print(get_proventos("WEGE3.SA", anos=2).to_string())