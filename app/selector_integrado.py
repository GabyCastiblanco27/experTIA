
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

from app.expertia_selector_pgvector_dev import (
    seleccionar as seleccionar_base,
    _resultado_rescate,
)
from app.repository import obtener_conocimientos

CONFIG = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "coberturas_hibridas_dev.json"
)


def normalizar(texto):
    texto = unicodedata.normalize(
        "NFKD", str(texto or "").lower()
    )
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )
    return " ".join(re.findall(r"[a-z0-9]+", texto))


def contiene(texto, frase):
    return (
        " " + normalizar(frase) + " "
        in " " + normalizar(texto) + " "
    )


def validar_regla(pregunta, conocimiento):
    try:
        datos = json.loads(
            CONFIG.read_text(encoding="utf-8-sig")
        )
        regla = datos["reglas"].get(
            str(int(conocimiento["id"]))
        )

        if not regla:
            return False

        respuesta = conocimiento.get("respuesta") or ""

        huella = hashlib.sha256(
            normalizar(respuesta).encode("utf-8")
        ).hexdigest()

        return (
            huella == regla["huella_respuesta"]
            and all(
                any(
                    contiene(pregunta, expresion)
                    for expresion in grupo
                )
                for grupo in regla["grupos"]
            )
            and not any(
                contiene(pregunta, expresion)
                for expresion in regla["excluir"]
            )
            and all(
                contiene(respuesta, evidencia)
                for evidencia in regla["evidencias"]
            )
        )

    except (OSError, ValueError, KeyError, TypeError):
        return False



def seleccionar(pregunta):
    resultado, diagnostico = seleccionar_base(pregunta)

    if os.getenv("EXPERTIA_ENTORNO", "").lower() != "dev":
        return resultado, diagnostico

    if os.getenv("EXPERTIA_RESCATES_CONSENSO_DEV", "0") != "0":
        return resultado, diagnostico

    if diagnostico.get("estado_vectorial") == "NO_DISPONIBLE":
        return resultado, diagnostico

    # Mantener las aclaraciones originales protegidas.
    if diagnostico.get("motivo") == "proteccion_existente":
        return resultado, diagnostico

    # Permitir revisar aclaraciones provisionales del h?brido.
    if resultado.get("requiere_aclaracion"):
        if diagnostico.get("motivo") not in (
            "evidencia_no_concluyente",
            "evidencia_insuficiente",
        ):
            return resultado, diagnostico

    arbitro = diagnostico.get("arbitro_sombra") or {}
    pre = diagnostico.get("prevalidacion_consenso") or {}

    if not (
        arbitro.get("consenso_estricto") is True
        and pre.get("validaciones_tecnicas_superadas") is True
        and pre.get("id_candidato") is not None
    ):
        return resultado, diagnostico

    candidato_id = int(pre["id_candidato"])

    candidato = next(
        (
            c for c in obtener_conocimientos()
            if int(c["id"]) == candidato_id
        ),
        None,
    )

    if candidato is not None and validar_regla(pregunta, candidato):
        diag = {
            **diagnostico,
            "decision": "RESPUESTA_HIBRIDA_REGLA_DEV",
            "motivo": "consenso_y_regla_documental_acotada",
            "cobertura_certificada": False,
            "cobertura_validada_por_reglas": True,
            "pendiente_validacion_productiva": True,
        }

        respuesta = _resultado_rescate(candidato, diag)

        conocimiento = respuesta.get("resultado") or {}
        detalle = conocimiento.setdefault("detalle_ranking", {})
        detalle["metodo"] = "rescate_acotado_dev"

        return respuesta, diag

    # Desacuerdo sin cobertura suficiente:
    # no entregar un procedimiento diferente como definitivo.
    conocimiento_actual = resultado.get("resultado") or {}
    id_actual = conocimiento_actual.get("id")

    if (
        resultado.get("encontrado")
        and id_actual is not None
        and int(id_actual) != candidato_id
    ):
        diag = {
            **diagnostico,
            "decision": "ACLARACION",
            "motivo": "desacuerdo_sin_alcance_documental",
            "cobertura_certificada": False,
            "requiere_revision_humana": True,
        }

        return {
            "encontrado": False,
            "confianza": 0.0,
            "resultado": None,
            "requiere_aclaracion": True,
            "mensaje": (
                "Encontr? informaci?n relacionada, pero necesito "
                "que precises el tr?mite o documento solicitado."
            ),
        }, diag

    return resultado, diagnostico
