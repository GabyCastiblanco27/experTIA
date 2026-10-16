
from functools import lru_cache
from sentence_transformers import SentenceTransformer
import numpy as np


MODELO = "intfloat/multilingual-e5-small"


@lru_cache(maxsize=1)
def cargar_modelo():
    """
    Carga el modelo una sola vez por proceso.
    """
    return SentenceTransformer(MODELO)


def generar_embeddings(textos, tipo="passage"):
    """
    Convierte textos en vectores semánticos.
    tipo: 'query' para preguntas, 'passage' para conocimientos.
    """
    if tipo not in ("query", "passage"):
        raise ValueError("El tipo debe ser 'query' o 'passage'.")

    if not textos:
        raise ValueError("Debes proporcionar al menos un texto.")

    modelo = cargar_modelo()

    textos_preparados = [
        f"{tipo}: {texto}"
        for texto in textos
    ]

    vectores = modelo.encode(
        textos_preparados,
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    return vectores


def calcular_similitud(pregunta, documentos):
    """
    Compara una pregunta contra una lista de documentos.
    Devuelve los índices ordenados por similitud.
    """
    if not documentos:
        return []

    vector_pregunta = generar_embeddings(
        [pregunta],
        tipo="query"
    )[0]

    vectores_documentos = generar_embeddings(
        documentos,
        tipo="passage"
    )

    similitudes = np.dot(
        vectores_documentos,
        vector_pregunta
    )

    ranking = np.argsort(-similitudes)

    return [
        {
            "indice": int(i),
            "documento": documentos[i],
            "similitud": round(float(similitudes[i]), 4)
        }
        for i in ranking
    ]
