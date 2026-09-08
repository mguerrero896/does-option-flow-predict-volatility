# RP4 — operación y verificación pública

Esta es una proyección pública de la documentación operativa, no el entorno
privado que produjo las evaluaciones. Los originales congelados y su entorno
operativo se conservan sin cambios. Véase la [correspondencia de publicación](publication_projection_v1.md).

## Verificación sin datos licenciados

Desde la raíz de esta copia, con Python 3.12 y las dependencias fijadas:

```powershell
uv run --offline --frozen --no-sync python -B artifacts/rp4_code/verify_delivery.py
$env:PYTHONPATH="$($PWD.Path)/src;$($PWD.Path)/scripts;$($PWD.Path)/artifacts/rp4_code"
uv run --offline --frozen --no-sync python -B -m pytest -o addopts= -q -p no:cacheprovider artifacts/rp4_code
```

El primer comando verifica bytes publicados, punteros a los hashes originales
y ocho extremos de las figuras contra pérdidas agregadas. No verifica datos
licenciados, disponibilidad de proveedores, potencia ni el planificador activo.
Puede comprobar además el checkout original preservado mediante
`--original-root RUTA_PRIVADA`: esa ruta no se publica ni se incluye en recibos públicos.

## Operación ya registrada

El cierre B4 verificó la colección diaria RP4, martes a sábado a las 09:10
Australia/Sydney. Su última comprobación ejecutó 24 trabajos con salida cero
y reutilización por hash. La automatización sigue en el entorno privado original;
esta corrección de publicación no cambia su configuración ni la reactiva otra vez.

La colección incorpora barras y tape para la última sesión XNYS cerrada más
30 minutos, con cinco intentos acotados y un pase final por faltantes. No modifica
phase9, no reajusta modelos y no sobrescribe evaluaciones o snapshots exógenos v1.
Una extensión analítica posterior debe vincular los exógenos de sus fechas y
conservar las ventanas anteriores; no constituye una réplica independiente por
solaparse con ellas.

## Límite de los ejecutores históricos

El código científico y la especificación JSON publicados conservan los bytes
de ejecución, incluidos sus valores de configuración de almacenamiento. Los
comandos originales requieren el entorno privado autorizado y sus entradas.
El verificador A1 original exige el Markdown original: no debe confundirse esta
copia saneada con aquel documento fijado por hash. La proyección no autoriza una nueva
evaluación ni cambia su hash científico.

El espacio mínimo de adquisición es 100 GiB. No se eliminan inputs, resultados,
manifiestos o fuentes de phase9 para conseguirlo. Las credenciales se heredan
del entorno, no se imprimen ni se almacenan en la documentación.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
