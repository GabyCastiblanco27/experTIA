"""
keyword_matcher.py

Detecta keywords presentes en la pregunta
y calcula qué conocimientos están relacionados
con ellas.
"""

from app.normalizer import normalize, tokenize

from app.repository import get_keyword_matches


def detectar_keywords(pregunta):

    texto_normalizado = normalize(pregunta)

    tokens = set(
        tokenize(pregunta)
    )

    keywords_bd = get_keyword_matches()

    encontradas = []

    for keyword in keywords_bd:

        palabra_bd = normalize(
            keyword["palabra"]
        )

        if not palabra_bd:
            continue

        tokens_keyword = set(
            palabra_bd.split()
        )

        # ----------------------------------------------------
        # Keyword de una palabra
        # ----------------------------------------------------

        if palabra_bd in texto_normalizado:

            encontradas.append({
                "conocimiento_id":
                    keyword["conocimiento_id"],

                "keyword_id":
                    keyword["keyword_id"],

                "palabra":
                    keyword["palabra"],

                "peso":
                    float(keyword["peso"])
            })

            continue

        # ----------------------------------------------------
        # Keyword de varias palabras
        # ----------------------------------------------------

        if tokens_keyword.issubset(tokens):

            encontradas.append({
                "conocimiento_id":
                    keyword["conocimiento_id"],

                "keyword_id":
                    keyword["keyword_id"],

                "palabra":
                    keyword["palabra"],

                "peso":
                    float(keyword["peso"])
            })

    return encontradas


def calcular_puntajes_keywords(pregunta):

    keywords = detectar_keywords(
        pregunta
    )

    puntajes = {}

    for keyword in keywords:

        conocimiento_id = keyword[
            "conocimiento_id"
        ]

        peso = keyword["peso"]

        if conocimiento_id not in puntajes:

            puntajes[conocimiento_id] = 0

        puntajes[conocimiento_id] += peso

    return puntajes