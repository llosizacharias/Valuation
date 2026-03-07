import re


def detect_unit_multiplier(sheet_df):
    """
    Detecta o multiplicador de unidade a partir do conteúdo de uma aba do Excel.

    Padrões suportados (muito comuns em ITRs e DFPs brasileiros):
    - "R$ milhões" / "em milhões" / "millions"     → 1.000.000
    - "R$ mil" / "em milhares" / "thousands"        → 1.000
    - "R$ bilhões" / "billions"                     → 1.000.000.000

    ✅ CORREÇÃO BUG CRÍTICO: esta função existia mas NUNCA ERA CHAMADA
    O table_detector.py tinha `multiplier = 1` hardcoded.
    Se uma empresa reporta em R$ milhões (padrão na B3), todos os valores
    ficam 1.000.000x menores — valuations completamente errados.

    Como usar no table_detector.py:
        from normalization.unit_detector import detect_unit_multiplier
        multiplier = detect_unit_multiplier(df_raw)
    """

    text_blob = " ".join(
        str(cell) for cell in sheet_df.values.flatten()
        if cell is not None
    ).lower()

    # Bilhões — verificar antes de milhões para evitar falso positivo
    if re.search(r"bilh[oõ]es|billions?", text_blob):
        return 1_000_000_000

    # Milhões — padrão mais comum nos releases da B3
    if re.search(r"milh[oõ]es|millions?|r\$\s*mi(?:lh)?[oõ]es?", text_blob):
        return 1_000_000

    # Milhares / R$ mil — também muito comum em pequenas e médias
    if re.search(r"milhares|thousands?|r\$\s*mil\b|\bm mil\b", text_blob):
        return 1_000

    return 1
