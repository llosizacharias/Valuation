from data_layer.database.db_manager import DatabaseManager


class FinancialRepository:

    def __init__(self):
        self.db = DatabaseManager()

    # =====================================================
    # QUARTERLY
    # =====================================================

    def save_quarterly(
        self,
        company_id,
        ano,
        trimestre,
        receita,
        ebitda,
        lucro_liquido
    ):

        cursor = self.db.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO financials_quarterly
            (company_id, ano, trimestre, receita, ebitda, lucro_liquido)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            ano,
            trimestre,
            receita,
            ebitda,
            lucro_liquido
        ))

        self.db.conn.commit()

    def get_quarterly_data(self, company_id):

        cursor = self.db.conn.cursor()

        cursor.execute("""
            SELECT ano, trimestre, receita, ebitda, lucro_liquido
            FROM financials_quarterly
            WHERE company_id = ?
            ORDER BY ano ASC, trimestre ASC
        """, (company_id,))

        rows = cursor.fetchall()

        result = []

        for row in rows:
            result.append({
                "ano": row[0],
                "trimestre": row[1],
                "receita": row[2],
                "ebitda": row[3],
                "lucro_liquido": row[4]
            })

        return result

    # =====================================================
    # ANNUAL
    # =====================================================

    def save_annual(
        self,
        company_id,
        ano,
        receita,
        ebitda,
        lucro_liquido
    ):

        cursor = self.db.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO financials_annual
            (company_id, ano, receita, ebitda, lucro_liquido)
            VALUES (?, ?, ?, ?, ?)
        """, (
            company_id,
            ano,
            receita,
            ebitda,
            lucro_liquido
        ))

        self.db.conn.commit()

    def get_annual_data(self, company_id, min_year=2014):

        cursor = self.db.conn.cursor()

        cursor.execute("""
            SELECT ano, receita, ebitda, lucro_liquido
            FROM financials_annual
            WHERE company_id = ?
            AND ano >= ?
            ORDER BY ano ASC
        """, (company_id, min_year))

        rows = cursor.fetchall()

        result = []

        for row in rows:
            result.append({
                "ano": row[0],
                "receita": row[1],
                "ebitda": row[2],
                "lucro_liquido": row[3]
            })

        return result

    def save_annual_balance(
        self,
        company_id,
        ano,
        short_term_debt=0,
        long_term_debt=0,
        cash=0,
        total_assets=0,
        total_equity=0,
        working_capital=0,
        capex=0
    ):

        cursor = self.db.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO financials_balance_annual
            (company_id, ano, short_term_debt, long_term_debt, cash,
            total_assets, total_equity, working_capital, capex)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            ano,
            short_term_debt,
            long_term_debt,
            cash,
            total_assets,
            total_equity,
            working_capital,
            capex
        ))

        self.db.conn.commit()

    def get_annual_balance(self, company_id, min_year=2014):

        cursor = self.db.conn.cursor()

        cursor.execute("""
            SELECT ano, short_term_debt, long_term_debt, cash,
                total_assets, total_equity, working_capital, capex
            FROM financials_balance_annual
            WHERE company_id = ?
            AND ano >= ?
            ORDER BY ano ASC
        """, (company_id, min_year))

        rows = cursor.fetchall()

        result = []

        for row in rows:
            result.append({
                "ano": row[0],
                "short_term_debt": row[1],
                "long_term_debt": row[2],
                "cash": row[3],
                "total_assets": row[4],
                "total_equity": row[5],
                "working_capital": row[6],
                "capex": row[7]
            })

        return result

    # =====================================================
    # CLOSE
    # =====================================================

    def close(self):
        self.db.close()