# Vencimientos y barras: auditoría descriptiva local

## Resultado principal

Los seis activos ya muestran vencimientos de lunes y miércoles en la cinta válida del **26 de enero de 2026**, no del 29. En esa primera sesión aparecen los lunes 2 y 9 de febrero y el miércoles 4 de febrero. En el intervalo revisado, los primeros 0DTE de lunes y miércoles ocurren el **2 y 4 de febrero**, respectivamente, para los seis activos.

El [aviso oficial de Nasdaq, publicado el 16 de enero de 2026](https://www.nasdaqtrader.com/MicroNews.aspx?id=OTA2026-2) anuncia el inicio del listado el 26 de enero. Distinguir fecha de listado, primera operación observada y primera expiración 0DTE evita atribuir el cambio al día 29 por observar un aumento de celdas ese jueves.

Se revisaron 144 activo-sesiones de cinta (12 de enero–13 de febrero) y 195,479 orígenes de 504 sesiones del panel (2 de agosto de 2024–4 de septiembre de 2026). No hubo reajustes, remuestreo, objetivos nuevos, descargas ni modificación de entradas.

## Primera presencia observada

| Activo | Primera operación disponible (Nueva York) | Primer lunes 0DTE | Primer miércoles 0DTE |
| --- | --- | --- | --- |
| AAPL | 2026-01-26T09:30:08.751944-05:00 | 2026-02-02 | 2026-02-04 |
| AMZN | 2026-01-26T09:30:03.686235-05:00 | 2026-02-02 | 2026-02-04 |
| META | 2026-01-26T09:30:02.380014-05:00 | 2026-02-02 | 2026-02-04 |
| MSFT | 2026-01-26T09:30:02.817156-05:00 | 2026-02-02 | 2026-02-04 |
| NVDA | 2026-01-26T09:30:01.969666-05:00 | 2026-02-02 | 2026-02-04 |
| TSLA | 2026-01-26T09:30:03.138872-05:00 | 2026-02-02 | 2026-02-04 |

La primera presencia sólo se afirma dentro del tramo acotado: las nueve sesiones revisadas hasta el 23 de enero no contienen vencimientos de lunes o miércoles; el 26 sí los contiene en todos los activos. La fecha oficial proviene del aviso, no se infiere a partir del archivo local.

## Cobertura por día de semana

Antes = fechas anteriores al 26 de enero; después = desde el 26, inclusive. Cada origen del panel tiene el mismo peso; no se selecciona por el objetivo ni por la máscara de evaluación. Presencia ATM = fracción finita de la celda 0–1DTE y moneyness 0.97–1.03. Las medianas 0DTE omiten únicamente valores no finitos de esa variable.

| Día | N antes / después | Celdas medias antes / después | ATM presente % antes / después | Mediana contratos 0DTE antes / después |
| --- | --- | --- | --- | --- |
| Lunes | 26129 / 11700 | 19.1790 / 22.7443 | 0.0000 / 95.0769 | 0 / 35 |
| Martes | 28254 / 12480 | 19.2869 / 23.1990 | 0.0000 / 91.7308 | 0 / 0 |
| Miércoles | 27474 / 12480 | 19.1987 / 22.4992 | 2.8390 / 90.6010 | 0 / 33 |
| Jueves | 25914 / 12480 | 19.1914 / 23.5241 | 99.9267 / 99.9760 | 0 / 0 |
| Viernes | 27258 / 11310 | 23.2845 / 23.5286 | 98.7270 / 99.8232 | 43 / 45 |

La media global de celdas es 20.036718 antes y 23.095318 después. Con este denominador no se reproducen exactamente las cifras propuestas de 19.5→23.5 o las medianas 31/28. La presencia ATM anterior de los miércoles tampoco es literalmente cero: incluye los días 16 de abril y 2 de julio de 2025. Martes y jueves conservan mediana 0DTE cero, lo que no significa que todos sus valores sean cero.

El corte alternativo del 29 de enero y los desgloses por activo, junto con una ventana local de ±28 días, permanecen en [la tabla de cobertura completa](../../../../../artifacts/rp4_market_audit/coverage_weekday.csv). Son comparaciones descriptivas; no identifican por sí mismas una causa del rendimiento predictivo.

## Conteo diario de vencimientos distintos

Unión de fechas de expiración en operaciones válidas y disponibles antes del cierre menos 120 segundos. Las dos últimas columnas muestran el rango mínimo–máximo del conteo de vencimientos de lunes/miércoles entre los seis activos, no número de operaciones.

| Sesión | AAPL | AMZN | META | MSFT | NVDA | TSLA | Lunes mín–máx | Miércoles mín–máx |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-01-12 | 22 | 22 | 22 | 22 | 22 | 22 | 0–0 | 0–0 |
| 2026-01-13 | 22 | 22 | 22 | 22 | 22 | 22 | 0–0 | 0–0 |
| 2026-01-14 | 22 | 22 | 22 | 22 | 22 | 22 | 0–0 | 0–0 |
| 2026-01-15 | 22 | 22 | 22 | 22 | 22 | 22 | 0–0 | 0–0 |
| 2026-01-16 | 22 | 22 | 22 | 22 | 22 | 22 | 0–0 | 0–0 |
| 2026-01-20 | 21 | 22 | 21 | 21 | 21 | 21 | 0–0 | 0–0 |
| 2026-01-21 | 21 | 22 | 22 | 21 | 21 | 21 | 0–0 | 0–0 |
| 2026-01-22 | 22 | 23 | 23 | 22 | 22 | 22 | 0–0 | 0–0 |
| 2026-01-23 | 22 | 23 | 23 | 22 | 22 | 22 | 0–0 | 0–0 |
| 2026-01-26 | 24 | 25 | 25 | 24 | 24 | 24 | 2–2 | 1–1 |
| 2026-01-27 | 25 | 26 | 26 | 25 | 25 | 25 | 2–2 | 2–2 |
| 2026-01-28 | 25 | 26 | 26 | 25 | 25 | 25 | 2–2 | 2–2 |
| 2026-01-29 | 26 | 27 | 27 | 26 | 26 | 26 | 2–2 | 2–2 |
| 2026-01-30 | 26 | 27 | 27 | 27 | 26 | 27 | 2–2 | 2–2 |
| 2026-02-02 | 25 | 26 | 26 | 26 | 25 | 26 | 2–2 | 2–2 |
| 2026-02-03 | 25 | 26 | 26 | 26 | 25 | 26 | 1–1 | 3–3 |
| 2026-02-04 | 25 | 26 | 26 | 26 | 26 | 26 | 1–1 | 3–3 |
| 2026-02-05 | 25 | 26 | 26 | 26 | 26 | 26 | 1–1 | 2–2 |
| 2026-02-06 | 25 | 26 | 26 | 26 | 26 | 26 | 1–1 | 2–2 |
| 2026-02-09 | 25 | 26 | 26 | 26 | 26 | 26 | 2–2 | 2–2 |
| 2026-02-10 | 25 | 26 | 26 | 26 | 25 | 26 | 1–1 | 2–3 |
| 2026-02-11 | 25 | 26 | 26 | 26 | 25 | 26 | 1–1 | 2–3 |
| 2026-02-12 | 25 | 26 | 26 | 26 | 25 | 26 | 1–1 | 1–2 |
| 2026-02-13 | 25 | 26 | 26 | 26 | 25 | 26 | 1–1 | 1–2 |

## Barras extremas

Los dos archivos coinciden con sus hashes históricos y con sus recibos de descarga. Ambos contienen 390 minutos únicos, sin minutos regulares faltantes, duplicados, OHLCV no finito, volumen negativo ni inconsistencias high/low respecto de open/close.

| Evento (inicio de barra, Nueva York) | Retorno log, pb | Siguiente, pb | Volumen / siguiente | Mediana de volumen del día | Veces la mediana |
| --- | --- | --- | --- | --- | --- |
| AMZN 2026-08-31T14:00:00-04:00 | -151.6789 | +71.3015 | 166560 / 615022 | 55178.0 | 3.0186 / 11.1461 |
| TSLA 2026-08-17T15:25:00-04:00 | +102.6607 | -83.1851 | 118179 / 314047 | 42135.5 | 2.8047 / 7.4533 |

Retorno log en puntos básicos = 10000 × ln(cierre actual / cierre anterior). La mediana usa los 390 volúmenes de la sesión. Son los mayores retornos absolutos de sus respectivas sesiones. No hay salto de timestamp alrededor de esos minutos, pero la apertura de la barra de reversión difiere del cierre anterior: +36.2960 pb en AMZN y −21.7853 pb en TSLA. Los movimientos netos de los dos minutos son −80.3773 y +19.4756 pb, respectivamente.

Esto reproduce las anomalías planteadas, pero **no demuestra** que los precios sean ejecuciones de mercado correctas: es validación interna de un único proveedor. No se atribuye ningún movimiento a una noticia, ni se justifica eliminar o corregir esas barras sin evidencia externa. No se publica ningún extracto por minuto.

## Método y custodia

La cinta se selecciona con el índice del productor existente. Se leen sólo identificador, activo, dos relojes, expiración, IV, tamaño, strike, tipo y NBBO. Se conserva la primera versión por max(created_at, executed_at), con orden de fuente para empates, proyectada a esos campos. Se exige IV finita en [0.03,3], bid>0, ask>bid, strike>0, tamaño>0 y tipo call/put; ejecución en horario regular, expiración no pasada y ambos relojes disponibles al cierre−120s. La unión diaria de contratos no equivale a la mediana del snapshot 0DTE del panel. Los relojes fuente siguen siendo proxies, no recepción demostrada por el cliente.

[Fuentes: alias y hashes](../../../../../artifacts/rp4_market_audit/sources.json) · [Recibo de ejecución](../../../../../artifacts/rp4_market_audit/receipt.json) · [Proyección pública](../../../../../artifacts/rp4_market_audit/publication_projection.json). Los hashes identifican entradas sin exponer rutas privadas; los registros por minuto se excluyen de esta proyección.
