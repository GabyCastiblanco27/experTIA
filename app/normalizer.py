import re
import unicodedata


# Palabras que normalmente no aportan valor
# para encontrar el conocimiento correcto.
PALABRAS_VACIAS = {

    "el",
    "la",
    "los",
    "las",

    "un",
    "una",
    "unos",
    "unas",

    "de",
    "del",
    "al",
    "a",
    "en",

    "por",
    "para",
    "con",

    "y",
    "o",

    "que",
    "como",
    "cual",
    "cuales",

    "es",
    "son",

    "mi",
    "mis",

    "me",
    "te",
    "se",

    "puedo",
    "puede",

    "necesito",
    "quiero",
    "deseo",

    "hacer",
    "realizar",

    "consultar",
    "buscar",

    "como",
    "donde",
    "cuando"
}


def quitar_tildes(texto):
    """
    Convierte:

    cesantías -> cesantias
    nómina -> nomina
    información -> informacion
    """

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    return "".join(
        caracter
        for caracter in texto
        if unicodedata.category(
            caracter
        ) != "Mn"
    )


def normalizar_texto(texto):
    """
    Normaliza texto para búsqueda.
    """

    if not texto:
        return ""

    texto = str(texto)

    texto = texto.lower()

    texto = quitar_tildes(texto)

    texto = re.sub(
        r"[^a-z0-9\s]",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


def obtener_palabras(texto):
    """
    Devuelve únicamente las palabras relevantes.
    """

    texto_normalizado = (
        normalizar_texto(texto)
    )

    palabras = texto_normalizado.split()

    return [

        palabra

        for palabra in palabras

        if palabra not in PALABRAS_VACIAS
    ]


def obtener_texto_normalizado(texto):
    """
    Devuelve el texto normalizado
    sin palabras vacías.
    """

    return " ".join(
        obtener_palabras(texto)
    )