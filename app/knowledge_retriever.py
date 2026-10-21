"""
knowledge_retriever.py

Motor principal de recuperación y ranking de conocimientos de ExperTIA.
Se conserva el nombre original del archivo: knowledge_retriever.py
"""

import logging
import os

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


_LOG = logging.getLogger(__name__)


def _reordenar_con_contraste(pregunta, conocimientos, preguntas_alternativas, resultados, *, diagnostico=False):
    """Reordena solo si la bandera experimental está activada.

    Conserva requisitos previos de contexto, puntajes clásicos y umbral
    de aceptación. Ante cualquier error interno utiliza el orden original.
    No modifica el JSON ni la base de datos.
    """
    if os.getenv("EXPERTIA_RANKING_CONTRASTIVO", "0").strip() != "1":
        return resultados
    if len(resultados) < 2:
        return resultados

    try:
        from app.concept_matcher import REQUISITOS_CONTEXTO
        from app.contrastive_ranker import calificar_conocimientos

        def obtener_id(fila):
            return int(fila["id"] if diagnostico else fila["conocimiento"]["id"])

        ids_validos = {obtener_id(fila) for fila in resultados}
        calificaciones = calificar_conocimientos(
            pregunta, conocimientos, preguntas_alternativas
        )
        orden = sorted(
            ((id_, score) for id_, score in calificaciones.items() if id_ in ids_validos),
            key=lambda item: item[1], reverse=True,
        )
        if len(orden) < 2:
            return resultados

        seleccionado = orden[0][0]
        margen = orden[0][1] - orden[1][1]
        ganador_clasico = resultados[0]
        id_clasico = obtener_id(ganador_clasico)
        score_clasico = float(ganador_clasico["score"])

        # Protecciones conservadoras contra regresiones, también basadas en
        # requisitos de contexto YA existentes en el motor.
        if id_clasico != seleccionado:
            if score_clasico >= 0.85 and margen <= 0.08:
                seleccionado = id_clasico
            elif (
                id_clasico in REQUISITOS_CONTEXTO
                and score_clasico >= 0.55
                and margen < 0.08
            ):
                seleccionado = id_clasico

        # EXPERTIA_CORRECCION_DESEMPATE_V1: resolver competencia muy estrecha.
        # Este score NO mide la cobertura del procedimiento.
        if seleccionado != id_clasico and margen < 0.045 and score_clasico >= 0.35:
            from app.contrastive_ranker import similitudes_mejores_alternativas
            from app.normalizer import tokenize

            evidencia = similitudes_mejores_alternativas(
                pregunta, conocimientos, preguntas_alternativas,
                (seleccionado, id_clasico),
            )
            evidencia_clasica = evidencia[id_clasico]
            evidencia_contraste = evidencia[seleccionado]
            if evidencia_clasica > evidencia_contraste + 0.015:
                seleccionado = id_clasico
            elif margen < 0.015:
                # Categoría general de preguntas sobre límites/valores, sin IDs fijos.
                terminos_valor = {
                    "monto", "maximo", "minimo", "limite", "valor", "cuanto",
                    "cuanta", "precio", "costo", "importe", "presupuesto",
                }
                tokens_pregunta = set(tokenize(pregunta))
                titulo_clasico = ganador_clasico["titulo"] if diagnostico else ganador_clasico["conocimiento"]["titulo"]
                tokens_titulo = set(tokenize(titulo_clasico or ""))
                if tokens_pregunta & terminos_valor and tokens_titulo & terminos_valor:
                    seleccionado = id_clasico

        # Evidencia contrastiva interna: no se expone como una probabilidad.
        elegido = next(f for f in resultados if obtener_id(f) == seleccionado)
        elegido["_contraste_score"] = float(calificaciones.get(seleccionado, 0.0))
        elegido["_contraste_margen"] = float(margen)

        if seleccionado == id_clasico:
            return resultados

        # Solo mover el ganador contrastivo a la primera posición; el resto
        # conserva el orden y los puntajes clásicos.
        return sorted(resultados, key=lambda fila: obtener_id(fila) == seleccionado, reverse=True)
    except Exception:
        _LOG.exception("Error en ranking contrastivo; se conserva el ranking original")
        return resultados


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
    resultados = _reordenar_con_contraste(
        pregunta, conocimientos, preguntas, resultados, diagnostico=False
    )

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
    score_salida = mejor["score"]

    # Rescate separado del reranking, desactivado por defecto. Exige
    # evidencia suficiente, ventaja sobre el siguiente candidato y un mínimo
    # de respaldo del ranking clásico. No intenta verificar acciones sin
    # cobertura documental, que siguen a cargo del orquestador.
    if (
        not encontrado
        and os.getenv("EXPERTIA_RANKING_CONTRASTIVO", "0") == "1"
        and os.getenv("EXPERTIA_RESCATE_CONTRASTIVO", "0") == "1"
        and mejor.get("_contraste_score", 0.0) >= 0.38
        and mejor.get("_contraste_margen", 0.0) >= 0.10
        and mejor["score"] >= 0.18
    ):
        encontrado = True
        score_salida = max(mejor["score"], mejor["_contraste_score"])

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
        score_salida,
        mejor["score_concepto"],
        mejor["score_keywords"],
        mejor["score_intencion"],
    )

    return {
        "encontrado": True,
        "confianza": round(score_salida, 2),
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
    resultados = _reordenar_con_contraste(
        pregunta, conocimientos, preguntas, resultados, diagnostico=True
    )
    return resultados[:limite]