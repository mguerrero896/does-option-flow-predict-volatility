# RP4 v3 — adición de medición para ventanas vacías

2026-09-07, decisión 132. Instrucción explícita de Miguel recibida **después** del registro A1 del commit `1a7b21c`, pero **antes de cualquier ajuste o evaluación real v3**. Se conserva A1; esta adición y su JSON efectivo tienen un hash nuevo anterior a la evaluación. No se presenta como una modificación anterior al primer hash ni se reescribe su fecha.

Complementa `specification_v3.md` y el addendum de estabilidad, sin tocar v1/v2 ni alterar ventanas, objetivos, modelos, hiperparámetros, contrastes o inferencia. La exposición gamma y jump30 se derivan bajo el registro A1 original; luego una nueva materialización aplica exclusivamente esta regla al diseño B2. El panel gamma/jump previo también queda inmutable.

## Regla exacta

Para cada origen, separadamente en las ventanas de 5 y 30 minutos, el contador es `b2_5m_trades` o `b2_30m_trades` ya calculado por el productor registrado. Cero finito identifica ausencia de operaciones elegibles disponibles en esa ventana al corte PIT; no prueba que el mercado estuviera cerrado o que no hubiera ejecuciones. Un contador ausente/no finito representa estado desconocido, no cero. Un contador finito negativo o no entero es un error de instrumento y detiene esa materialización.

Si el contador es cero, únicamente las columnas de ese prefijo terminadas en `_share` o cuyo sufijo es `interarrival_cv`, `contract_entropy`, `strike_hhi`, `expiry_hhi`, `d_mid_rel`, `d_iv`, `d_spread` o `decay_intensity_innovation` pasan a NaN. El JSON efectivo enumera la lista exacta derivada de B2 registrado; no selecciona columnas mirando pérdidas. No hay variables Hawkes adicionales en el diseño heredado: se conserva y describe la intensidad con decaimiento como tal.

Conteos, tamaño, contratos, prima, tasa y flujos permanecen exactamente como los produjo v2, incluidos sus ceros. El estado histórico `decay_intensity_last` no es una innovación y no se borra por ausencia de operaciones en una ventana. Ningún valor de ventana no vacía o desconocida se cambia.

Se añaden `b2_5m_window_empty` y `b2_30m_window_empty`: 1 cuando el contador es cero, 0 cuando es positivo; NaN sólo si el contador es desconocido. En el panel fuente auditado antes del registro, ambos contadores están presentes y finitos en 195479 filas; hay 424 ceros de 5 minutos y 396 de 30 minutos. Es un censo **de predictores del panel completo**, no un resultado de evaluación ni su N elegible. No se consultaron objetivos para este censo.

Estos dos indicadores son excepciones explícitas autorizadas a la exclusión previa de diagnósticos de ventana vacía: codifican presencia del instrumento; no se reintroducen las antiguas columnas de latencia/calidad. Transformación cruda 0/1 para ambas familias, sin objetivo ni afinado adicional. B0/B1 siguen 29/69; B2 pasa de 136 a **138** predictores anidados.

LightGBM utiliza NaN nativo. Ridge conserva mediana e indicadores de presencia aprendidos sólo en el entrenamiento de cada ajuste, winsorización ±5 y cotas P1/P99 del addendum. Las columnas nuevas y las ausencias son opcionales. No se excluye ninguna sesión ni origen por esta regla; máscaras primarias y de salto no cambian.

## Comprobaciones y diagnóstico registrado

La materialización compara por claves: filas/tipos/claves intactos, B0/B1/RV30/jump/gamma y todo valor no afectado exactos; sólo se permiten conversiones a NaN en las columnas enumeradas con contador cero. Los ceros de actividad se verifican, no se convierten en medianas ni se fabrican operaciones. La versión anterior del panel nunca se sobrescribe.

El informe ofrece censo por ventana de evaluación, activo, sesión y ventana 5/30; diferencia entre todas las filas disponibles y filas elegibles evaluadas. Reporta B2 sobre B1 dentro y fuera de las ventanas vacías en ambas familias, manteniendo los signos, y estado desconocido aparte. Un grupo vacío o de menos de diez sesiones no obtiene una inferencia ficticia: muestra el N y, cuando existe, su estimación descriptiva. Son diagnósticos secundarios registrados, nunca sustitutos del contraste global.

Las cifras y la atribución causal del mensaje del propietario a dos sesiones son antecedentes por verificar, no se presuponen demostradas por esta adición. Una ventana vacía puede ser económica o responder a cobertura/latencia del proveedor: la regla repara la definición de ratios sin afirmar que todo vacío sea un fallo del proveedor.

El JSON efectivo se fija en `artifacts/rp4_v3_a1_empty_window/specification.json`; su freeze vincula este documento, decisión 132 y A1 original. La entrada de evaluación será `materialized_empty_windows/panel.parquet` en la raíz privada v3. Comandos, salidas y hashes se conservan por etapa. RESEARCH_ONLY. NOT INVESTMENT ADVICE. capital_go=false.
