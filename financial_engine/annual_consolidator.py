from data_layer.database.db_manager import DatabaseManager


class AnnualConsolidator:

    def __init__(self):
        self.db = DatabaseManager()

    # ---------------------------------------------------
    # 🔹 Consolidar um ano específico
    # ---------------------------------------------------

    def consolidate_year(self, company_id, ano):

        # ✅ CORREÇÃO BUG: cursor não estava sendo fechado após uso
        # Em bancos SQLite com muitas operações, cursors abertos causam
        # travamentos e vazamento de memória
        cursor = self.db.conn.cursor()

        try:
            cursor.execute("""
                SELECT receita, ebitda, lucro_liquido
                FROM financials_quarterly
                WHERE company_id = ? AND ano = ?
            """, (company_id, ano))

            rows = cursor.fetchall()

            if not rows or len(rows) < 4:
                print(f"[WARN] Ano {ano} não possui 4 trimestres completos "
                      f"(encontrados: {len(rows) if rows else 0}). Pulando.")
                return None

            receita_total = sum(r[0] or 0 for r in rows)
            ebitda_total  = sum(r[1] or 0 for r in rows)
            lucro_total   = sum(r[2] or 0 for r in rows)

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

            print(f"[OK] Ano {ano} consolidado: "
                  f"Receita={receita_total:,.0f} | "
                  f"EBITDA={ebitda_total:,.0f} | "
                  f"Lucro={lucro_total:,.0f}")

            return {
                "ano": ano,
                "receita": receita_total,
                "ebitda": ebitda_total,
                "lucro_liquido": lucro_total
            }

        except Exception as e:
            # ✅ MELHORIA: rollback em caso de erro para não deixar dados corrompidos
            self.db.conn.rollback()
            print(f"[ERROR] Falha ao consolidar ano {ano}: {e}")
            return None

        finally:
            # ✅ CORREÇÃO: cursor sempre fechado, mesmo se der erro
            cursor.close()

    # ---------------------------------------------------
    # 🔹 Consolidar todos os anos disponíveis
    # ---------------------------------------------------

    def consolidate_all_years(self, company_id):

        cursor = self.db.conn.cursor()

        try:
            cursor.execute("""
                SELECT DISTINCT ano
                FROM financials_quarterly
                WHERE company_id = ?
                ORDER BY ano ASC
            """, (company_id,))

            anos = [row[0] for row in cursor.fetchall()]

        finally:
            cursor.close()

        if not anos:
            print(f"[WARN] Nenhum dado trimestral encontrado para company_id={company_id}")
            return []

        resultados = []

        for ano in anos:
            result = self.consolidate_year(company_id, ano)
            if result:
                resultados.append(result)

        print(f"\n[OK] Consolidação concluída: {len(resultados)}/{len(anos)} anos processados.")

        return resultados

    def close(self):
        self.db.close()
