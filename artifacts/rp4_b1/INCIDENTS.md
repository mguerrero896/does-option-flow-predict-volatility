# RP4 B1 — incidentes y continuaciones

La especificación A1 no cambia. No se modifican datos de phase9 ni paneles A2.

1. El primer analizador FOMC incluyó una votación por notación del 22 de agosto
   de 2025. Se corrigió antes de calcular resultados: solo bloques oficiales
   `Statement` de reuniones. El calendario válido contiene 16 fechas y es
   `manifests/events/fomc_meetings_v1.json`; el anterior se preserva como
   historial y no alimenta RP4. Hay prueba de regresión.
2. Se detectó posible convergencia de dos colas UW. Se separaron listas de
   fechas y se añadió exclusión mutua por sesión con bloqueo del sistema
   operativo, liberado al terminar el proceso. Los resultados PASS se
   verifican por hash y se reutilizan, no se reemplazan.
3. Los agentes auxiliares se interrumpieron por límite de uso. Sus procesos
   locales siguieron vivos; el operador principal asumió la coordinación.
   Los códigos de salida perdidos por transporte se etiquetan NO VERIFICABLE,
   sin atribuir un cero a un resultado no observado.
4. Rendimiento: el filtro original consultaba apertura/cierre XNYS por cada
   operación. Una medición de 10.000 llamadas dio 0,4000 s con el original y
   0,003339 s con límites horarios ya calculados. Se añadió caché de esos
   límites inmutables; la conversión CSV, deduplicación, esquema y todas las
   compuertas se reutilizan sin cambios. La prueba comprueba bordes exactos,
   cierre anticipado y cambio de horario. No es un ajuste a resultados.
5. Las fuentes de dividendos de phase6 estaban capturadas el 13 de agosto y
   no acreditaban integridad hasta el 4 de septiembre. Se descargaron seis
   respuestas FMP nuevas (PASS, salida 0) en RP4. Se usan solo en la extensión;
   sus diferencias históricas se registran, sin reescribir desarrollo.
6. El primer chequeo estático de materialización detectó anotaciones faltantes
   en código nuevo: se corrigieron antes de construir la extensión. Incluir
   también los productores antiguos revela ocho avisos de tipos en tres
   scripts de origin/main, fuera del código RP4; no se presenta esa ejecución
   como un pase completo del repositorio. La comprobación focalizada de RP4
   usa MYPYPATH explícito para resolver los módulos locales y no reescribe los
   productores históricos.
7. Un pase global de comprobación coincidió con el procesamiento aún activo
   del 4 de septiembre. El bloqueo exclusivo devolvió PermissionError tras
   cinco intentos y el pase final: recibo parcial
   `acquisition_batch_all_20260907T000914787883Z.json`, SHA-256
   `5298985a39d9f30f51f130a39f4fdd2d2216b7ecbb9583e1db39093220a6827f`,
   salida observada 1. Se preservó el trabajador; al terminar con PASS se
   ejecutó otra verificación global, sin cambiar ni descargar de nuevo las
   sesiones completas: PASS, salida 0, faltantes cero, SHA-256
   `19e9de749ddad8d81b76bda11b67f80cd099b734839aaba71f87dbb4d5585477`.
   El estado parcial era contención local, no ausencia de datos del proveedor.

Las versiones de `acquire.py` utilizadas antes de cada mejora se conservan
en los ZIP de código de este directorio. Los recibos por sesión incluyen
`acquire_code_sha256`; los ZIP contienen código, no tape ni filas licenciadas.
Los checkpoints de calendario y los comandos finales se incorporan al recibo
de etapa al cerrar B1. Las demoras HTTP no se convierten en datos inventados.
