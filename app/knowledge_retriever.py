"""
knowledge_retriever.py

Motor principal de recuperación y ranking
de conocimientos de ExperTIA.

Se conserva el nombre original del archivo:
knowledge_retriever.py
"""

from app.keyword_matcher import (
    calcular_puntajes_keywords
)

from app.intent_detector import (
    detectar_intencion
)

from app.concept_matcher import (
    calcular_score_conceptual
)

from app.repository import (
    obtener_conocimientos,
    obtener_preguntas_alternativas,
    obtener_recursos_por_conocimiento
)


# ============================================================
# PESOS DEL MOTOR
# ============================================================

PESO_CONCEPTO = 0.60

PESO_KEYWORDS = 0.30

PESO_INTENCION = 0.10


# ============================================================
# UTILIDADES
# ============================================================

def agrupar_preguntas_alternativas(
    preguntas
):

    resultado = {}

    for pregunta in preguntas:

        conocimiento_id = (
            pregunta["conocimiento_id"]
        )

        if conocimiento_id not in resultado:

            resultado[
                conocimiento_id
            ] = []

        resultado[
            conocimiento_id
        ].append(
            pregunta["pregunta"]
        )

    return resultado


def calcular_score_keywords(
    conocimiento_id,
    puntajes_keywords,
    conocimiento
):
    """
    Normaliza el puntaje de keywords.

    Las keywords específicas y compuestas ya reciben
    mayor peso desde keyword_matcher.py.
    """

    puntaje = puntajes_keywords.get(
        conocimiento_id,
        0.0
    )

    if puntaje <= 0:
        return 0.0

    # Evitamos que muchas keywords hagan que
    # el resultado supere 1.0.

    return min(
        puntaje / 2.0,
        1.0
    )


def construir_resultado(
    conocimiento,
    score,
    score_concepto,
    score_keywords,
    score_intencion
):

    recursos = obtener_recursos_por_conocimiento(
        conocimiento["id"]
    )

    return {

        "id":
            conocimiento["id"],

        "titulo":
            conocimiento["titulo"],

        "area":
            conocimiento["area"],

        "proceso":
            conocimiento["proceso"],

        "respuesta":
            conocimiento["respuesta"],

        "responsable":
            conocimiento["responsable"],

        "estado":
            conocimiento["estado"],

        "recursos":
            recursos,

        "confianza":
            round(score, 2),

        "detalle_ranking": {

            "concepto":
                round(
                    score_concepto,
                    2
                ),

            "keywords":
                round(
                    score_keywords,
                    2
                ),

            "intencion":
                round(
                    score_intencion,
                    2
                )
        }
    }


# ============================================================
# BÚSQUEDA PRINCIPAL
# ============================================================
def buscar_conocimiento(
    pregunta
):

    conocimientos = (
        obtener_conocimientos()
    )

    preguntas = (
        obtener_preguntas_alternativas()
    )

    if not conocimientos:

        return {

            "encontrado": False,

            "confianza": 0,

            "resultado": None,

            "intencion": None,

            "mensaje":
                "No existen conocimientos activos."
        }

    # --------------------------------------------------------
    # Agrupar preguntas alternativas
    # --------------------------------------------------------

    alternativas = (
        agrupar_preguntas_alternativas(
            preguntas
        )
    )

    # --------------------------------------------------------
    # Detectar keywords
    # --------------------------------------------------------

    puntajes_keywords = (
        calcular_puntajes_keywords(
            pregunta
        )
    )

    # --------------------------------------------------------
    # Detectar intención
    # --------------------------------------------------------

    intencion = detectar_intencion(
        pregunta
    )

    if intencion:

        score_intencion = (
            intencion["score"]
        )

    else:

        score_intencion = 0.0

    # --------------------------------------------------------
    # Ranking
    # --------------------------------------------------------

    resultados = []

    for conocimiento in conocimientos:

        conocimiento_id = (
            conocimiento["id"]
        )

        preguntas_conocimiento = (
            alternativas.get(
                conocimiento_id,
                []
            )
        )

        # ----------------------------------------------------
        # Score conceptual
        # ----------------------------------------------------

        conceptual = (
            calcular_score_conceptual(

                pregunta,

                conocimiento,

                preguntas_conocimiento
            )
        )

        score_concepto = (
            conceptual["score"]
        )

        # ----------------------------------------------------
        # Score keywords
        # ----------------------------------------------------

        score_keywords = (
            calcular_score_keywords(

                conocimiento_id,

                puntajes_keywords,

                conocimiento
            )
        )

        # ----------------------------------------------------
        # Score final
        # ----------------------------------------------------

        score_final = (

            score_concepto
            *
            PESO_CONCEPTO

            +

            score_keywords
            *
            PESO_KEYWORDS

            +

            score_intencion
            *
            PESO_INTENCION
        )

        resultados.append({

            "conocimiento":
                conocimiento,

            "score":
                score_final,

            "score_concepto":
                score_concepto,

            "score_keywords":
                score_keywords,

            "score_intencion":
                score_intencion
        })

    # --------------------------------------------------------
    # Ordenar de mayor a menor
    # --------------------------------------------------------

    resultados.sort(

        key=lambda x: x["score"],

        reverse=True
    )

    # --------------------------------------------------------
    # Verificar resultados
    # --------------------------------------------------------

    if not resultados:

        return {

            "encontrado": False,

            "confianza": 0,

            "resultado": None,

            "intencion": intencion,

            "mensaje":
                "No se encontraron resultados."
        }

    # --------------------------------------------------------
    # Obtener SOLO el mejor resultado
    # --------------------------------------------------------

    mejor = resultados[0]

    # --------------------------------------------------------
    # Umbral mínimo
    # --------------------------------------------------------

    UMBRAL_CONFIANZA = 0.35

    encontrado = (

        mejor["score"]
        >=
        UMBRAL_CONFIANZA
    )

    # --------------------------------------------------------
    # Si no supera el umbral
    # --------------------------------------------------------

    if not encontrado:

     return {

        "encontrado": False,

        "confianza":
            round(
                mejor["score"],
                2
            ),

        "resultado": None,

        "intencion": intencion,

        "detalle_ranking": {

            "conocimiento_id":
                mejor["conocimiento"]["id"],

            "titulo":
                mejor["conocimiento"]["titulo"],

            "score_total":
                round(
                    mejor["score"],
                    4
                ),

            "score_concepto":
                round(
                    mejor["score_concepto"],
                    4
                ),

            "score_keywords":
                round(
                    mejor["score_keywords"],
                    4
                ),

            "score_intencion":
                round(
                    mejor["score_intencion"],
                    4
                )
        },

        "mensaje":
            "No se encontró un conocimiento con suficiente confianza."
    }

    # --------------------------------------------------------
    # Construir únicamente el mejor resultado
    # --------------------------------------------------------

    resultado_final = construir_resultado(

        mejor["conocimiento"],

        mejor["score"],

        mejor["score_concepto"],

        mejor["score_keywords"],

        mejor["score_intencion"]
    )

    # --------------------------------------------------------
    # Respuesta final
    # --------------------------------------------------------

    return {

        "encontrado":
            True,

        "confianza":
            round(
                mejor["score"],
                2
            ),

        "resultado":
            resultado_final,

        "intencion":
            intencion,

        "mensaje":
            "Conocimiento encontrado."
    }