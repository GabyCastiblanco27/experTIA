from fastapi import FastAPI
from pydantic import BaseModel

from app.knowledge_retriever import (
    buscar_conocimientos
)

app = FastAPI(
    title="ExperTIA API"
)


class PreguntaRequest(BaseModel):
    pregunta: str


@app.get("/")
def inicio():

    return {
        "mensaje": "ExperTIA API funcionando"
    }


@app.post("/buscar")
def buscar(request: PreguntaRequest):

    pregunta = request.pregunta.strip()

    if not pregunta:

        return {
            "encontrado": False,
            "mensaje": "Debes ingresar una pregunta"
        }

    resultados = buscar_conocimientos(
        pregunta
    )

    if not resultados:

        return {
            "encontrado": False,
            "mensaje": "No encontré información relacionada"
        }

    mejor = resultados[0]

    return {
        "encontrado": True,
        "respuesta": {
            "titulo":
                mejor["titulo"],

            "area":
                mejor["area"],

            "proceso":
                mejor["proceso"],

            "descripcion":
                mejor["descripcion"],

            "respuesta":
                mejor["respuesta"],

            "responsable":
                mejor["responsable"],

            "recursos":
                mejor["recursos"]
        }
    }