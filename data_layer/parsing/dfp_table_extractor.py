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

                for table in tables:

                    if not table or len(table) < 2:
                        continue

                    header = table[0]

                    # tentar identificar colunas que contenham ano
                    years = []

                    for col in header:
                        if col:
                            match = re.search(r"(20\d{2})", col)
                            if match:
                                years.append(match.group(1))
                            else:
                                years.append(None)
                        else:
                            years.append(None)

                    # agora iterar linhas de contas
                    for row in table[1:]:

                        if not row or not row[0]:
                            continue

                        label = row[0].strip()

                        for i in range(1, len(row)):

                            if i >= len(years):
                                continue

                            year = years[i]

                            if not year:
                                continue

                            value = row[i]

                            if not value:
                                continue

                            value = value.replace(".", "").replace(",", ".")

                            try:
                                value = float(value)
                            except:
                                continue

                            structured.append({
                                "period": year,
                                "category": label,
                                "value": value
                            })

        return pd.DataFrame(structured)