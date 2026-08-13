from fastapi import FastAPI
from pydantic import BaseModel

from app.concept_matcher import detectar_conceptos
from app.intent_detector import detectar_intenciones
from app.keyword_matcher import detectar_keywords
from app.knowledge_retriever import buscar_conocimientos


app = FastAPI(
    title="ExperTIA API",
    description="Motor de búsqueda inteligente de ExperTIA",
    version="1.0.0"
)


# =====================================================
# MODELO DE ENTRADA
# =====================================================

class PreguntaRequest(BaseModel):
    pregunta: str


# =====================================================
# ENDPOINT PRINCIPAL
# =====================================================

@app.get("/")
def inicio():

    return {
        "mensaje": "ExperTIA API funcionando",
        "estado": "OK"
    }


# =====================================================
# ENDPOINT DE BÚSQUEDA
# =====================================================

@app.post("/buscar")
def buscar(request: PreguntaRequest):

    pregunta = request.pregunta.strip()

    # =================================================
    # VALIDAR PREGUNTA
    # =================================================

    if not pregunta:

        return {
            "encontrado": False,
            "pregunta": pregunta,
            "respuesta": None,
            "mensaje": "Debes ingresar una pregunta."
        }

    # =================================================
    # 1. DETECTAR CONCEPTOS
    # =================================================

    conceptos = detectar_conceptos(pregunta)

    # =================================================
    # 2. DETECTAR INTENCIONES
    # =================================================

    intenciones = detectar_intenciones(pregunta)

    # =================================================
    # 3. DETECTAR KEYWORDS
    # =================================================

    keywords = detectar_keywords(pregunta)

    # =================================================
    # 4. BUSCAR CONOCIMIENTOS
    # =================================================

    conocimientos = buscar_conocimientos(
        conceptos,
        intenciones,
        keywords
    )

    # =================================================
    # 5. SI NO ENCUENTRA INFORMACIÓN
    # =================================================

    if not conocimientos:

        return {
            "encontrado": False,
            "pregunta": pregunta,
            "respuesta": None,
            "mensaje": "No encontré información relacionada con tu pregunta."
        }

    # =================================================
    # 6. TOMAR EL MEJOR CONOCIMIENTO
    # =================================================

    mejor = conocimientos[0]

    # =================================================
    # 7. CONSTRUIR RESPUESTA
    # =================================================

    respuesta = {

        "area":
            mejor.get("area"),

        "proceso":
            mejor.get("proceso"),

        "sub_proceso":
            mejor.get("sub_proceso"),

        "tema":
            mejor.get("tema"),

        "pregunta_principal":
            mejor.get("pregunta_principal"),

        "descripcion_proceso":
            mejor.get("descripcion_proceso"),

        "paso_a_paso":
            mejor.get("paso_a_paso"),

        "responsable":
            mejor.get("responsable"),

        "entradas":
            mejor.get("entradas"),

        "salidas":
            mejor.get("salidas"),

        "herramientas":
            mejor.get("herramientas"),

        "recursos":
            mejor.get("recursos", []),

        "recursos_texto":
            mejor.get("recursos_texto", "")
    }

    # =================================================
    # 8. RESPUESTA FINAL
    # =================================================

    return {

        "encontrado": True,

        "pregunta": pregunta,

        "respuesta": respuesta

    }