"""
knowledge_retriever.py

Motor principal de recuperación y ranking de conocimientos de ExperTIA.
Se conserva el nombre original del archivo: knowledge_retriever.py
"""

from app.keyword_matcher import calcular_puntajes_keywords
from app.intent_detector import detectar_intencion
from app.concept_matcher import (
    calcular_score_conceptual,
    cumple_requisito_contexto,
)
from app.repository import (
    obtener_conocimientos,
    obtener_preguntas_alternativas,
    obtener_recursos_por_conocimiento,
)


# ============================================================
# PESOS DEL MOTOR (sin cambios)
# ============================================================

PESO_CONCEPTO = 0.70
PESO_KEYWORDS = 0.25
PESO_INTENCION = 0.05


# ============================================================
# UTILIDADES
# ============================================================

def agrupar_preguntas_alternativas(preguntas):
    resultado = {}
    for pregunta in preguntas:
        conocimiento_id = pregunta["conocimiento_id"]
        if conocimiento_id not in resultado:
            resultado[conocimiento_id] = []
        resultado[conocimiento_id].append(pregunta["pregunta"])
    return resultado


def calcular_score_keywords(conocimiento_id, puntajes_keywords, conocimiento):
    """Normaliza el puntaje de keywords; las compuestas ya se ponderan en keyword_matcher."""
    puntaje = puntajes_keywords.get(conocimiento_id, 0.0)
    if puntaje <= 0:
        return 0.0
    return min(puntaje / 2.0, 1.0)


def construir_resultado(
    conocimiento,
    score,
    score_concepto,
    score_keywords,
    score_intencion,
):
    recursos = obtener_recursos_por_conocimiento(conocimiento["id"])
    return {
        "id": conocimiento["id"],
        "titulo": conocimiento["titulo"],
        "area": conocimiento["area"],
        "proceso": conocimiento["proceso"],
        "respuesta": conocimiento["respuesta"],
        "responsable": conocimiento["responsable"],
        "estado": conocimiento["estado"],
        "recursos": recursos,
        "confianza": round(score, 2),
        "detalle_ranking": {
            "concepto": round(score_concepto, 2),
            "keywords": round(score_keywords, 2),
            "intencion": round(score_intencion, 2),
        },
    }


# ============================================================
# BÚSQUEDA PRINCIPAL
# ============================================================

def buscar_conocimiento(pregunta):
    conocimientos = obtener_conocimientos()
    preguntas = obtener_preguntas_alternativas()

    if not conocimientos:
        return {
            "encontrado": False,
            "confianza": 0,
            "resultado": None,
            "intencion": None,
            "mensaje": "No existen conocimientos activos.",
        }

    alternativas = agrupar_preguntas_alternativas(preguntas)
    puntajes_keywords = calcular_puntajes_keywords(pregunta)
    intencion = detectar_intencion(pregunta)
    score_intencion = intencion["score"] if intencion else 0.0

    resultados = []
    for conocimiento in conocimientos:
        conocimiento_id = conocimiento["id"]

        # CORRECCIÓN: el contexto es obligatorio para TODO el ranking.
        # No basta con anular el score conceptual, ya que las keywords
        # podrían hacer ganar a un conocimiento fuera de contexto.
        if not cumple_requisito_contexto(pregunta, conocimiento_id):
            continue

        preguntas_conocimiento = alternativas.get(conocimiento_id, [])
        conceptual = calcular_score_conceptual(
            pregunta,
            conocimiento,
            preguntas_conocimiento,
        )
        score_concepto = conceptual["score"]
        score_keywords = calcular_score_keywords(
            conocimiento_id,
            puntajes_keywords,
            conocimiento,
        )
        score_final = (
            score_concepto * PESO_CONCEPTO
            + score_keywords * PESO_KEYWORDS
            + score_intencion * PESO_INTENCION
        )
        resultados.append({
            "conocimiento": conocimiento,
            "score": score_final,
            "score_concepto": score_concepto,
            "score_keywords": score_keywords,
            "score_intencion": score_intencion,
        })

    resultados.sort(key=lambda x: x["score"], reverse=True)

    if not resultados:
        return {
            "encontrado": False,
            "confianza": 0,
            "resultado": None,
            "intencion": intencion,
            "mensaje": "No se encontraron resultados.",
        }

    mejor = resultados[0]
    UMBRAL_CONFIANZA = 0.35
    encontrado = mejor["score"] >= UMBRAL_CONFIANZA

    if not encontrado:
        return {
            "encontrado": False,
            "confianza": round(mejor["score"], 2),
            "resultado": None,
            "intencion": intencion,
            "detalle_ranking": {
                "conocimiento_id": mejor["conocimiento"]["id"],
                "titulo": mejor["conocimiento"]["titulo"],
                "score_total": round(mejor["score"], 4),
                "score_concepto": round(mejor["score_concepto"], 4),
                "score_keywords": round(mejor["score_keywords"], 4),
                "score_intencion": round(mejor["score_intencion"], 4),
                "keywords_detectadas": puntajes_keywords,
            },
            "mensaje": "No se encontró un conocimiento con suficiente confianza.",
        }

    resultado_final = construir_resultado(
        mejor["conocimiento"],
        mejor["score"],
        mejor["score_concepto"],
        mejor["score_keywords"],
        mejor["score_intencion"],
    )

    return {
        "encontrado": True,
        "confianza": round(mejor["score"], 2),
        "resultado": resultado_final,
        "intencion": intencion,
        "detalle_ranking": {
            "conocimiento_id": mejor["conocimiento"]["id"],
            "titulo": mejor["conocimiento"]["titulo"],
            "score_total": round(mejor["score"], 4),
            "score_concepto": round(mejor["score_concepto"], 4),
            "score_keywords": round(mejor["score_keywords"], 4),
            "score_intencion": round(mejor["score_intencion"], 4),
            "keywords_detectadas": puntajes_keywords,
        },
        "mensaje": "Conocimiento encontrado.",
    }


# ============================================================
# RANKING DE DIAGNÓSTICO
# ============================================================

def obtener_ranking(pregunta, limite=10):
    conocimientos = obtener_conocimientos()
    preguntas = obtener_preguntas_alternativas()
    alternativas = agrupar_preguntas_alternativas(preguntas)
    puntajes_keywords = calcular_puntajes_keywords(pregunta)
    intencion = detectar_intencion(pregunta)
    score_intencion = intencion["score"] if intencion else 0.0

    resultados = []
    for conocimiento in conocimientos:
        conocimiento_id = conocimiento["id"]

        # MISMA CORRECCIÓN que en buscar_conocimiento().
        if not cumple_requisito_contexto(pregunta, conocimiento_id):
            continue

        preguntas_conocimiento = alternativas.get(conocimiento_id, [])
        conceptual = calcular_score_conceptual(
            pregunta,
            conocimiento,
            preguntas_conocimiento,
        )
        score_concepto = conceptual["score"]
        score_keywords = calcular_score_keywords(
            conocimiento_id,
            puntajes_keywords,
            conocimiento,
        )
        score_final = (
            score_concepto * PESO_CONCEPTO
            + score_keywords * PESO_KEYWORDS
            + score_intencion * PESO_INTENCION
        )
        resultados.append({
            "id": conocimiento_id,
            "titulo": conocimiento["titulo"],
            "score": round(score_final, 4),
            "score_concepto": round(score_concepto, 4),
            "score_keywords": round(score_keywords, 4),
            "score_intencion": round(score_intencion, 4),
        })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:limite]