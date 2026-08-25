"""
intent_detector.py

Detecta la intención de la pregunta
utilizando intenciones e intencion_variantes.
"""

from difflib import SequenceMatcher

from app.normalizer import normalize, tokenize

from app.repository import get_intention_variants


def calcular_similitud(texto1, texto2):

    if not texto1 or not texto2:
        return 0.0

    tokens1 = set(
        texto1.split()
    )

    tokens2 = set(
        texto2.split()
    )

    interseccion = (
        len(tokens1 & tokens2)
    )

    union = (
        len(tokens1 | tokens2)
    )

    if union == 0:
        similitud_tokens = 0
    else:
        similitud_tokens = (
            interseccion / union
        )

    similitud_secuencia = (
        SequenceMatcher(
            None,
            texto1,
            texto2
        ).ratio()
    )

    return max(
        similitud_tokens,
        similitud_secuencia
    )


def detectar_intencion(pregunta):

    pregunta_normalizada = normalize(
        pregunta
    )

    tokens_pregunta = set(
        tokenize(pregunta)
    )

    variantes = get_intention_variants()

    mejor_resultado = None

    for variante in variantes:

        frase = normalize(
            variante["frase"]
        )

        if not frase:
            continue

        tokens_frase = set(
            frase.split()
        )

        # ----------------------------------------------------
        # Coincidencia exacta de tokens
        # ----------------------------------------------------

        coincidencia_exacta = (
            tokens_frase.issubset(
                tokens_pregunta
            )
        )

        if coincidencia_exacta:

            puntaje = 1.0

        else:

            puntaje = calcular_similitud(
                pregunta_normalizada,
                frase
            )

        resultado = {

            "intencion_id":
                variante["intencion_id"],

            "intencion":
                variante["intencion"],

            "frase":
                variante["frase"],

            "score":
                puntaje
        }

        if (
            mejor_resultado is None
            or puntaje >
               mejor_resultado["score"]
        ):

            mejor_resultado = resultado

    return mejor_resultado