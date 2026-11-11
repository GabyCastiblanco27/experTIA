# -*- coding: utf-8 -*-
"""Recuperación dual en modo SOLO DIAGNÓSTICO para ExperTIA.

Une Top 3 Bekko original con Top 3 multirrepresentación sin evaluar
cobertura ni cambiar la respuesta final. Solo Neon DEV, solo SELECT.
"""
from __future__ import annotations

import os
from contextlib import closing

import psycopg2
from psycopg2.extensions import parse_dsn

from app.semantic_retriever import MODELO, generar_embeddings

TABLA_ORIGINAL = "public.expertia_indice_vectorial_bekko"
TABLA_MULTI = "public.expertia_indice_vectorial_bekko_multi_v1_dev"


def _conexion():
    from app.conexion_vectorial_expertia import conexion_vectorial
    return conexion_vectorial()



def _validar_indice(cur, tabla, modelo, ids, por_conocimiento):
    # Los nombres de tabla son constantes internas, no entradas del usuario.
    cur.execute(
        f"SELECT conocimiento_id, COUNT(*) FROM {tabla} "
        "WHERE modelo = %s GROUP BY conocimiento_id",
        (modelo,),
    )
    conteo = {int(cid): int(n) for cid, n in cur.fetchall()}
    if set(conteo) != set(ids) or any(n != por_conocimiento for n in conteo.values()):
        raise RuntimeError("Índice inconsistente con los 44 conocimientos DEV")


def _ranking(cur, tabla, vec, modelo, ids, limite):
    cur.execute(
        f"SELECT conocimiento_id, MAX(1 - (embedding <=> %s::vector)) AS similitud "
        f"FROM {tabla} WHERE modelo=%s AND conocimiento_id=ANY(%s) "
        "GROUP BY conocimiento_id ORDER BY similitud DESC, conocimiento_id LIMIT %s",
        (vec, modelo, sorted(ids), limite),
    )
    return [
        {"id": int(cid), "similitud": float(sim)}
        for cid, sim in cur.fetchall()
    ]


def unir_candidatos(original, multi):
    """Unión estable sin duplicados; no es un orden de confianza ni cobertura."""
    ids = set()
    salida = []
    for origen, entradas in (("original", original), ("multi", multi)):
        for registro in entradas:
            cid = int(registro["id"])
            if cid not in ids:
                salida.append({"id": cid, "similitud": float(registro["similitud"])})
                ids.add(cid)
    return salida


def buscar_candidatos_duales(pregunta, catalogo, limite=3):
    """Hace un embedding query; consulta 2 índices; nunca escribe ni responde."""
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("Pregunta vacía")
    ids = set(int(cid) for cid in catalogo)
    if len(ids) != 44:
        raise ValueError("Se esperan 44 IDs oficiales únicos")
    if not isinstance(limite, int) or limite < 1 or limite > 10:
        raise ValueError("Límite inválido")
    matriz = generar_embeddings([pregunta], tipo="query")
    if matriz.shape != (1, 384):
        raise RuntimeError("Dimensiones inesperadas del modelo Bekko")
    vec = "[" + ",".join(format(float(x), ".9g") for x in matriz[0]) + "]"
    with closing(_conexion()) as con:
        with con.cursor() as cur:
            _validar_indice(cur, TABLA_ORIGINAL, MODELO, ids, 1)
            _validar_indice(cur, TABLA_MULTI, MODELO, ids, 8)
            original = _ranking(cur, TABLA_ORIGINAL, vec, MODELO, ids, limite)
            multi = _ranking(cur, TABLA_MULTI, vec, MODELO, ids, limite)
    return {
        "original": original,
        "multi": multi,
        "union": unir_candidatos(original, multi),
        "cobertura_certificada": False,
        "respuesta_modificada": False,
    }
