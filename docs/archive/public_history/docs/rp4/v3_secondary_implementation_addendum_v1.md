# RP4 v3 — addendum de reparación de implementación de secundarios

Autorización: encargo expreso de Miguel, posterior al cierre v3 y durante la ejecución v4. Este addendum se fija antes de ajustar los componentes secundarios faltantes. No modifica los pronósticos principales, la especificación v3, sus resultados, las ventanas, el panel ni ningún archivo congelado.

## Alcance y entradas invariables

- Especificación efectiva v3: SHA-256 `930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5`.
- Panel `materialized_empty_windows/panel.parquet`: SHA-256 `a63ff5e61092d2bc00917c5de4e0e73f928005acc475f46370348eaca6ad4637`.
- Cierres principales: primaria `645d319f4b5b283a2b1bc6ecda1a185650b8436cdbf3b319e9debfc41210ef1d`; confirmación `64af964691d1127df7b3e2e0f05395c810719f2fe4e5ba3fa0207fcc8e15591b`.
- Las 419 sesiones primarias y 25 de confirmación conservan el calendario, elegibilidad, purga/embargo y validación de las últimas diez sesiones. El único objetivo de los ajustes nuevos es el indicador registrado `jump30 > 0`, no una prueba estadística formal de salto.

## Logística: mismo objetivo, corrección de geometría numérica

Se conserva exactamente `F(beta) = [sum(logloss) + lambda * sum(beta_slopes^2)] / N`, con intercepto sin penalizar y rejilla lambda `[0.0001, 0.01, 1, 100, 10000]`. Se reutilizan la imputación, estandarización, winsorización y eliminación de columnas del diseño v3, todas ajustadas sólo con entrenamiento. La selección sigue siendo logloss de validación ponderada por activo y sesión, nunca AUC de evaluación; mismo desempate por lambda mayor.

La matriz inicial de Fisher penalizada es `M = pbar*(1-pbar)*X'X/N + 2*lambda*diag(0,1,...)/N = L*L'`, usando exclusivamente entrenamiento. El cambio invertible es `theta=L'*beta`, `beta=L'^(-1)*theta`, `gradient_theta=L^(-1)*gradient_beta`. No se añade jitter, no se cambia la penalización y no se elimina un lambda porque sea difícil de ajustar. Se reutiliza la matriz Gram dentro de la misma ventana de entrenamiento.

L-BFGS-B empieza con `ftol=1e-12`, `gtol_theta=1e-8/max(1, ||L||_infinito)`. Si el cierre inicial no certifica el gradiente original, continúa una sola vez con `ftol=0`, usando únicamente el resto del presupuesto total de 1.000 iteraciones. El certificado exige coeficientes y objetivo finitos, gradiente infinito en coordenadas originales ≤ `1e-8`, objetivo final no mayor al inicial más `1e-12`, equivalencia de las dos expresiones algebraicas del objetivo con diferencia ≤ `1e-10*max(1,abs(F))`, y gradientes equivalentes con diferencia ≤ `1e-10`. El certificado explícito, no sólo la bandera de SciPy, determina la convergencia. Se conserva la excepción registrada de entrenamiento con una clase: frecuencia empírica y clip de probabilidades v3.

El código del solver se fija con SHA-256 `d21a3c06520cd4ad6369e82afc5c89a8b8845ca728173754fff0a45709e2f570`, en `artifacts/rp4_v3_secondary_repair/jump_repair.py`. Diez pruebas sintéticas comprobaron gradiente, equivalencia y convergencia antes de cualquier ajuste empírico nuevo: en el caso correlacionado que agotaba 1.000 iteraciones, el candidato necesitó diez y dejó gradiente original `1.6923449264e-9`. Es una prueba numérica sintética, no un resultado científico de salto.

## Reutilización y ejecución acotada

El inventario de los cierres verificados contiene 962 componentes de salto completos: 912 en primaria y 50 en confirmación. Se conservan sus bytes y sus pronósticos; se verifican los recibos, claves, objetivo y probabilidades antes de reutilizarlos. Faltan 1.702 componentes: 801 logísticas y 801 LightGBM en primaria; 50 y 50, respectivamente, en confirmación. El fallo de la logística también había impedido ejecutar componentes LightGBM posteriores.

Sólo se ajustan esas piezas faltantes. LightGBM conserva el objetivo binario, rejilla, semillas, validación y reglas v3; usa dos hilos en lugar de cuatro por la restricción operativa expresa. No se reajustan RV30 medio, cuantil ni MZ. Nuevos archivos en `private-input/e90b04c9636db3ce4b5d`; ninguna salida nueva reemplaza una anterior. El código del ejecutor y sus entradas quedan ligados por hash antes del primer ajuste.

La ejecución secundaria tendrá como máximo dos hilos de cálculo en total y prioridad baja de Windows. Empezará cuando haya finalizado la auditoría MZ de un hilo, sin reservar núcleos ni alterar la prioridad de v4. Cada pieza se intenta con esta implementación; un fallo se registra como NO VERIFICABLE, nunca se acepta un coeficiente sin certificado ni se sustituye por cero. Los componentes ya completos no se reajustan durante una reanudación.

La inferencia reutiliza exclusivamente el agregador de salto de v3: AUC pooled fuera de muestra por conjunto, diferencias de AUC, bootstrap por bloques de sesión con los mismos 9.999 remuestreos, y secuencia unilateral H1→H2 por familia. Mismas máscaras comunes y controles de clases, insuficiencia y disponibilidad. Se reportan N, componentes reutilizados/nuevos/fallidos y todos los signos. Estos resultados continúan siendo secundarios no promovibles.

## Mincer–Zarnowitz: auditoría, no corrección ficticia

La auditoría primaria ya había reproducido exactamente la fórmula afín registrada. La auditoría adicional de confirmación, sólo sobre pronósticos y coeficientes guardados, también encontró diferencia máxima cero entre fórmula aplicada y salida almacenada. El problema es de positividad: una recta ajustada a diez medias de sesión puede producir valores negativos al aplicarse a cada origen; el piso `1e-12` dispara QLIKE. No se ha demostrado un error aritmético de escala, de suma o de intercepto que pueda repararse conservando esa fórmula.

Se aplica la salida autorizada para MZ: **NO VERIFICABLE como recalibración utilizable**, con el diagnóstico y recibo de auditoría; no se presenta una tabla corregida como COMPUTED ni se introduce una recalibración distinta después de ver resultados. Investigación finalizada dentro de la hora concedida, sin nuevos ajustes. Las tablas principales v3 permanecen idénticas y su revisión de presentación será otro archivo.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false. Sin descargas, publicación, nueva campaña ni modificación de v4. La corrección numérica no convierte las ventanas reutilizadas en una réplica independiente.
