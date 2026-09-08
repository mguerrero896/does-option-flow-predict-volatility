# RP4 — correspondencia de publicación v1

La publicación se saneó el 2026-09-07 con autorización expresa, después de
completar A1–B4. No es un nuevo congelamiento, una nueva evaluación ni un cambio
de metodología. Los siete commits públicos son proyecciones de las siete etapas
originales; los commits de ejecución citados en el informe identifican la
evidencia original conservada, no los nuevos identificadores públicos.

Los originales completos se conservan en un respaldo privado verificado y en
el checkout operativo intacto. Se retiraron rutas personales de las versiones
publicadas actuales y anteriores. La documentación operativa pública ya no
incluye ubicaciones personales ni referencias a herramientas internas.

El [manifiesto](../../../../../artifacts/rp4_publication_v1/manifest.json) distingue para
cada archivo el SHA-256 original y el publicado, e identifica también versiones
históricas saneadas. Los hashes y códigos de salida de los recibos de etapa
describen la ejecución original; no se recalcularon para fingir que los bytes
proyectados fueron los fijados antes de evaluar. Los documentos saneados están
identificados como copias de publicación.

Se conservan byte a byte el informe científico, sus tablas, resultados JSON,
CSV de pérdidas, figuras, especificación JSON, freeze.json, ejecutor científico
y archivos históricos de código comprimidos. El Markdown público de A1 tiene
otra huella por la supresión de la ubicación privada y el aviso de proyección;
su hash original sigue siendo
`24a0fe96ba917bf284cbc0eda3f64f7ab3f41ede665f7021a9be20bdbeebd03d`.

El comando público `python artifacts/rp4_code/verify_delivery.py` verifica la
proyección y figuras sin paneles licenciados. Su resultado es distinto de un
PASS de la custodia privada: la opción `--original-root` comprueba adicionalmente
los originales preservados. La reproducción científica sigue requiriendo
el entorno, fuentes y documentos originales autorizados.

El defecto del cierre anterior fue no ejecutar los controles completos de
rutas personales y prosa interna antes del primer envío. El escaneo de secretos
sin hallazgos no cubría esa obligación. Los controles de publicación permanecen
activos y no se modifican para aceptar la proyección.

Esta corrección de publicación no cambia la conclusión: la jerarquía global
robusta no está demostrada. Tampoco modifica main, phase9, colecciones ajenas,
datos licenciados, el planificador existente o decisiones de inversión.

La comprobación del historial se refiere a las referencias públicas accesibles
verificadas; no garantiza retirar copias descargadas o cachés externas. El estado
remoto y la CI final se informan en el PR de la entrega.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
