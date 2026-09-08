# Contrato de proyección pública v2 — adenda de seguimiento administrativo

Esta adenda conserva el [contrato de material nuevo](publication_contract_v2.md) como antecedente y añade exclusiones de documentación administrativa y sus sellos asociados. Los documentos de incidente, verificación administrativa, solicitud de soporte y análisis de exposición de licencia permanecen en el checkout privado; sus instrucciones de operación y referencias de soporte no se distribuyen en una proyección pública futura.

La lista estructural del espejo incorpora estas exclusiones. El punto de entrada para la proyección de seguimiento es followup_contract_v2.py: extiende el conjunto compartido que consultan clasificación, proyección individual, preparación del conjunto y verificación final. Incluye el recibo administrativo versionado ya existente; comprobar solamente el sufijo genérico de recibo dejaría esa variante fuera del filtro. El productor histórico permanece íntegro. El contrato hermético usa bytes sintéticos para comprobar que ninguno de los documentos o sidecars excluidos llega al conjunto proyectado y que un documento científico permitido sí llega; también contrasta los nombres presentes, sin leer el contenido administrativo, para detectar variantes nuevas.

Esta adenda no construye una rama ni publica material. La autorización posterior de publicación y sus verificaciones se mantienen. El estado vigente del colector se rige por el registro prospectivo y sus enmiendas; la instrucción de mantenerlo deshabilitado en el contrato histórico ha quedado superada por esa autorización documentada.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
