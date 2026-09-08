"""Publishable aggregate-only projection; licensed origin exports stay private."""

# ruff: noqa: E501 - literal report paragraphs retain their readable text as units.

from __future__ import annotations

import datetime as dt
import json
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
from artifacts.rp4_closeout_audit_code.audit_closed import (
    OUTPUT,
    ROOT,
    load,
    new_file,
    sha,
    window_paths,
)


def neutral_inputs(sources: dict[str, str]) -> dict[str, str]:
    """Logical aliases deliberately reveal neither owner names nor local paths."""
    return {
        f"inputs/source_{i:05d}": digest for i, (_, digest) in enumerate(sorted(sources.items()), 1)
    }


def markdown(frame: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for values in frame[columns].itertuples(index=False, name=None):
        cells = [f"{v:.9g}" if isinstance(v, float) else str(v) for v in values]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def run() -> dict[str, Any]:
    base = load(OUTPUT / "manifest.json")
    extra = load(OUTPUT / "metadata_manifest.json")
    sources = {**base["source_sha256"], **extra["source_sha256"]}
    for manifest in [base, extra]:
        for filename, digest in manifest["artifacts_sha256"].items():
            assert sha(OUTPUT / filename) == digest
    endpoints = []
    for horizon in [15, 5]:
        for window in ["primary", "confirmation"]:
            public, private = window_paths(horizon, window)
            summary = load(public / "summary.json")
            for filename, digest in summary["completed_session_sha256"].items():
                rec = load(private / "sessions" / filename, digest)
                selected = dt.datetime.fromisoformat(rec["max_training_selected_target_end_utc"])
                guard = dt.datetime.fromisoformat(rec["max_training_target_end_utc"])
                assert guard - selected == dt.timedelta(minutes=30 - horizon)
                endpoints.append(
                    {
                        "horizon_minutes": horizon,
                        "window": window,
                        "session": rec["session"],
                        "selected_target_end_utc": str(selected),
                        "conservative_rv30_guard_end_utc": str(guard),
                        "selected_end_utc_clock": selected.strftime("%H:%M"),
                        "selected_end_ny_clock": selected.astimezone(
                            ZoneInfo("America/New_York")
                        ).strftime("%H:%M"),
                    }
                )
    ep = pd.DataFrame(endpoints)
    new_file(
        "selected_target_endpoint_by_session.csv",
        ep.to_csv(index=False, lineterminator="\n").encode(),
    )
    clocks = (
        ep.groupby(["horizon_minutes", "window", "selected_end_utc_clock", "selected_end_ny_clock"])
        .size()
        .rename("N_sessions")
        .reset_index()
    )
    new_file(
        "selected_target_endpoint_clock_census.csv",
        clocks.to_csv(index=False, lineterminator="\n").encode(),
    )
    c = pd.read_csv(OUTPUT / "b2_coefficient_summary.csv")
    presence = c[c.kind == "presence"]
    new_file(
        "b2_presence_coefficient_summary.csv",
        presence.to_csv(index=False, lineterminator="\n").encode(),
    )
    rv15 = c[(c.horizon_minutes == 15) & (c.window == "primary") & (c.kind == "feature")]
    gamma = rv15[rv15.column.str.startswith("rp4_gamma_imb_")]
    shares = rv15[
        rv15.column.isin([f"b2_5m_{kind}_premium_share" for kind in ["passive", "buy", "sell"]])
    ]
    profiles = pd.read_csv(OUTPUT / "descriptive_profiles.csv")
    p = profiles[
        (profiles.horizon_minutes == 15)
        & (profiles.window == "primary")
        & (profiles.contrast == "B2_over_B1")
    ]
    tariff = p[
        (p.profile == "tariff_calendar")
        & (p.family == "lightgbm_qlike")
        & p.stratum.isin(
            [
                "four_days_first_market_hour_origin_lt60",
                "four_days_first_observed_hour_origin35_94",
                "outside_four_days_first_observed_hour_origin35_94",
                "outside_four_days_remainder_origin_ge95",
            ]
        )
    ]
    intraday = p[(p.profile == "intraday") & (p.family == "log_ridge_harq")]
    empty = p[(p.profile == "window_empty_5m") & (p.stratum == "inside")]
    months = profiles[
        (profiles.horizon_minutes.isin([30, 15]))
        & (profiles.window == "primary")
        & (profiles.family == "log_ridge_harq")
        & (profiles.contrast == "B2_over_B1")
        & (profiles.profile == "month")
        & profiles.stratum.isin(["2025-10", "2025-11"])
    ]
    tiers = profiles[
        (profiles.horizon_minutes == 15)
        & (profiles.window == "primary")
        & (profiles.family == "log_ridge_harq")
        & (profiles.contrast == "B1_over_B0")
        & profiles.profile.isin(["training_size_tercile", "calendar_early"])
    ]
    prune = pd.read_csv(OUTPUT / "ridge_bounds_pruning_summary.csv")
    prune = prune[(prune.horizon_minutes == 15) & (prune.window == "primary")]
    rounds = pd.read_csv(OUTPUT / "loss_tails_and_rounds_summary.csv")
    rounds = rounds[(rounds.horizon_minutes == 15) & (rounds.window == "primary")]
    evidence = load(
        ROOT / "artifacts/rp4_v3_secondary_closeout/evidence.json",
        "e5951301b649caed3270906aa38c86831b28de8ad218eba5a899ad0397167cd1",
    )
    jumps = []
    for window in ["primary", "confirmation"]:
        j = evidence["newton_final"][window]["summary"]["jump_secondary"]
        jumps.append(
            {
                "window": window,
                "N_sessions": j["N_sessions"],
                "N_origins": j["N_origins"],
                "positive_labels": j["positive_labels"],
                "positive_percent": 100 * j["positive_labels"] / j["N_origins"],
            }
        )
    sources[str(ROOT / "artifacts/rp4_v3_secondary_closeout/evidence.json")] = sha(
        ROOT / "artifacts/rp4_v3_secondary_closeout/evidence.json"
    )
    text = (
        "\n\n".join(
            [
                "# Auditoría descriptiva de cierre RP4 — RV30, RV15 y RV5",
                "Se extrajeron pronósticos y diagnósticos ya cerrados: 419 sesiones/160.832 orígenes primarios y 25/9.750 de confirmación por horizonte. No se ajustó ningún modelo, no se consultó tape bruto ni se calculó ningún nuevo p, AUC o bootstrap. Las 7.992 medias QLIKE de sesión reconstruidas desde pronósticos coinciden con los CSV fijados hasta 6,67e-16. No cambia ninguna decisión primaria.",
                "## Coeficientes: escala y correspondencia exacta",
                "B2 tiene 138 predictores registrados más cinco efectos de activo, 109 indicadores de presencia y un intercepto: 253 términos representados por sesión. El CSV privado contiene 336.996 filas (253×444×3); el resumen público tiene 1.518 filas (253×2 ventanas×3 horizontes). `presence:nombre` corresponde a disponibilidad finita de esa variable, no a su pendiente.",
                "Los coeficientes actúan sobre variables transformadas, centradas/escaladas sólo con entrenamiento y recortadas a ±5 desviaciones; no se reestandariza después. Predicen log-RV antes de Duan y las cotas de salida. Una poda se representa como contribución cero y motivo explícito, NO como efecto estimado nulo. Su magnitud/signo no identifica causalidad, aportación marginal aislada ni importancia de ablación.",
                "[Resumen completo de coeficientes](b2_coefficient_summary.csv) · [Sólo presencias](b2_presence_coefficient_summary.csv). Los valores siguientes son B2 ridge, RV15, primaria.",
                markdown(
                    gamma,
                    [
                        "column",
                        "mean",
                        "median",
                        "positive_count",
                        "negative_count",
                        "active_sessions",
                    ],
                ),
                "Gamma total es positivo en 361/419 sesiones (86,16%); el contador `signed_trades` es negativo en 419/419. Ese predictor cuenta operaciones con dirección identificada y usa log1p: no es una variable firmada de compra/venta. Los signos no demuestran que estas cuatro columnas causen la mejora observada.",
                markdown(
                    shares,
                    ["column", "mean", "median", "absolute_mean", "zero_count", "active_sessions"],
                ),
                "Las medias absolutas 0,25–0,31 pertenecen a shares de 5 minutos, no a todas las shares de 30 minutos. Las medianas están cerca de cero, pero NO son exactamente cero; la media absoluta no describe una contribución típica estable.",
                "## Regularización, podas y cotas",
                "Se verifican 102/114/111 elecciones de lambda=1e-4 en B0/B1/B2 sobre 419 sesiones RV15. El objetivo implementado es suma de residuos cuadrados de log-RV más lambda×L2, sin penalizar intercepto; no es MSE+lambda independiente de N. El factor n/(n+lambda) sólo es una ilustración bajo un diseño ortogonal y escalado apropiado, no la contracción real de este diseño correlacionado y winsorizado.",
                markdown(
                    prune,
                    [
                        "information_set",
                        "N_sessions",
                        "removed_min",
                        "removed_median",
                        "removed_max",
                        "count_low",
                        "count_high",
                    ],
                ),
                "Las 88 podas de B2 son el mínimo, no una constante: mediana 89 y máximo 97. Incluyen columnas de presencia; el número de predictores brutos no debe confundirse con el rango efectivo. Los límites altos 223/324/302 y bajos cero son incidencias por origen sobre 160.832 pronósticos de cada conjunto.",
                "## Perfiles temporales y ventana de cuatro días",
                "Delta siempre significa QLIKE base menos QLIKE ampliado: positivo favorece B2. Los cortes de esta auditoría son descriptivos posteriores y no nuevas pruebas. La ventana llamada tarifas es únicamente el calendario 2025-04-07 a 2025-04-10 solicitado; estas asociaciones no identifican un efecto causal de aranceles.",
                markdown(
                    tariff,
                    [
                        "stratum",
                        "N_origins",
                        "N_sessions",
                        "delta_pooled",
                        "delta_equal_session_asset",
                    ],
                ),
                "Las 288 observaciones y delta −0,322087411 corresponden a 35≤origin_minute<95, primera hora observable. El corte declarado origin_minute<60 contiene 120 y delta −0,482621152. No son intercambiables. Fuera de los cuatro días, +0,000255369 y +0,000390846 corresponden al corte observable <95 y su resto, con promedio por origen; excluir ese calendario no produce un nuevo p autorizado.",
                markdown(
                    intraday,
                    [
                        "stratum",
                        "N_origins",
                        "N_sessions",
                        "delta_pooled",
                        "delta_equal_session_asset",
                    ],
                ),
                "`last_hour` en el productor registrado significa origin_minute≥300. No es la última hora de mercado (≥330 en sesión normal de390min). Por ello se exponen ambos cortes con nombres explícitos. No se trasladan cifras entre cortes ni entre ponderación por origen y por sesión/activo.",
                markdown(
                    months,
                    ["horizon_minutes", "stratum", "delta_pooled", "delta_equal_session_asset"],
                ),
                "Octubre y noviembre de2025 son negativos para B2 ridge en RV30 y RV15; la mejora media no implica estabilidad mensual completa.",
                markdown(
                    tiers,
                    [
                        "profile",
                        "stratum",
                        "N_sessions",
                        "first_session",
                        "last_session",
                        "delta_equal_session_asset",
                    ],
                ),
                "El tramo evaluado octubre2024–febrero2025 tiene64 sesiones, 15,27% de419, no84/20%. En ese tramo B1 ridge RV15 es negativo. No constituye el primer tercil: los terciles de tamaño de entrenamiento tienen140/139/140 sesiones y sus límites aparecen en la tabla. Tamaño creciente, calendario y regímenes se confunden; esta partición no demuestra que más entrenamiento cause estabilidad.",
                "## Vacíos, extremos y degeneración",
                markdown(
                    empty,
                    [
                        "family",
                        "N_origins",
                        "N_sessions",
                        "N_asset_sessions",
                        "base_qlike_pooled",
                        "rich_qlike_pooled",
                        "base_qlike_equal_session_asset",
                        "rich_qlike_equal_session_asset",
                    ],
                ),
                "Las412 filas vacías de5min abarcan seis sesiones y25 activo-sesiones. El salto ridge0,102703519→0,202126323 es el promedio igual-sesión/activo; el promedio por origen es0,185885062→0,247087047. Fuera hay160.420 filas repartidas en418 sesiones (una sesión puede tener filas dentro y fuera). El p=0,0007 propuesto para excluirlas es NO VERIFICABLE sin un artefacto fijado que lo respalde; aquí no se recalcula.",
                markdown(
                    rounds,
                    [
                        "family",
                        "information_set",
                        "loss_above_5",
                        "selected_rounds_min",
                        "selected_rounds_max",
                    ],
                ),
                "LightGBM RV15 usa entre16 y1.013 rondas, ninguna llega a2.000. Hay364–393 pérdidas QLIKE>5 según conjunto/familia, no un conteo único. Se verificaron cero pronósticos constantes dentro de activo-sesión y cero igualdad exacta entre B0/B1/B2 en5.028 unidades activo-sesión-familia POR horizonte primario (15.084 entre los tres); confirmación aporta300 por horizonte. No igualdad exacta no demuestra ventaja útil.",
                "## UTC, purga y máscaras",
                markdown(
                    clocks[(clocks.horizon_minutes == 15) & (clocks.window == "primary")],
                    ["selected_end_utc_clock", "selected_end_ny_clock", "N_sessions"],
                ),
                "El objetivo RV15 termina normalmente a15:40 Nueva York:19:40UTC en horario de verano y20:40UTC en invierno, con cierres reducidos separados. No es19:40UTC en419/419. La compuerta temporal usa deliberadamente el fin RV30 heredado:15:55NY normalmente, 15 minutos después del objetivo RV15 y25 después deRV5. No deben compararse ambos campos como si fueran la misma etiqueta. El margen guardado mínimo supera la purga de60min:1.090min.",
                "Los seis bindings son constantes dentro de cada ventana y sus códigos coinciden por hash. Los bitmasks RV15/RV5 son idénticos; frente aRV30 se compararon exactamente claves, número de sesiones de entrenamiento, última sesión y fin del objetivo conservador. RV30 no guardó aquellos bitmasks: no se afirma una comparación binaria inexistente.",
                "## Salto y cierre de interpretación",
                markdown(
                    pd.DataFrame(jumps),
                    ["window", "N_sessions", "N_origins", "positive_labels", "positive_percent"],
                ),
                "La primaria final de salto ya tiene419 sesiones, no418. `jump30>0` clasifica exceso positivo RV−BPV, no un test formal de salto. En estas ventanas cerradas las frecuencias son63,61% y64,29%, no56%; otra población necesita su propio denominador. Los agregados cerrados no rechazan H1 y no abren H2. No se estimó nueva AUC.",
                "## Custodia y publicación",
                "La proyección public_manifest.json contiene sólo aliases neutros de fuentes y hashes, sin rutas privadas. Los CSV por origen, los coeficientes por sesión, los recibos operativos con rutas y los diagnósticos detallados quedan fuera de la allowlist pública. Nada se publica automáticamente. La licencia de software no redistribuye datos de proveedores ni derivados granulares; rige la política de acceso del proyecto.",
                "La skill Model Evaluator guió la separación de métricas, máscaras, escalas y procedencia; no se usó para entrenar o buscar un resultado favorable. RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.",
            ]
        )
        + "\n"
    )
    new_file("REPORT.md", text.encode())
    allowed = ["REPORT.md", "b2_coefficient_summary.csv", "b2_presence_coefficient_summary.csv"]
    projection = {
        "status": "AGGREGATE_ONLY_NOT_PUBLISHED",
        "inputs_sha256": neutral_inputs(sources),
        "outputs_sha256": {name: sha(OUTPUT / name) for name in allowed},
        "source_alias_semantics": "Logical source aliases; licensed sources are not bundled. Original digests preserved. Mapping held in restricted local manifests.",
        "model_fits": 0,
        "new_p_values": 0,
        "bootstrap_runs": 0,
        "exclude_all_outputs_not_explicitly_allowlisted": True,
        "granular_licensed_exports_included": False,
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    encoded = json.dumps(projection, indent=2) + "\n"
    for forbidden in [
        "mguer",
        "private-input/d0023e7cb6a981751ef5",
        "private-input/8d10eace3eede3521e71",
        "private-input/8545a81f99f36eda523c",
        "private-input/77a21ec4f7934cdbc426",
        "public_checkout",
        "publication_remediation",
    ]:
        assert forbidden not in encoded
    new_file("public_manifest.json", encoded.encode())
    return {
        "status": "PASS_PUBLIC_PROJECTION",
        "public_output_count": len(allowed),
        "neutral_source_aliases": len(sources),
        "new_model_fits": 0,
        "new_p_values": 0,
        "private_origin_exports_published": 0,
        "report_sha256": sha(OUTPUT / "REPORT.md"),
        "public_manifest_sha256": sha(OUTPUT / "public_manifest.json"),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
