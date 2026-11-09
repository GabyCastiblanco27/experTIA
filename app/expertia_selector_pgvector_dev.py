"""ExperTIA: selector híbrido DEV, versión integrada.

Índice BEKKO aislado; el índice E5 original permanece sin modificaciones.

Estrategia:
  - Mantiene la decisión tradicional y sus aclaraciones existentes.
  - pgvector recupera candidatos; el árbitro contrastivo reordena desacuerdos.
  - El consenso estricto es una PROPUESTA, no una certificación de cobertura.
  - Por defecto, no cambia ninguna respuesta tradicional aceptada.
  - Rescates por consenso: experimento DEV, DESACTIVADO por defecto.

Bandera de diagnóstico: EXPERTIA_ARBITRO_SOMBRA_DEV=1
Bandera de ensayo: EXPERTIA_RESCATES_CONSENSO_DEV=1 (NO usar en PROD)
Bandera de tolerancia: EXPERTIA_FALLBACK_TRADICIONAL_DEV=1 (por defecto)

No escribe en Neon ni modifica otros módulos. El índice se lee en modo readonly.
"""

from __future__ import annotations

import os
import re
import unicodedata
from contextlib import closing
from difflib import SequenceMatcher
from threading import Lock

import psycopg2
from psycopg2.extensions import parse_dsn

from app.busqueda_asistida import (
    buscar_conocimiento_asistido_con_ranking,
    _pedir_aclaracion,
)
from app.concept_matcher import cumple_requisito_contexto
from app.repository import obtener_recursos_por_conocimiento

from app.response_validator import (
    analizar_cobertura_textual,
    verificar_cancelacion,
)
from app.semantic_retriever import generar_embeddings, MODELO


_lock = Lock()
_indice_verificado_para = None


def _flag(nombre, predeterminado="0"):
    return os.getenv(nombre, predeterminado).strip() == "1"


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", texto))


def _conexion_dev():
    url = (os.getenv("EXPERTIA_PGVECTOR_DEV_URL") or "").strip()
    if not url:
        raise RuntimeError("Falta EXPERTIA_PGVECTOR_DEV_URL")
    if os.getenv("EXPERTIA_CONFIRMAR_NEON_DEV") != "SI":
        raise RuntimeError("Debes confirmar la conexión Neon DEV")

    parametros = parse_dsn(url)
    host = (parametros.get("host") or "").lower()
    sslmode = (parametros.get("sslmode") or "").lower()
    if not host.endswith(".neon.tech"):
        raise RuntimeError("Host Neon no autorizado")
    if sslmode not in {"require", "verify-ca", "verify-full"}:
        raise RuntimeError("La conexión requiere TLS")

    conexion = psycopg2.connect(url, connect_timeout=15)
    conexion.set_session(readonly=True, autocommit=True)
    return conexion


def _catalogo(conocimientos):
    conocimientos = list(conocimientos or [])

    if not conocimientos:
        raise RuntimeError("El catálogo de conocimientos está vacío")

    catalogo = {
        int(c["id"]): c
        for c in conocimientos
    }

    if len(catalogo) != len(conocimientos):
        raise RuntimeError("Hay IDs duplicados en el catálogo")

    return catalogo


def _comprobar_indice(con, catalogo):
    """Comprueba IDs/modelo; invalida caché si cambia el catálogo activo."""
    global _indice_verificado_para
    firma = (MODELO, tuple(sorted(catalogo)))
    if _indice_verificado_para == firma:
        return

    with _lock:
        if _indice_verificado_para == firma:
            return
        with con.cursor() as cur:
            cur.execute("""
                SELECT conocimiento_id, modelo
                FROM public.expertia_indice_vectorial_bekko
            """)
            filas = cur.fetchall()

        ids_indice = {
            int(cid) for cid, modelo in filas if modelo == MODELO
        }
        faltantes = set(catalogo) - ids_indice
        if faltantes:
            raise RuntimeError(
                "Faltan IDs activos en pgvector: " + str(sorted(faltantes))
            )
        _indice_verificado_para = firma


def buscar_top_vectorial(pregunta, catalogo, limite=3):
    """Recupera candidatos activos desde el índice vectorial de DEV."""
    if not catalogo:
        return []
    with closing(_conexion_dev()) as con:
        _comprobar_indice(con, catalogo)
        embedding = generar_embeddings([pregunta], tipo="query")[0]
        vector = "[" + ",".join(format(float(x), ".9g") for x in embedding) + "]"
        with con.cursor() as cur:
            cur.execute("""
                SELECT conocimiento_id,
                       1 - (embedding <=> %s::vector) AS similitud
                FROM public.expertia_indice_vectorial_bekko
                WHERE modelo = %s
                  AND conocimiento_id = ANY(%s)
                ORDER BY embedding <=> %s::vector, conocimiento_id
                LIMIT %s
            """, (vector, MODELO, list(catalogo), vector, limite))
            filas = cur.fetchall()
    return [
        {"id": int(cid), "similitud": float(sim)}
        for cid, sim in filas
    ]


def _mejor_alternativa(pregunta, conocimiento_id, alternativas):
    """Señal diagnóstica, no una prueba de cobertura."""
    consulta = _normalizar(pregunta)
    mejor = 0.0
    for alternativa in alternativas:
        if int(alternativa["conocimiento_id"]) != conocimiento_id:
            continue
        texto = _normalizar(alternativa.get("pregunta", ""))
        if texto:
            mejor = max(mejor, SequenceMatcher(None, consulta, texto).ratio())
    return mejor


def _proteccion_cobertura(pregunta, conocimiento):
    """Respeta protecciones EXISTENTES; no certifica cobertura semántica."""
    titulo = _normalizar(conocimiento.get("titulo"))
    consulta = _normalizar(pregunta)

    if "consulta de estado de pedidos" in titulo:
        cambiar = bool(re.search(
            r"\b(?:cambi\w*|modific\w*|actualiz\w*|correg\w*)\b",
            consulta,
        ))
        direccion = "direccion" in consulta.split()
        cancelar = bool(re.search(r"\b(?:cancel\w*|anul\w*)\b", consulta))
        if (cambiar and direccion) or cancelar:
            return False

    validacion = verificar_cancelacion(pregunta, conocimiento)
    return validacion.get("estado") != "cobertura_no_confirmada"


def _resultado_rescate(conocimiento, diagnostico):
    """Construye la respuesta experimental sin inventar confianza."""
    cid = int(conocimiento["id"])
    recursos = conocimiento.get("recursos")
    if not recursos:
        recursos = obtener_recursos_por_conocimiento(cid)

    resultado = {
        "id": cid,
        "titulo": conocimiento.get("titulo"),
        "respuesta": conocimiento.get("respuesta"),
        "area": conocimiento.get("area"),
        "proceso": conocimiento.get("proceso"),
        "responsable": conocimiento.get("responsable"),
        "recursos": recursos or [],
        "confianza": 0.0,
        "detalle_ranking": {
            **diagnostico,
            "metodo": "rescate_consenso_experimental_dev",
            "confianza_calibrada": False,
        },
    }
    return {
        "encontrado": True,
        "confianza": 0.0,
        "resultado": resultado,
        "mensaje": "Candidato recuperado por consenso experimental DEV",
    }


def _evaluar_arbitro(pregunta, catalogo, vectoriales, tradicional_id,
                    id_aceptado, vector_id, alternativas, conocimientos):
    """Arbitra candidatos sin consultar etiquetas esperadas ni cambiar respuestas."""
    from app.contrastive_ranker import calificar_conocimientos

    candidatos = list(dict.fromkeys(
        [int(c["id"]) for c in vectoriales]
        + ([tradicional_id] if tradicional_id is not None else [])
    ))
    candidatos = [
        cid for cid in candidatos
        if cid in catalogo and cumple_requisito_contexto(pregunta, cid)
    ]
    if not candidatos:
        return {
            "estado": "SIN_CANDIDATOS",
            "consenso_estricto": False,
            "respuesta_modificada": False,
            "cobertura_certificada": False,
        }

    puntajes = calificar_conocimientos(
        pregunta,
        conocimientos,
        alternativas,
        bonificar_solo_base=True,
    )
    orden = sorted(
        candidatos,
        key=lambda cid: (-float(puntajes.get(cid, 0.0)), cid),
    )
    propuesto = orden[0]
    consenso = (
        vector_id is not None
        and propuesto == vector_id
        and propuesto != id_aceptado
    )
    margen = (
        float(puntajes.get(orden[0], 0.0))
        - float(puntajes.get(orden[1], 0.0))
        if len(orden) > 1 else None
    )
    return {
        "estado": "EVALUADO",
        "candidatos": candidatos,
        "id_propuesto": propuesto,
        "id_actual": id_aceptado,
        "consenso_estricto": consenso,
        "accion_propuesta": (
            "CANDIDATO_A_RESCATE" if consenso else "CONSERVAR_RESULTADO"
        ),
        "difiere_del_actual": propuesto != id_aceptado,
        "margen_contrastivo": round(margen, 4) if margen is not None else None,
        "respuesta_modificada": False,
        "cobertura_certificada": False,
    }



def _prevalidar(pregunta, catalogo, arbitro):
    """
    Verifica requisitos técnicos y genera un diagnóstico
    de cobertura textual.

    El diagnóstico textual NO certifica cobertura
    ni autoriza rescates.
    """
    cid = int(arbitro["id_propuesto"])
    candidato = catalogo.get(cid)

    respuesta_disponible = bool(
        candidato
        and str(candidato.get("respuesta") or "").strip()
    )

    contexto_valido = bool(
        candidato
        and cumple_requisito_contexto(pregunta, cid)
    )

    protecciones_validas = bool(
        candidato
        and _proteccion_cobertura(pregunta, candidato)
    )

    # Diagnóstico exploratorio: no representa una certificación.
    cobertura_textual = analizar_cobertura_textual(
        pregunta,
        candidato,
    )

    return {
        "id_candidato": cid,
        "respuesta_oficial_disponible": respuesta_disponible,
        "contexto_valido": contexto_valido,
        "protecciones_validas": protecciones_validas,

        "validaciones_tecnicas_superadas": all((
            respuesta_disponible,
            contexto_valido,
            protecciones_validas,
        )),

        "diagnostico_cobertura_textual": cobertura_textual,

        # Nunca certificar únicamente por coincidencia textual.
        "cobertura_certificada": False,
        "rescate_activado": False,
    }

def _decision_tradicional(tradicional):
    if tradicional.get("requiere_aclaracion"):
        return "ACLARACION"
    if tradicional.get("encontrado") and (tradicional.get("resultado") or {}).get("id"):
        return "RESPUESTA"
    return "SIN_COBERTURA"


def seleccionar(pregunta):
    """Devuelve (respuesta, diagnóstico), respetando el contrato actual de la API.

    En DEV la bandera EXPERTIA_RESCATES_CONSENSO_DEV=1 puede activar un
    experimento. El consenso no certifica cobertura; NO habilitar en PROD.
    """
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("Pregunta vacía")
    if os.getenv("EXPERTIA_MODO_BUSQUEDA", "tradicional").lower() != "tradicional":
        raise RuntimeError("El selector DEV requiere modo tradicional")

    evaluacion_compartida = buscar_conocimiento_asistido_con_ranking(
        pregunta,
        limite=5,
    )

    tradicional = evaluacion_compartida["busqueda"]
    ranking_precalculado = evaluacion_compartida["ranking"]

    # Las aclaraciones de las reglas actuales tienen prioridad absoluta.
    if tradicional.get("requiere_aclaracion"):
        return tradicional, {
            "selector": "hibrido_unificado_dev",
            "decision": "ACLARACION",
            "motivo": "proteccion_existente",
            "cobertura_certificada": False,
        }

    aceptado = bool(
        tradicional.get("encontrado")
        and (tradicional.get("resultado") or {}).get("id")
    )
    id_aceptado = int(tradicional["resultado"]["id"]) if aceptado else None

    modo_sombra = _flag("EXPERTIA_ARBITRO_SOMBRA_DEV")
    modo_rescate = _flag("EXPERTIA_RESCATES_CONSENSO_DEV")

    diagnostico = {
        "selector": "hibrido_unificado_dev",
        "tradicional_id_aceptado": id_aceptado,
        "cobertura_certificada": False,
        "rescates_consenso_habilitados": modo_rescate,
    }

    try:
        conocimientos = evaluacion_compartida["conocimientos"]
        alternativas = evaluacion_compartida["preguntas"]

        catalogo = _catalogo(conocimientos)
        ranking = [
            r for r in ranking_precalculado
            if int(r["id"]) in catalogo
        ]
        primero_tradicional = ranking[0] if ranking else None
        tradicional_id = (
            int(primero_tradicional["id"]) if primero_tradicional else None
        )
        score_tradicional = (
            float(primero_tradicional["score"]) if primero_tradicional else 0.0
        )
        vectoriales = buscar_top_vectorial(pregunta, catalogo, limite=3)
        primero_vector = vectoriales[0] if vectoriales else None
        vector_id = int(primero_vector["id"]) if primero_vector else None
        similitud = float(primero_vector["similitud"]) if primero_vector else 0.0
        segunda = float(vectoriales[1]["similitud"]) if len(vectoriales) > 1 else 0.0
        margen = similitud - segunda

        alternativa_score = (
            _mejor_alternativa(pregunta, vector_id, alternativas)
            if vector_id is not None else 0.0
        )
        diagnostico.update({
            "tradicional_id_candidato": tradicional_id,
            "tradicional_score": round(score_tradicional, 4),
            "vector_id_candidato": vector_id,
            "vector_top3": [int(c["id"]) for c in vectoriales],
            "similitud_coseno": round(similitud, 4),
            "margen_vectorial": round(margen, 4),
            "similitud_alternativa": round(alternativa_score, 4),
            "coinciden_top1": (tradicional_id is not None and tradicional_id == vector_id),
        })

    except Exception as exc:
        # Si falla pgvector, el canal DEV conserva lo que respondió el motor
        # tradicional, sin exponer DSN, tokens ni contraseñas en el diagnóstico.
        if not _flag("EXPERTIA_FALLBACK_TRADICIONAL_DEV", "1"):
            raise
        diagnostico.update({
            "estado_vectorial": "NO_DISPONIBLE",
            "tipo_error_vectorial": type(exc).__name__,
            "decision": _decision_tradicional(tradicional),
            "motivo": "fallback_tradicional_dev",
        })
        return tradicional, diagnostico

    if (modo_sombra or modo_rescate) and not (aceptado and id_aceptado == vector_id):
        try:
            arbitro = _evaluar_arbitro(
                pregunta,
                catalogo,
                vectoriales,
                tradicional_id,
                id_aceptado,
                vector_id,
                alternativas,
                conocimientos,
            )
            diagnostico["arbitro_sombra"] = arbitro
            if arbitro.get("consenso_estricto") is True:
                diagnostico["prevalidacion_consenso"] = _prevalidar(
                    pregunta, catalogo, arbitro
                )
        except Exception as exc:
            diagnostico["arbitro_sombra"] = {
                "estado": "ERROR",
                "tipo_error": type(exc).__name__,
                "respuesta_modificada": False,
                "cobertura_certificada": False,
            }

    prevalidacion = diagnostico.get("prevalidacion_consenso") or {}
    if (
        modo_rescate
        and prevalidacion.get("validaciones_tecnicas_superadas") is True
        and prevalidacion.get("cobertura_certificada") is True
    ):
        candidato_id = int(prevalidacion["id_candidato"])
        # SOLO DEV: nunca marcar cobertura como certificada por una coincidencia.
        diagnostico["prevalidacion_consenso"]["rescate_activado"] = True
        diagnostico["arbitro_sombra"]["respuesta_modificada"] = True
        diagnostico.update({
            "decision": "RESPUESTA",
            "motivo": "consenso_experimental_dev_sin_cobertura_certificada",
        })
        return _resultado_rescate(catalogo[candidato_id], diagnostico), diagnostico

    # El motor tradicional sigue decidiendo cuando el ensayo está desactivado
    # o cuando el consenso no superó los filtros disponibles.
    if aceptado:
        diagnostico.update({
            "decision": "RESPUESTA",
            "motivo": (
                "tradicional_aceptado_y_acuerdo_vectorial"
                if id_aceptado == vector_id
                else "tradicional_aceptado_sin_acuerdo_vectorial"
            ),
        })
        return tradicional, diagnostico

    # No activar el rescate antiguo de similitud/margen: carece de respaldo
    # suficiente y de un mecanismo independiente de certificación de cobertura.
    if vector_id is None or (similitud < 0.70 and score_tradicional < 0.18):
        diagnostico.update({
            "decision": "SIN_COBERTURA",
            "motivo": "evidencia_insuficiente",
        })
        return tradicional, diagnostico

    aclaracion = _pedir_aclaracion(
        "Encontré información relacionada, pero necesito que precises "
        "el trámite que deseas realizar. ¿Puedes darme un poco más de contexto?",
        "seleccion_hibrida_sin_cobertura_confirmada",
    )
    diagnostico.update({
        "decision": "ACLARACION",
        "motivo": "evidencia_no_concluyente",
    })
    return aclaracion, diagnostico
