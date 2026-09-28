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

    # Coincidencia exacta
    if tokens1 == tokens2:
        return 1.0

    # Palabras demasiado genéricas para determinar por sí solas
    tokens_genericos = {
        "reporte",
        "factura",
        "proveedor",
        "cambio",
        "consulta",
        "solicitud",
        "dano",
        "perdida",
        "retiro",
        "pago",
        "fecha",
        "cierre",
        "novedad",
        "proceso",
        "informacion"
    }

    # Si todas las coincidencias son palabras genéricas,
    # la similitud debe ser baja.
    if interseccion.issubset(tokens_genericos):
        return 0.10

    # Una sola coincidencia
    if len(interseccion) == 1:

        token = next(iter(interseccion))

        if token in tokens_genericos:
            return 0.05

        if len(tokens1) == 1 or len(tokens2) == 1:
            return 0.85

        return 0.20

    # Coincidencias múltiples
    precision = len(interseccion) / len(tokens2)
    recall = len(interseccion) / len(tokens1)

    if precision + recall == 0:
        return 0.0

    score = 2 * precision * recall / (precision + recall)

    return min(score, 1.0)

# ============================================================
# SIMILITUD DE TEXTO
# ============================================================


def similitud_texto(texto1, texto2):

    texto1 = normalize(texto1)
    texto2 = normalize(texto2)

    if not texto1 or not texto2:
        return 0.0

    tokens1 = set(tokenize(texto1))
    tokens2 = set(tokenize(texto2))

    if not tokens1 or not tokens2:
        return 0.0

    # Coincidencia exacta de los tokens
    # Ejemplo:
    # "que es udemy" -> {"udemy"}
    # "que es udemy" -> {"udemy"}
    if tokens1 == tokens2:
        return 1.0

    score_tokens = similitud_tokens(texto1, texto2)
    score_secuencia = SequenceMatcher(
        None,
        texto1,
        texto2
    ).ratio()

    coincidencias = tokens1 & tokens2

    if len(coincidencias) >= 2:
        score = (
            score_tokens * 0.75
            + score_secuencia * 0.25
        )

    else:
        score = (
            score_tokens * 0.40
            + score_secuencia * 0.10
        )

    return min(score, 1.0)


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