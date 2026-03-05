from data_layer.database.db_manager import DatabaseManager


class DocumentRepository:

    def __init__(self):
        self.db = DatabaseManager()

    # ---------------------------------------------------
    # 🔹 Inserir ou obter empresa
    # ---------------------------------------------------

    def get_or_create_company(self, ticker, nome, ri_url, provider, company_id_mz):

        cursor = self.db.conn.cursor()

        cursor.execute(
            "SELECT id FROM companies WHERE ticker = ?",
            (ticker,)
        )

        result = cursor.fetchone()

        if result:
            return result[0]

        cursor.execute("""
            INSERT INTO companies (ticker, nome, ri_url, provider, company_id_mz)
            VALUES (?, ?, ?, ?, ?)
        """, (ticker, nome, ri_url, provider, company_id_mz))

        self.db.conn.commit()

        return cursor.lastrowid

    # ---------------------------------------------------
    # 🔹 Salvar documentos
    # ---------------------------------------------------

    def save_documents(self, company_id, documents):

        cursor = self.db.conn.cursor()

        for doc in documents:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO documents
                    (company_id, ano, trimestre, tipo, titulo, url, data_publicacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    company_id,
                    doc["ano"],
                    doc.get("trimestre"),
                    doc.get("categoria"),
                    doc.get("titulo"),
                    doc.get("url"),
                    doc.get("data_publicacao")
                ))
            except Exception as e:
                print("Erro ao salvar documento:", e)

        self.db.conn.commit()

    def close(self):
        self.db.close()