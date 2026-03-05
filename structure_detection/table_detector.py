import pandas as pd
import re


class UniversalTableExtractor:

    def __init__(self, file_path):
        self.file_path = file_path

    # =====================================================
    # SAFE FLOAT ROBUSTO
    # =====================================================

    def safe_to_float(self, value):

        # Se vier uma Series (coluna duplicada), pega o primeiro valor válido
        if isinstance(value, pd.Series):
            value = value.dropna()
            if value.empty:
                return None
            value = value.iloc[0]

        # Agora é escalar
        if pd.isna(value):
            return None

        value = str(value).strip()

        if value in ["", "-", "nan", "None"]:
            return None

        value = value.replace(" ", "")

        negative = False
        if value.startswith("(") and value.endswith(")"):
            negative = True
            value = value[1:-1]

        # Notação científica
        if "e" in value.lower():
            try:
                number = float(value)
                return -number if negative else number
            except:
                return None

        # Padrão brasileiro
        if "," in value and "." in value:
            value = value.replace(".", "").replace(",", ".")
        elif "," in value:
            value = value.replace(",", ".")
        else:
            value = value.replace(",", "")

        try:
            number = float(value)
            return -number if negative else number
        except:
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

        xls = pd.ExcelFile(self.file_path)
        all_data = []

        for sheet in xls.sheet_names:

            df_raw = pd.read_excel(xls, sheet_name=sheet, header=None)

            # 🔥 MULTIPLIER FIXO (DESATIVADO AUTOMÁTICO)
            multiplier = 1

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

                label_col = (
                    df_raw.iloc[period_row + 1:, :]
                    .apply(lambda col: col.astype(str).str.len().mean())
                    .idxmax()
                )

                labels = df_raw.iloc[period_row + 1:, label_col]

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
            # ==========================
            elif orientation == "vertical":

                period_col = ref

                data = df_raw[
                    df_raw[period_col].apply(
                        lambda x: self.is_period(str(x))
                    )
                ]

                label_cols = [c for c in df_raw.columns if c != period_col]

                for _, row in data.iterrows():

                    period = row[period_col]

                    for col in label_cols:

                        label = df_raw.iloc[0, col]
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

        return pd.DataFrame(all_data)