
from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType


# Mismo modelo base utilizado para los embeddings de Neon.
MODELO = "intfloat/multilingual-e5-small"

_MODELO_ONNX = "expertia/multilingual-e5-small-int8"


@lru_cache(maxsize=1)
def cargar_modelo():
    """
    Ejecuta multilingual-e5-small mediante ONNX INT8.
    El modelo se carga una sola vez por proceso.
    """
    TextEmbedding.add_custom_model(
        model=_MODELO_ONNX,
        pooling=PoolingType.MEAN,
        normalization=True,
        sources=ModelSource(hf=MODELO),
        dim=384,
        model_file="onnx/model_qint8_avx512_vnni.onnx",
    )

    return TextEmbedding(
        model_name=_MODELO_ONNX,
        threads=1,
        max_length=512,
    )


def generar_embeddings(textos, tipo="passage"):
    """
    Genera embeddings de 384 dimensiones.
    Conserva los prefijos E5: query y passage.
    """
    if tipo not in ("query", "passage"):
        raise ValueError("El tipo debe ser 'query' o 'passage'.")

    if not textos:
        raise ValueError("Debes proporcionar al menos un texto.")

    textos_preparados = [
        f"{tipo}: {texto}"
        for texto in textos
    ]

    vectores = list(
        cargar_modelo().embed(
            textos_preparados,
            batch_size=1,
        )
    )

    salida = np.stack(vectores).astype(np.float32)

    if (
        salida.ndim != 2
        or salida.shape[1] != 384
        or not np.isfinite(salida).all()
    ):
        raise RuntimeError("Embeddings no validos")

    return salida


def calcular_similitud(pregunta, documentos):
    """
    Compara una pregunta contra documentos.
    Devuelve los índices ordenados por similitud.
    """
    if not documentos:
        return []

    vector_pregunta = generar_embeddings(
        [pregunta],
        tipo="query",
    )[0]

    vectores_documentos = generar_embeddings(
        documentos,
        tipo="passage",
    )

    similitudes = np.dot(
        vectores_documentos,
        vector_pregunta,
    )

    ranking = np.argsort(-similitudes)

    return [
        {
            "indice": int(i),
            "documento": documentos[i],
            "similitud": round(float(similitudes[i]), 4),
        }
        for i in ranking
    ]
