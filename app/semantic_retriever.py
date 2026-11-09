# -*- coding: utf-8 -*-
"""Embeddings compactos para ExperTIA usando ONNX Runtime sin PyTorch.

Modelo: hotchpotch/bekko-embedding-v1-a8m.
El archivo ONNX y tokenizer se preparan durante el Build de Render.
El modelo NO recibe prefijos E5: no son compatibles con Bekko.
"""
import os

# Debe configurarse antes de importar ONNX/NumPy.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from functools import lru_cache
from pathlib import Path

import numpy as np

MODELO = "hotchpotch/bekko-embedding-v1-a8m"
_MODELO_DIR = Path(__file__).resolve().parents[1] / "modelos" / "bekko"
_MODELO_ONNX = _MODELO_DIR / "onnx" / "model.onnx"
_TOKENIZER_JSON = _MODELO_DIR / "tokenizer.json"
_MAX_TOKENS = 192


@lru_cache(maxsize=1)
def cargar_modelo():
    """Carga una sola sesión ONNX, en CPU y con memoria de arena desactivada."""
    if not _MODELO_ONNX.is_file() or not _TOKENIZER_JSON.is_file():
        raise FileNotFoundError(
            "Bekko no preparado. Ejecuta: python scripts/descargar_modelo_bekko.py"
        )

    # Imports tardíos: el motor tradicional nunca carga estas librerías.
    import onnxruntime as ort
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(str(_TOKENIZER_JSON))
    tokenizer.enable_truncation(max_length=_MAX_TOKENS)
    opciones = ort.SessionOptions()
    opciones.intra_op_num_threads = 1
    opciones.inter_op_num_threads = 1
    opciones.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    opciones.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    opciones.enable_cpu_mem_arena = False
    opciones.enable_mem_pattern = False

    sesion = ort.InferenceSession(
        str(_MODELO_ONNX),
        sess_options=opciones,
        providers=["CPUExecutionProvider"],
    )
    entradas = {entrada.name for entrada in sesion.get_inputs()}
    if not entradas.issubset({"input_ids", "attention_mask", "token_type_ids"}):
        raise RuntimeError("La firma ONNX de Bekko no coincide con la esperada")
    return tokenizer, sesion, entradas


def _vector_texto(texto, tokenizer, sesion, nombres):
    tokens = tokenizer.encode(texto, add_special_tokens=True)
    entradas = {
        "input_ids": np.asarray([tokens.ids], dtype=np.int64),
        "attention_mask": np.asarray([tokens.attention_mask], dtype=np.int64),
        "token_type_ids": np.asarray([tokens.type_ids], dtype=np.int64),
    }
    salida = np.asarray(sesion.run(None, {k: entradas[k] for k in nombres})[0])

    if salida.ndim == 3:
        mascara = entradas["attention_mask"][..., None]
        vector = (salida * mascara).sum(axis=1) / np.maximum(mascara.sum(axis=1), 1)
    elif salida.ndim == 2:
        vector = salida
    else:
        raise RuntimeError(f"Forma ONNX inesperada: {salida.shape}")

    if vector.shape != (1, 384) or not np.isfinite(vector).all():
        raise RuntimeError("Bekko devolvió embeddings inválidos")
    norma = float(np.linalg.norm(vector[0]))
    if not np.isfinite(norma) or norma < 1e-8:
        raise RuntimeError("Norma de embedding inválida")
    return np.asarray(vector[0] / norma, dtype=np.float32)


def generar_embeddings(textos, tipo="passage"):
    """Contratado con selector actual: matriz (n, 384) normalizada.

    'tipo' se conserva para compatibilidad, pero Bekko no usa prefijos query/passage.
    La inferencia es secuencial para limitar la RAM.
    """
    if tipo not in ("query", "passage"):
        raise ValueError("tipo debe ser 'query' o 'passage'")
    if not textos:
        raise ValueError("Se requiere al menos un texto")
    tokenizer, sesion, nombres = cargar_modelo()
    return np.stack([
        _vector_texto(str(t), tokenizer, sesion, nombres) for t in textos
    ], axis=0)


def calcular_similitud(pregunta, documentos):
    """Conserva el formato histórico usado por otras partes de ExperTIA."""
    if not documentos:
        return []
    vector_pregunta = generar_embeddings([pregunta], tipo="query")[0]
    vectores = generar_embeddings(documentos, tipo="passage")
    similitudes = np.dot(vectores, vector_pregunta)
    ranking = np.argsort(-similitudes)
    return [
        {
            "indice": int(i),
            "documento": documentos[i],
            "similitud": round(float(similitudes[i]), 4),
        }
        for i in ranking
    ]
