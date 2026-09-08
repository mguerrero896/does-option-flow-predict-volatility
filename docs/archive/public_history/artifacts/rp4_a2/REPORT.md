# RP4 A2 — desarrollo materializado

PASS: seis activos, 479 sesiones, 185.729 orígenes entre 2024-08-02 y
2026-07-31. Se conservan las 181.829 claves registradas y se añaden 3.900
orígenes del 20 al 31 de julio. La construcción no ajustó modelos.

Panel privado: `private-input/c1ae6ab902047da171cf`.
SHA256: `51f04c5937a7922757f929ef0ca53941b7766719cf2799673669f8545f97a949`.
Manifiesto: `323d404eb6c5d3327722fe318d3b81247a50813d76cfbae135ff877edef01579`.

Se construyeron 25 celdas IV más su conteo, tres medidas de dealers con
tasas/dividendos reales y siete HARQ, manteniendo las columnas registradas.
Los diagnósticos conservados para auditoría no entran en las matrices X.

## Objetivo y cobertura

RV30 reconstruido válido: 185.715; 14 orígenes excluidos porque alguna de sus
31 barras de cierre no fue observada. No se sustituyó por un cierre rellenado.
De las 83.509 claves que se cruzaban inicialmente con el objetivo registrado,
83.502 conservan comparación válida: diferencia absoluta máxima y media 0.
Las otras siete pertenecen a ventanas excluidas por la nueva comprobación de
barras observadas; no se afirma coincidencia de valores que no se utilizaron.

La [tabla de cobertura](../../../../../artifacts/rp4_a2/coverage.csv) contiene las 150 combinaciones
activo/vencimiento/moneyness, con denominadores y conteos. En las celdas ATM
8–30 días la cobertura va de 99,7577 % a 99,7836 %. La cobertura mínima de
alas extremas para vencimientos de al menos ocho días es 82,8687 % (MSFT).
No se fuerza el centro a 100 %. Se conservan también las celdas cortas de
baja cobertura como NaN, sin imputarlas ni eliminarlas.

Los [agregados y hashes](../../../../../artifacts/rp4_a2/summary.json) contienen las comparaciones por activo
y los seis manifiestos de componentes. Cada componente conserva en D: hashes
de barras, fuentes exógenas, paneles registrados y tape por sesión. Los seis
comparten identidad de inputs
`1d30aec0e306459396e0913679b3017234a5fea91d8445a6f684a966279e0e60`.

Se declara el hueco de UW 2025-01-25 a 2025-02-24, sin relleno. Los 479 días
presentes menos las primeras 60 sesiones de entrenamiento dejan como máximo
419 sesiones programadas para la primaria, antes de aplicar su máscara.

## Verificación

El comando completo de combinación consta en `summary.json`, salida 0.
Verificador A1: salida 0; nueve pruebas focalizadas de materialización: salida
0; Ruff: salida 0. Se mantuvo el hash de especificación
`865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5`.

NO VERIFICABLE: el código de salida original de los subprocesos NVDA y TSLA
no se recuperó tras interrumpirse el transporte de sus colaboradors por límite de
uso; ambos produjeron manifiestos completos, sus hashes se verificaron y la
combinación final sí terminó con código 0 observado directamente. No se
repite una evaluación para resolver esa ausencia de transporte.

Los [incidentes anteriores](INCIDENTS.md) se preservan; ninguna fuente,
especificación congelada ni carpeta phase9 fue modificada. La convención RV30
de RP2 usa los cierres de índices origen a origen+30; con barras etiquetadas
al inicio, el último cierre se completa un minuto después del sello nominal
target_end_utc. La separación por sesiones y la purga/embargo de 60 minutos
evitan que ese desfase de etiqueta cruce entrenamiento y evaluación.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
