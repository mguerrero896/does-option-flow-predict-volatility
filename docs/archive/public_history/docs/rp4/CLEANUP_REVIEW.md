# RP4 — revisión de limpieza y coherencia documental

## Dictamen

**No se autoriza ningún borrado.** Las versiones científicas anteriores, sus
resultados adversos, fallos numéricos, manifiestos y recibos forman la trazabilidad
del cierre. Estar superadas como punto de entrada no las convierte en basura.

La autoridad de lectura es [RESULTADO_FINAL.md](../../../../rp4/RESULTADO_FINAL.md), revisión
`9ad65b6b8be5d7c7dbbf2af44083a7305be4748d`, SHA-256
`6d629b2416601af39a6e7f4fc0f04db1455b6c20ba4c298e7fb21a6ed00b2b19`.
No hay una propuesta separada: las acciones acotadas se proponen en este documento.
Los archivos de autoridad y los originales congelados no se modificaron.

## Inventario Git: alcance y lectura

El [inventario reproducible](../../../../../artifacts/rp4_cleanup_review/inventory.json)
contiene el commit exacto y la hora del snapshot, alias de los checkouts, puntas
de referencias y resultados reales de `merge-base --is-ancestor`.
La tabla siguiente describe este clon. El inventario incluye además dos raíces
relacionadas y sus metadatos Git, separadas de este clon. No hubo actualización
de referencias remotas ni cambio de rama.

| Alias | Sufijo de referencia | Estado comprobado |
| --- | --- | --- |
| branch_01 | rp4-v2-20260907 | Punta ancestro de HEAD del snapshot; no de origin/main local |
| branch_02 | rp4-v3-20260907 | Rama de trabajo del snapshot; no fusionada en origin/main local |
| branch_03 | rp4-walkforward-20260907 | Punta local ancestro de HEAD; no de origin/main local |
| branch_04 | rp4-walkforward-20260907 | Referencia remota localmente almacenada; misma punta que branch_03 |
| checkout_01 | checkout actual | Único checkout que declara este directorio Git compartido |

Las puntas v1/v2 están integradas por ascendencia en el checkout actual. No se
deduce que todos sus objetos o artefactos sean prescindibles, ni que el remoto
actual haya aceptado el cierre. No se retiró ninguna rama o checkout.

### Otros repositorios y carpetas físicas

Las dos raíces relacionadas existen y declaran el mismo directorio Git compartido
por su hash: cada consulta enumera los mismos 45 checkouts, no 90. La raíz
principal tiene HEAD `e4dd32ab60a9395b1af6eb9645ae3d4e9bf1d121`; el checkout
RP4 original tiene HEAD `cec290a99f643ac02cf11bd195bb8334ac53b4b2`.
Ambas muestran dos referencias RP4 —local y remota almacenada— con esa última
punta: no es ancestro del HEAD principal ni de su origin/main local. Su presencia
como HEAD del checkout original tampoco autoriza retirarlo. Los 45 alias, hashes
de ruta, HEAD y pertenencia a rama RP4 se conservan en `related_repositories`.
Junto con el checkout actual son 46 checkouts conocidos en dos directorios Git
compartidos; no se afirma que sean todos los repositorios de la estación.

El censo físico separado enumera ocho carpetas cuyo nombre comienza por `rp4_`
en la raíz local de artefactos. Sólo se leyeron nombres/metadatos y cantidades de
hijos inmediatos, no datos granulares ni sus manifiestos internos:

| Alias físico | Archivos inmediatos | Directorios inmediatos | Archivos con referencia literal en el checkout |
| --- | ---: | ---: | ---: |
| physical_artifact_01 | 0 | 20 | 73 |
| physical_artifact_02 | 3 | 1 | 0 |
| physical_artifact_03 | 0 | 3 | 17 |
| physical_artifact_04 | 0 | 4 | 27 |
| physical_artifact_05 | 2 | 1 | 10 |
| physical_artifact_06 | 1 | 0 | 10 |
| physical_artifact_07 | 3 | 3 | 16 |
| physical_artifact_08 | 0 | 3 | 15 |

Las ocho quedan **NO VERIFICABLE como candidatas de borrado**: el grafo de
referencias externo no está completo. La segunda tiene cero referencias literales
en el alcance actual, no una demostración de orfandad. La correspondencia exacta
entre alias y rutas se conserva únicamente en un localizador privado excluido
de Git; el inventario público contiene sus hashes, no sus rutas.

El contrato de publicación conserva la historia base y el espacio técnico
existente. No se propone migrar la historia, renombrar paquetes técnicos ni
crear otro destino; sólo organizar la lectura actual y preservar la custodia.

## Referencias a carpetas de artefactos

Se recorrieron 1.803 archivos de texto, incluidos 726 JSON, entre los archivos
rastreados y no rastreados del checkout. Se buscan tokens literales exactos de
carpeta y se distingue referencia externa de autorreferencia. Los ejemplos de
referencia conservan alias, hash de ruta y hash de contenido; no rutas privadas.

Quedan fuera archivos sensibles, directorios de datos/checkpoints, extensiones
no textuales, directorios ocultos y otros clones. No se resuelven nombres
construidos dinámicamente ni manifiestos privados externos. El inventario enumera
esas exclusiones y un hash del conjunto leído. Por tanto, el rastreo **no es un
grafo global completo** y no confirma ningún artefacto huérfano.

Estas carpetas carecían de referencias literales externas en ese snapshot:

| Carpeta | Interpretación y acción propuesta |
| --- | --- |
| artifacts/rp4_closeout_stage1 | Recibo/paquete reciente del cierre; conservar y enlazar desde el índice del cierre |
| artifacts/rp4_closeout_stage1_audit_supplement | Evidencia complementaria reciente; conservar y enlazar desde su etapa |
| artifacts/rp4_closeout_stage2 | Historia de figuras del cierre; conservar aunque una revisión posterior sea la entrada vigente |
| artifacts/rp4_closeout_stage2_revision2 | Revisión de figuras reciente; conservar y vincular con la figura vigente |
| artifacts/rp4_closeout_stage4 | Recibo de una etapa reciente; conservar y vincular al cierre |
| artifacts/rp4_publication_precheck | Comprobaciones recientes de publicación; conservar y vincular al recibo del cierre |
| artifacts/rp4_publication_projection_code | Productor reciente en preparación; conservar y revisar sus enlaces al integrarse |

No son candidatos de borrado. Son candidatos de **revisión de enlaces**. La
ausencia de un enlace literal no prueba desuso; precisamente los productores
pueden construir esas raíces sin escribir su nombre completo. Las demás carpetas
tienen al menos una referencia externa en el alcance inspeccionado. Ninguna se
marca como segura para eliminar.

## Contradicciones y ambigüedades exactas

Los números antiguos, cuando se leen como resultados de su propia versión, no
contradicen los de v4: son observaciones históricas distintas. Lo que debe corregirse
en la navegación es presentarlos como estado actual o usar una frase absoluta
desmentida por la auditoría. Se propone una corrección por referencia, sin reescribir
el contenido científico congelado.

| Evidencia documental | Contraste con la autoridad vigente | Propuesta acotada |
| --- | --- | --- |
| data_and_execution_v1.md, líneas 3–8: «La ejecución RP4 está terminada» y «B2 empeora en ambas» | Es la primaria RV30 v1; el cierre actual registra mejoras B1/B0 y B2/B1 de la familia lineal RV15. No describe todas las versiones | Mantener v1; usar RESULTADO_FINAL como entrada y añadir en el índice la etiqueta «histórico v1 / RV30» |
| data_and_execution_v1.md, líneas 35–38: 29/71/136 predictores y «diagnósticos … no se usan como predictores» | Las dimensiones son de v1, no 29/69/138 vigentes. La negación absoluta sí tiene errata: v1 incluía los dos observed_span; no los nueve diagnósticos sugeridos inicialmente | Conservar el original; enlazar la fe de erratas de results_v2.md, línea 315, desde la navegación |
| data_and_execution_v1.md, líneas 65–66: 5.360 orígenes en confirmación | Correcto para la máscara v1; el cierre v2–v4 usa 9.750. No es evidencia de descarga faltante | Etiquetar la cobertura por versión; no reemplazar el 5.360 histórico ni borrar su máscara |
| results_v3.md, línea 130: jump_secondary N=1 y exclusiones por no convergencia | Describe el primer evaluador. El combinado final del salto tiene 419 sesiones y 160.832 orígenes | Conservar fallos iniciales; enlazar results_v3_revision2.md, sección «resultado final combinado» |
| results_v3_revision2.md, líneas 69–95: tabla de primer pase con 418 sesiones | Es historia expresamente separada. La tabla final de líneas 30–34 tiene 419; citar 418 como cierre sería un error de lectura | Referenciar la tabla final, no retirar el primer pase ni contar ambos como réplicas |
| results_v3_revision2.md, líneas 13–14: familia denominada «Ridge» | El nombre histórico no explica la penalización sobre suma de cuadrados ni el filtro de rango. La autoridad usa «modelo lineal winsorizado con filtro de rango (ridge nominal)» | Mantener el identificador de custodia y ampliar la etiqueta en textos de síntesis, sin atribuir la ventaja a regularización fuerte |
| results_v2.md, línea 296: cotas 0,1×mínimo y 10×máximo | Regla v2 histórica; en v3/v4 se usan 0,5×P1 y 2×P99 del entrenamiento | No mezclar reglas; enlazar cada especificación y no corregir retrospectivamente su estimador |
| operations_v1.md, sección de verificación: verificador público v1 | Sus hashes/figuras no certifican automáticamente v3/v4 ni una ejecución del colector actual | Conservar el gate v1 como tal; usar los gates de RUNBOOK para el alcance de bytes v3/v4 y sus recibos |
| publication_projection_v1.md: cierre de saneamiento de la publicación v1 | Es custodia de esa proyección, no evidencia del cierre científico posterior ni portabilidad de todos los originales | Conservar el registro; separar verificación pública de reproducción con originales licenciados |

Fuentes:
[datos y ejecución v1](../../../../rp4/data_and_execution_v1.md),
[errata v2](results_v2.md),
[informe original v3](../../../../rp4/results_v3.md),
[secundarios finales v3](../../../../rp4/results_v3_revision2.md),
[operación v1](operations_v1.md) y
[proyección v1](publication_projection_v1.md).
Los hashes de los documentos principales contrastados figuran en el inventario y en el gate.
Esta tabla es un plan documental, no cambios ya aplicados a esos archivos.

## Qué se conserva y qué quedó fuera

Se conservan todas las versiones A1, los releases A2, resultados B2/B3, recibos B4,
resultados adversos, errores originales y reparaciones explícitas; son necesarios
para revisar la selección entre versiones y la identidad del material reutilizado.
Las carpetas v1/v2/v3 no deben desaparecer por haber un resultado final favorable
bajo un criterio más acotado.

No se revisaron ni modificaron licencias, credenciales, contenidos de datos crudos,
tareas recurrentes ni contenidos de las otras raíces. Sus metadatos Git y el
censo físico sí se leyeron como se indica arriba. No se modificaron ramas/remotos
ni se borraron cachés.
Las referencias públicas son alias o rutas relativas; no hay una lista de rutas
privadas destinada a publicación.

## Verificación de esta revisión

El [RUNBOOK](../../../../rp4/OPERATING_GUIDE.md) contiene comandos de verificación que no ajustan modelos
ni recomputan inferencia. El [recibo](../../../../../artifacts/rp4_cleanup_review/receipt.json)
registra comandos, salidas, pruebas y hashes reales. El inventario puede repetirse
en lectura mediante:

```powershell
uv run --offline --frozen --no-sync python -B artifacts/rp4_cleanup_review/inventory_review.py --inventory --physical-artifacts-root $env:RP4_ARTIFACTS_ROOT --related-repository $env:RP4_PRIMARY_REPOSITORY --related-repository $env:RP4_ORIGINAL_REPOSITORY
```

Las tres variables deben configurarse localmente con la raíz física de artefactos,
el repositorio principal y el checkout RP4 original, respectivamente. No se
imprimen sus valores ni se copian al inventario público. Omitir esas opciones
produce sólo el alcance del checkout actual, no el censo ampliado aquí descrito.

Una nueva ejecución representa otro snapshot y no debe sobreescribir el inventario
firmado. Cualquier retirada futura requiere demostrar referencias completas,
recuperabilidad y alcance concreto; esta revisión no aporta esa autorización.
