"""
keyword_matcher.py

Detecta keywords presentes en la pregunta
y calcula qué conocimientos están relacionados
con ellas.
"""

from app.normalizer import normalize, tokenize
from app.repository import get_keyword_matches


def detectar_keywords(pregunta):
    """
    Detecta las keywords relacionadas con la pregunta.

    La comparación se realiza utilizando texto y tokens
    previamente normalizados.
    """

    texto_normalizado = normalize(pregunta)

    if not texto_normalizado:
        return []

    tokens_pregunta = set(
        tokenize(pregunta)
    )

    keywords_bd = get_keyword_matches()

    encontradas = []

    for keyword in keywords_bd:

        palabra_original = keyword["palabra"]

        palabra_bd = normalize(
            palabra_original
        )

        if not palabra_bd:
            continue

        tokens_keyword = set(
            tokenize(palabra_bd)
        )

        if not tokens_keyword:
            continue

        # ====================================================
        # COINCIDENCIA DE KEYWORD
        # ====================================================

        # Keyword de una sola palabra
        if len(tokens_keyword) == 1:

            if tokens_keyword.issubset(
                tokens_pregunta
            ):

                encontradas.append({
                    "conocimiento_id":
                        keyword["conocimiento_id"],

                    "keyword_id":
                        keyword["keyword_id"],

                    "palabra":
                        palabra_original,

                    "peso":
                        float(keyword["peso"])
                })

            continue

        # ====================================================
        # KEYWORD DE VARIAS PALABRAS
        # ====================================================

        if tokens_keyword.issubset(
            tokens_pregunta
        ):

            encontradas.append({
                "conocimiento_id":
                    keyword["conocimiento_id"],

                "keyword_id":
                    keyword["keyword_id"],

                "palabra":
                    palabra_original,

                "peso":
                    float(keyword["peso"])
            })

    return encontradas


def calcular_puntajes_keywords(pregunta):
    """
    Calcula el puntaje acumulado de keywords
    para cada conocimiento.
    """

    keywords = detectar_keywords(
        pregunta
    )

    puntajes = {}

    for keyword in keywords:

        conocimiento_id = (
            keyword["conocimiento_id"]
        )

        peso = float(
            keyword["peso"]
        )

        if conocimiento_id not in puntajes:

            puntajes[conocimiento_id] = 0.0

        puntajes[conocimiento_id] += peso

    return puntajes