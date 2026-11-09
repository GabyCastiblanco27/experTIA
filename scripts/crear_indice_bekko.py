# -*- coding: utf-8 -*-
"""Crea el índice Bekko en Neon DEV. No altera ni elimina el índice E5.

Ejecutar LOCALMENTE y únicamente tras aprobar la prueba de embeddings:
  $env:CONFIRMAR_CREAR_INDICE_BEKKO = "SI"
  python scripts/crear_indice_bekko.py

Credenciales: usa EXPERTIA_PGVECTOR_DEV_URL existente (debe permitir escritura).
Catálogo oficial: consulta la conexión principal ya configurada en ExperTIA.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv
load_dotenv(RAIZ / '.env')

import psycopg2
from psycopg2.extensions import parse_dsn

from app.repository import obtener_conocimientos
from app.semantic_retriever import MODELO, generar_embeddings

TABLA = "public.expertia_indice_vectorial_bekko"


def _texto_conocimiento(c):
    """Texto para índice semántico; no modifica la respuesta original.

    Se indexan título, descripción, área, proceso y extracto del contenido.
    La pregunta NO usa prefijos query: de acuerdo con las instrucciones Bekko.
    """
    partes = []
    for clave in ("titulo", "descripcion", "area", "proceso", "keywords", "palabras_clave"):
        valor = c.get(clave)
        if isinstance(valor, (list, tuple)):
            valor = ", ".join(str(x) for x in valor)
        if valor is not None and str(valor).strip():
            partes.append(str(valor).strip())
    if not partes:
        raise RuntimeError(f"Conocimiento {c.get('id')} sin texto para indexar")
    respuesta = str(c.get("respuesta") or "").strip()
    if respuesta:
        partes.append(respuesta[:650])
    return ". ".join(partes)


def main():
    if os.getenv('CONFIRMAR_CREAR_INDICE_BEKKO') != 'SI':
        raise RuntimeError('Falta CONFIRMAR_CREAR_INDICE_BEKKO=SI. No se escribió nada.')
    if os.getenv('EXPERTIA_CONFIRMAR_NEON_DEV') != 'SI':
        raise RuntimeError('Neon DEV no confirmado; no se escribió nada.')
    url = (os.getenv('EXPERTIA_PGVECTOR_DEV_URL') or '').strip()
    if not url:
        raise RuntimeError('Falta EXPERTIA_PGVECTOR_DEV_URL')
    dsn = parse_dsn(url)
    host = (dsn.get('host') or '').lower()
    if not host.endswith('.neon.tech'):
        raise RuntimeError('Solo se permite un endpoint Neon autorizado')
    if (dsn.get('sslmode') or '').lower() not in ('require','verify-ca','verify-full'):
        raise RuntimeError('La conexión requiere SSL')

    conocimientos = list(obtener_conocimientos())
    if len(conocimientos) != 44 or len({int(c['id']) for c in conocimientos}) != 44:
        raise RuntimeError('Catálogo inesperado: se esperaban 44 IDs únicos; no se escribió nada.')
    print('Catálogo oficial validado:', len(conocimientos), 'registros',flush=True)

    # Primero generar en el PC, ANTES de escribir en Neon.
    # Baja la probabilidad de una transacción parcialmente terminada.
    datos = []
    for c in sorted(conocimientos, key=lambda x: int(x['id'])):
        vector = generar_embeddings([_texto_conocimiento(c)], tipo='passage')[0]
        literal = '[' + ','.join(format(float(v), '.9g') for v in vector) + ']'
        datos.append((int(c['id']), MODELO, literal))
    print('Vectores Bekko generados:', len(datos),flush=True)

    conexion = psycopg2.connect(url, connect_timeout=15)
    try:
        with conexion.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS public.expertia_indice_vectorial_bekko (
                    conocimiento_id INTEGER PRIMARY KEY,
                    modelo TEXT NOT NULL,
                    embedding vector(384) NOT NULL
                )
            ''')
            cur.execute('SELECT conocimiento_id FROM public.expertia_indice_vectorial_bekko')
            existentes = {int(f[0]) for f in cur.fetchall()}
            ids_oficiales = {f[0] for f in datos}
            if existentes - ids_oficiales:
                raise RuntimeError('Índice Bekko tiene IDs no oficiales. Operación cancelada.')
            for cid, modelo, literal in datos:
                cur.execute('''
                    INSERT INTO public.expertia_indice_vectorial_bekko
                        (conocimiento_id, modelo, embedding)
                    VALUES (%s, %s, %s::vector)
                    ON CONFLICT (conocimiento_id) DO UPDATE SET
                        modelo=EXCLUDED.modelo,
                        embedding=EXCLUDED.embedding
                ''', (cid, modelo, literal))
            cur.execute('''
                SELECT COUNT(*) FROM public.expertia_indice_vectorial_bekko
                WHERE modelo = %s
            ''', (MODELO,))
            total = cur.fetchone()[0]
            if total != 44:
                raise RuntimeError(f'Índice incompleto: {total}/44; no se confirma.')
        conexion.commit()
        print('INDICE_BEKKO_LISTO: 44/44. Índice E5 original intacto.',flush=True)
    except BaseException:
        conexion.rollback()
        raise
    finally:
        conexion.close()


if __name__ == '__main__':
    main()
