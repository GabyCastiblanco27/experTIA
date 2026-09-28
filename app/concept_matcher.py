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

def similitud_tokens(texto1, texto2):

    tokens1 = set(tokenize(texto1))
    tokens2 = set(tokenize(texto2))

    if not tokens1 or not tokens2:
        return 0.0

    interseccion = tokens1 & tokens2

    if not interseccion:
        return 0.0

    # ========================================================
    # COINCIDENCIA EXACTA
    # ========================================================
    #
    # Si ambos textos tienen exactamente los mismos tokens,
    # la coincidencia es completa.
    #
    # Ejemplo:
    #
    # "udemy"
    # "udemy"
    #
    # => 1.0
    #

    if tokens1 == tokens2:
        return 1.0

    # ========================================================
    # UNA SOLA COINCIDENCIA
    # ========================================================

    if len(interseccion) == 1:

        token = next(iter(interseccion))

        # Palabras demasiado genéricas que no deben
        # determinar por sí solas un conocimiento.

        tokens_genericos = {
            "reporte",
            "reporte",
            "factura",
            "proveedor",
            "cambio",
            "consulta",
            "solicitud",
            "daño",
            "perdida",
            "retiro",
            "pago",
            "fecha",
            "cierre",
            "novedad",
            "proceso",
            "informacion"
        }

        if token in tokens_genericos:
            return 0.05

        # Una palabra específica compartida puede ser
        # una señal válida.
        #
        # Ejemplo:
        #
        # "udemy"
        # "udemy"
        #
        # Pero no debe ser tan fuerte cuando forma parte
        # de un texto mucho más largo.

        if len(tokens1) == 1 or len(tokens2) == 1:
            return 0.85

        return 0.20

    # ========================================================
    # DOS O MÁS COINCIDENCIAS
    # ========================================================

    precision = len(interseccion) / len(tokens2)
    recall = len(interseccion) / len(tokens1)

    if precision + recall == 0:
        return 0.0

    score = (
        2 * precision * recall
        /
        (precision + recall)
    )

    return min(score, 1.0)


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

    Las coincidencias de una sola palabra tienen
    una influencia mínima.
    """

    texto1 = normalize(
        texto1
    )

    texto2 = normalize(
        texto2
    )

    if not texto1 or not texto2:

        return 0.0

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

    # --------------------------------------------------------
    # Sin coincidencias
    # --------------------------------------------------------

    if not coincidencias:

        return 0.0

    # --------------------------------------------------------
    # Una sola coincidencia
    # --------------------------------------------------------

    if len(coincidencias) == 1:

        # No permitimos que SequenceMatcher
        # convierta una coincidencia genérica
        # en un score conceptual alto.

        return 0.05

    # --------------------------------------------------------
    # Varias coincidencias
    # --------------------------------------------------------

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

    # Cuando existen varias palabras coincidentes,
    # el contenido semántico por tokens tiene mayor peso.

    score = (
        score_tokens * 0.80
        +
        score_secuencia * 0.20
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