# RP4 B1 — adquisición y panel completo

PASS: 331 trabajos verificados, faltantes cero. Cierre de custodia con salida 0.

| Entrada | Cobertura ejecutada |
| --- | --- |
| FMP 1 minuto | 280/280 activo-sesiones: 35 fechas × seis activos, SPY y QQQ, 2026-07-20 a 2026-09-04 |
| UW normalizado | 25/25 sesiones, 2026-08-03 a 2026-09-04 |
| Copias de phase9 | 11/11 sesiones; 54 archivos originales y copias revalidados por SHA-256 |
| Exógenos | Treasury 2024 y 2026; seis respuestas de dividendos actualizadas |
| Eventos | Seis calendarios de earnings y calendario FOMC corregido de 16 fechas |

`summary.json` contiene un manifiesto por trabajo y el hash de cada archivo,
sin filas licenciadas ni credenciales. El pase global final fue
`acquisition_batch_all_20260907T001147950705Z.json`, SHA-256
`19e9de749ddad8d81b76bda11b67f80cd099b734839aaba71f87dbb4d5585477`, salida 0.
Los incidentes y el pase anterior con contención local se conservan en
`INCIDENTS.md`; no son faltantes del panel final.

## Materialización

Se añadieron 9.750 orígenes, 25 sesiones y seis activos. Los 9.750 RV30 son
finitos y se construyeron desde barras observadas: cero ventanas con barras
no observadas, cero claves de barras faltantes y cero bloques activo-sesión
excluidos durante esta materialización. La evaluación aplica además la
máscara común de predictores obligatorios; estos 9.750 no son una promesa de
9.750 orígenes modelables.

Centro 8–30 días de la rejilla: 100 % en los seis activos. Mínima cobertura
de alas extremas con vencimiento ≥8 días: 93,84615385 %, MSFT, 8–30 días,
moneyness >1,10. Ocho celdas activo/rejilla tienen cobertura inferior al 50 %;
se conservaron, como exige A1, sin rellenar IV ausente. Los 150 cruces
activo/vencimiento/moneyness se encuentran en `coverage.csv`.

El panel unido contiene 195.479 orígenes. Se comprobó igualdad exacta por
claves de las 185.729 filas de desarrollo antes y después de añadir la
extensión, incluidos NaN. Las fuentes nuevas de dividendos no cambian ningún
par tasa/caja histórica de desarrollo comparado. No se reescribió A2.

| Artefacto privado | SHA-256 |
| --- | --- |
| A2, desarrollo | 51f04c5937a7922757f929ef0ca53941b7766719cf2799673669f8545f97a949 |
| Extensión de panel | 381ec3191cb2fcf42035f4281c2adc99e70dd6edd075c653558441d56435a7e8 |
| Panel completo | ecb1c6cce76cb6464d3cdf3d4ef409c60e204adf2df22fba6851e32199819d93 |
| Prueba de unión / linaje | abe40d6990fbc59bcee6f3912bda1d2dc5c85f488a38ef95dd835cff537577e1 |

Los precios y las IV son de proveedores reales. El OI de cierre previo es
la atribución autorizada por el propietario, no una disponibilidad histórica
certificada por recibos del cliente. Las tres exposiciones son proxies bajo
la convención de signos fijada, no posiciones observadas de dealers.

## Comandos ejecutados

Entorno: `docs/rp4/operations_v1.md`. Cada comando siguiente terminó con 0.

```powershell
uv run --offline --frozen --no-sync python -B artifacts/rp4_code/acquire.py --spec-hash 865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5 --mode batch --leg all
uv run --offline --frozen --no-sync python -B artifacts/rp4_code/materialize.py --spec artifacts/rp4_a1/specification.json --spec-sha256 865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5 --output-root D:/MDS650/artifacts/rp4_20260907 --start 2026-08-03 --end 2026-09-04 --stage B1_extension_v1 --development-panel D:/MDS650/artifacts/rp4_20260907/a2_combined_v2/panel.parquet
uv run --offline --frozen --no-sync python -B artifacts/rp4_code/materialize.py --spec artifacts/rp4_a1/specification.json --spec-sha256 865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5 --output-root D:/MDS650/artifacts/rp4_20260907 --stage B1_complete_v1 --development-panel D:/MDS650/artifacts/rp4_20260907/a2_combined_v2/panel.parquet --extension-panel D:/MDS650/artifacts/rp4_20260907/b1_extension_v1/panel.parquet
uv run --offline --frozen --no-sync python -B artifacts/rp4_code/close_b1.py --acquisition-summary D:/MDS650/artifacts/rp4_20260907/manifests/acquisition_batch_all_20260907T001147950705Z.json
```

El código del evaluador se incluye en este commit como dependencia de la
escritura atómica de recibos. El resultado primario y su recibo se versionan
en la etapa B2; el hash del evaluador no cambió durante su ejecución.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
