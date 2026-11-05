
"""API REST de ExperTIA: tradicional e hibrido DEV."""

import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.database import obtener_conexion
from app.busqueda_asistida import buscar_conocimiento_asistido
from app.repository import save_query_history

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ExperTIA Search Engine",
    version="2.1",
)


class ConsultaRequest(BaseModel):
    pregunta: str = Field(..., min_length=1)


@app.get("/health")
def health():
    conexion = None

    try:
        conexion = obtener_conexion()
        return {
            "status": "ok",
            "database": "connected",
        }

    except Exception:
        logger.exception("Error consultando la base de datos")
        return {
            "status": "error",
            "database": "disconnected",
        }

    finally:
        if conexion is not None:
            conexion.close()


def _ejecutar_busqueda(pregunta: str) -> dict:
    """
    Punto unico de entrada de ExperTIA.

    - Tradicional por defecto.
    - Hibrido en DEV.
    - Sin rescates experimentales no certificados.
    """

    modo = os.getenv(
        "EXPERTIA_API_MOTOR", "tradicional"
    ).strip().lower()

    if modo == "tradicional":
        return buscar_conocimiento_asistido(pregunta)

    entorno = os.getenv("EXPERTIA_ENTORNO", "").strip().lower()
    if modo == "hibrido_dev":
        if entorno != "dev":
            raise RuntimeError("hibrido_dev solo funciona en DEV")
    elif modo == "hibrido":
        if entorno != "prod":
            raise RuntimeError("hibrido exige EXPERTIA_ENTORNO=prod")
    else:
        raise RuntimeError("Modo de busqueda no autorizado")

    if os.getenv(
        "EXPERTIA_RESCATES_CONSENSO_DEV", "0"
    ) != "0":
        raise RuntimeError(
            "Los rescates experimentales deben estar desactivados"
        )

    # El selector existente ejecuta:
    # tradicional + pgvector + arbitro.
    from app.selector_integrado import seleccionar

    try:
        resultado, diagnostico = seleccionar(pregunta)
    except Exception:
        if modo == "hibrido":
            logger.exception("Fallo el hibrido; se conserva el buscador tradicional")
            return buscar_conocimiento_asistido(pregunta)
        raise

    if not isinstance(resultado, dict) or not isinstance(
        diagnostico, dict
    ):
        raise RuntimeError(
            "El selector devolvio un formato inesperado"
        )

    conocimiento = resultado.get("resultado") or {}
    detalle = conocimiento.get("detalle_ranking") or {}

    # Proteccion adicional ante un rescate no certificado.
    rescate_experimental = (
        diagnostico.get("decision")
        == "PROPUESTA_EXPERIMENTAL_DEV"
        or detalle.get("metodo")
        == "rescate_consenso_experimental_dev"
    )

    if (
        rescate_experimental
        and diagnostico.get("cobertura_certificada") is not True
    ):
        logger.warning("Rescate no certificado bloqueado")

        return {
            "encontrado": False,
            "confianza": 0.0,
            "resultado": None,
            "requiere_aclaracion": True,
            "mensaje": (
                "Encontre informacion relacionada, pero "
                "necesito mas precision para ofrecer "
                "el procedimiento correcto."
            ),
            "_diagnostico_hibrido": diagnostico,
        }

    if diagnostico.get("estado_vectorial") == "NO_DISPONIBLE":
        logger.warning(
            "pgvector DEV no disponible; "
            "se conservo el motor tradicional"
        )

    salida = dict(resultado)
    salida["_diagnostico_hibrido"] = diagnostico

    return salida


@app.post("/buscar")
def buscar(consulta: ConsultaRequest):
    try:
        resultado = _ejecutar_busqueda(consulta.pregunta)

        conocimiento = resultado.get("resultado") or {}

        encontrado = bool(
            resultado.get("encontrado")
            and conocimiento.get("id")
        )

        # Un solo registro de historial por consulta.
        save_query_history(
            usuario=None,
            pregunta=consulta.pregunta,
            conocimiento_id=(
                conocimiento.get("id") if encontrado else None
            ),
            confianza=resultado.get("confianza", 0),
        )

        if not encontrado:
            mensaje = (
                resultado.get("mensaje")
                if resultado.get("requiere_aclaracion")
                else None
            ) or (
                "No encontré información específica "
                "sobre tu consulta."
            )

            return {
                "encontrado": False,
                "confianza": resultado.get("confianza", 0),
                "respuesta": mensaje,
                "titulo": None,
                "area": None,
                "proceso": None,
                "responsable": None,
                "recursos": [],
            }

        detalle = conocimiento.get("detalle_ranking") or {}

        diagnostico = resultado.get("_diagnostico_hibrido")

        if diagnostico is not None:
            detalle = {
                **detalle,
                "diagnostico_hibrido": diagnostico,
            }

        # Se conserva el contrato que consume Power Automate.
        return {
            "encontrado": True,
            "confianza": conocimiento.get(
                "confianza",
                resultado.get("confianza", 0),
            ),
            "titulo": conocimiento.get("titulo"),
            "respuesta": conocimiento.get("respuesta"),
            "area": conocimiento.get("area"),
            "proceso": conocimiento.get("proceso"),
            "responsable": conocimiento.get("responsable"),
            "recursos": conocimiento.get("recursos") or [],
            "detalle_ranking": detalle,
        }

    except Exception:
        logger.exception("Error ejecutando el motor de busqueda")

        raise HTTPException(
            status_code=500,
            detail="Error interno del motor de busqueda",
        )

@app.on_event("startup")
def diagnosticar_neon_vectorial():
    if os.getenv("EXPERTIA_DIAGNOSTICO_VECTOR", "0") != "1":
        return

    import psycopg2

    conexion = None
    try:
        conexion = psycopg2.connect(
            os.environ["EXPERTIA_PGVECTOR_DEV_URL"],
            connect_timeout=8
        )
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM public.expertia_indice_vectorial_dev"
            )
            cantidad = cursor.fetchone()[0]

        logger.warning(
            "DIAGNOSTICO_VECTOR: CONEXION_OK registros=%s",
            cantidad
        )

    except Exception as error:
        logger.warning(
            "DIAGNOSTICO_VECTOR: ERROR tipo=%s",
            type(error).__name__
        )

    finally:
        if conexion:
            conexion.close()