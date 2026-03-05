import pandas as pd
import re
import numpy as np
from rapidfuzz import fuzz
from unidecode import unidecode


TARGETS = {
    "receita": ["receita", "revenue", "vendas"],
    "ebitda": ["ebitda"],
    "imposto": ["imposto", "income tax", "ir"],
    "capex": ["capex", "investimento"],
    "wc": ["capital de giro", "working capital"]
}


def normalize_text(text):
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = unidecode(text)
    return text.strip()


def detect_year_columns(df):
    year_cols = {}
    for col in df.columns:
        match = re.search(r"20\d{2}", str(col))
        if match:
            year = int(match.group())
            year_cols[col] = year
    return year_cols


def normalize_number(value):
    if pd.isna(value):
        return np.nan

    if isinstance(value, str):
        value = value.replace(".", "").replace(",", ".")
        if "(" in value:
            value = "-" + value.replace("(", "").replace(")", "")
    try:
        return float(value)
    except:
        return np.nan


def score_line(label):
    label_norm = normalize_text(label)
    scores = {}

    for key, variations in TARGETS.items():
        best_score = 0
        for word in variations:
            score = fuzz.partial_ratio(word, label_norm)
            if score > best_score:
                best_score = score
        scores[key] = best_score

    best_match = max(scores, key=scores.get)
    return best_match, scores[best_match]


def parse_excel(file_path):

    xls = pd.ExcelFile(file_path)
    candidates = {}

    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df = df.dropna(how="all")
        df.columns = [str(c) for c in df.columns]

        year_cols = detect_year_columns(df)
        if not year_cols:
            continue

        for idx, row in df.iterrows():
            label = row.iloc[0]
            match, score = score_line(label)

            if score > 75:
                if match not in candidates:
                    candidates[match] = []

                extracted_values = {}
                for col, year in year_cols.items():
                    value = normalize_number(row[col])
                    if not np.isnan(value):
                        extracted_values[year] = value

                if extracted_values:
                    candidates[match].append({
                        "sheet": sheet,
                        "label": label,
                        "score": score,
                        "values": extracted_values
                    })

    return candidates
