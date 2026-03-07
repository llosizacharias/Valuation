import requests
from datetime import datetime

DFP_KEYWORDS = [
    "dfp", "itr", "release", "resultado", "apresentacao",
    "demonstracao", "financeiro", "trimestral", "anual"
]

FALLBACK_CATEGORIES = [
    "central_de_resultados_release_resultados",
    "central_de_resultados_itr_dfp",
    "central_de_resultados_apresentacao_dos_resultados",
    "central_de_resultados_apresentacao_resultados",
    "release_de_resultados",
    "itr_dfp",
    "apresentacao_resultados",
]

# Endpoint original que funcionou para WEG
SEARCH_ENDPOINT = "https://apicatalog.mziq.com/filemanager/search"


class MZAPIProvider:

    def __init__(self, empresa: str, company_id: str, referer_url: str):
        self.empresa     = empresa
        self.company_id  = company_id
        self.referer_url = referer_url.rstrip("/")

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent":   "Mozilla/5.0",
        })

        self._discovered_categories = None
        self._working_origin        = None   # cache do origin que funcionou

    # ─────────────────────────────────────────────────────
    # REQUEST COM RETRY DE ORIGIN
    # ─────────────────────────────────────────────────────

    def _origins_to_try(self) -> list:
        """Gera variações de Origin/Referer para tentar."""
        base = self.referer_url
        candidates = []

        for url in [base, base + "/"]:
            # https e http
            https = url.replace("http://", "https://")
            http  = url.replace("https://", "http://")
            for o in [https, http]:
                if o not in candidates:
                    candidates.append(o)

        return candidates

    def _post(self, payload: dict, timeout: int = 15):
        """
        POST com retry em variações de Origin/Referer.
        Cacheia o origin que funcionou para chamadas subsequentes.
        """
        # Se já sabemos qual origin funciona, usa direto
        if self._working_origin:
            self.session.headers.update({
                "Referer": self._working_origin,
                "Origin":  self._working_origin,
            })
            try:
                resp = self.session.post(SEARCH_ENDPOINT, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    return resp
                # Origin parou de funcionar, força redescoberta
                if resp.status_code in (401, 403):
                    self._working_origin = None
            except Exception:
                self._working_origin = None

        # Tenta todos os origins
        for origin in self._origins_to_try():
            self.session.headers.update({
                "Referer": origin,
                "Origin":  origin,
            })
            try:
                resp = self.session.post(SEARCH_ENDPOINT, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    self._working_origin = origin
                    print(f"  [OK] Origin aceito: {origin}")
                    return resp
                if resp.status_code not in (401, 403):
                    return resp   # 404/500 etc — não adianta mudar origin
            except Exception as e:
                print(f"  [WARN] {origin}: {e}")
                continue

        return None

    # ─────────────────────────────────────────────────────
    # DESCOBERTA DE CATEGORIAS
    # Faz uma busca sem filtro de categoria para ver o que existe
    # ─────────────────────────────────────────────────────

    def discover_categories(self, year: int = None) -> list:
        if year is None:
            year = datetime.now().year

        payload = {
            "companyId":  self.company_id,
            "categories": [],
            "language":   "pt_BR",
            "published":  True,
            "year":       str(year),
            "page":       1,
            "pageSize":   200,
        }

        try:
            resp = self._post(payload)
            if not resp or resp.status_code != 200:
                return []

            data  = resp.json()
            items = data.get("data", {}).get("document_metas", [])

            all_cats = set()
            for item in items:
                cat = item.get("internal_name", "")
                if cat:
                    all_cats.add(cat)

            relevant = [c for c in all_cats if any(kw in c.lower() for kw in DFP_KEYWORDS)]
            result   = relevant if relevant else list(all_cats)

            if result:
                print(f"  Categorias disponíveis ({self.empresa}): {result}")
            return result

        except Exception as e:
            print(f"  [WARN] discover_categories: {e}")
            return []

    def _get_categories(self) -> list:
        if self._discovered_categories is not None:
            return self._discovered_categories

        for year in [datetime.now().year, datetime.now().year - 1]:
            cats = self.discover_categories(year)
            if cats:
                self._discovered_categories = cats
                return cats

        print(f"  [WARN] Usando categorias fallback para {self.empresa}")
        self._discovered_categories = FALLBACK_CATEGORIES
        return FALLBACK_CATEGORIES

    # ─────────────────────────────────────────────────────
    # BUSCA POR ANO
    # ─────────────────────────────────────────────────────

    def get_documents_by_year(self, year: int) -> list:

        categories = self._get_categories()
        page       = 1
        page_size  = 100
        documentos = []

        while True:
            payload = {
                "companyId":  self.company_id,
                "categories": categories,
                "language":   "pt_BR",
                "published":  True,
                "year":       str(year),
                "page":       page,
                "pageSize":   page_size,
            }

            resp = self._post(payload)

            if not resp:
                print(f"  [WARN] Sem resposta ({self.empresa} {year})")
                return documentos

            if resp.status_code != 200:
                print(f"  [WARN] HTTP {resp.status_code} ({self.empresa} {year})")
                return documentos

            try:
                data = resp.json()
            except Exception:
                return documentos

            items = (
                data.get("data", {}).get("document_metas")
                or data.get("document_metas")
                or []
            )

            if not items:
                break

            for item in items:
                if not isinstance(item, dict):
                    continue
                documentos.append({
                    "empresa":         self.empresa,
                    "ano":             year,
                    "titulo":          item.get("file_title"),
                    "categoria":       item.get("internal_name"),
                    "data_publicacao": item.get("file_published_date"),
                    "url":             item.get("file_url"),
                    "trimestre":       item.get("file_quarter"),
                })

            if len(items) < page_size:
                break
            page += 1

        return documentos

    # ─────────────────────────────────────────────────────
    # HISTÓRICO COMPLETO
    # ─────────────────────────────────────────────────────

    def get_all_available_documents(self, min_year: int = 2010) -> list:

        current_year = datetime.now().year
        historico    = []

        print(f"Descobrindo categorias ({self.empresa})...")
        self._get_categories()

        for year in range(current_year, min_year - 1, -1):
            print(f"  Buscando {year}...", end=" ", flush=True)
            docs = self.get_documents_by_year(year)
            if docs:
                print(f"{len(docs)} docs")
                historico.extend(docs)
            else:
                print("0")

        return historico