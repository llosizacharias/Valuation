def detect_unit_multiplier(sheet_df):

    # Converter tudo para string de forma segura
    text_blob = " ".join(
        str(cell) for cell in sheet_df.values.flatten()
    ).lower()

    if "milhoes" in text_blob or "milhões" in text_blob or "millions" in text_blob:
        return 1_000_000

    if "milhares" in text_blob or "thousands" in text_blob or " mil " in text_blob:
        return 1_000

    if "bilhoes" in text_blob or "bilhões" in text_blob or "billions" in text_blob:
        return 1_000_000_000

    return 1
