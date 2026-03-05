from data_layer.database.db_manager import DatabaseManager


class AnnualConsolidator:

    def __init__(self):
        self.db = DatabaseManager()

    # ---------------------------------------------------
    # 🔹 Consolidar um ano específico
    # ---------------------------------------------------

    def consolidate_year(self, company_id, ano):

        cursor = self.db.conn.cursor()

        cursor.execute("""
            SELECT receita, ebitda, lucro_liquido
            FROM financials_quarterly
            WHERE company_id = ? AND ano = ?
        """, (company_id, ano))

        rows = cursor.fetchall()

        if not rows or len(rows) < 4:
            print(f"Ano {ano} não possui 4 trimestres completos.")
            return None

        receita_total = sum(r[0] or 0 for r in rows)
        ebitda_total = sum(r[1] or 0 for r in rows)
        lucro_total = sum(r[2] or 0 for r in rows)

        cursor.execute("""
            INSERT OR REPLACE INTO financials_annual
            (company_id, ano, receita, ebitda, lucro_liquido)
            VALUES (?, ?, ?, ?, ?)
        """, (
            company_id,
            ano,
            receita_total,
            ebitda_total,
            lucro_total
        ))

        self.db.conn.commit()

        print(f"Ano {ano} consolidado com sucesso.")

        return {
            "ano": ano,
            "receita": receita_total,
            "ebitda": ebitda_total,
            "lucro_liquido": lucro_total
        }

    # ---------------------------------------------------
    # 🔹 Consolidar todos os anos disponíveis
    # ---------------------------------------------------

    def consolidate_all_years(self, company_id):

        cursor = self.db.conn.cursor()

        cursor.execute("""
            SELECT DISTINCT ano
            FROM financials_quarterly
            WHERE company_id = ?
        """, (company_id,))

        anos = [row[0] for row in cursor.fetchall()]

        resultados = []

        for ano in anos:
            result = self.consolidate_year(company_id, ano)
            if result:
                resultados.append(result)

        return resultados

    def close(self):
        self.db.close()