from app.concept_matcher import detectar_conceptos
from app.intent_detector import detectar_intenciones
from app.keyword_matcher import detectar_keywords
from app.knowledge_retriever import buscar_conocimientos


def main():

    print("\n========== EXPERTIA ==========\n")

    # =========================================
    # PREGUNTA DE PRUEBA
    # =========================================

    pregunta = "Quiero retirar una parte de mis cesantías"

    print("Pregunta:")
    print(pregunta)

    # =========================================
    # 1. DETECTAR CONCEPTOS
    # =========================================

    conceptos = detectar_conceptos(pregunta)

    print("\n========== CONCEPTOS ==========\n")

    if conceptos:

        for concepto in conceptos:

            print(
                f"{concepto['concepto']} "
                f"→ {concepto['mejor_score']:.2f}"
            )

    else:

        print("No se detectaron conceptos.")

    # =========================================
    # 2. DETECTAR INTENCIONES
    # =========================================

    intenciones = detectar_intenciones(pregunta)

    print("\n========== INTENCIONES ==========\n")

    if intenciones:

        for intencion in intenciones:

            print(
                f"{intencion['intencion']} "
                f"→ {intencion['mejor_score']:.2f}"
            )

    else:

        print("No se detectaron intenciones.")

    # =========================================
    # 3. DETECTAR KEYWORDS
    # =========================================

    keywords = detectar_keywords(pregunta)

    print("\n========== KEYWORDS ==========\n")

    if keywords:

        for resultado in keywords:

            print(
                f"Conocimiento: "
                f"{resultado['conocimiento_id']}"
            )

            print(
                f"Score keywords: "
                f"{resultado['score_keywords']:.2f}"
            )

            print("\nKeywords detectadas:")

            for keyword in resultado[
                "keywords_detectadas"
            ]:

                print(
                    f"  - {keyword['keyword']} "
                    f"→ {keyword['score']:.2f}"
                )

            print("\n" + "-" * 50)

    else:

        print("No se detectaron keywords.")

    # =========================================
    # 4. BUSCAR CONOCIMIENTOS
    # =========================================

    conocimientos = buscar_conocimientos(
        conceptos,
        intenciones,
        keywords
    )

    print("\n========== CONOCIMIENTOS ==========\n")

    if not conocimientos:

        print(
            "No se encontraron conocimientos "
            "relacionados con la pregunta."
        )

        return

    # =========================================
    # 5. MOSTRAR RESULTADOS
    # =========================================

    for conocimiento in conocimientos:

        print(
            f"ID: "
            f"{conocimiento['conocimiento_id']}"
        )

        print(
            f"Pregunta: "
            f"{conocimiento['pregunta_principal']}"
        )

        print(
            f"Score conceptos: "
            f"{conocimiento['score_conceptos']:.2f}"
        )

        print(
            f"Score intenciones: "
            f"{conocimiento['score_intenciones']:.2f}"
        )

        print(
            f"Score keywords: "
            f"{conocimiento['score_keywords']:.2f}"
        )

        print(
            f"Score final: "
            f"{conocimiento.get('score_final', 0):.2f}"
        )

        # =====================================
        # CONCEPTOS
        # =====================================

        print("\nConceptos:")

        for concepto in conocimiento[
            "conceptos_detectados"
        ]:

            print(
                f"  - {concepto['concepto']} "
                f"→ {concepto['score']:.2f}"
            )

        # =====================================
        # INTENCIONES
        # =====================================

        print("\nIntenciones:")

        for intencion in conocimiento[
            "intenciones_detectadas"
        ]:

            print(
                f"  - {intencion['intencion']} "
                f"→ {intencion['score']:.2f}"
            )

        # =====================================
        # KEYWORDS
        # =====================================

        print("\nKeywords:")

        for keyword in conocimiento[
            "keywords_detectadas"
        ]:

            print(
                f"  - {keyword['keyword']} "
                f"→ {keyword['score']:.2f}"
            )

        # =====================================
        # RECURSOS
        # =====================================

        print("\nRecursos:")

        recursos = conocimiento.get(
            "recursos",
            []
        )

        if recursos:

            for recurso in recursos:

                print(
                    f"  - {recurso.get('nombre', 'Sin nombre')}"
                )

                print(
                    f"    Tipo: "
                    f"{recurso.get('tipo', 'Sin tipo')}"
                )

                print(
                    f"    URL: "
                    f"{recurso.get('url', 'Sin URL')}"
                )

                print(
                    f"    Descripción: "
                    f"{recurso.get('descripcion', '')}"
                )

        else:

            print(
                "  No hay recursos asociados."
            )

        # =====================================
        # SEPARADOR
        # =====================================

        print("\n" + "=" * 60)


# =========================================
# EJECUTAR PROGRAMA
# =========================================

if __name__ == "__main__":
    main()