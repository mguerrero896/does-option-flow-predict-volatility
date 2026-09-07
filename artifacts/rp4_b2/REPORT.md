# RP4 B2 — evaluación primaria ejecutada

Estado de ejecución: COMPLETE, salida 0. Estado científico: no se demuestra
la jerarquía completa B2 > B1 > B0 con esta especificación.

Etiqueta: fuera de muestra walk-forward, partición fijada 2026-09-07.

418 sesiones (2024-10-28 a 2026-07-31), 92.261 orígenes y 2.504
activo-sesiones. De 479 sesiones de desarrollo, 60 son entrenamiento inicial;
la sesión 2025-10-20 no tiene orígenes elegibles. Cada pronóstico usa solo
sesiones anteriores, con las reglas de purga, embargo y selección interna
fijadas en A1. Las seis celdas modelo/conjunto comparten la misma máscara.

| Familia | Contraste | Delta QLIKE | IC 95 % | p crudo | p Holm | Reducción QLIKE % |
| --- | --- | --- | --- | --- | --- | --- |
| log-OLS HARQ | B1 sobre B0 | +0.00042374551 | [-0.0016802447, +0.0023750514] | 0.6746 | 1 | +0.29030380 |
| log-OLS HARQ | B2 sobre B1 | -243.70844486 | [-731.12865876, +0.0023546663] | 0.6095 | 1 | -167448.32044 |
| LightGBM QLIKE | B1 sobre B0 | +0.0018152183 | [-0.00037879140, +0.0041613972] | 0.1181 | 0.4724 | +1.2035977 |
| LightGBM QLIKE | B2 sobre B1 | -0.00010841274 | [-0.0010017585, +0.00069008833] | 0.8002 | 1 | -0.07275983 |

Delta positivo favorece al conjunto ampliado. Reducción = 100 × delta /
QLIKE base. El bootstrap circular usa bloques de cinco sesiones, 9.999
réplicas, intervalo percentil y p bilateral centrado; Holm cubre los cuatro
contrastes de esta ventana. Su validez depende de los supuestos registrados,
no queda probada por ejecutar el código.

## Cola adversa preservada

El 2025-05-15 concentra el 99,94095565 % de la suma de pérdidas QLIKE por
sesión de B2 log-OLS. Dos pronósticos alcanzan el suelo registrado de 1e-12:
uno en MSFT y uno en TSLA. La razón objetivo/pronóstico en QLIKE penaliza
severamente esa infrapredicción. La media de la sesión es 101870,78223.
El ajuste guardado tiene rango 155 para 166 columnas y singular mínimo
5,9028e-14; estos metadatos no identifican qué variable causó el extremo.
No se eliminó la sesión, no se reajustó el modelo y no se cambió el suelo.

La comprobación es de pronósticos ya calculados, no una nueva evaluación.
El diagnóstico por activo, sus comprobaciones de hashes y reconciliación
con la pérdida diaria están en `tail_diagnostic.json`. El código reproducible
es `../rp4_code/tail_diagnostic.py`.

## Evidencia y comando

`summary.json` conserva inferencia, secundarios, todos los signos por activo
y bloque, y exclusiones. `session_losses.csv` contiene los agregados diarios.
Pronósticos y objetivos por origen permanecen fuera de Git en la raíz privada
de RP4. El panel A2 y su especificación se identifican en `binding`.

Con el entorno de `docs/rp4/operations_v1.md`:

```powershell
uv run --offline --frozen --no-sync python -B artifacts/rp4_code/evaluate.py --panel D:/MDS650/artifacts/rp4_20260907/a2_combined_v2/panel.parquet --spec artifacts/rp4_a1/specification.json --spec-sha256 865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5 --window primary --output D:/MDS650/artifacts/rp4_20260907/evaluation/primary --public-output artifacts/rp4_b2 --threads 4
```

Salida observada: `RP4_WINDOW_COMPLETE:primary:sessions=418`, código 0.
SHA-256 de `summary.json`:
`d311d2773ae195968a59cea7d4e0c68dcf35d5d80e005c6cc0f1e028496d2eb2`.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
