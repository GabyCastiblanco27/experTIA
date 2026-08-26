"""
concept_matcher.py

Compara la pregunta del usuario contra
el contenido conceptual de cada conocimiento.
"""

from difflib import SequenceMatcher

from app.normalizer import normalize, tokenize


# ============================================================
# SIMILITUD POR TOKENS
# ============================================================

def similitud_tokens(
    texto1,
    texto2
):
    """
    Calcula similitud entre dos textos
    utilizando tokens normalizados.

    Se mide principalmente cuánto del texto
    comparado está presente en la pregunta.
    """

    tokens1 = set(
        tokenize(texto1)
    )

    tokens2 = set(
        tokenize(texto2)
    )

    if not tokens1 or not tokens2:
        return 0.0

    interseccion = (
        tokens1
        &
        tokens2
    )

    if not interseccion:
        return 0.0

    # --------------------------------------------------------
    # Cobertura de la pregunta
    # --------------------------------------------------------

    cobertura_pregunta = (
        len(interseccion)
        /
        len(tokens1)
    )

    # --------------------------------------------------------
    # Cobertura del contenido
    # --------------------------------------------------------

    cobertura_contenido = (
        len(interseccion)
        /
        len(tokens2)
    )

    # --------------------------------------------------------
    # Usamos la mejor cobertura
    #
    # Esto permite:
    #
    # "se me dañaron las botas, como solicito unas nuevas"
    #
    # vs
    #
    # "se me dañaron las botas"
    #
    # --------------------------------------------------------

    return max(
        cobertura_pregunta,
        cobertura_contenido
    )


# ============================================================
# SIMILITUD DE TEXTO
# ============================================================

def similitud_texto(
    texto1,
    texto2
):
    """
    Calcula similitud entre dos textos utilizando:

    - coincidencia de tokens
    - similitud de secuencia
    """

    texto1 = normalize(
        texto1
    )

    texto2 = normalize(
        texto2
    )

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

    return min(
        max(
            score_tokens,
            score_secuencia
        ),
        1.0
    )


# ============================================================
# PREGUNTAS ALTERNATIVAS
# ============================================================

def mejor_pregunta_alternativa(
    pregunta,
    preguntas_alternativas
):
    """
    Encuentra la pregunta alternativa
    más relacionada con la pregunta del usuario.
    """

    if not preguntas_alternativas:

        return 0.0

    mejor = 0.0

    for alternativa in preguntas_alternativas:

        if not alternativa:

            continue

        score = similitud_texto(
            pregunta,
            alternativa
        )

        if score > mejor:

            mejor = score

    return min(
        mejor,
        1.0
    )


# ============================================================
# SCORE CONCEPTUAL
# ============================================================

def calcular_score_conceptual(
    pregunta,
    conocimiento,
    preguntas_alternativas
):
    """
    Calcula el score conceptual de un conocimiento.

    Componentes:

    - Preguntas alternativas: 65 %
    - Título: 25 %
    - Descripción: 10 %
    """

    score_alternativas = (
        mejor_pregunta_alternativa(
            pregunta,
            preguntas_alternativas
        )
    )

    score_titulo = (
        similitud_texto(
            pregunta,
            conocimiento.get(
                "titulo",
                ""
            )
        )
    )

    score_descripcion = (
        similitud_texto(
            pregunta,
            conocimiento.get(
                "descripcion",
                ""
            )
        )
    )

    # --------------------------------------------------------
    # Ranking conceptual
    # --------------------------------------------------------

    score_final = (

        score_alternativas
        *
        0.65

        +

        score_titulo
        *
        0.25

        +

        score_descripcion
        *
        0.10

    )

    return {

        "score":
            min(
                score_final,
                1.0
            ),

        "preguntas_alternativas":
            score_alternativas,

        "titulo":
            score_titulo,

        "descripcion":
            score_descripcion
    }