# -*- coding: utf-8 -*-
"""Etapas aisladas de Bekko. Solo llamar desde semantic_retriever.py.

IMPORTANTE: no cargar tokenizer y onnxruntime en el mismo subproceso.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

BASE = Path(__file__).resolve().parents[1] / "modelos" / "bekko"


def tokenizar(entrada: dict) -> dict:
    # Importacion exclusiva de esta etapa. No importar ONNX ni numpy aqui.
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(str(BASE / "tokenizer.json"))
    tokenizer.enable_truncation(max_length=192)
    textos = entrada.get("textos")
    if not isinstance(textos, list) or not textos or len(textos) > 100:
        raise ValueError("Cantidad de textos no autorizada")
    tokens = [tokenizer.encode(str(t), add_special_tokens=True) for t in textos]
    return {
        "input_ids": [t.ids for t in tokens],
        "attention_mask": [t.attention_mask for t in tokens],
        "token_type_ids": [t.type_ids for t in tokens],
    }


def inferir(entrada: dict) -> dict:
    # Importacion exclusiva de esta etapa. No importar tokenizers aqui.
    import numpy as np
    import onnxruntime as ort

    opciones = ort.SessionOptions()
    opciones.intra_op_num_threads = 1
    opciones.inter_op_num_threads = 1
    opciones.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    opciones.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    opciones.enable_cpu_mem_arena = False
    opciones.enable_mem_pattern = False

    sesion = ort.InferenceSession(
        str(BASE / "onnx" / "model.onnx"),
        sess_options=opciones,
        providers=["CPUExecutionProvider"],
    )
    requeridos = {e.name for e in sesion.get_inputs()}
    if not requeridos <= {"input_ids", "attention_mask", "token_type_ids"}:
        raise RuntimeError("Firma ONNX de Bekko inesperada")

    ids = entrada["input_ids"]
    mascaras = entrada["attention_mask"]
    tipos = entrada["token_type_ids"]
    if not (len(ids) == len(mascaras) == len(tipos) and 1 <= len(ids) <= 100):
        raise ValueError("Formato tokenizado invalido")

    vectores = []
    for i in range(len(ids)):
        disponibles = {
            "input_ids": np.asarray([ids[i]], dtype=np.int64),
            "attention_mask": np.asarray([mascaras[i]], dtype=np.int64),
            "token_type_ids": np.asarray([tipos[i]], dtype=np.int64),
        }
        salida = np.asarray(sesion.run(
            None, {k: disponibles[k] for k in requeridos}
        )[0])
        if salida.ndim == 3:
            mascara = disponibles["attention_mask"][..., None]
            vector = (
                (salida * mascara).sum(axis=1)
                / np.maximum(mascara.sum(axis=1), 1)
            )
        elif salida.ndim == 2:
            vector = salida
        else:
            raise RuntimeError("Forma ONNX inesperada")
        if vector.shape != (1, 384) or not np.isfinite(vector).all():
            raise RuntimeError("Vector Bekko invalido")
        norma = float(np.linalg.norm(vector[0]))
        if not np.isfinite(norma) or norma < 1e-8:
            raise RuntimeError("Norma Bekko invalida")
        vectores.append(np.asarray(vector[0] / norma, dtype=np.float32).tolist())
    return {"vectores": vectores}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"tokenizar", "inferir"}:
        raise SystemExit(2)
    entrada = json.load(sys.stdin)
    salida = tokenizar(entrada) if sys.argv[1] == "tokenizar" else inferir(entrada)
    try:
        import resource
        salida["_worker_peak_mb"] = round(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1
        )
    except ImportError:
        pass
    sys.stdout.write(json.dumps(salida, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
