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
    Calcula similitud entre dos textos utilizando
    tokens normalizados.

    Se utiliza una medida basada en F1:

        precision = coincidencias / tokens del contenido
        recall    = coincidencias / tokens de la pregunta

    Esto evita que una coincidencia parcial de una
    sola palabra produzca una similitud artificialmente alta.
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
    # Precisión
    # --------------------------------------------------------

    precision = (
        len(interseccion)
        /
        len(tokens2)
    )

    # --------------------------------------------------------
    # Recall
    # --------------------------------------------------------

    recall = (
        len(interseccion)
        /
        len(tokens1)
    )

    # --------------------------------------------------------
    # F1
    # --------------------------------------------------------

    if precision + recall == 0:
        return 0.0

    score = (
        2
        *
        precision
        *
        recall
        /
        (precision + recall)
    )

    # --------------------------------------------------------
    # Bonus por coincidencias múltiples
    #
    # Dos o más palabras compartidas indican
    # una relación conceptual más fuerte.
    # --------------------------------------------------------

    if len(interseccion) >= 2:

        score += 0.10

    elif len(interseccion) == 1:

        # Una sola palabra no debe ser suficiente
        # para generar un score conceptual elevado.

        score *= 0.50

    return min(
        score,
        1.0
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

    Se prioriza la coincidencia de tokens cuando
    existen varias palabras relevantes en común.
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

    # --------------------------------------------------------
    # Si existen al menos dos tokens coincidentes,
    # damos prioridad al score por tokens.
    # --------------------------------------------------------

    tokens1 = set(
        tokenize(texto1)
    )

    tokens2 = set(
        tokenize(texto2)
    )

    coincidencias = (
        tokens1
        &
        tokens2
    )

    if len(coincidencias) >= 2:

        score = (
            score_tokens * 0.75
            +
            score_secuencia * 0.25
        )

    else:

        # Cuando solamente coincide una palabra,
        # reducimos la influencia de SequenceMatcher
        # para evitar falsos positivos.

        score = (
            score_tokens * 0.40
            +
            score_secuencia * 0.10
        )

    return min(
        score,
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