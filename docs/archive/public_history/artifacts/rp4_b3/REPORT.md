# RP4 B3 — confirmación ejecutada

Estado de ejecución: COMPLETE, salida 0. Etiqueta: fuera de muestra
walk-forward, partición fijada 2026-09-07. No hay una confirmación estadística
de la jerarquía completa.

25 sesiones (2026-08-03 a 2026-09-04) y 5.360 orígenes con máscara común.
Ninguna sesión omitida. Es el mismo hash de especificación, evaluador e
imports de B2; el panel amplía desarrollo sin cambiar sus valores por clave.
No se modificaron parámetros, columnas, transformaciones, suelo ni inferencia
después de observar la primaria.

| Familia | Contraste | Delta QLIKE | IC 95 % | p crudo | p Holm | Reducción QLIKE % |
| --- | --- | --- | --- | --- | --- | --- |
| log-OLS HARQ | B1 sobre B0 | +0.0057236107 | [-0.0023060234, +0.017995993] | 0.3585 | 0.6470 | +2.6647328 |
| log-OLS HARQ | B2 sobre B1 | +0.0087467944 | [+0.00055846115, +0.023447609] | 0.0586 | 0.2312 | +4.1837168 |
| LightGBM QLIKE | B1 sobre B0 | +0.0091802888 | [+0.0016390168, +0.021021638] | 0.0578 | 0.2312 | +4.4712598 |
| LightGBM QLIKE | B2 sobre B1 | -0.0035553314 | [-0.010764728, +0.00047970784] | 0.3235 | 0.6470 | -1.8126736 |

La media log-OLS satisface B2 > B1 > B0 en esta ventana; LightGBM no.
Todos los p Holm son superiores a 0,05. Además, el bloque temporal intermedio
es negativo para ambos incrementos log-OLS; al retirar el tercer bloque,
B1 log-OLS pasa a -0,00076519781. B2 LightGBM sigue negativo al retirar
cualquiera de los tres bloques. Todos los signos están en `summary.json`.

El IC percentil y el p bilateral centrado predefinidos no son procedimientos
inversos; con bootstrap asimétrico puede haber un IC que excluya cero y un
p crudo superior a 0,05. Se conservan los dos cálculos especificados. En
ningún caso el p ajustado de esta ventana alcanza el umbral 0,05.

## Comando y evidencia

Con el entorno de `docs/rp4/operations_v1.md`:

```powershell
uv run --offline --frozen --no-sync python -B artifacts/rp4_code/evaluate.py --panel private-input/16baf18760d99542f617 --spec artifacts/rp4_a1/specification.json --spec-sha256 865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5 --window confirmation --output private-input/af79705b17c26b893225 --public-output artifacts/rp4_b3 --threads 4
```

Salida: `RP4_WINDOW_COMPLETE:confirmation:sessions=25`, código 0.
SHA-256 de `summary.json`:
`76816cf06a6483c009f9f148728c02ee39d065e7926fbf44dd80fa27dbf29ad7`.
Los pronósticos por origen quedan privados en D; Git conserva agregados.
Los CSV se marcan `-text` para que Git conserve sus bytes y hashes exactos.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
