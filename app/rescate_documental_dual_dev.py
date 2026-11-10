# -*- coding: utf-8 -*-
"""Rescate documental de candidatos duales, únicamente en DEV.

Esta capa no elige por el TOP1 del árbitro. Conserva cualquier resultado existente
aceptado, todas las aclaraciones protegidas y las negativas sin cobertura.
Solo admite rescatar si exactamente una regla documental VIGENTE de la configuración
existente valida un candidato de la unión dual.
"""
from __future__ import annotations

import os


def _autorizado():
    return (
        os.getenv('EXPERTIA_ENTORNO', '').strip().lower() == 'dev'
        and os.getenv('EXPERTIA_CONFIRMAR_NEON_DEV') == 'SI'
        and os.getenv('EXPERTIA_DUAL_SOMBRA_DEV') == '1'
        and os.getenv('EXPERTIA_RESCATE_DUAL_DOCUMENTAL_DEV') == '1'
        and os.getenv('EXPERTIA_RESCATES_CONSENSO_DEV', '0') == '0'
    )


def aplicar_rescate(pregunta, resultado, diagnostico):
    """Recibe la respuesta vigente y la conserva salvo cobertura unívoca validada.

    Nunca consulta etiquetas de auditoría, nunca modifica el procedimiento y no
    cambia nada si el índice dual no estuvo disponible.
    """
    if not _autorizado():
        return resultado, diagnostico
    if not isinstance(diagnostico, dict) or not isinstance(resultado, dict):
        return resultado, diagnostico
    if diagnostico.get('motivo') == 'proteccion_existente':
        return resultado, diagnostico
    if resultado.get('encontrado') and (resultado.get('resultado') or {}).get('id'):
        return resultado, diagnostico
    if diagnostico.get('motivo') not in ('evidencia_insuficiente', 'evidencia_no_concluyente'):
        return resultado, diagnostico
    dual = diagnostico.get('dual_sombra') or {}
    if dual.get('estado') != 'EVALUADO':
        return resultado, diagnostico
    ids = dual.get('union_ids') or []
    if not ids:
        return resultado, diagnostico
    # Importación diferida para mantener la capa desacoplada y verificable.
    from app.selector_integrado import validar_regla
    from app.repository import obtener_conocimientos
    from app.expertia_selector_pgvector_dev import _resultado_rescate, _proteccion_cobertura
    from app.concept_matcher import cumple_requisito_contexto

    catalogo = {int(c['id']): c for c in obtener_conocimientos()}
    validos = []
    for cid in dict.fromkeys(int(x) for x in ids):
        c = catalogo.get(cid)
        if not c or not str(c.get('respuesta') or '').strip():
            continue
        if not cumple_requisito_contexto(pregunta, cid):
            continue
        if not _proteccion_cobertura(pregunta, c):
            continue
        if validar_regla(pregunta, c):
            validos.append(cid)

    # No responder si la validación es ambigua (0 o 2+ conocimientos).
    if len(validos) != 1:
        return resultado, {**diagnostico, 'rescate_dual_documental': {
            'estado': 'SIN_COINCIDENCIA' if not validos else 'AMBIGUO',
            'cantidad_reglas_validas': len(validos),
            'respuesta_modificada': False,
        }}
    cid = validos[0]
    diag = {**diagnostico,
        'decision': 'RESPUESTA_DOCUMENTAL_DUAL_DEV',
        'motivo': 'unica_regla_documental_vigente_entre_candidatos_duales',
        'cobertura_certificada': False,
        'cobertura_validada_por_reglas': True,
        'pendiente_validacion_productiva': True,
        'rescate_dual_documental': {
            'estado': 'REGLA_UNICA', 'id_seleccionado': cid,
            'cantidad_reglas_validas': 1,
            'respuesta_modificada': True,
        },
    }
    respuesta = _resultado_rescate(catalogo[cid], diag)
    (respuesta.get('resultado') or {}).setdefault('detalle_ranking', {})['metodo'] = 'regla_documental_dual_dev'
    return respuesta, diag
