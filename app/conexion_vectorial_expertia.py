# -*- coding: utf-8 -*-
"""Lectura Neon por entorno: DEV nunca se confunde con PROD.

Desactivado por defecto en PROD. Solo SELECT y conexión TLS al endpoint fijado.
"""
import os
from contextlib import closing

import psycopg2
from psycopg2.extensions import parse_dsn


def _host_y_modo(url):
    params = parse_dsn(url)
    host = (params.get("host") or "").strip().lower()
    mode = (params.get("sslmode") or "").strip().lower()
    if not host.endswith(".neon.tech"):
        raise RuntimeError("Endpoint Neon no autorizado")
    if mode not in ("require", "verify-ca", "verify-full"):
        raise RuntimeError("TLS requerido para Neon")
    return host


def conexion_vectorial():
    entorno = os.getenv("EXPERTIA_ENTORNO", "").strip().lower()
    if entorno == "dev":
        if os.getenv("EXPERTIA_CONFIRMAR_NEON_DEV") != "SI":
            raise RuntimeError("Conexion DEV sin confirmar")
        url = (os.getenv("EXPERTIA_PGVECTOR_DEV_URL") or "").strip()
        if not url:
            raise RuntimeError("Falta URL vectorial DEV")
        _host_y_modo(url)
    elif entorno == "prod":
        if os.getenv("EXPERTIA_VECTOR_PROD_ENABLE", "0") != "1":
            raise RuntimeError("Lectura vectorial PROD no habilitada")
        url = (os.getenv("EXPERTIA_PGVECTOR_PROD_URL") or "").strip()
        host_esperado = (os.getenv("EXPERTIA_PGVECTOR_PROD_HOST") or "").strip().lower()
        if not url or not host_esperado:
            raise RuntimeError("Falta configuracion vectorial PROD")
        host = _host_y_modo(url)
        if host != host_esperado:
            raise RuntimeError("La URL PROD no coincide con el endpoint autorizado")
        url_dev = (os.getenv("EXPERTIA_PGVECTOR_DEV_URL") or "").strip()
        if url_dev and _host_y_modo(url_dev) == host:
            raise RuntimeError("Las conexiones vectoriales DEV y PROD coinciden")
    else:
        raise RuntimeError("Entorno de ExperTIA no autorizado")

    conexion = psycopg2.connect(url, connect_timeout=15)
    try:
        conexion.set_session(readonly=True, autocommit=True)
        if conexion.info.ssl_in_use is not True:
            raise RuntimeError("No se confirmo TLS en la conexion Neon")
    except Exception:
        conexion.close()
        raise
    return conexion
