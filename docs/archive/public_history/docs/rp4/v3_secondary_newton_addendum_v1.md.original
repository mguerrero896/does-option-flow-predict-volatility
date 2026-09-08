# RP4 v3 — precisión numérica adicional del secundario de salto

Autorización: el encargo de Miguel incluye reparar la convergencia de los secundarios de v3. Se registra esta resolución mientras el primer paso continúa, antes de consultar su AUC y antes de ejecutar la resolución. No cambia ninguna hipótesis, dato, familia, lambda, tolerancia, máscara, validación o pronóstico principal; no es una nueva versión científica ni una campaña.

## Fallo y alcance

En el componente nuevo lineal B2 del 2025-03-26, lambda 0.0001, L-BFGS terminó ambas fases por estancamiento del valor objetivo después de 27 iteraciones. El gradiente original quedó en `1.0226994386690321e-8`, frente al certificado `1e-8`. El rechazo del primer paso es correcto y permanece intacto. El componente fallido tiene SHA-256 `5e3c67a2f3b7d2e5b1d85d5789ecc0061e9a7483b5df30cbfe048451d92b2bdc`; ambas expresiones del objetivo coincidieron, por lo que no se atribuye el caso a escala o a una regularización distinta.

La resolución se aplica exclusivamente a componentes lineales faltantes que el primer paso haya dejado NO VERIFICABLE por un gradiente finito no certificado. No se reabre ningún componente COMPUTED, original o reparado; no se vuelve a ajustar LightGBM, la media, el cuantil ni MZ. El primer paso y sus recibos se conservan. Los nuevos resultados y su agregación secundaria viven en otra salida y tendrán release y recibos propios.

## Algoritmo fijado

Se conservan literalmente el objetivo logístico penalizado, el intercepto libre, las cinco lambdas y las dos fases L-BFGS del addendum `606a8c8d5dbe51628e7507b504cf7c5f8483a9aa5e7c80f62be33b2cb12e55de`. Sólo si persiste un gradiente finito fuera del certificado se añade un pulido Newton, con a lo sumo `min(8, 1000 - iteraciones_LBFGS)` pasos dentro de la nueva llamada. Se informan por separado el trabajo del primer intento y el de esta resolución: el coeficiente fallido no estaba guardado y reconstruirlo no es reutilización gratuita.

Con `z=X*beta`, la Hessiana es `H = X' diag(sigmoid(z)*sigmoid(-z)) X/N + 2*lambda*diag(0,1,...)/N`. Se simetriza aritméticamente y se factoriza por Cholesky sin jitter. La dirección es `d=-H^(-1)*g`, y debe cumplir `g'*d<0`. Se prueban pasos `alpha=2^(-j)`, para `j=0..20` (hasta veinte mitades).

La aceptación Armijo usa `c=1e-4` y exige `F_trial<F` y `F_trial<=F+c*alpha*g'*d`. Para un estancamiento por redondeo, la única excepción exige simultáneamente: `F_trial<=F`, `F-F_trial<=ulp(F)`, `-c*alpha*g'*d<=ulp(F)` y una reducción estricta del máximo de las normas infinitas de los gradientes estable y literal. Aquí `ulp(F)=nextafter(F,+infinito)-F`; no se introduce una tolerancia elegida a partir de AUC.

El certificado final sigue exigiendo ambos gradientes originales ≤ `1e-8`, coeficientes/objetivo finitos, objetivo final no mayor al inicial más `1e-12`, diferencia entre objetivos algebraicamente equivalentes ≤ `1e-10*max(1,abs(F))` y diferencia de gradientes ≤ `1e-10`. No se relaja ningún umbral. Si falla la positividad de la Hessiana, la dirección, la búsqueda de paso, el presupuesto o el certificado, el componente sigue NO VERIFICABLE.

## Verificación, ejecución y presentación

El código nuevo y sus pruebas se fijarán en un release antes de cualquier ajuste empírico de esta resolución. Las pruebas deben cubrir derivadas, equivalencia del objetivo, mejora del residuo en un caso sintético próximo al límite, rechazo de pasos ascendentes y conservación del certificado. Ninguna prueba sobre AUC decide el algoritmo.

No habrá dos ejecutores secundarios simultáneos: primero termina el paso actual; después se ejecutan las pruebas numéricas y esta resolución, manteniendo un máximo de dos hilos de cálculo y prioridad baja. Las nuevas predicciones se unirán por claves a los componentes ya completos. Se conserva también la inferencia del primer paso, y la tabla final identificará qué salidas fueron completadas por esta corrección; una mejora numérica no se presenta como cambio de evidencia primaria.

La AUC y sus contrastes se calculan con el mismo agregador secundario de v3, los mismos 9.999 remuestreos por sesión y la misma secuencia unilateral. Si persisten faltantes se cuentan y se declara su alcance; no se rellenan pérdidas o probabilidades. MZ sigue NO VERIFICABLE por la inestabilidad documentada. v3 primaria y toda v4 permanecen intactas.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false. Sin descargas, publicación, v5 ni modificación de artefactos congelados.
