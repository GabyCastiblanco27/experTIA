from app.database import obtener_conexion


def buscar_conocimientos(
    conceptos,
    intenciones,
    keywords
):
    """
    Busca los conocimientos que mejor coinciden
    con los conceptos, intenciones y keywords detectados.
    """

    conexion = None
    cursor = None

    try:

        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        # =====================================================
        # 1. OBTENER CONOCIMIENTOS ACTIVOS
        # =====================================================

        consulta = """
            SELECT
                c.id AS conocimiento_id,
                c.area_id,
                a.nombre AS area,
                c.proceso,
                c.sub_proceso,
                c.tema,
                c.pregunta_principal,
                c.descripcion_proceso,
                c.paso_a_paso,
                c.responsable,
                c.entradas,
                c.salidas,
                c.herramientas,
                c.link_politica,
                c.estado
            FROM conocimientos c

            LEFT JOIN areas a
                ON c.area_id = a.id

            WHERE c.estado = 'ACTIVO'

            ORDER BY c.id;
        """

        cursor.execute(consulta)

        conocimientos = cursor.fetchall()

        # =====================================================
        # 2. CONVERTIR DETECCIONES EN DICCIONARIOS
        #    PARA BUSCARLAS MÁS FÁCILMENTE
        # =====================================================

        conceptos_por_id = {}

        for concepto in conceptos:

            concepto_id = concepto["concepto_id"]

            conceptos_por_id[concepto_id] = concepto


        intenciones_por_id = {}

        for intencion in intenciones:

            intencion_id = intencion["intencion_id"]

            intenciones_por_id[intencion_id] = intencion


        keywords_por_id = {}

        for resultado_keyword in keywords:

            conocimiento_id = (
                resultado_keyword["conocimiento_id"]
            )

            keywords_por_id[
                conocimiento_id
            ] = resultado_keyword

        # =====================================================
        # 3. RECORRER CADA CONOCIMIENTO
        # =====================================================

        resultados = []

        for conocimiento in conocimientos:

            conocimiento_id = (
                conocimiento["conocimiento_id"]
            )

            # -----------------------------------------------
            # SCORE DE CONCEPTOS
            # -----------------------------------------------

            score_conceptos = 0.0

            conceptos_detectados = []


            consulta_conceptos = """
                SELECT
                    cc.concepto_id,
                    cc.peso,
                    c.nombre AS concepto
                FROM conocimiento_conceptos cc

                INNER JOIN conceptos c
                    ON cc.concepto_id = c.id

                WHERE cc.conocimiento_id = %s
                  AND c.activo = TRUE;
            """

            cursor.execute(
                consulta_conceptos,
                (conocimiento_id,)
            )

            relaciones_conceptos = (
                cursor.fetchall()
            )


            for relacion in relaciones_conceptos:

                concepto_id = (
                    relacion["concepto_id"]
                )

                if concepto_id not in conceptos_por_id:
                    continue

                concepto_detectado = (
                    conceptos_por_id[concepto_id]
                )

                score = (
                    float(
                        concepto_detectado[
                            "mejor_score"
                        ]
                    )
                    *
                    float(
                        relacion["peso"]
                    )
                )

                score_conceptos += score

                conceptos_detectados.append({

                    "concepto_id":
                        concepto_id,

                    "concepto":
                        relacion["concepto"],

                    "score":
                        round(score, 4),

                    "peso_conocimiento":
                        float(
                            relacion["peso"]
                        )
                })


            # -----------------------------------------------
            # SCORE DE INTENCIONES
            # -----------------------------------------------

            score_intenciones = 0.0

            intenciones_detectadas = []


            consulta_intenciones = """
                SELECT
                    ci.intencion_id,
                    ci.peso,
                    i.nombre AS intencion
                FROM conocimiento_intenciones ci

                INNER JOIN intenciones i
                    ON ci.intencion_id = i.id

                WHERE ci.conocimiento_id = %s
                  AND i.activo = TRUE;
            """

            cursor.execute(
                consulta_intenciones,
                (conocimiento_id,)
            )

            relaciones_intenciones = (
                cursor.fetchall()
            )


            for relacion in relaciones_intenciones:

                intencion_id = (
                    relacion["intencion_id"]
                )

                if intencion_id not in intenciones_por_id:
                    continue

                intencion_detectada = (
                    intenciones_por_id[
                        intencion_id
                    ]
                )

                score = (
                    float(
                        intencion_detectada[
                            "mejor_score"
                        ]
                    )
                    *
                    float(
                        relacion["peso"]
                    )
                )

                score_intenciones += score

                intenciones_detectadas.append({

                    "intencion_id":
                        intencion_id,

                    "intencion":
                        relacion["intencion"],

                    "score":
                        round(score, 4),

                    "peso_intencion":
                        float(
                            relacion["peso"]
                        )
                })


            # -----------------------------------------------
            # SCORE DE KEYWORDS
            # -----------------------------------------------

            score_keywords = 0.0

            keywords_detectadas = []


            if conocimiento_id in keywords_por_id:

                resultado_keyword = (
                    keywords_por_id[
                        conocimiento_id
                    ]
                )

                # -------------------------------------------
                # IMPORTANTE:
                # resultado_keyword viene de detectar_keywords()
                #
                # Tiene esta estructura:
                #
                # {
                #   "conocimiento_id": 1,
                #   "score_keywords": 1.0,
                #   "keywords_detectadas": [...]
                # }
                # -------------------------------------------

                score_keywords = float(
                    resultado_keyword.get(
                        "score_keywords",
                        0.0
                    )
                )

                keywords_detectadas = (
                    resultado_keyword.get(
                        "keywords_detectadas",
                        []
                    )
                )


            # =================================================
            # 4. CALCULAR SCORE FINAL
            # =================================================

            # Por ahora utilizamos:
            #
            # 50% conceptos
            # 30% intención
            # 20% keywords
            #
            # Más adelante podemos ajustar estos pesos
            # después de hacer pruebas reales.

            score_final = (

                score_conceptos * 0.50

                +

                score_intenciones * 0.30

                +

                score_keywords * 0.20
            )


            # =================================================
            # 5. SOLO GUARDAR CONOCIMIENTOS CON COINCIDENCIAS
            # =================================================

            if (

                score_conceptos > 0

                or

                score_intenciones > 0

                or

                score_keywords > 0

            ):

                resultados.append({

                    "conocimiento_id":
                        conocimiento_id,

                    "area_id":
                        conocimiento["area_id"],

                    "area":
                        conocimiento["area"],

                    "proceso":
                        conocimiento["proceso"],

                    "sub_proceso":
                        conocimiento["sub_proceso"],

                    "tema":
                        conocimiento["tema"],

                    "pregunta_principal":
                        conocimiento[
                            "pregunta_principal"
                        ],

                    "descripcion_proceso":
                        conocimiento[
                            "descripcion_proceso"
                        ],

                    "paso_a_paso":
                        conocimiento[
                            "paso_a_paso"
                        ],

                    "responsable":
                        conocimiento[
                            "responsable"
                        ],

                    "entradas":
                        conocimiento[
                            "entradas"
                        ],

                    "salidas":
                        conocimiento[
                            "salidas"
                        ],

                    "herramientas":
                        conocimiento[
                            "herramientas"
                        ],

                    "link_politica":
                        conocimiento[
                            "link_politica"
                        ],

                    "conceptos_detectados":
                        conceptos_detectados,

                    "keywords_detectadas":
                        keywords_detectadas,

                    "intenciones_detectadas":
                        intenciones_detectadas,

                    "score_conceptos":
                        round(
                            score_conceptos,
                            4
                        ),

                    "score_keywords":
                        round(
                            score_keywords,
                            4
                        ),

                    "score_intenciones":
                        round(
                            score_intenciones,
                            4
                        ),

                    "score_final":
                        round(
                            score_final,
                            4
                        )
                })


        # =====================================================
        # 6. ORDENAR POR RELEVANCIA
        # =====================================================

        resultados.sort(
            key=lambda x:
                x["score_final"],
            reverse=True
        )


        # =====================================================
        # 7. DEVOLVER LOS RESULTADOS
        # =====================================================

        return resultados


    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()