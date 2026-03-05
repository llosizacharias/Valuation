import sqlite3
from pathlib import Path


class DatabaseManager:

    def __init__(self, db_name="shipyard.db"):
        self.db_path = Path(db_name)
        self.conn = sqlite3.connect(self.db_path)
        self.create_tables()

    def create_tables(self):

        cursor = self.conn.cursor()

        # ------------------------------
        # Companies
        # ------------------------------

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT UNIQUE,
            nome TEXT,
            ri_url TEXT,
            provider TEXT,
            company_id_mz TEXT
        )
        """)

        # ------------------------------
        # Documents
        # ------------------------------

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            ano INTEGER,
            trimestre INTEGER,
            tipo TEXT,
            titulo TEXT,
            url TEXT,
            data_publicacao TEXT,
            UNIQUE(company_id, ano, trimestre, tipo),
            FOREIGN KEY(company_id) REFERENCES companies(id)
        )
        """)

        # ------------------------------
        # Financials Quarterly
        # ------------------------------

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS financials_quarterly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            ano INTEGER,
            trimestre INTEGER,
            receita REAL,
            ebitda REAL,
            lucro_liquido REAL,
            UNIQUE(company_id, ano, trimestre),
            FOREIGN KEY(company_id) REFERENCES companies(id)
        )
        """)

        # ------------------------------
        # Financials Annual
        # ------------------------------

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS financials_annual (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            ano INTEGER,
            receita REAL,
            ebitda REAL,
            lucro_liquido REAL,
            UNIQUE(company_id, ano),
            FOREIGN KEY(company_id) REFERENCES companies(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS financials_balance_annual (
            company_id INTEGER,
            ano INTEGER,
            short_term_debt REAL,
            long_term_debt REAL,
            cash REAL,
            total_assets REAL,
            total_equity REAL,
            working_capital REAL,
            capex REAL,
            PRIMARY KEY (company_id, ano)
        )
        """)

    def close(self):
        self.conn.close()