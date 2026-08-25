"""
normalizer.py
-------------
Normalización de preguntas realizadas a ExperTIA.
"""

import re
import unicodedata


# ============================================================
# STOPWORDS
# ============================================================

STOPWORDS = {
    "a",
    "al",
    "con",
    "de",
    "del",
    "el",
    "en",
    "es",
    "la",
    "las",
    "lo",
    "los",
    "me",
    "mi",
    "mis",
    "para",
    "por",
    "que",
    "se",
    "su",
    "sus",
    "un",
    "una",
    "unos",
    "unas",
    "y",
    "o",
    "u",
    "como",
    "cómo",
    "donde",
    "dónde",
    "cuando",
    "cuándo",
    "cual",
    "cuál",
    "cuales",
    "cuáles",
    "puedo",
    "puede",
    "pueden",
    "quiero",
    "necesito",
    "quisiera",
    "hay",
    "hacer",
    "hago"
}


# ============================================================
# REEMPLAZOS
# ============================================================

REPLACEMENTS = {

    # --------------------------------------------------------
    # Retiros
    # --------------------------------------------------------

    "retirar": "retiro",
    "retiros": "retiro",
    "retiro": "retiro",

    # --------------------------------------------------------
    # Solicitudes
    # --------------------------------------------------------

    "solicitar": "solicitud",
    "solicito": "solicitud",
    "solicitudes": "solicitud",
    "solicitud": "solicitud",

    # --------------------------------------------------------
    # Trámites
    # --------------------------------------------------------

    "tramitar": "tramite",
    "tramito": "tramite",
    "tramites": "tramite",
    "tramite": "tramite",

    # --------------------------------------------------------
    # Descargas
    # --------------------------------------------------------

    "descargar": "descarga",
    "descargo": "descarga",
    "descargas": "descarga",
    "descarga": "descarga",

    # --------------------------------------------------------
    # Actualizaciones
    # --------------------------------------------------------

    "actualizar": "actualizacion",
    "actualizo": "actualizacion",
    "actualizaciones": "actualizacion",
    "actualizacion": "actualizacion",

    # --------------------------------------------------------
    # Reportes
    # --------------------------------------------------------

    "reportar": "reporte",
    "reporto": "reporte",
    "reportes": "reporte",
    "reporte": "reporte"
}


# ============================================================
# ELIMINAR TILDES
# ============================================================

def remove_accents(text: str) -> str:
    """
    Elimina las tildes de un texto.

    Ejemplo:

        cesantías -> cesantias
        nómina -> nomina
    """

    if not text:
        return ""

    normalized = unicodedata.normalize(
        "NFD",
        text
    )

    return "".join(
        character
        for character in normalized
        if unicodedata.category(
            character
        ) != "Mn"
    )


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalize(text: str) -> str:
    """
    Normaliza una pregunta.

    Ejemplo:

        ¿Cómo retiro mis cesantías?

    Resultado:

        retiro cesantias
    """

    if not text:
        return ""

    # --------------------------------------------------------
    # Minúsculas
    # --------------------------------------------------------

    text = text.lower().strip()

    # --------------------------------------------------------
    # Eliminar tildes
    # --------------------------------------------------------

    text = remove_accents(text)

    # --------------------------------------------------------
    # Eliminar signos
    # --------------------------------------------------------

    text = re.sub(
        r"[^a-z0-9ñü\s]",
        " ",
        text
    )

    # --------------------------------------------------------
    # Eliminar espacios repetidos
    # --------------------------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    # --------------------------------------------------------
    # Procesar tokens
    # --------------------------------------------------------

    tokens = []

    for token in text.split():

        # Ignorar stopwords
        if token in STOPWORDS:
            continue

        # Aplicar normalización léxica
        token = REPLACEMENTS.get(
            token,
            token
        )

        tokens.append(token)

    return " ".join(tokens)


# ============================================================
# TOKENIZACIÓN
# ============================================================

def tokenize(text: str) -> list[str]:
    """
    Convierte una pregunta en tokens normalizados.

    Ejemplo:

        "¿Cómo retiro mis cesantías?"

    Resultado:

        ["retiro", "cesantias"]
    """

    normalized = normalize(text)

    if not normalized:
        return []

    return normalized.split()