## Lectura del resultado completo

La ejecución RP4 está terminada; la jerarquía global robusta no queda
demostrada. En la primaria B1 mejora en promedio en ambas familias, pero B2
empeora en ambas. En confirmación log-OLS muestra B2 > B1 > B0 en promedio
(+2,6647 % y +4,1837 % de reducción incremental de QLIKE); LightGBM mejora
con B1 (+4,4713 %) y empeora al añadir B2 (-1,8127 %). Ninguno de los ocho
contrastes de las dos tablas tiene p Holm inferior a 0,05.

La estabilidad tampoco es uniforme: en confirmación el segundo bloque
temporal es negativo para ambos incrementos log-OLS, y B1 log-OLS pasa a
-0,00076519781 al retirar el tercer bloque. B2 LightGBM es negativo al
retirar cualquiera de los tres bloques. Tener más información disponible
no garantiza que el estimador extraiga una mejora estable de ella.

En la primaria, el 2025-05-15 aporta el 99,94095565 % de la suma de pérdidas
QLIKE por sesión de B2 log-OLS. Dos pronósticos, en MSFT y TSLA, alcanzan el
suelo fijado de 1e-12. El diagnóstico reproduce por activo la pérdida
agregada a partir de los pronósticos guardados. La sesión permanece en todas
las cifras primarias; no hubo reajuste ni cambio de suelo. Los metadatos de
rango del ajuste no bastan para atribuir causalmente el extremo a una
variable concreta. Evidencia: [diagnóstico](../../artifacts/rp4_b2/tail_diagnostic.json).

Los intervalos percentiles y los p bilaterales centrados no son inversiones
del mismo test. Su asimetría explica que en dos contrastes de confirmación
el IC percentil excluya cero mientras el p crudo supere 0,05. Ambos se
reportan tal como fueron especificados; los p Holm de esa ventana son
0,2312 o 0,6470. El secundario de eventos de confirmación tiene solo dos
sesiones: se informa su media, no una confirmación inferencial adicional.

## Datos y cobertura realmente ejecutados

Los archivos registrados y sus columnas exactas permanecen en el
[inventario aceptado](../../artifacts/rp4_inventory_v1/REPORT.md).
La [especificación](specification_v1.md) fija conjuntos anidados de 29,
71 y 136 predictores, más intercepto y contrastes de activo comunes.
Las 25 celdas admiten NaN; las demás variables son obligatorias. Los
diagnósticos de calidad, antigüedad y latencia no se usan como predictores.

A2 contiene 185.729 orígenes y 479 sesiones: 181.829 orígenes registrados
más 3.900 reconstruidos del 20 al 31 de julio. Hay 185.715 RV30 finitos;
14 ventanas se excluyen por falta de barras observadas (siete AAPL y siete
TSLA). De los 83.509 cruces con objetivos registrados, 83.502 conservan
pares finitos tras ese control y coinciden exactamente, diferencia máxima
y media cero. No se rellenaron ventanas del objetivo ni el hueco UW.

El RV30 reutiliza la indexación de barras de rp2_block3. Con barras rotuladas
al comienzo, la última barra usada termina un minuto después de la etiqueta
nominal de target_end; las particiones por sesión y el embargo de 60 minutos
separan holgadamente ese minuto. No se cambió el objetivo para mejorar
resultados. Las comparaciones son por asset, session_date y origin_minute.

La cobertura ATM 8–30 días de A2 es 99,7577–99,7836 %, no el 100 % declarado
inicialmente. La mínima ala extrema con vencimiento ≥8 días es 82,86868 %.
En la extensión de 25 sesiones, esas cifras son 100 % y 93,84615 %,
respectivamente. Todas las celdas se conservan, incluidas las poco pobladas:
[cobertura A2](../../artifacts/rp4_a2/coverage.csv) y
[cobertura de extensión](../../artifacts/rp4_b1/coverage.csv).

B1 cerró 331 trabajos: 280 activo-sesiones FMP, 25 sesiones UW, 11 copias
phase9, seis dividendos, seis earnings, dos años Treasury y un calendario
FOMC. Faltantes finales: cero. Se revalidaron los 54 archivos originales de
phase9 por hash sin modificarlos. La extensión añade 9.750 RV30 finitos,
sin bloques activo-sesión excluidos en materialización. Tras aplicar la
misma máscara de predictores a las seis celdas de evaluación, quedan 5.360
orígenes en confirmación, 54,9744 % de esos 9.750. Las exclusiones no se
confunden con descargas faltantes ni se resuelven con imputación no registrada.

El panel completo tiene 195.479 filas. Se comprobó igualdad exacta, por
claves y también tras releer el parquet, de las 185.729 filas de desarrollo
antes y después de la unión. Las nuevas respuestas de dividendos produjeron
cero diferencias de tasa/caja histórica en el desarrollo comparado. Las
griegas nuevas usan tasas y dividendos reales; las columnas griegas antiguas
del B2 registrado conservan su convención histórica r=q=0, divulgada en A1.

## Trazabilidad y etapas

| Etapa | Cierre verificado | Commit |
| --- | --- | --- |
| INIT | Rama desde origin/main; decisión 128, inventario y estado generado | 0d98e79a |
| A1 | Especificación y decisión 129 antes de evaluar | 9748d246 |
| A2 | Materialización de desarrollo y comparación RV30 | 643b5226 |
| B1 | Entradas completas y prueba de unión inmutable | fdd12c5e |
| B2 | 418 sesiones primarias, salida 0 | 71a491b3 |
| B3 | 25 sesiones de confirmación, salida 0 | 852d6133 |

Los comandos exactos, códigos observados y hashes por etapa están en
[A1](../../artifacts/rp4_a1), [A2](../../artifacts/rp4_a2/receipt.json),
[B1](../../artifacts/rp4_b1/receipt.json),
[B2](../../artifacts/rp4_b2/receipt.json) y
[B3](../../artifacts/rp4_b3/receipt.json). Los códigos de salida originales
perdidos por transporte de algunos trabajadores A2 siguen como NO VERIFICABLE;
los manifiestos, hashes y comando de unión posteriores sí fueron comprobados.
El PASS de software no equivale a significación estadística.

| Artefacto | SHA-256 |
| --- | --- |
| Especificación Markdown | 24a0fe96ba917bf284cbc0eda3f64f7ab3f41ede665f7021a9be20bdbeebd03d |
| Especificación JSON | 865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5 |
| Panel de desarrollo A2 | 51f04c5937a7922757f929ef0ca53941b7766719cf2799673669f8545f97a949 |
| Panel completo B1 | ecb1c6cce76cb6464d3cdf3d4ef409c60e204adf2df22fba6851e32199819d93 |
| Evaluador, ambas ventanas | 0064e37bebb00a0fb2550682e0c5590d64f16d88b2dfd9a4403b9ea82946ff14 |
| Resultado primario | d311d2773ae195968a59cea7d4e0c68dcf35d5d80e005c6cc0f1e028496d2eb2 |
| Resultado de confirmación | 76816cf06a6483c009f9f148728c02ee39d065e7926fbf44dd80fa27dbf29ad7 |

Los CSV del evaluador contienen finales CRLF; se preservan byte a byte con
atributos Git `-text`, en lugar de cambiar un artefacto ya calculado. El
control de espacios de Git usa `cr-at-eol` para reconocer esos finales como
terminadores. Los ZIP de historial B1 contienen únicamente versiones de
código; los datos licenciados y pronósticos por origen permanecen privados.
El cierre B4 registra la verificación final del informe, figuras y bytes Git.

## Operación diaria activada

Nombre: **RP4 colección diaria**. Activa martes a sábado a las 09:10,
Australia/Sydney, con raíz nueva RP4. La aplicación admite un solo seguimiento
por tarea: se actualizó el seguimiento de esta tarea, conservando su ID
interno y una copia de la configuración anterior. El recolector K3 separado
no fue modificado, y phase9 permanece intacto.

El modo diario se ejecutó ahora sobre la última sesión cerrada, 2026-09-04:
24 trabajos PASS, faltantes cero, salida 0. Reutilizó los archivos recibidos
por hash. Manifiesto SHA-256:
`270d3b92cb2bad3914f942efe2c66c7afbe1da91f1bcdc0c26f4ae76e081eaa2`.
Esto verifica el comando de colección; no acredita de antemano una futura
activación del planificador con el equipo apagado o sin acceso al proveedor.

La colección añade barras y tape; no reajusta modelos ni reescribe este
informe. Los snapshots exógenos v1 quedan preservados y una extensión
analítica posterior deberá vincular los exógenos correspondientes a sus
fechas. No hay publicación automática, operación con capital ni compra
adicional. El [runbook](operations_v1.md) contiene entorno y recuperación.
