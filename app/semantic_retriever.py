# -*- coding: utf-8 -*-
"""Bekko para ExperTIA con carga aislada para servidores de RAM limitada.

El proceso web no carga ni el tokenizer ni ONNX. Ejecuta primero un proceso
corto para tokenizar, espera a que termine y solo despues inicia otro
proceso para inferencia. Conservar modelo, pooling, limite y vectores.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from threading import Lock

MODELO = "hotchpotch/bekko-embedding-v1-a8m"
_MODELO_DIR = Path(__file__).resolve().parents[1] / "modelos" / "bekko"
_MODELO_ONNX = _MODELO_DIR / "onnx" / "model.onnx"
_TOKENIZER_JSON = _MODELO_DIR / "tokenizer.json"
_MAX_TOKENS = 192

# Serializa toda la operacion en un worker web. No multiplica consumos
# por peticiones HTTP simultaneas dentro del mismo proceso uvicorn.
_LOCK = Lock()


def _ejecutar(etapa: str, datos: dict, timeout: int) -> dict:
    entorno = os.environ.copy()
    entorno.update({
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "MALLOC_ARENA_MAX": "2",
    })
    try:
        proceso = subprocess.run(
            [sys.executable, "-m", "app.bekko_worker", etapa],
            input=json.dumps(datos, ensure_ascii=False),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            env=entorno,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Bekko etapa {etapa}: tiempo agotado") from e
    if proceso.returncode != 0:
        # El selector conserva el fallback tradicional. No exponer stderr de
        # librerias ni secretos de infraestructura al cliente.
        raise RuntimeError(
            f"Bekko etapa {etapa}: proceso finalizo con codigo {proceso.returncode}"
        )
    try:
        respuesta = json.loads(proceso.stdout)
        if not isinstance(respuesta, dict):
            raise ValueError("Formato inesperado")
        return respuesta
    except (ValueError, TypeError) as e:
        raise RuntimeError(f"Bekko etapa {etapa}: salida no valida") from e


def generar_embeddings(textos, tipo="passage"):
    """Devuelve ndarray (n,384) normalizado, igual contrato del selector."""
    if tipo not in ("query", "passage"):
        raise ValueError("tipo debe ser 'query' o 'passage'")
    if not textos:
        raise ValueError("Se requiere al menos un texto")
    if not _MODELO_ONNX.is_file() or not _TOKENIZER_JSON.is_file():
        raise FileNotFoundError(
            "Bekko no preparado: python scripts/descargar_modelo_bekko.py"
        )

    # Los procesos son SECUENCIALES: el tokenizer ya termino y libero su
    # memoria antes de que se cargue ONNX Runtime.
    with _LOCK:
        codificados = _ejecutar(
            "tokenizar", {"textos": [str(t) for t in textos]}, timeout=40
        )
        vectores = _ejecutar("inferir", codificados, timeout=60)

    # Metrica para diagnostico: son picos de PROCESOS SEPARADOS,
    # no se suman entre si. No incluye preguntas ni credenciales.
    try:
        import resource
        padre = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    except ImportError:
        padre = "no_disponible"
    logging.getLogger("uvicorn.error").info(
        "BEKKO_PROCESOS_RAM pico_token_mb=%s pico_inferencia_mb=%s pico_api_mb=%s",
        codificados.get("_worker_peak_mb", "nd"),
        vectores.get("_worker_peak_mb", "nd"),
        padre,
    )

    # Solo importar numpy en el servidor web al terminar los dos procesos.
    import numpy as np
    matriz = np.asarray(vectores.get("vectores"), dtype=np.float32)
    if (
        matriz.shape != (len(textos), 384)
        or not np.isfinite(matriz).all()
    ):
        raise RuntimeError("Bekko devolvio matriz incorrecta")
    return matriz


def calcular_similitud(pregunta, documentos):
    """Conserva el contrato previo de ranking vectorial."""
    if not documentos:
        return []
    import numpy as np
    vectores = generar_embeddings([pregunta] + list(documentos), tipo="query")
    similitudes = np.dot(vectores[1:], vectores[0])
    ranking = np.argsort(-similitudes)
    return [
        {
            "indice": int(i),
            "documento": documentos[i],
            "similitud": round(float(similitudes[i]), 4),
        }
        for i in ranking
    ]
