"""
concept_matcher.py

Compara la pregunta del usuario contra
el contenido conceptual de cada conocimiento.
"""

from difflib import SequenceMatcher

from app.normalizer import normalize, tokenize


def similitud_tokens(texto1, texto2):

    tokens1 = set(
        tokenize(texto1)
    )

    tokens2 = set(
        tokenize(texto2)
    )

    if not tokens1 or not tokens2:
        return 0.0

    interseccion = (
        tokens1 & tokens2
    )

    return (
        len(interseccion)
        /
        len(tokens1)
    )


def similitud_texto(texto1, texto2):

    texto1 = normalize(texto1)
    texto2 = normalize(texto2)

    if not texto1 or not texto2:
        return 0.0

    score_tokens = (
        similitud_tokens(
            texto1,
            texto2
        )
    )

    score_secuencia = (
        SequenceMatcher(
            None,
            texto1,
            texto2
        ).ratio()
    )

    return max(
        score_tokens,
        score_secuencia
    )


def mejor_pregunta_alternativa(
    pregunta,
    preguntas_alternativas
):

    if not preguntas_alternativas:
        return 0.0

    mejor = 0.0

    for alternativa in preguntas_alternativas:

        score = similitud_texto(
            pregunta,
            alternativa
        )

        if score > mejor:
            mejor = score

    return mejor


def calcular_score_conceptual(
    pregunta,
    conocimiento,
    preguntas_alternativas
):

    score_alternativas = (
        mejor_pregunta_alternativa(
            pregunta,
            preguntas_alternativas
        )
    )

    score_titulo = similitud_texto(
        pregunta,
        conocimiento["titulo"]
    )

    score_descripcion = similitud_texto(
        pregunta,
        conocimiento["descripcion"]
    )

    # --------------------------------------------------------
    # Peso de cada elemento
    # --------------------------------------------------------

    score_final = (

        score_alternativas * 0.55

        +

        score_titulo * 0.30

        +

        score_descripcion * 0.15
    )

    return {

        "score":
            min(score_final, 1.0),

        "preguntas_alternativas":
            score_alternativas,

        "titulo":
            score_titulo,

        "descripcion":
            score_descripcion
    }