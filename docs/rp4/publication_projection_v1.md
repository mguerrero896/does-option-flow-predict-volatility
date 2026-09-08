# Correspondencia de publicación: cierre v1–v4

Esta copia se prepara después de las evaluaciones. Sus commits tienen fechas actuales de proyección: no son prerregistros históricos ni prueba independiente del momento en que se decidió una especificación.

La rama `rp4/walkforward-v1-v4` conserva la base pública y sus ancestros. Añade, en orden, v1, v2, v3, v4, el cierre y la operación documentada. El [contrato de material nuevo](publication_contract_v2.md) sustituye el alcance de historia completa de la auditoría anterior. No se creó otro repositorio ni se cambió el nombre técnico de la biblioteca.

## Qué se conserva y qué cambia

Las fuentes científicas originales y los datos privados permanecen intactos. Las copias públicas sustituyen rutas de máquina por referencias del repositorio o alias `private-input/…`, y utilizan nombres genéricos en la prosa nueva. El manifiesto de la instantánea (`artifacts/rp4_publication_projection_release/snapshot_manifest.json`, solo en la proyección) registra los hashes originales y los de las copias; toda omisión conserva hash, tamaño y razón. Cambiar el texto de un documento cambia su hash.

Los valores numéricos de los resúmenes JSON se comprueban antes y después de la proyección. La excepción explícita es el recibo MZ: se omiten tres ejemplos reales por origen, conservando métricas agrupadas y agregados por sesión sin recalcularlos. El CSV de calibración MZ conserva sus 1.332 registros agregados y sus 18 columnas; no contiene objetivos ni pronósticos por origen. Los signos adversos y las cuatro versiones permanecen visibles; no son réplicas independientes y no demuestran una jerarquía global robusta.

Se excluyen de lo nuevo paneles columnares, barras por minuto, pronósticos por origen, coeficientes del modelo por sesión, archivos comprimidos y configuración privada. Los cuatro archivos de auditoría enlazados se incorporan con revisión específica por ruta y hash; el log del candidato elimina identidad de usuario, máquina y rutas locales. El candidato de gamma se conserva como código (`artifacts/rp4_v3_candidate/build_gamma_imbalance.py`, solo en la proyección) y metadatos (`artifacts/rp4_v3_candidate/metadata.json`, solo en la proyección), con el hash de su panel **NO_DISTRIBUTED**. El prerregistro de v4 (`artifacts/rp4_v4_prereg/protocol.md`, solo en la proyección) tiene hash de copia y hash original separados (`artifacts/rp4_v4_prereg/provenance.json`, solo en la proyección); no se atribuye un sello temporal independiente a su fecha declarada. Estas incorporaciones aparecen en las instantáneas de su versión y posteriores, no en v1/v2. Sus dos archivos físicos se añaden al registro de congelados; sus sidecars GNU identifican esos archivos, no JSON inexistentes.

## Verificación y sus límites

El control de proyección verifica los hashes de las copias, las omisiones, los commits nuevos, la base conservada y la sintaxis del código proyectado. No entrena modelos, no repite bootstrap y no equivale a una ejecución completa de CI.

**Reproducción científica en frío: NO VERIFICABLE desde esta copia sola.** Los verificadores históricos conservan sus algoritmos y hashes de origen; no se cambian para aceptar documentos saneados. Esos controles pueden requerir los originales preservados y las fuentes con licencia. La verificación pública de agregados es distinta de la custodia y del replay privado.

La copia pública de las tres exclusiones locales utiliza nombres genéricos. La lista de exclusión del espejo y su control de prosa originales se conservan sin excepción de comandos. El cuerpo del PR, los comandos de operador y su prueba de excepción no se distribuyen: permanecen únicamente en la rama privada. Los enlaces internos se verifican sobre el árbol completo. Una referencia a un insumo no redistribuible se identifica expresamente como tal en la copia pública, conservando el documento original privado y su hash; no se presenta como una descarga disponible.

## Corrección de historia del PR 81 — 2026-09-08

La primera publicación de los seis commits, punta `e589d4cf326dc4eb89b81581e40cce8784f2bdd5`, incluyó por error `artifacts/rp4_v3_b4/fit_selection.csv`: 15.465.642 bytes de detalles de ajuste por sesión derivados de datos licenciados. El control de historia del CI lo rechazó. Su SHA-256 original es `dc68bbf65168ef01584fa10b9e6d9a999d219e167b2ef263b24930d498346bf1`. El archivo original privado no se modifica ni se elimina.

Con autorización específica se regeneran los seis commits de esta única rama no fusionada, omitiendo ese archivo desde su primera aparición, no solamente en la punta. El manifiesto de cada instantánea registra la omisión, tamaño, hash y razón `LICENSED_DERIVED_PER_SESSION_FIT_DETAILS`; los recibos científicos conservan el hash original como evidencia de ejecución, no como promesa de distribución. La copia pública del informe sustituye el enlace al CSV por una declaración de no distribución. El productor aplica además el límite tabular de 2 MiB del control de historia existente antes de crear cualquier instantánea; el test no se debilita ni se omite.

El censo de todos los blobs nuevos mayores de 1 MiB encontró otros tres archivos: los resúmenes JSON de primaria v3, v4 RV15 y v4 RV5. Contienen agregados de evaluación, no paneles ni pronósticos por origen; se conservan sin cambios numéricos. La base `6f219d436018a5b0f239aadd801ec3e8e70877bf`, sus ancestros y `main` permanecen intactos. El reemplazo remoto usa una lease sobre la punta anterior exacta y no autoriza la fusión. No puede retirar clones ya descargados ni garantizar la eliminación de cachés externas.

El siguiente pase de CI comprobó correctamente la estructura del PR y detectó que el correo genérico de los seis commits de proyección no cumplía la regla pública `noreply`. El productor utiliza ahora `Research maintainers <noreply@github.com>` para estas copias; esa identidad de proyección no acredita la autoría original ni una firma de GitHub. Se preservan seis commits neutros y se ejecuta el escáner sin excepciones nuevas.

Lea el [resultado final](RESULTADO_FINAL.md) y el [runbook](OPERATING_GUIDE.md). Los archivos de operador quedan fuera de la distribución. El estado remoto y los resultados finales de CI se registran en el PR 81 y en el recibo de reparación. Esta corrección no activa el colector ni reejecuta modelos o inferencia.

`RESEARCH_ONLY`; `NOT INVESTMENT ADVICE`; `capital_go=false`.
