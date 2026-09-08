# RP4 A2 — incidentes de implementación, antes de modelos

Especificación inalterada:
`865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5`.

## 001 — límites de fecha tratados como nombres de columna

Primer comando A2: salida 1, `polars.exceptions.ColumnNotFoundError: unable to
find column "2024-08-02"`. `Expr.is_between` interpreta strings como expresiones
de columna, no como literales. Se corrigió mediante `pl.lit` en el nuevo código
RP4 y se añadió `test_session_window_uses_literal_dates`. No se había escrito
ninguna partición ni se había entrenado ningún modelo.

Código de ese intento:
`1e13ca018e0805c7acf266e11221435110ae8edc8f3b5e82458107bde93725a6`.

## 002 — revisión de completitud y custodia durante materialización

Se interrumpió el segundo intento A2 (sesión de ejecución 28109, salida 1 por
interrupción) tras 31 particiones AAPL. Quedan intactas en
`private-input/eec0bd4c3e6529a5fd06`; no se usan para ajustar ni evaluar modelos.
Su comparación de objetivos se conserva: 83.509 claves coincidentes, diferencia
absoluta máxima y media 0, antes de la compuerta estricta de barras observadas.

La revisión exigió comprobar 31 cierres realmente observados para cada RV30:
`grid.valid` no basta, porque permanece verdadero después de un relleno forward.
RP4 ahora cuenta las barras originales del intervalo y excluye el objetivo si
falta alguna; `test_missing_target_bar_is_not_forward_filled` reproduce el caso.
La máscara de predictores sigue siendo la especificada, sin ajuste por resultados.

Se reforzó además la custodia: cada partición vincula el hash de especificación,
código, identidad de inputs (barras, fuentes exógenas, paneles, calendario) y
hashes del tape; una reanudación verifica esas identidades antes de reutilizar.
Se añadió una prueba real de lectura de Parquet para deduplicación de IDs y
conflictos. Se incorporaron secundarios sin convertirlos en predictores.

## Ejecución corregida

Código A2v2:
`6d9889c6c9191c9f407f422a35e83dd716f074b2b07d2a0bfe979ec999940d8a`.
Pruebas:
`d2179f7270941bb8beb10559b975a42a4e89737742e2b18f765cc2386fad5656`.
Verificación ejecutada: 9 pruebas aprobadas y Ruff aprobado, salidas 0.
Cuatro procesos como máximo, separados por activo; cada uno escribe una raíz
`a2_v2_<activo>` distinta. La combinación posterior verifica manifiestos y claves.
No se modificó ninguna fuente licenciada, artefacto congelado ni directorio phase9.

Comando por activo, desde el checkout RP4 con PYTHONPATH a `src`, `scripts` y
`artifacts/rp4_code`, POLARS_MAX_THREADS=4 y OMP_NUM_THREADS=1:

```text
uv run --offline --frozen --no-sync python -B artifacts/rp4_code/materialize.py --spec artifacts/rp4_a1/specification.json --spec-sha256 865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5 --output-root private-input/66c0e77362caa29dd928 --start 2024-08-02 --end 2026-07-31 --stage A2_v2_AAPL --assets AAPL
```

Se repite el mismo comando para AMZN, META, MSFT, NVDA y TSLA, sustituyendo el
activo y el sufijo de etapa. No constituye repetición de evaluación: es una
partición de la construcción de variables con la misma especificación.
