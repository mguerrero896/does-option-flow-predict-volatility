"""Append Part 34 without rewriting previous report or registration evidence."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from artifacts.rp4_v5_part34.audit import METHODS, OUT, ROOT, RUN, sha, write_json


def main():
    summary = json.loads((OUT / "summary.json").read_text())
    table = pd.read_csv(OUT / "table.csv", index_col="family")
    diag = pd.read_csv(OUT / "diagnostics.csv", index_col="family")
    registration = ROOT / "docs/rp4/prospective_combination_decision_136.md"
    registration_receipt = json.loads(
        registration.with_name(registration.stem + "_receipt.json").read_text()
    )
    assert sha(registration) == registration_receipt["document_sha256"]
    for path, digest in registration_receipt["antecedent_sha256"].items():
        assert sha(Path(path)) == digest
    assert summary["refits"] == summary["prospective_data_reads"] == 0
    labels = dict(
        zip(
            METHODS,
            [
                "Ridge recalculada en v5 (referencia v4)",
                "Promedio HAR/ridge/ElasticNet",
                "Promedio de cuatro con LightGBM",
            ],
            strict=True,
        )
    )
    rows, p_rows = [], []
    auditor = dict(zip(METHODS, [(0.046, 0.0023), (0.042, 0.0007), (0.025, 0.0028)], strict=True))
    for method in METHODS:
        pair = [
            next(
                r
                for r in summary["contrasts"]
                if r["method"] == method and r["contrast"] == h and r["bootstrap_seed"] == 20260908
            )
            for h in ("H1", "H2")
        ]
        rows.append(
            "| "
            + labels[method]
            + " | "
            + " | ".join(f"{table.loc[method, b]:.9f}" for b in ("B0", "B1", "B2"))
            + " | "
            + " | ".join(f"+{r['reduction_percent']:.3f} %, p={r['p_raw']:.4f}" for r in pair)
            + " |"
        )
        for i, h in enumerate(("H1", "H2")):
            p07 = next(
                r["p_raw"]
                for r in summary["contrasts"]
                if r["method"] == method and r["contrast"] == h and r["bootstrap_seed"] == 20260907
            )
            origin = next(
                r["p_raw"]
                for r in summary["origin_weight_auditor_seed_contrasts"]
                if r["method"] == method and r["contrast"] == h
            )
            p_rows.append(
                f"| {labels[method]} {h} | {auditor[method][i]:.4f} | "
                f"{pair[i]['p_raw']:.4f} | {p07:.4f} | {origin:.4f} |"
            )
    gaps = "\n".join(
        f"| {f} | {diag.loc[f, 'gap_canonical']:+.9f} | {diag.loc[f, 'gap_origin']:+.9f} |"
        for f in ("lightgbm_qlike", "log_elastic_net", "log_ridge_harq", "log_har")
    )
    reduction_ridge = 100 * (1 - table.loc["average_learned4", "B2"] / 0.1809103004317701)
    reduction_top2 = 100 * (
        1 - table.loc["average_learned4", "B2"] / table.loc["ensemble_top2", "B2"]
    )
    section = f"""

## Sensibilidad post hoc: combinar en vez de elegir

**POST HOC.** Procedimientos escogidos después de ver los resultados históricos;
los p siguientes no controlan la búsqueda ni sustituyen el titular v4 o el
selector registrado. Sólo se combinan pronósticos guardados, sin reajustar modelos.
Se verificaron 2.095 registros/recibos y las 419 sesiones, con claves y objetivos
comunes. El recálculo de las pérdidas de las cinco familias y los dos selectores
coincide con el informe cerrado: error absoluto máximo
{summary["canonical_roundtrip_max_abs_error"]:.3g}. Las frecuencias B0 se reproducen:
LightGBM 203, ElasticNet 119, ridge 68 y HAR 29. No se detecta error del selector.

La combinación es la media aritmética de los niveles positivos antes de QLIKE.
Se utiliza el productor canónico: pesos iguales por activo/sesión, luego por
sesión; bootstrap circular de bloque 5, 9.999 réplicas, semilla histórica v5
20260908, nula centrada, corrección +1, una cola. H1 compara B1/B0; H2 B2/B1.
Reducción = 100 × media(pérdida base − ampliada) / media(pérdida base).

| Procedimiento | B0 | B1 | B2 | H1 | H2 |
|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

El promedio de cuatro tiene el menor QLIKE B2 entre los procedimientos de esta
comparación histórica: {reduction_ridge:.3f} % por debajo de la ridge v4 original
y {reduction_top2:.3f} % por debajo de top2, calculados como
100 × (1 − QLIKE combinación / QLIKE referencia). No demuestra superioridad
estadística entre modelos ni éxito prospectivo. Las tres cadenas nominales de
esta sensibilidad pasan H1→H2, sin corrección por su búsqueda post hoc.

### Diagnosis y alcance

Brecha B2 = pérdida realizada menos QLIKE de validación interna, promediada
entre sesiones. La validación usa pesos iguales por activo/sesión; la segunda
columna cambia sólo la pérdida realizada a pesos iguales por origen dentro
de sesión y reproduce las cifras aproximadas del auditor:

| Familia | Brecha canónica | Brecha con realizado por origen |
|---|---:|---:|
{gaps}

Esto documenta optimismo histórico relativo de la validación para LightGBM y
pesimismo para HAR/ridge. Es compatible con una selección demasiado favorable
a los árboles en esta muestra; no prueba un sesgo causal universal de ventanas
de diez sesiones. La diversidad puede aprovecharse promediando pronósticos,
sin exigir acertar el ganador diario.

El oráculo ex post toma la menor pérdida de las **cinco** familias por sesión,
incluida persistencia: B2 canónico {summary["oracle"]["canonical"]["ex_post_oracle_B2"]:.9f}
frente a mejor fija HAR {summary["oracle"]["canonical"]["best_fixed_B2"]:.9f}.
Con realizado por origen: {summary["oracle"]["origin"]["ex_post_oracle_B2"]:.9f}
y {summary["oracle"]["origin"]["best_fixed_B2"]:.9f}, que reproducen 0,1743 y 0,1806
del auditor al redondear. Es un límite con conocimiento del resultado, no una
estrategia disponible antes de la sesión. No se excluye persistencia del oráculo.

La parte 34 también informa estos filtros post hoc con ponderación por origen:
selección por QLIKE realizado previo de 10/20/40/60 sesiones,
0,1833/0,1834/0,1811/0,1809; histéresis 0,002/0,005/0,01,
0,1834/0,1833/0,1819; selector de tres lineales, 0,1810; referencia ridge fija,
0,180823. Se consignan como **resultados atribuidos al auditor, no reproducidos
en este recibo**: la orden no aporta su implementación, inicialización o regla
exacta de histéresis. No justifican afirmar que ningún filtro pueda funcionar;
describen únicamente los candidatos que informó. No se mezclan con la tabla
canónica ni se usan para cambiar el selector o el registro.

### Conciliación con la auditoría independiente

Todas las pérdidas de la tabla solicitada coinciden dentro de 1e-4. Las
reducciones porcentuales son compatibles con su redondeo a tres decimales:
diferencias de hasta 0,0005 puntos porcentuales; por ejemplo, H1 del promedio
de cuatro es 1,0104506 % frente al 1,010 % informado. Los p difieren más allá de
1e-4. Se conserva la receta ejecutable registrada, sin escoger una semilla por
su significación. El contraste adicional con semilla del auditor permite
separar su efecto; cambiar también la ponderación no reproduce sus p:

| Contraste | p informado auditor | Canónico 20260908 | Canónico 20260907 | Por origen 20260907 |
|---|---:|---:|---:|---:|
{chr(10).join(p_rows)}

La semilla explica la diferencia entre las dos columnas canónicas, pero no
toda la discrepancia con el auditor. Sin su código, vector de contrastes e
índices de remuestreo, **no puedo confirmar la causa exacta de esa discrepancia**.
No se atribuye exclusivamente al redondeo o a la ponderación. El recibo deja
los vectores por sesión, los parámetros, p, excedencias e IC completos para
compararlos. El IC percentil bilateral no invierte el p unilateral centrado.

### Deriva numérica ridge frente a v4

| Conjunto | Ridge v4 | Ridge v5 | v5 − v4 |
|---|---:|---:|---:|
| B0 | 0,1836603717937846 | 0,18366037179378455 | ≈ 0 |
| B1 | 0,1820440600908625 | 0,18205096062361725 | +0,000006900532755 |
| B2 | 0,1809103004317701 | 0,18091349242944227 | +0,000003191997672 |

LightGBM coincide a ocho decimales en B0/B1/B2 (diferencias de redondeo del CSV).
La parte 34 atribuye la deriva ridge a Gram de la enmienda técnica 1. La revisión
del código no acredita esa atribución: `precompute=True` se introduce para
ElasticNet en `artifacts/rp4_v5_a2_code/models.py::_elastic_candidate`; ridge
sigue llamando a `artifacts/rp4_v3_code/models.py::fit_ridge`, que ya calculaba
Gram. El origen causal exacto de las millonésimas no queda aislado por esta
auditoría sin reajustes. Se divulga la diferencia medida; no se inventa su causa
ni se presenta la ridge recalculada como reproducción idéntica de v4.

### Registro prospectivo y recibo de esta sensibilidad

La [decisión 136](prospective_combination_decision_136.md), SHA-256
`{sha(registration)}`, incorpora top2 y combinación de cuatro como secundarios;
v4 sigue primario. Lecturas 20/40/45/335 con sus cohortes exactas y reglas
H1→H2; 45 = 25 históricas + 20 prospectivas. Registro sellado antes de cualquier
lectura prospectiva en esta tarea, sin afirmar el conocimiento de terceros.

La evidencia está en [summary.json](../../artifacts/rp4_v5_part34/summary.json),
[tabla](../../artifacts/rp4_v5_part34/table.csv),
[recibo con hashes](../../artifacts/rp4_v5_part34/receipt.json) y
[productor reproducible](../../artifacts/rp4_v5_part34/audit.py).
Se preserva byte por byte el
[informe anterior](../../artifacts/rp4_v5_part34/results_v5_before_part34.md),
además del snapshot 5_control y sus recibos. La rutina antigua de publicación
reconstruye sólo ese informe anterior: esta sección se repone con el productor
`artifacts/rp4_v5_part34/publish.py`, sin cambiar los resultados congelados.
"""
    (OUT / "sensitivity_section.md").write_text(section, encoding="utf-8")
    live = ROOT / "docs/rp4/results_v5.md"
    prior_report = (OUT / "results_v5_before_part34.md").read_bytes().replace(b"\r\n", b"\n")
    live.write_bytes(prior_report + section.encode())
    decisions = ROOT / "docs/methodology_decisions.md"
    addition = f"""

<a id="decision-136"></a>

136. **RP4: secundarios prospectivos top2 y combinación equiponderada de cuatro
     familias (2026-09-09, autorización del propietario en parte 34).**
     Nuevo registro: `docs/rp4/prospective_combination_decision_136.md`, SHA-256
     `{sha(registration)}`.
     v4 ridge RV15 conserva el primario; top2 y media en niveles de HAR/ridge/
     ElasticNet/LightGBM son secundarios. Lecturas 20/40/45/335: 45 reúne las
     25 históricas registradas y las primeras 20 nuevas, no 45 prospectivas.
     Misma secuencia H1→H2 nominal al 5 %, bootstrap circular 5/9999, semilla
     20260907; no control global entre secundarios, lecturas o búsqueda.
     Se reporta cualquier ranking prospectivo favorable o adverso sin cambiar
     el primario ni rescatar decisiones anteriores. Registro sellado antes de
     cualquier lectura prospectiva en esta tarea. La sensibilidad histórica
     se identifica como post hoc, sin reajustes; no confirma el programa.
     Los registros anteriores y el borrador 4 sin sellar permanecen intactos.
     RESEARCH_ONLY; NOT INVESTMENT ADVICE; capital_go=false. Sin push.
"""
    prior_decisions = (OUT / "methodology_decisions_before_part34.md").read_bytes().replace(
        b"\r\n", b"\n"
    )
    decisions.write_bytes(prior_decisions + addition.encode())
    ledger_path = ROOT / "artifacts/rp4_v5_a3_operations/inbox_ledger.json"
    ledger = json.loads(ledger_path.read_text())
    filename = "20260909_0200_parte34_hiloC_auditoria_selector_y_combinacion.md"
    ledger["files"] = [row for row in ledger["files"] if row["name"] != filename] + [
        {
            "name": filename,
            "sha256": registration_receipt["instruction_sha256"],
            "read_completely": True,
            "remaining": None,
            "status": "executed_verified",
            "receipt": "artifacts/rp4_v5_part34/receipt.json",
        }
    ]
    ledger.update(
        last_executed_filename=filename,
        last_read_filename=filename,
        updated_at_utc=datetime.now(UTC).isoformat(),
    )
    write_json(ledger_path, ledger)
    files = [
        p for p in OUT.iterdir() if p.is_file() and p.name not in ("receipt.json", "receipt.sha256")
    ]
    files += [
        live,
        decisions,
        registration,
        registration.with_suffix(".sha256"),
        registration.with_name(registration.stem + "_receipt.json"),
        ledger_path,
        RUN / "reports/5_control/receipt.json",
        ROOT / "artifacts/rp4_v5_a3/freeze.json",
        ROOT / "artifacts/rp4_v3_code/inference.py",
        ROOT / "src/mds650/rp2/inference.py",
        ROOT / "artifacts/rp4_v5_a2_code/reporting.py",
        ROOT / "artifacts/rp4_v5_a3_code/reporting.py",
    ]
    files += list(
        (ROOT / "docs/rp4").glob("prospective_combination_decision_136_clarification_1.*")
    )
    write_json(
        OUT / "receipt.json",
        {
            "status": "PASS_PART34_HISTORICAL_AUDIT_AND_NEW_REGISTRATION",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "refits": 0,
            "prospective_data_reads": 0,
            "canonical_roundtrip_max_abs_error": summary["canonical_roundtrip_max_abs_error"],
            "auditor_p_values_exactly_reproduced": False,
            "ridge_drift_cause_proven": False,
            "hashes": {str(p.relative_to(ROOT)): sha(p) for p in files},
        },
    )
    (OUT / "receipt.sha256").write_text(sha(OUT / "receipt.json") + "  receipt.json\n")
    assert live.read_bytes().startswith(prior_report)
    assert decisions.read_bytes().startswith(prior_decisions)
    print(sha(OUT / "receipt.json"))


if __name__ == "__main__":
    main()
