"""
api.py

API REST del motor de búsqueda de ExperTIA.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.database import obtener_conexion

from app.knowledge_retriever import (
    buscar_conocimiento
)

from app.repository import (
    save_query_history
)


# ============================================================
# APLICACIÓN
# ============================================================

app = FastAPI(
    title="ExperTIA Search Engine",
    version="2.0"
)


# ============================================================
# MODELO DE REQUEST
# ============================================================

class ConsultaRequest(BaseModel):

    pregunta: str = Field(
        ...,
        min_length=1
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    conexion = None

    try:

        conexion = obtener_conexion()

        return {
            "status": "ok",
            "database": "connected"
        }

    except Exception as error:

        return {
            "status": "error",
            "database": "disconnected",
            "detalle": str(error)
        }

    finally:

        if conexion:
            conexion.close()


# ============================================================
# BUSCAR
# ============================================================

@app.post("/buscar")
def buscar(
    consulta: ConsultaRequest
):

    try:

        # ----------------------------------------------------
        # Ejecutar motor de búsqueda
        # ----------------------------------------------------

        resultado = buscar_conocimiento(
            consulta.pregunta
        )

        # ----------------------------------------------------
        # Obtener ID del conocimiento seleccionado
        # ----------------------------------------------------

        conocimiento_id = None

        if resultado.get("resultado"):

            conocimiento_id = (
                resultado[
                    "resultado"
                ]["id"]
            )

        # ----------------------------------------------------
        # Guardar historial
        # ----------------------------------------------------

        save_query_history(

            usuario=None,

            pregunta=consulta.pregunta,

            conocimiento_id=conocimiento_id,

            confianza=resultado.get(
                "confianza",
                0
            )
        )

        # ----------------------------------------------------
        # Devolver solamente la información necesaria
        # ----------------------------------------------------

        if not resultado.get("encontrado"):

            return {

                "encontrado": False,

                "confianza":
                    resultado.get(
                        "confianza",
                        0
                    ),

                "respuesta":
                    "No encontré información específica sobre tu consulta.",

                "titulo": None,

                "area": None,

                "proceso": None,

                "responsable": None,

                "recursos": []
            }

        conocimiento = (
            resultado["resultado"]
        )

        return {

            "encontrado": True,

            "confianza":
                conocimiento["confianza"],

            "titulo":
                conocimiento["titulo"],

            "respuesta":
                conocimiento["respuesta"],

            "area":
                conocimiento["area"],

            "proceso":
                conocimiento["proceso"],

            "responsable":
                conocimiento["responsable"],

            "recursos":
                conocimiento["recursos"]
        }

    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=(
                "Error ejecutando el "
                "motor de búsqueda: "
                + str(error)
            )
        )