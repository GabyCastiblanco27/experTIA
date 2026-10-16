"""Motor híbrido experimental de ExperTIA.

Optimiza el cálculo de embeddings del catálogo e instrumenta tiempos.
Conserva la selección del motor validado (128/129 en la batería histórica).
NO autoriza respuestas ni modifica la API o Neon.
"""

from functools import lru_cache
from time import perf_counter

import numpy as np
from sentence_transformers import CrossEncoder

from app.knowledge_retriever import obtener_ranking
from app.repository import obtener_conocimientos, obtener_recursos_por_conocimiento
from app.semantic_retriever import generar_embeddings

MODELO_RERANKER = "BAAI/bge-reranker-v2-m3"
TOP_K = 5


@lru_cache(maxsize=1)
def cargar_reranker():
    """Carga el reranker una sola vez por proceso de Python."""
    return CrossEncoder(MODELO_RERANKER, max_length=512)


def construir_documento(conocimiento, campos):
    partes = []
    for campo in campos:
        valor = conocimiento.get(campo)
        if valor is not None and str(valor).strip():
            partes.append(f"{campo}: {str(valor).strip()}")
    return "\n".join(partes)


@lru_cache(maxsize=2)
def _embeddings_del_catalogo(documentos):
    """Reutiliza embeddings si el texto del catálogo no ha cambiado.

    La clave es una tupla de los textos; si cambia título, descripción,
    respuesta, proceso, área u orden, se recalculan automáticamente.
    Caché solo en memoria y solo para este proceso.
    """
    return generar_embeddings(list(documentos), tipo="passage")


def buscar_conocimiento_hibrido(pregunta):
    """Selecciona un candidato para diagnóstico; NO autoriza respuesta."""
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta debe ser un texto no vacío.")

    inicio = perf_counter()
    conocimientos = obtener_conocimientos()
    fin_catalogo = perf_counter()

    if not conocimientos:
        return {
            "encontrado": False,
            "confianza": None,
            "resultado": None,
            "mensaje": "No existen conocimientos activos.",
            "validacion_pendiente": True,
        }

    # Mantener EXACTAMENTE los cinco campos del recuperador semántico.
    documentos_recuperacion = tuple(
        construir_documento(c, ("titulo", "proceso", "area", "descripcion", "respuesta"))
        for c in conocimientos
    )
    hits_antes = _embeddings_del_catalogo.cache_info().hits
    vectores = _embeddings_del_catalogo(documentos_recuperacion)
    cache_embeddings_reutilizada = _embeddings_del_catalogo.cache_info().hits > hits_antes
    fin_documentos = perf_counter()

    vector_pregunta = generar_embeddings([pregunta], tipo="query")[0]
    similitudes = np.dot(vectores, vector_pregunta)
    indices = np.argsort(-similitudes)[:TOP_K]
    ids_semanticos = [int(conocimientos[int(i)]["id"]) for i in indices]
    fin_semantico = perf_counter()

    # No se altera la función tradicional ni sus reglas de contexto.
    ranking_tradicional = obtener_ranking(pregunta, limite=TOP_K)
    ids_tradicionales = [int(item["id"]) for item in ranking_tradicional]
    fin_tradicional = perf_counter()

    candidatos_ids = list(dict.fromkeys(ids_semanticos + ids_tradicionales))
    conocimientos_por_id = {int(c["id"]): c for c in conocimientos}

    # Configuración C: título + descripción + respuesta.
    pares = [
        (
            pregunta,
            construir_documento(
                conocimientos_por_id[cid], ("titulo", "descripcion", "respuesta")
            ),
        )
        for cid in candidatos_ids
    ]

    modelo_cargado_antes = cargar_reranker.cache_info().hits > 0
    reranker = cargar_reranker()
    fin_carga_reranker = perf_counter()

    scores = reranker.predict(pares, show_progress_bar=False)
    orden = sorted(
        zip(candidatos_ids, scores),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    fin_reranker = perf_counter()

    id_reranker, score_reranker = orden[0]
    id_elegido, score_bruto = id_reranker, score_reranker
    motivo_seleccion = "reranker"
    regla_tradicional_aplicada = False

    # Mantener sin cambios la primera regla provisional.
    if len(ranking_tradicional) >= 2:
        primero, segundo = ranking_tradicional[:2]
        id_primero = int(primero["id"])
        puntaje_primero = float(primero["score"])
        margen = puntaje_primero - float(segundo["score"])
        keywords_primero = float(primero["score_keywords"])
        ranking_trad_por_id = {
            int(item["id"]): (pos + 1, float(item["score"]))
            for pos, item in enumerate(ranking_tradicional)
        }
        posicion_reranker, puntaje_trad_reranker = ranking_trad_por_id.get(
            int(id_reranker), (TOP_K + 1, 0.0)
        )
        if (
            id_primero != int(id_reranker)
            and id_primero in candidatos_ids
            and int(id_reranker) in ranking_trad_por_id
            and puntaje_primero >= 0.65
            and margen >= 0.15
            and keywords_primero >= 0.40
            and posicion_reranker >= 4
            and puntaje_primero - puntaje_trad_reranker >= 0.25
        ):
            id_elegido = id_primero
            score_bruto = next(
                score for cid, score in orden if int(cid) == id_elegido
            )
            motivo_seleccion = "regla_de_consenso_tradicional_provisional"
            regla_tradicional_aplicada = True

    # Mantener sin cambios la segunda regla provisional.
    if (
        motivo_seleccion == "reranker"
        and ids_semanticos
        and ids_tradicionales
        and ids_semanticos[0] == ids_tradicionales[0]
        and int(id_reranker) != ids_semanticos[0]
    ):
        id_elegido = ids_semanticos[0]
        score_bruto = next(
            score for cid, score in orden if int(cid) == id_elegido
        )
        motivo_seleccion = "consenso_semantico_tradicional_provisional"
        regla_tradicional_aplicada = True

    conocimiento = conocimientos_por_id[id_elegido]
    recursos = obtener_recursos_por_conocimiento(id_elegido)
    fin_recursos = perf_counter()

    resultado = {
        "id": id_elegido,
        "titulo": conocimiento.get("titulo"),
        "area": conocimiento.get("area"),
        "proceso": conocimiento.get("proceso"),
        "respuesta": conocimiento.get("respuesta"),
        "responsable": conocimiento.get("responsable"),
        "estado": conocimiento.get("estado"),
        "recursos": recursos,
        "score_reranker_bruto": float(score_bruto),
    }

    indice_por_id = {int(c["id"]): i for i, c in enumerate(conocimientos)}
    similitud_seleccionado = float(similitudes[indice_por_id[id_elegido]])
    similitud_mejor = float(similitudes[int(indices[0])])
    margen_reranker = (
        float(orden[0][1]) - float(orden[1][1]) if len(orden) > 1 else None
    )
    puntaje_tradicional_seleccionado = next(
        (
            float(item["score"]) for item in ranking_tradicional
            if int(item["id"]) == id_elegido
        ),
        None,
    )
    fin_total = perf_counter()

    return {
        "encontrado": False,
        "confianza": None,
        "resultado": resultado,
        "validacion_pendiente": True,
        "mensaje": "Candidato seleccionado; falta validar si responde la pregunta.",
        "detalle_ranking": {
            "ids_semanticos": ids_semanticos,
            "ids_tradicionales": ids_tradicionales,
            "top_3_reranker": [
                {"id": int(cid), "score_bruto": float(score)}
                for cid, score in orden[:3]
            ],
            "id_ganador_reranker": int(id_reranker),
            "id_seleccionado_final": int(id_elegido),
            "motivo_seleccion": motivo_seleccion,
            "regla_tradicional_aplicada": regla_tradicional_aplicada,
            "ranking_tradicional": ranking_tradicional,
            "similitud_semantica_top1": similitud_mejor,
            "similitud_semantica_seleccionado": similitud_seleccionado,
            "margen_reranker_top2": margen_reranker,
            "puntaje_tradicional_seleccionado": puntaje_tradicional_seleccionado,
            "consenso_top1": bool(
                ids_semanticos and ids_tradicionales
                and ids_semanticos[0] == ids_tradicionales[0]
            ),
            "cache_embeddings_reutilizada": cache_embeddings_reutilizada,
            "reranker_ya_cargado": modelo_cargado_antes,
            "tiempos_segundos": {
                "neon_catalogo": round(fin_catalogo - inicio, 3),
                "embeddings_catalogo": round(fin_documentos - fin_catalogo, 3),
                "busqueda_semantica": round(fin_semantico - fin_documentos, 3),
                "ranking_tradicional": round(fin_tradicional - fin_semantico, 3),
                "carga_reranker": round(fin_carga_reranker - fin_tradicional, 3),
                "inferencia_reranker": round(fin_reranker - fin_carga_reranker, 3),
                "recursos_y_seleccion": round(fin_recursos - fin_reranker, 3),
                "total": round(fin_total - inicio, 3),
            },
        },
    }
