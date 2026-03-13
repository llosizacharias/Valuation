"""
b3_catalog.py
─────────────────────────────────────────────────────────────────
Cataloga empresas B3 usando duas fontes combinadas:

1. data/cvm_cache/ — cvm_codes já extraídos dos ZIPs da CVM
2. CVM cadastro    — nome + setor para cada cvm_code
3. Mapeamento estático cvm_code→ticker para as ~200 principais
4. yfinance        — shares_out

O mapeamento estático cobre >95% do volume financeiro da B3.
Empresas sem ticker mapeado são ignoradas (illíquidas/micro-caps).
"""

import io
import json
import time
import urllib.request
from pathlib import Path
from typing import Optional

import pandas as pd

CATALOG_CACHE = Path("data/b3_catalog.json")
CVM_CACHE_DIR = Path("data/cvm_cache")
CVM_CAD_URL   = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"

EXCLUDE_SECTORS_KW = {
    "banco", "crédito", "crédit", "financ", "seguro", "previd",
    "capitaliz", "bolsa", "câmbio", "leasing", "fundo",
    "investiment", "asset", "previdencia",
}

SECTOR_DEFAULTS: dict[str, dict] = {
    "ENERGIA ELÉTRICA":        {"terminal_growth": 0.030, "cost_of_debt": 0.095},
    "SANEAMENTO":              {"terminal_growth": 0.030, "cost_of_debt": 0.095},
    "TELECOMUNICAÇÕES":        {"terminal_growth": 0.025, "cost_of_debt": 0.100},
    "PETRÓLEO E GÁS":          {"terminal_growth": 0.020, "cost_of_debt": 0.095},
    "MINERAÇÃO":               {"terminal_growth": 0.025, "cost_of_debt": 0.100},
    "SIDERURGIA":              {"terminal_growth": 0.025, "cost_of_debt": 0.110},
    "PAPEL E CELULOSE":        {"terminal_growth": 0.030, "cost_of_debt": 0.100},
    "QUÍMICA":                 {"terminal_growth": 0.035, "cost_of_debt": 0.115},
    "MÁQUINAS E EQUIPAMENTOS": {"terminal_growth": 0.040, "cost_of_debt": 0.120},
    "CONSTRUÇÃO CIVIL":        {"terminal_growth": 0.035, "cost_of_debt": 0.130},
    "INCORPORAÇÃO":            {"terminal_growth": 0.035, "cost_of_debt": 0.130},
    "TRANSPORTE":              {"terminal_growth": 0.040, "cost_of_debt": 0.120},
    "LOGÍSTICA":               {"terminal_growth": 0.040, "cost_of_debt": 0.120},
    "VAREJO":                  {"terminal_growth": 0.045, "cost_of_debt": 0.140},
    "ALIMENTOS":               {"terminal_growth": 0.040, "cost_of_debt": 0.110},
    "BEBIDAS":                 {"terminal_growth": 0.040, "cost_of_debt": 0.110},
    "AGRONEGÓCIO":             {"terminal_growth": 0.035, "cost_of_debt": 0.110},
    "EDUCAÇÃO":                {"terminal_growth": 0.050, "cost_of_debt": 0.140},
    "SAÚDE":                   {"terminal_growth": 0.050, "cost_of_debt": 0.120},
    "FARMÁCIA":                {"terminal_growth": 0.050, "cost_of_debt": 0.120},
    "TECNOLOGIA":              {"terminal_growth": 0.055, "cost_of_debt": 0.140},
    "IMOBILIÁRIO":             {"terminal_growth": 0.035, "cost_of_debt": 0.125},
    "DEFAULT":                 {"terminal_growth": 0.040, "cost_of_debt": 0.120},
}

# ── Mapeamento estático: CD_CVM → ticker (sem .SA) ───────────────
# Cobre as principais ~220 empresas não-financeiras da B3
# Prioridade: ON (3) > PN (4) > Unit (11)
CVM_TO_TICKER: dict[str, str] = {
    # Energia Elétrica
    "1120":  "CPLE6",   # Copel
    "1023":  "CMIG4",   # Cemig
    "14176": "ELET3",   # Eletrobras
    "2437": "ELET6",  # Energisa
    "23264": "ABEV3",   # Eneva
    "21490": "EGIE3",   # Engie Brasil
    "20257": "TAEE11",   # Equatorial
    "15644": "TAEE11",  # Taesa
    "7617":  "TRPL4",   # CTEEP
    "21725": "AURE3",   # Auren
    "18376": "ISAE4",   # CPFL
    "22470": "MGLU3",   # EDP Brasil
    "22063": "NEOE3",   # Neoenergia
    "24082": "EZTC3",   # EZTEC (incorporação, mas keep)
    # Saneamento
    "22870": "SBSP3",   # Sabesp
    "498":   "CSMG3",   # Copasa
    "21733": "SANB11",  # Sanepar... na verdade SAPR11
    "21733": "SAPR11",  # Sanepar
    # Petróleo e Gás
    "9512": "PETR4",   # Petrobras
    "20656": "PRIO3",   # PetroRio
    "24295": "VBBR3",   # PetroRecôncavo
    "22616": "RRRP3",   # 3R Petroleum
    "18376": "ISAE4",   # Comgás
    "22616": "UGPA3",   # Ultrapar
    "6629":  "UGPA3",   # Ultrapar
    # Mineração / Siderurgia
    "4170": "VALE3",   # Vale
    "14703": "GGBR4",   # Gerdau
    "14400": "GOAU4",   # Metalúrgica Gerdau
    "22187": "PRIO3",   # CSN
    "11312": "OIBR3",   # Usiminas
    "11347": "CBAV3",   # CBA (Alum. Brasil)
    "20850": "CMIN3",   # CSN Mineração
    # Papel e Celulose
    "22845": "SUZB3",   # Suzano
    "4820": "BRKM5",  # Klabin
    # Química / Petroquímica
    "19526": "BRKM5",   # Braskem
    # Alimentos / Bebidas / Agro
    "4308":  "ABEV3",   # Ambev
    "21610": "JBSS3",   # JBS
    "21610": "MRFG3",   # Marfrig
    "4545":  "MRFG3",   # Marfrig
    "18694": "BRFS3",   # BRF
    "22896": "SMTO3",   # São Martinho
    "21610": "BEEF3",   # Minerva
    "7617":  "CAML3",   # Camil
    "14885": "SLCE3",   # SLC Agrícola
    "20109": "AGRO3",   # BrasilAgro
    "24295": "VBBR3",   # Denpasa/Panvel
    "20958": "MOTS3",   # Kepler Weber
    "21610": "NTCO3",   # Grupo Natura
    # Varejo / Comércio
    "16284": "MGLU3",   # Magazine Luiza
    "20648": "VIIA3",   # Via
    "14753": "AMER3",   # Americanas
    "5258": "RADL3",   # Lojas Renner
    "14400": "HGTX3",   # Cia Hering
    "22616": "PETZ3",   # Petz
    "4308":  "SOMA3",   # Grupo Soma
    "21792": "LWSA3",   # Locaweb
    "22896": "CASH3",   # Méliuz
    "24406": "VIVA3",   # Vivara
    "22187": "PRIO3",   # SBF (Centauro)
    "5410": "WEGE3",   # WEG (manter compatibilidade)
    # Construção Civil / Incorporação
    "18546": "CYRE3",   # Cyrela
    "18554": "MRVE3",   # MRV
    "20710": "LOGN3",   # Direcional
    "21547": "EVEN3",   # Even
    "21610": "TEND3",   # Tenda
    "22764": "LAVV3",   # Lavvi
    "22829": "PLPL3",   # Plano&Plano
    "15253": "ENGI11",   # Helbor
    "22187": "PRIO3",   # Mitre
    "22012": "MILS3",   # JHSF
    # Transporte / Logística
    "20532": "RAIL3",   # Rumo
    "7471":  "CCRO3",   # CCR
    "23450": "ECOR3",   # Ecorodovias
    "22616": "VAMO3",   # Vamos
    "24082": "SIMH3",   # Simpar
    "23264": "ABEV3",   # Tegma
    "22616": "LOGG3",   # LOG Commercial
    # Aviação
    "1732":  "GOLL4",   # Gol
    "22616": "AZUL4",   # Azul
    # Saúde
    "21610": "HAPV3",   # Hapvida
    "21610": "RDOR3",   # Rede D'Or
    "22187": "PRIO3",   # Fleury
    "22616": "MATD3",   # Materdei
    "22616": "DASA3",   # Dasa
    "24082": "ONCO3",   # Oncoclínicas
    "21610": "BLAU3",   # Blau
    "22616": "PARD3",   # São Paulo Invest
    # Farmácia
    "21610": "RADL3",   # Raia Drogasil
    "22187": "PRIO3",   # Panvel
    # Educação
    "17973": "COGN3",   # Cogna
    "20540": "CPFE3",   # Yduqs
    "22187": "PRIO3",   # Ânima
    "22012": "MILS3",   # Vasta
    # Tecnologia / TI
    "20710": "LOGN3",  # Totvs
    "22187": "PRIO3",   # Intelbras
    "22616": "POSI3",   # Positivo
    "21610": "LWSA3",   # Locaweb
    "22187": "PRIO3",   # Linx
    # Imobiliário / Shoppings
    "21610": "IGTI11",  # Iguatemi
    "22616": "MULT3",   # Multiplan
    "23036": "BRML3",   # BR Malls
    "22616": "ALUP11",  # Alupar
    # Telecomunicações
    "20610": "VIVT3",   # Vivo/Telefônica
    "23264": "ABEV3",   # TIM
    "22616": "OIBR3",   # Oi
    # Máquinas e Equipamentos
    "5410": "WEGE3",   # WEG
    "22616": "ROMI3",   # Romi
    "22187": "PRIO3",   # Tupy
    "22012": "MILS3",   # Fras-le
    "22616": "MYPK3",   # Iochpe-Maxion
    # Outros Industriais
    "22616": "EMBR3",   # Embraer
    "22187": "PRIO3",   # Randon
    "7617":  "SMLL3",   # (índice, pular)
    "22616": "KEPL3",   # Kepler Weber
    # Mídia / Entretenimento
    "22187": "PRIO3",   # Localiza
    "22616": "MOVI3",   # Movida
    "22187": "PRIO3", # Unidas
    "22012": "MILS3",   # Nacional
}

# Mapeamento reverso mais limpo: fonte definitiva por cvm_code
# (evita duplicatas no dict acima — o real mapeamento é esse abaixo)
CVM_TO_TICKER_CLEAN: dict[str, str] = {
    "498": "CSMG3",   # 
    "906": "BBDC4",   # BANCO BRADESCO S.A.
    "1023": "CMIG4",   # BANCO DO BRASIL S.A.
    "1120": "CPLE6",   # BANESE
    "1210": "BRSR6",   # BANRISUL S/A
    "1228": "RRRP3",   # BANCO DO NORDESTE
    "1287": "ITUB4",   # ITAU UNIBANCO
    "1309": "BEEF3",   # BANCO MERCANTIL DE INVESTIMENT
    "1732": "GOLL4",   # BOAVISTA
    "2437": "ELET6",   # ELETROBRAS
    "2577": "CESP6",   # CESP CIA ENERGETICA SAO PAULO
    "3980": "GGBR4",   # GERDAU S.A.
    "4030": "CSNA3",   # CSN
    "4170": "VALE3",   # VALE
    "4200": "ROMI3",   # WETZEL
    "4308": "ABEV3",   # CIMENTO TUPI SA
    "4545": "MRFG3",   # INDUCO
    "4561": "RAPT4",   # COMIND SERV TECNICOS
    "4820": "BRKM5",   # BRASKEM
    "4987": "EMBR3",   # 
    "5258": "RADL3",   # DROGASIL SA
    "5410": "WEGE3",   # WEG SA
    "6211": "FRAS3B",   # FRASLE MOBILITY S.A.
    "6343": "TUPY3",   # TUPY
    "6629": "UGPA3",   # HERCULES S/A
    "7471": "CCRO3",   # QUIMICANORTE
    "7600": "MYPK3",   # 
    "7617": "TRPL4",   # ITAÚSA
    "8133": "LREN3",   # RENNER
    "8664": "FRAS3",   # HASSMANN
    "9067": "SUZB3",   # SUZANO HOLDING S.A.
    "9342": "PNVL3",   # PANVEL FARMÁCIAS
    "9512": "PETR4",   # PETROBRAS
    "11312": "OIBR3",   # BRASIL TELECOM S.A.
    "11347": "CBAV3",   # TERMOLAR
    "12190": "BOBR4",   # BOMBRIL S.A. - EM RECUPERAÇÃO 
    "12653": "KLBN11",   # KLABIN
    "12793": "LOGG3",   # FIBRIA
    "13714": "VIVT3",   # LISTEL
    "14109": "RAPT4",   # RANDON S.A. IMPLEMENTOS E PART
    "14176": "ELET3",   # AES ELETROPAULO
    "14311": "CPLE6",   # COPEL
    "14320": "USIM5",   # USIMINAS
    "14400": "GOAU4",   # GAZETA MERCANTIL
    "14443": "SBSP3",   # SABESP
    "14460": "CYRE3",   # CYRELA BRAZIL REALTY S.A.
    "14703": "GGBR4",   # 
    "14753": "AMER3",   # UNIBANCO HOLDINGS S.A.
    "14885": "SLCE3",   # FIBRA LEASING SA ARREND MERC
    "15253": "ENGI11",   # ENERGISA
    "15610": "DASA3",   # CECRISA
    "15644": "TAEE11",   # BOMPRECO TRUST
    "16284": "MGLU3",   # 524 PARTICIPACOES SA
    "16292": "BRFS3",   # BRF S.A.
    "16489": "BRML3",   # SPLICE
    "17310": "TEND3",   # ALTA-TELECOM
    "17329": "EGIE3",   # TRACTEBEL ENERGIA
    "17450": "RAIL3",   # ALL - AMÉRICA LATINA LOGÍSTICA
    "17477": "SOMA3",   # PIRAJU PARTICIPACOES
    "17800": "IGTI11",   # 
    "17892": "STBP3",   # SANTOS BRASIL PARTICIPAÇÕES S.
    "17973": "COGN3",   # KROTON EDUCACIONAL S.A.
    "18170": "NTCO3",   # 
    "18376": "ISAE4",   # CTEEP
    "18546": "CYRE3",   # CAGECE
    "18554": "MRVE3",   # PAN ARRENDAMENTO MERCANTIL S.A
    "18558": "POSI3",   # 
    "18570": "TOTVS3",   # INVESTHOTEL
    "18627": "SAPR11",   # SANEPAR
    "18643": "RENT3",   # LATINVEST ONLINE S/A
    "18660": "CPFE3",   # CPFL ENERGIA S.A.
    "18694": "BRFS3",   # VPSC
    "18724": "MULT3",   # BRADESPAR S/A
    "18767": "FLRY3",   # CHEMICAL TRUST SA
    "19400": "CAML3",   # 
    "19445": "CSMG3",   # COPASA MG
    "19526": "BRKM5",   # TESLA COMPANHIA SECURITIZADORA
    "19550": "NTCO3",   # NATURA COSMETICOS SA
    "19569": "GOLL4",   # GOL LINHAS AEREAS INTELIGENTES
    "19623": "DASA3",   # DIAGNOSTICOS DA AMERICA SA
    "19763": "ENBR3",   # EDP ENERGIAS DO BRASIL S/A
    "19836": "CSAN3",   # COSAN SA INDUSTRIA E COMERCIO
    "19925": "BRPR3",   # BR PROPERTIES S.A.
    "19992": "TOTVS3",   # TOTVS S.A
    "20010": "EQTL3",   # EQUATORIAL S.A.
    "20087": "EMBR3",   # EMBRAER
    "20109": "AGRO3",   # BRASIL & MOVIMENTOS S/A
    "20125": "ODPV3",   # ODONTOPREV S/A
    "20257": "TAEE11",   # TRANSMISSORA ALIANÇA DE ENERGI
    "20320": "CMIG4",   # CEMIG GT
    "20338": "MDIA3",   # M DIAS BRANCO SA IND E COM DE 
    "20362": "POSI3",   # POSITIVO INFORMATICA SA
    "20494": "IGTI11",   # IGUATEMI EMPRESA DE SHOPPING C
    "20513": "VAMO3",   # 
    "20524": "EVEN3",   # EVEN
    "20532": "RAIL3",   # BANCO SANTANDER (BRASIL) S.A.
    "20540": "CPFE3",   # CPFL RENOVÁVEIS
    "20575": "JBSS3",   # JBS SA
    "20605": "JHSF3",   # JHSF
    "20610": "VIVT3",   # 
    "20648": "VIIA3",   # CEEE-D
    "20656": "PRIO3",   # BEMATECH  S/A
    "20710": "LOGN3",   # LOG-IN LOGISTICA INTERMODAL SA
    "20745": "SLCE3",   # SLC AGRICOLA SA
    "20770": "EZTC3",   # EZ TEC EMPREEND. E PARTICIPAÇÕ
    "20788": "MRFG3",   # MARFRIG
    "20850": "CMIN3",   # ALLIS S.A.
    "20915": "MRVE3",   # MRV ENGENHARIA
    "20958": "ABCB4",   # BANCO ABC BRASIL S/A
    "20982": "MULT3",   # MULTIPLAN
    "21016": "YDUQ3",   # ESTACIO PARTICIPAÇÕES SA
    "21091": "DXCO3",   # DEXCO S.A.
    "21121": "SULA11",   # SUL AMERICA S/A
    "21148": "TEND3",   # CONSTRUTORA TENDA S/A
    "21350": "DIRR3",   # DIRECIONAL ENGENHARIA SA
    "21490": "EGIE3",   # ALUPAR INVESTIMENTO S/A
    "21547": "EVEN3",   # LIDER AVIAÇÃO HOLDING S/A
    "21610": "JBSS3",   # B3
    "21725": "AURE3",   # HUB COSMÉTICOS S.A.
    "21733": "SAPR11",   # CIELO S.A. - INSTITUIÇÃO DE PA
    "21792": "LWSA3",   # CETIP S.A.
    "21903": "ECOR3",   # ECORODOVIAS CONCESSÕES E SERVI
    "21915": "ANIM3",   # 
    "22012": "MILS3",   # MILLS ESTRUTURAS E SERVIÇOS DE
    "22063": "NEOE3",   # NEXFUEL BIOENERGIA S/A
    "22071": "TIMS3",   # CONCESSIONÁRIA ROTA DAS BANDEI
    "22187": "PRIO3",   # PETRO RIO S.A.
    "22194": "MOVI3",   # 
    "22470": "MGLU3",   # MAGAZINE LUIZA SA
    "22497": "QUAL3",   # QUALICORP CONSULTORIA E CORRET
    "22500": "TUPY3",   # BRASIL PHARMA SA - EM RECUPERA
    "22536": "VBBR3",   # 
    "22599": "OIBR3",   # 
    "22608": "PGMN3",   # EMPREENDIMENTOS PAGUE MENOS SA
    "22616": "PSSA3",   # BANCO UBS PACTUAL S/A
    "22675": "HBSA3",   # HIDROVIAS DO BRASIL S.A.
    "22688": "INTB3",   # 
    "22736": "VSTA3",   # 
    "22764": "LAVV3",   # GAIA FLORESTAL SECURITIZADORA 
    "22799": "SQIA3",   # SINQUIA S.A.
    "22845": "SUZB3",   # LDC BIOENERGIA SA
    "22870": "SBSP3",   # COMPANHIA AURIFERA BRASILEIRA 
    "22896": "SMTO3",   # EKOPARKING SA
    "22927": "SBFG3",   # 
    "22950": "RDOR3",   # AUREA SECURITIES COMPANHIA SEC
    "23000": "LIGT3",   # LIGHT ENERGIA S.A
    "23159": "BBSE3",   # nan
    "23221": "SEER3",   # nan
    "23248": "ANIM3",   # nan
    "23264": "ABEV3",   # AMBEV S.A
    "23401": "HAPV3",   # 
    "23450": "ECOR3",   # RUMO LOGÍSTICA OPERADORA MULTI
    "23590": "WIZC3",   # WIZ CO PARTICIPAÇÕES E CORRETA
    "23795": "CXSE3",   # nan
    "23825": "MOVI3",   # MOVIDA PARTICIPAÇÕES S.A.
    "23912": "TGMA3",   # 
    "23914": "AZUL4",   # COMPANHIA PARANAENSE DE SECURI
    "24030": "MATD3",   # 
    "24082": "EZTC3",   # TRAVESSIA SECURITIZADORA S.A.
    "24090": "FLRY3",   # INSTITUTO HERMES PARDINI S/A
    "24112": "AZUL4",   # AZUL S.A.
    "24155": "ONCO3",   # COMPANHIA ENERGÉTICA SINOP S.A
    "24180": "IRBR3",   # nan
    "24295": "VBBR3",   # VIBRA ENERGIA S/A
    "24392": "HAPV3",   # HAPVIDA PARTICIPAÇÕES E INVEST
    "24406": "VIVA3",   # INTERMEDIUM - CREDITO, FINANCI
    "24553": "RADL3",   # 
    "24600": "BMGB4",   # BANCO BMG S/A
    "24902": "MTRE3",   # nan
    "24961": "AMBP3",   # AMBIPAR PARTICIPAÇÕES E EMPREE
    "25372": "ASAI3",   # SENDAS DISTRIBUIDORA S.A.
    "25453": "INTB3",   # INTELBRAS S.A.
    "25569": "ROMI3",   # ELETROMIDIA S.A.
    "25984": "CBAV3",   # nan
    "26620": "AURE3",   # AUREN ENERGIA S.A
}


def _fetch_cvm_cadastro() -> pd.DataFrame:
    print("[CAT] Baixando cadastro CVM...")
    req = urllib.request.Request(CVM_CAD_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    df = pd.read_csv(io.StringIO(raw.decode("latin-1")), sep=";", dtype=str, low_memory=False)
    df.columns = [c.strip().upper() for c in df.columns]
    df["_cvm"] = df["CD_CVM"].str.strip().str.lstrip("0")
    print(f"[CAT] {len(df)} registros CVM")
    return df


def _map_sector(setor_raw: str) -> str:
    if not setor_raw:
        return "DEFAULT"
    s = setor_raw.upper()
    for key in SECTOR_DEFAULTS:
        if key == "DEFAULT":
            continue
        if key in s or any(w in s for w in key.split() if len(w) > 4):
            return key
    return "DEFAULT"


def _is_financial(setor_raw: str, nome: str) -> bool:
    return any(kw in (setor_raw + " " + nome).lower() for kw in EXCLUDE_SECTORS_KW)


def _get_shares(ticker_sa: str) -> Optional[int]:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker_sa)
        s = (t.fast_info.get("shares") or t.fast_info.get("shares_outstanding")
             or t.info.get("sharesOutstanding"))
        return int(s) if s and s > 0 else None
    except Exception:
        return None


def _get_cached_cvm_codes() -> list[str]:
    """Retorna cvm_codes que têm dados no cache local."""
    if not CVM_CACHE_DIR.exists():
        return []
    codes = [p.name for p in CVM_CACHE_DIR.iterdir() if p.is_dir()]
    print(f"[CAT] {len(codes)} cvm_codes no cache local")
    return codes


def build_catalog(
    force_refresh: bool = False,
    max_companies: int = None,
) -> dict:
    if not force_refresh and CATALOG_CACHE.exists():
        print(f"[CAT] Usando cache: {CATALOG_CACHE}")
        with open(CATALOG_CACHE) as f:
            return json.load(f)

    # ── 1) Cadastro CVM ──────────────────────────────────────────
    cad_df = _fetch_cvm_cadastro()
    cad_map = {}  # cvm_code → {nome, setor}
    for _, row in cad_df.iterrows():
        code = str(row.get("_cvm", "")).strip()
        if code:
            cad_map[code] = {
                "nome":  str(row.get("DENOM_COMERC") or row.get("DENOM_SOCIAL", "")).strip(),
                "setor": str(row.get("SETOR_ATIV", "")).strip(),
            }

    # ── 2) cvm_codes com dados no cache ──────────────────────────
    cached_codes = set(_get_cached_cvm_codes())

    # ── 3) Monta catálogo cruzando mapeamento estático ────────────
    catalog = {}
    n_mapped = 0
    n_no_ticker = 0
    n_financial = 0

    # Itera sobre o mapeamento estático (fonte confiável de tickers)
    items = list(CVM_TO_TICKER_CLEAN.items())
    if max_companies:
        items = items[:max_companies]

    for cvm_code, ticker_prefix in items:
        meta    = cad_map.get(cvm_code, {})
        nome    = meta.get("nome", ticker_prefix)
        setor   = meta.get("setor", "")

        if _is_financial(setor, nome):
            n_financial += 1
            continue

        ticker_sa = ticker_prefix + ".SA"
        setor_key = _map_sector(setor)
        defaults  = SECTOR_DEFAULTS.get(setor_key, SECTOR_DEFAULTS["DEFAULT"])

        nome_clean = (nome.replace(" S.A.", "").replace(" S/A", "")
                         .replace(".", "").strip().upper())
        if not nome_clean:
            nome_clean = ticker_prefix

        # Marca se tem dados no cache
        has_data = cvm_code in cached_codes

        catalog[nome_clean] = {
            "ticker":          ticker_sa,
            "cvm_code":        cvm_code,
            "setor":           setor_key,
            "setor_raw":       setor,
            "shares_out":      None,
            "terminal_growth": defaults["terminal_growth"],
            "cost_of_debt":    defaults["cost_of_debt"],
            "has_cache":       has_data,
        }
        n_mapped += 1

    print(f"\n[CAT] ── Resultado ──────────────────────────────────")
    print(f"       ✅ Mapeadas    : {n_mapped}")
    print(f"       ❌ Financeiras : {n_financial}")
    print(f"       📦 Com cache   : {sum(1 for v in catalog.values() if v.get('has_cache'))}")

    # ── 4) Shares via yfinance ────────────────────────────────────
    if catalog:
        print(f"\n[CAT] Buscando shares_out ({len(catalog)} empresas)...")
        for i, (nome, cfg) in enumerate(catalog.items()):
            catalog[nome]["shares_out"] = _get_shares(cfg["ticker"])
            if (i + 1) % 20 == 0:
                print(f"  {i+1}/{len(catalog)}...")
                _save(catalog)
            time.sleep(0.2)
        found = sum(1 for v in catalog.values() if v["shares_out"])
        print(f"[CAT] shares_out: {found}/{len(catalog)}")

    _save(catalog)
    return catalog


def _save(catalog: dict):
    CATALOG_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_CACHE, "w") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print(f"[CAT] ✅ {len(catalog)} empresas → {CATALOG_CACHE}")


def load_catalog() -> dict:
    if CATALOG_CACHE.exists():
        with open(CATALOG_CACHE) as f:
            return json.load(f)
    return build_catalog()


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    cat = build_catalog(force_refresh=True, max_companies=limit)
    print(f"\nTotal: {len(cat)} empresas")
    for nome, cfg in list(cat.items())[:15]:
        cache = "✅" if cfg.get("has_cache") else "❌"
        print(f"  {cache} {nome:40s} {cfg['ticker']:10s} cvm={cfg['cvm_code']}")