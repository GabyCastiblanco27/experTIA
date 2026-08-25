"""
normalizer.py
------------
Normalización de preguntas realizadas a ExperTIA.
"""

import re
import unicodedata


# Palabras que normalmente no aportan información
# relevante para la búsqueda.
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


# Normalización de algunas formas frecuentes.
REPLACEMENTS = {
    "retirar": "retiro",
    "retiros": "retiro",

    "solicitar": "solicitud",
    "solicito": "solicitud",
    "solicitudes": "solicitud",

    "tramitar": "tramite",
    "tramito": "tramite",

    "descargar": "descarga",
    "descargo": "descarga",

    "actualizar": "actualizacion",
    "actualizo": "actualizacion",

    "reportar": "reporte",
    "reporto": "reporte"
}


def remove_accents(text: str) -> str:
    """
    Elimina tildes.

    Ejemplo:

    cesantías -> cesantias
    nómina -> nomina
    """

    normalized = unicodedata.normalize(
        "NFD",
        text
    )

    return "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    )


def normalize(text: str) -> str:
    """
    Normaliza una pregunta.

    Ejemplo:

    ¿Cómo retiro mis cesantías?

    -->

    retiro cesantias
    """

    if not text:
        return ""

    # Convertir a minúsculas
    text = text.lower().strip()

    # Quitar tildes
    text = remove_accents(text)

    # Eliminar signos de puntuación
    text = re.sub(
        r"[^a-z0-9ñü\s]",
        " ",
        text
    )

    # Eliminar espacios repetidos
    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    tokens = []

    for token in text.split():

        # Ignorar palabras vacías
        if token in STOPWORDS:
            continue

        # Aplicar reemplazo si existe
        token = REPLACEMENTS.get(
            token,
            token
        )

        tokens.append(token)


    return " ".join(tokens)


def tokenize(text: str) -> list[str]:
    """
    Convierte una pregunta normalizada en una lista de palabras.

    Ejemplo:

    "retiro cesantias"

    -->

    ["retiro", "cesantias"]
    """

    normalized = normalize(text)

    if not normalized:
        return []

    return normalized.split()