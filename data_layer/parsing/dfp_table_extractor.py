import pdfplumber
import pandas as pd
import re


class DFPTableExtractor:

    def __init__(self, file_path):
        self.file_path = file_path

    def extract_tables(self):

        structured = []

        with pdfplumber.open(self.file_path) as pdf:

            for page in pdf.pages:
                tables = page.extract_tables()

                if not tables:
                    continue

                for table in tables:

                    if not table or len(table) < 2:
                        continue

                    header = table[0]

                    years = []
                    for col in header:
                        if col:
                            match = re.search(r"(20\d{2})", col)
                            years.append(match.group(1) if match else None)
                        else:
                            years.append(None)

                    for row in table[1:]:

                        if not row or not row[0]:
                            continue

                        label = row[0].strip()

                        for i in range(1, len(row)):

                            if i >= len(years) or not years[i]:
                                continue

                            raw = row[i]
                            if not raw:
                                continue

                            # ✅ CORREÇÃO BUG: except nu silenciava todos os erros
                            # incluindo erros de memória e outros críticos
                            value_str = str(raw).strip().replace(".", "").replace(",", ".")

                            # Trata parênteses como negativo: (1.234) → -1234
                            negative = value_str.startswith("(") and value_str.endswith(")")
                            if negative:
                                value_str = value_str[1:-1]

                            try:
                                value = float(value_str)
                                if negative:
                                    value = -value
                            except (ValueError, TypeError):
                                continue

                            structured.append({
                                "period":   years[i],
                                "category": label,
                                "value":    value
                            })

        if not structured:
            return pd.DataFrame(columns=["period", "category", "value"])

        return pd.DataFrame(structured)
