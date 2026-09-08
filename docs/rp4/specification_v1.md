> Copia pública saneada; no es un nuevo congelamiento ni una nueva ejecución.
> SHA-256 del original conservado: `24a0fe96ba917bf284cbc0eda3f64f7ab3f41ede665f7021a9be20bdbeebd03d`.
> Los hashes y comandos históricos describen el original; [correspondencia de bytes](../../artifacts/rp4_publication_v1/manifest.json).

# RP4 — especificación v1

Propietario: Miguel. Fecha de fijación: 2026-09-07 (Australia/Sydney).
Autoridad: decisiones 128 y 129. Estado: especificación anterior a cualquier
materialización de objetivos, entrenamiento o evaluación RP4.
Etiqueta: **fuera de muestra walk-forward, partición fijada 2026-09-07**.
RESEARCH_ONLY; NOT INVESTMENT ADVICE; capital_go=false.

## Diseño, ventanas y unidad

Partición de calendario 2026-08-01. Desarrollo 2024-08-02–2026-07-31;
evaluación posterior 2026-08-03–2026-09-04 para esta entrega, y nuevas sesiones
cerradas en actualizaciones con la misma especificación. Seis activos:
AAPL, AMZN, META, MSFT, NVDA, TSLA; controles SPY y QQQ.
La primaria pronostica cada sesión después de las primeras 60 sesiones disponibles
de entrenamiento; no se prometen más de 450 sesiones de evaluación después del
calentamiento. Se conserva el hueco UW 2025-01-25–2025-02-24, sin relleno.
Fase 9 deja de ser cohorte sellada para RP4 por orden del propietario;
sus bytes solo se copian a la raíz RP4 y se comparan por hash. C10 sigue inactivo.

Claves exactas: asset, session_date, origin_minute (minutos desde apertura NY);
se materializan también forecast_origin_utc y target_end_utc=origen+30 minutos.
Nunca se unen filas por posición. Se usan sesiones XNYS reales, DST y cierres
anticipados del calendario instalado. Solo entran barras de la sesión regular.
Datos granulares nuevos: almacenamiento privado RP4; código y evidencia
pública nueva: artifacts/rp4_* y docs/rp4. Ningún dato granular se publica.

## Entradas, objetivos y compuertas

Los cuatro archivos y hashes del inventario RP4 aceptado son fuentes de entrada.
Los productores registrados ya declaran corte de 120 segundos: no se aplica un
segundo retraso a esas columnas. Toda extensión conserva esos contratos.
Cada RV30 se reconstruye con forward_measures y build_session_grid del productor
rp2_block3 para el horizonte30 y las claves originales, sin heredar el recorte
120..269 necesario para calcular todos los horizontes simultáneamente.
Se compara por clave con los objetivos existentes (83509 coincidencias según
el propietario; se informa el número realmente encontrado), con error absoluto
máximo/medio y proporción dentro de tolerancia atol=1e-12, rtol=1e-8.
Siempre se utiliza el RV30 reconstruido; ninguna diferencia autoriza modificar
objetivos antiguos. Son necesarios 31 precios consecutivos y 30 retornos log.

Se reutilizan compuertas de parsing, deduplicación, sesión, integridad OHLCV,
timestamps, precios positivos y completitud del productor; no se inventan OHLCV
ni se sustituye un cierre previo por una barra futura. Se reportan exclusiones
por razón y activo. Las filas modelables requieren todos los predictores
obligatorios finitos y RV30 finito positivo; únicamente las 25 celdas nuevas
pueden quedar ausentes. Los seis modelos comparten esa máscara. El tape ausente
no equivale a flujo cero. Se conservan las filas no elegibles en auditoría.

La cobertura comunicada por Miguel (centro100%, alas>=80% en vencimientos>=8d;
OI presente100%) queda registrada como OWNER_PROVIDED y se distingue de los
conteos producidos en A2. No se elimina una celda por baja cobertura.

## Conjuntos anidados y exclusión de diagnósticos

Se conservan las listas nominales registradas: B0=22, superficie=28, flujo=68.
Para cumplir la instrucción más específica de no ajustar sobre calidad,
antigüedad ni latencia, se excluyen explícitamente de X estas columnas aunque
formen parte del registro:

- B1: b1_median_quote_age_s, b1_median_relative_spread, b1_surface_coverage, b1_butterfly_violations, b1_expiries, b1_forward_expiries_fitted, b1_max_log_moneyness, b1_min_log_moneyness, b1_pcp_residual, b1_smile_residual, b1_strikes, b1_zero_dte_contracts.
- B2: b2_5m_mean_provider_latency_s, b2_30m_is_empty_window, b2_30m_late_arrival_share, b2_30m_mean_provider_latency_s, b2_5m_is_empty_window, b2_5m_late_arrival_share.

Se conservan como auditoría, no se borran del panel. Es una exclusión semántica
antes de resultados, no selección por signo. El conteo nuevo de celdas pobladas
y los indicadores de presencia OLS son las excepciones expresamente solicitadas.

La lista completa ejecutable queda en artifacts/rp4_a1/specification.json.
B0 incluye sus 22 registradas más log_rv_30m, log_rv_session, log_rv_day, log_rv_week, minute_fraction, minute_fraction_sq, rq_attenuation.
B1 acumula B0, las 16 columnas económicas de superficie restantes, 25 celdas y
su conteo: 71 entradas nominales. B2 acumula B1, 62 columnas de flujo restantes
y las tres medidas de dealers: 136. B0 tiene29.
Se añaden intercepto y cinco contrastes de activo compartidos en las familias.
rv30, jump30, minute_bucket, role, source, claves y flags de auditoría nunca
son predictores. No se construye una familia Gamma sobre niveles crudos.

HARQ reutiliza research.har con barras start-labelled completadas: effective_time
=bar_start+1min, disponible<=origen-120s; para el operador estricto del productor,
se usa origen desplazado-120s+1microsegundo. La estacionalidad se restaura al
origen de pronóstico original. Los rezagos diarios solo usan sesiones anteriores.

## Superficie nueva

25 celdas rp4_iv_<tenor>_<moneyness>; tenores dte_0_1,dte_2_7,dte_8_30,
dte_31_90,dte_gt90 por días calendario hasta vencimiento NY, con contratos
no vencidos a la hora exacta del corte.
Moneyness K/S: [0,.90),[.90,.97),[.97,1.03),[1.03,1.10],(1.10,infinito).
Nombres de bins m_lt090,m_090_097,m_097_103,m_103_110,m_gt110.
Por cada origen de cinco minutos, operaciones válidas con created_at en
(corte-5min,corte], corte=origen-120s. IV del proveedor, peso tamaño positivo;
mediana ponderada = primer valor ordenado cuya suma acumulada alcanza la mitad.
Se agrupan calls y puts en cada celda. Spot FMP usa última barra completada
disponible al corte. Celda sin operaciones válidas=NaN, no una IV fabricada.
rp4_surface_populated_cells cuenta celdas finitas0..25.
Cobertura por activo, tenor y moneyness usa todos los bins de origen elegibles.

## Dealers: proxy bajo convención declarada

Convención del propietario: calls largos y puts cortos. No es observación del
inventario real de dealers. Por contrato se toma la última observación válida
visible<=corte, antigüedad máxima1800s; el OI de ese registro diario se interpreta
como cierre previo por declaración del propietario (OWNER_ATTESTED), sin
rezagarlo nuevamente ni sumarlo repetidamente por cada operación.
Para cada strike:
G(K)=100*S^2*(sum_call OI*gamma - sum_put OI*gamma).
Se usan IV UW, spot FMP y tasa/dividendo exógenos reales conforme al productor
b1q: tasa Treasury3m más reciente estrictamente anterior; dividendo trailing365
de declaraciones conocidas dividido por spot. Se registran fuentes y fechas.
Cuando falta una fuente no se impone r=q=0; se adquiere fuente oficial acotada
o se conserva ausente y se aplica la máscara declarada.
Las griegas nuevas incluyen exp(-q*T), r-q en d1 y año365.
Las griegas históricas ya materializadas del B2 registrado no se reescriben;
su anterior supuesto r=q=0 se divulga y las nuevas medidas se distinguen por nombre.
Intensidad con decaimiento anterior intacta, no se denomina Hawkes estimado.

Nuevas columnas: rp4_dealer_gamma_net=sum_K G(K);
rp4_dealer_gamma_near_spot=sum con |K/S-1|<=.05;
rp4_dealer_max_gamma_distance=(Kmax-S)/S, donde Kmax maximiza |G(K)|.
Empates: strike más cercano al spot y después el strike menor.

## Modelos y procedimiento temporal invariable

Un modelo agrupado de seis activos por familia y conjunto de información.
Cada día se entrena solo con sesiones anteriores; purga y embargo60min
comprobados con target_end<=inicio_de_validación_o_test-60min.
Nunca se usa el objetivo del día a pronosticar. La ventana es expansiva:
una sesión pasada puede incorporarse al entrenamiento del siguiente paso
según el algoritmo fijado, sin ajustes humanos guiados por sus resultados.

log-OLS HARQ: log(RV30) con intercepto, transformaciones del registro
(log con piso1e-12, signed=sign(x)*log1p(abs(x)), raw sin transformación),
celdas IV nuevas log, gamma neta signed y distancia raw.
Centrado/escalado solo en entrenamiento; rango por SVD rcond1e-10,
sin ridge. Se permiten columnas redundantes mediante solución de mínimos
cuadrados de rango revelado; se registra el rango.
Retransformación Duan por media aritmética de exp(residuo) del entrenamiento.
No hay hiperparámetros OLS a elegir. Para las celdas NaN, se estima una
contribución del valor centrado solo cuando está presente, más un indicador
de presencia. La matriz numérica tiene contribución cero cuando falta, pero
la celda del dataset sigue NaN: no se afirma haber observado esa IV.

LightGBM QLIKE: objetivo sobre log-pronóstico f, gradiente1-y*exp(-f),
hessiano y*exp(-f), con guardas numéricas existentes. Inicialización
log(media RV30 de entrenamiento). Rejilla cerrada hojas7/15,
iteraciones25/50/100; learning_rate.05,min_data_in_leaf100,max_bin63,
feature_fraction=bagging_fraction=1, deterministic=true,
force_col_wise=true, 4 hilos, seed20260907.
Solo las últimas10 sesiones de entrenamiento seleccionan hiperparámetros:
ajustar sobre las anteriores, evaluar puntos25/50/100 y elegir menor QLIKE
agregada por sesión. Empates: menos hojas y menos iteraciones.
Después se reajusta con todo el pasado elegible. No se cambia la rejilla.
NaN nativo, zero_as_missing=false. Ajuste con igual peso por origen para ambas
familias; puntuación con igual peso por activo y sesión.
Pronósticos de ambas familias: exp(logforecast limitado[-30,30]), piso1e-12.

El entrenamiento de confirmación aplica exactamente el mismo algoritmo, sin
nuevo ajuste del diseño. Las predicciones completadas se preservan con hashes
de especificación, código e inputs; reanudar proceso no autoriza volver a
optimizar un resultado terminado. Correcciones de implementación se documentan
como incidentes y se verifican con fixtures, nunca afinando signos.

## Inferencia y secundarios

QLIKE(y,h)=y/h-log(y/h)-1. Contraste positivo=menor pérdida del conjunto
ampliado: delta1=L(B0)-L(B1),delta2=L(B1)-L(B2).
Promedio por origen dentro de activo/sesión, después activos con igual peso,
después sesiones con igual peso. Reducción%=100*delta/media de pérdida base.

Por ventana se publican cuatro contrastes (dos incrementos por dos familias).
Bootstrap circular de sesiones, bloques5, 9999réplicas, seed20260907;
intervalo percentil95% y p bilateral del nulo centrado con corrección+1.
Holm sobre esos cuatro p dentro de cada ventana a alfa.05.
N incluye orígenes, pares activo-sesión y sesiones; con menos10 sesiones los
p/intervalos se marcan NO VERIFICABLE, sin sustituirlos por significación.

DM sobre diferencia de pérdida por sesión, HAC Bartlett hasta min(5,N-2) y
referencia normal bilateral. GW-HAC usa instrumentos (1,delta_sesión_previa)
y Wald chi-cuadrado; se reporta como diagnóstico asintótico, no como garantía
del teorema GW para memoria fija. Mincer–Zarnowitz sobre medias por sesión
de objetivo/pronóstico, H0 intercepto0 y pendiente1, HAC5 y prueba conjunta.
Errores estándar degenerados, rangos deficientes o N insuficiente producen
NO VERIFICABLE, no p=0 fabricado. Se mantienen los signos adversos.

Secundarios predefinidos: orígenes en primera hora NY; activo/sesión de alto
flujo si el promedio b2_30m_premium del día anterior supera el tercil superior
calculado solo en sesiones de entrenamiento; earnings por activo, días FOMC,
vencimiento mensual según calendario real. Si falta calendario se informa
NO VERIFICABLE, no se codifican falsos negativos. Ninguno es predictor.
Desgloses por activo, tres bloques cronológicos de igual número de sesiones
(último absorbe resto), últimos30 y exclusión de cada bloque se reportan
sin elección de submuestras para cambiar la conclusión.
Dos tablas primaria/confirmación y una figura por contraste, ambas familias
y ventanas visibles; pérdidas acumuladas agregadas por sesión.

## Adquisición y operación

UW Aug3–18 y Sep3–4,2026; FMP 1min Jul20–Sep4 para seis activos y SPY/QQQ.
Se reutilizan primero fuentes exactas locales verificadas. Los11 directorios
de phase9/raw incluyen un hueco real de tape Aug26; se autoriza su reparación
acotada en RP4, nunca sobre phase9. Tasas Treasury2024 oficiales y metadatos
de eventos faltantes se consideran insumos auxiliares necesarios.
Cinco intentos con esperas1,2,4,8,16s y un pase final por faltantes; se sigue
con sesiones obtenidas y se informa cada falta. Se preservan ZIP y hashes
por sesión, fuentes/licencias y CRC/deduplicación. Disco<100GB:
solo cachés regenerables expresamente permitidas, rutas resueltas y respaldo
o regenerabilidad acreditada, nunca inputs.
Colector diario nuevo RP4 solo para última sesión XNYS cerrada, idempotente,
sin modificar los trabajos/raíz phase9; futuros informes versionados no
sobrescriben B3/B4v1. No cambio de modelo automático a partir de scores.

## Divulgación y límites

Divulgación solicitada: “La ventana 20 de julio a 28 de agosto fue leída una
vez por el puente de Fase8 con otra especificación.” “El PIT es proxy de
tiempo fuente a120s, como en la literatura.” La primera está atribuida
también a la confirmación del propietario y al protocolo del puente; la segunda
describe el supuesto operacional, no prueba recepción real del cliente.
El hueco UW aceptado se declara con sus fechas.

Limitación: la exposición previa no desaparece por fijar hoy la partición,
el tiempo fuente y la convención de dealers son proxies, y los p asintóticos
o bootstrap dependen de supuestos (GW original no cubre esta ventana expansiva).

## Fuentes primarias y verificación

El procedimiento está definido arriba, no se delegan decisiones a enlaces:
[Diebold–Mariano](https://doi.org/10.1080/07350015.1995.10524599),
[Giacomini–White](https://doi.org/10.1111/j.1468-0262.2006.00718.x),
[GW, texto completo](https://economia.uc3m.es/jgonzalo/teaching/PhdTimeSeries/GiacominiWhite.pdf)
y [LightGBM, parámetros](https://lightgbm.readthedocs.io/en/stable/Parameters.html).
Se reutilizan las versiones de código y dependencias de origin/main6f219d43
con el entorno Python3.12 existente; no se importan correcciones K3.

Antes de datos: prueba de exclusión de objetivo/diagnósticos, anidamiento,
límites temporales y medianas/Greeks con fixtures. Antes de resultados:
test de purga, tuning pasado, cambio del objetivo futuro no cambia pronóstico,
NaN/presencia, QLIKE gradiente/hessiano, bootstrap/Holm y continuidad de claves.
Cada etapa conserva comando, exitcode, hashes y commit. A1 se fija con hashes
SHA256 de este documento y specification.json en freeze.json; ninguno de esos
tres archivos se reescribe después. Un resultado favorable no se garantiza.

