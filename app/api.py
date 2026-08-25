"""
api.py

API REST del motor de búsqueda de ExperTIA.
"""

from typing import Optional

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

    usuario: Optional[str] = None

    top_k: int = Field(
        default=5,
        ge=1,
        le=20
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

        resultado = (
            buscar_conocimiento(

                consulta.pregunta,

                consulta.top_k
            )
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

            usuario=consulta.usuario,

            pregunta=consulta.pregunta,

            conocimiento_id=conocimiento_id,

            confianza=resultado.get(
                "confianza",
                0
            )
        )

        return resultado

    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=(
                "Error ejecutando el "
                "motor de búsqueda: "
                + str(error)
            )
        )