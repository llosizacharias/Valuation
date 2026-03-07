import pandas as pd
import re

# ✅ CORREÇÃO BUG CRÍTICO: unit_detector existia mas nunca era chamado
# Sem isso, empresas que reportam em R$ milhões (padrão B3) geravam
# valuations 1.000.000x menores que o real
from normalization.unit_detector import detect_unit_multiplier


class UniversalTableExtractor:

    def __init__(self, file_path):
        self.file_path = file_path

    # =====================================================
    # SAFE FLOAT ROBUSTO
    # =====================================================

    def safe_to_float(self, value):

        if isinstance(value, pd.Series):
            value = value.dropna()
            if value.empty:
                return None
            value = value.iloc[0]

        if pd.isna(value):
            return None

        value = str(value).strip()

        if value in ["", "-", "nan", "None", "N/A", "#N/A"]:
            return None

        value = value.replace(" ", "")

        negative = False
        if value.startswith("(") and value.endswith(")"):
            negative = True
            value = value[1:-1]

        # Notação científica
        if "e" in value.lower():
            # ✅ CORREÇÃO: except tipado — nunca usar except nu
            try:
                number = float(value)
                return -number if negative else number
            except (ValueError, TypeError):
                return None

        # Padrão brasileiro: 1.234.567,89
        if "," in value and "." in value:
            value = value.replace(".", "").replace(",", ".")
        elif "," in value:
            value = value.replace(",", ".")
        else:
            value = value.replace(",", "")

        try:
            number = float(value)
            return -number if negative else number
        except (ValueError, TypeError):
            return None

    # =====================================================
    # DETECÇÃO DE PERÍODO
    # =====================================================

    def is_period(self, value):
        if not isinstance(value, str):
            return False

        value = value.strip()

        if re.match(r"^20\d{2}$", value):
            return True

        if re.match(r"^[1-4][QT]\d{2}$", value.upper()):
            return True

        return False

    # =====================================================
    # DETECTAR LINHA DE PERÍODO
    # =====================================================

    def detect_period_row(self, df):
        for i in range(min(25, len(df))):
            row = df.iloc[i].astype(str)
            count = sum(self.is_period(x) for x in row)
            if count >= 3:
                return i
        return None

    # =====================================================
    # DETECTAR COLUNA DE LABELS
    # =====================================================

    def detect_label_col(self, df, start_row):
        """
        Detecta a coluna de labels como a que tem maior proporção
        de células com texto (não numérico) após a linha de período.

        ✅ CORREÇÃO: pandas StringArray mantém NaN como objeto nan, não string "nan"
           → verificação explícita com pd.isna() antes da comparação de string
        ✅ MELHORIA: ignora col 0 se ela for toda NaN (col de índice vazia)
        """
        data_slice = df.iloc[start_row:]

        best_col = 1  # começa em 1 — col 0 costuma ser índice/vazia
        best_score = -1

        for col_idx in range(len(df.columns)):
            col = data_slice.iloc[:, col_idx]
            text_count = 0
            for v in col:
                # ✅ CORREÇÃO: pd.isna() captura float NaN e pd.NA
                if pd.isna(v):
                    continue
                v_str = str(v).strip()
                if v_str in ("nan", "", "None", "NaN", "<NA>"):
                    continue
                if self.safe_to_float(v_str) is None:
                    text_count += 1

            score = text_count / max(len(col), 1)
            if score > best_score:
                best_score = score
                best_col = col_idx

        return best_col

    # =====================================================
    # DETECTAR ORIENTAÇÃO
    # =====================================================

    def detect_orientation(self, df):
        period_row = self.detect_period_row(df)

        if period_row is not None:
            return "horizontal", period_row

        for col in df.columns:
            col_values = df[col].astype(str)
            count = sum(self.is_period(x) for x in col_values)
            if count >= 3:
                return "vertical", col

        return None, None

    # =====================================================
    # EXTRAÇÃO LONG FORMAT
    # =====================================================

    def extract_long_format(self):

        # ✅ MELHORIA: ExcelFile usado como context manager — fecha automaticamente
        all_data = []

        with pd.ExcelFile(self.file_path) as xls:

            for sheet in xls.sheet_names:

                df_raw = pd.read_excel(xls, sheet_name=sheet, header=None)

                multiplier = detect_unit_multiplier(df_raw)

                orientation, ref = self.detect_orientation(df_raw)

                if orientation is None:
                    continue

                # ==========================
                # HORIZONTAL
                # ==========================
                if orientation == "horizontal":

                    period_row = ref
                    periods = df_raw.iloc[period_row]
                    data = df_raw.iloc[period_row + 1:].copy()
                    data.columns = periods

                    valid_columns = [
                        col for col in data.columns
                        if self.is_period(str(col))
                    ]

                    if not valid_columns:
                        continue

                    data = data[valid_columns]

                    # ✅ MELHORIA: usa detect_label_col mais robusto
                    label_col_idx = self.detect_label_col(df_raw, period_row + 1)
                    labels = df_raw.iloc[period_row + 1:, label_col_idx]

                    for idx, label in labels.items():

                        if pd.isna(label):
                            continue

                        for period in valid_columns:

                            value = data.loc[idx, period]
                            value = self.safe_to_float(value)

                            if value is None:
                                continue

                            value *= multiplier

                            all_data.append({
                                "sheet": sheet,
                                "label_original": str(label),
                                "period": str(period),
                                "value": value
                            })

                # ==========================
                # VERTICAL
                # ✅ MELHORIA: substituído iterrows() por itertuples() — mais rápido
                # ==========================
                elif orientation == "vertical":

                    period_col = ref

                    data = df_raw[
                        df_raw[period_col].apply(
                            lambda x: self.is_period(str(x))
                        )
                    ]

                    label_cols = [c for c in df_raw.columns if c != period_col]

                    # cabeçalhos da primeira linha
                    header_row = df_raw.iloc[0]

                    for row in data.itertuples(index=False):

                        period = getattr(row, str(period_col), None) \
                                 if hasattr(row, str(period_col)) \
                                 else row[period_col]

                        for col in label_cols:
                            label = header_row[col]
                            value = self.safe_to_float(row[col])

                            if value is None:
                                continue

                            value *= multiplier

                            all_data.append({
                                "sheet": sheet,
                                "label_original": str(label),
                                "period": str(period),
                                "value": value
                            })

        if not all_data:
            return pd.DataFrame(
                columns=["sheet", "label_original", "period", "value"]
            )

        return pd.DataFrame(all_data)
