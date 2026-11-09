# -*- coding: utf-8 -*-
"""Verificación local simple de Bekko; no necesita Neon ni cambia archivos."""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

import numpy as np
from app.semantic_retriever import generar_embeddings

preguntas = [
    'Como puedo solicitar mis cesantias?',
    'Como actualizo mi RUT?',
    'Como reporto una fuga de agua?',
]
v = generar_embeddings(preguntas, tipo='query')
if v.shape != (3,384) or not np.isfinite(v).all():
    raise RuntimeError('Dimensión o embeddings incorrectos')
print('BEKKO_VECTOR_OK', v.shape)
try:
    import psutil
    memoria = psutil.Process().memory_info().rss / (1024**2)
    print('RAM_ACTUAL_MB', round(memoria,1))
except ImportError:
    pass
