"""Render aggregate-only descriptive evidence; never export minute-level observations."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from artifacts.rp4_market_audit_code.audit import (
    ASSETS,
    ROOT,
    csv_bytes,
    json_bytes,
    sha256,
    write_once,
)

DAY_NAMES = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
}
NOTICE = "https://www.nasdaqtrader.com/MicroNews.aspx?id=OTA2026-2"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def table(headers: list[str], rows: list[list[Any]]) -> str:
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
            *("| " + " | ".join(map(str, row)) + " |" for row in rows),
        ]
    )


def aggregates(
    coverage: list[dict[str, str]],
    daily: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    selected = {
        (row["weekday"], row["period"]): row
        for row in coverage
        if row["scope"] == "all_available_origins"
        and row["asset"] == "ALL"
        and row["transition_date"] == "2026-01-26"
    }
    wide: list[dict[str, Any]] = []
    for weekday in DAY_NAMES:
        row: dict[str, Any] = {"weekday": weekday, "transition_date": "2026-01-26"}
        for period in ("before", "from_date"):
            value = selected[(weekday, period)]
            for field in (
                "N_origins",
                "N_sessions",
                "atm_0_1dte_presence_pct",
                "surface_populated_cells_mean",
                "zero_dte_contracts_median_finite",
            ):
                row[period + "__" + field] = float(value[field])
        wide.append(row)
    first: list[dict[str, Any]] = []
    for asset in ASSETS:
        available = sorted(
            [r for r in daily if r["asset"] == asset], key=lambda r: r["session_date"]
        )
        row = next(
            r
            for r in available
            if int(r["expiry_count_monday"]) + int(r["expiry_count_wednesday"]) > 0
        )
        expiries = [date.fromisoformat(d) for d in row["expiry_dates"].split(";")]
        item = {
            "asset": asset,
            "first_observed_session": row["session_date"],
            "first_observed_timestamp_ny": row["first_mon_wed_available_ny"],
            "monday_expiries_on_first_observed_session": ";".join(
                d.isoformat() for d in expiries if d.weekday() == 0
            ),
            "wednesday_expiries_on_first_observed_session": ";".join(
                d.isoformat() for d in expiries if d.weekday() == 2
            ),
        }
        for weekday in ("Monday", "Wednesday"):
            item["first_zero_dte_" + weekday.lower()] = next(
                r["session_date"]
                for r in available
                if r["weekday"] == weekday and int(r["zero_dte_trade_rows"]) > 0
            )
        first.append(item)
    days: list[dict[str, Any]] = []
    for session in sorted({r["session_date"] for r in daily}):
        values = {r["asset"]: r for r in daily if r["session_date"] == session}
        if set(values) != set(ASSETS):
            raise ValueError("DAILY_ASSET_SET")
        counts: dict[str, Any] = {
            "session_date": session,
            "weekday": next(iter(values.values()))["weekday"],
        }
        counts.update(
            {asset: int(values[asset]["distinct_expiries_by_close_minus_120s"]) for asset in ASSETS}
        )
        for weekday in ("monday", "wednesday"):
            nums = [int(r["expiry_count_" + weekday]) for r in values.values()]
            counts[weekday + "_expiry_count_min"] = min(nums)
            counts[weekday + "_expiry_count_max"] = max(nums)
        days.append(counts)
    return wide, first, days


def render(
    summary: dict[str, Any],
    wide: list[dict[str, Any]],
    first: list[dict[str, Any]],
    days: list[dict[str, Any]],
) -> str:
    def overall(period: str) -> float:
        return float(
            sum(
                r[period + "__surface_populated_cells_mean"] * r[period + "__N_origins"]
                for r in wide
            )
            / sum(r[period + "__N_origins"] for r in wide)
        )

    lines = [
        "# Vencimientos y barras: auditoría descriptiva local",
        "",
        "## Resultado principal",
        "",
        "Los seis activos ya muestran vencimientos de lunes y miércoles en la cinta válida "
        "del **26 de enero de 2026**, no del 29. En esa primera sesión aparecen los lunes "
        "2 y 9 de febrero y el miércoles 4 de febrero. En el intervalo revisado, los primeros "
        "0DTE de lunes y miércoles ocurren el **2 y 4 de febrero**, respectivamente, "
        "para los seis activos.",
        "",
        "El [aviso oficial de Nasdaq, publicado el 16 de enero de 2026](" + NOTICE + ") "
        "anuncia el inicio del listado el 26 de enero. Distinguir fecha de listado, primera "
        "operación observada y primera expiración 0DTE evita atribuir el cambio al día 29 "
        "por observar un aumento de celdas ese jueves.",
        "",
        f"Se revisaron {summary['tape_asset_sessions']} activo-sesiones de cinta "
        f"(12 de enero–13 de febrero) y {summary['panel_rows']:,} orígenes de "
        f"{summary['panel_sessions']} sesiones del panel "
        "(2 de agosto de 2024–4 de septiembre de 2026). "
        "No hubo reajustes, remuestreo, objetivos nuevos, descargas ni modificación de entradas.",
        "",
        "## Primera presencia observada",
        "",
        table(
            [
                "Activo",
                "Primera operación disponible (Nueva York)",
                "Primer lunes 0DTE",
                "Primer miércoles 0DTE",
            ],
            [
                [
                    r["asset"],
                    r["first_observed_timestamp_ny"],
                    r["first_zero_dte_monday"],
                    r["first_zero_dte_wednesday"],
                ]
                for r in first
            ],
        ),
        "",
        "La primera presencia sólo se afirma dentro del tramo acotado: las nueve sesiones "
        "revisadas hasta el 23 de enero no contienen vencimientos de lunes o miércoles; "
        "el 26 sí los contiene en todos los activos. La fecha oficial proviene del aviso, "
        "no se infiere a partir del archivo local.",
        "",
        "## Cobertura por día de semana",
        "",
        "Antes = fechas anteriores al 26 de enero; después = desde el 26, inclusive. "
        "Cada origen del panel tiene el mismo peso; no se selecciona por el objetivo ni por "
        "la máscara de evaluación. Presencia ATM = fracción finita de la celda 0–1DTE y "
        "moneyness 0.97–1.03. Las medianas 0DTE omiten únicamente "
        "valores no finitos de esa variable.",
        "",
        table(
            [
                "Día",
                "N antes / después",
                "Celdas medias antes / después",
                "ATM presente % antes / después",
                "Mediana contratos 0DTE antes / después",
            ],
            [
                [
                    DAY_NAMES[r["weekday"]],
                    f"{int(r['before__N_origins'])} / {int(r['from_date__N_origins'])}",
                    f"{r['before__surface_populated_cells_mean']:.4f} / "
                    f"{r['from_date__surface_populated_cells_mean']:.4f}",
                    f"{r['before__atm_0_1dte_presence_pct']:.4f} / "
                    f"{r['from_date__atm_0_1dte_presence_pct']:.4f}",
                    f"{r['before__zero_dte_contracts_median_finite']:.0f} / "
                    f"{r['from_date__zero_dte_contracts_median_finite']:.0f}",
                ]
                for r in wide
            ],
        ),
        "",
        f"La media global de celdas es {overall('before'):.6f} antes y "
        f"{overall('from_date'):.6f} después. Con este denominador no se reproducen "
        "exactamente las cifras propuestas de 19.5→23.5 o las medianas 31/28. "
        "La presencia ATM anterior de los miércoles tampoco es literalmente cero: "
        "incluye los días 16 de abril y 2 de julio de 2025. "
        "Martes y jueves conservan mediana 0DTE cero, "
        "lo que no significa que todos sus valores sean cero.",
        "",
        "El corte alternativo del 29 de enero y los desgloses por activo, junto con una "
        "ventana local de ±28 días, permanecen en "
        "[la tabla de cobertura completa](coverage_weekday.csv). "
        "Son comparaciones descriptivas; no identifican por sí mismas "
        "una causa del rendimiento predictivo.",
        "",
        "## Conteo diario de vencimientos distintos",
        "",
        "Unión de fechas de expiración en operaciones válidas y disponibles antes del "
        "cierre menos 120 segundos. Las dos últimas columnas muestran el rango mínimo–máximo "
        "del conteo de vencimientos de lunes/miércoles entre los seis activos, "
        "no número de operaciones.",
        "",
        table(
            ["Sesión", *ASSETS, "Lunes mín–máx", "Miércoles mín–máx"],
            [
                [
                    r["session_date"],
                    *(r[a] for a in ASSETS),
                    f"{r['monday_expiry_count_min']}–{r['monday_expiry_count_max']}",
                    f"{r['wednesday_expiry_count_min']}–{r['wednesday_expiry_count_max']}",
                ]
                for r in days
            ],
        ),
        "",
        "## Barras extremas",
        "",
        "Los dos archivos coinciden con sus hashes históricos y con sus recibos de descarga. "
        "Ambos contienen 390 minutos únicos, sin minutos regulares faltantes, duplicados, "
        "OHLCV no finito, volumen negativo ni inconsistencias high/low respecto de open/close.",
        "",
        table(
            [
                "Evento (inicio de barra, Nueva York)",
                "Retorno log, pb",
                "Siguiente, pb",
                "Volumen / siguiente",
                "Mediana de volumen del día",
                "Veces la mediana",
            ],
            [
                [
                    r["asset"] + " " + r["event_bar_start_ny"],
                    f"{r['event_close_to_close_log_return_bp']:+.4f}",
                    f"{r['next_close_to_close_log_return_bp']:+.4f}",
                    f"{r['event_volume']:.0f} / {r['next_volume']:.0f}",
                    f"{r['full_session_volume_median']:.1f}",
                    f"{r['event_volume_over_session_median']:.4f} / "
                    f"{r['next_volume_over_session_median']:.4f}",
                ]
                for r in summary["bars"]
            ],
        ),
        "",
        "Retorno log en puntos básicos = 10000 × ln(cierre actual / cierre anterior). "
        "La mediana usa los 390 volúmenes de la sesión. Son los mayores retornos absolutos "
        "de sus respectivas sesiones. No hay salto de timestamp alrededor de esos minutos, "
        "pero la apertura de la barra de reversión difiere del cierre anterior: "
        "+36.2960 pb en AMZN y −21.7853 pb en TSLA. Los movimientos netos de los dos "
        "minutos son −80.3773 y +19.4756 pb, respectivamente.",
        "",
        "Esto reproduce las anomalías planteadas, pero **no demuestra** que los precios "
        "sean ejecuciones de mercado correctas: es validación interna de un único proveedor. "
        "No se atribuye ningún movimiento a una noticia, ni se justifica eliminar o corregir "
        "esas barras sin evidencia externa. No se publica ningún extracto por minuto.",
        "",
        "## Método y custodia",
        "",
        "La cinta se selecciona con el índice del productor existente. Se leen sólo "
        "identificador, activo, dos relojes, expiración, IV, tamaño, strike, tipo y NBBO. "
        "Se conserva la primera versión por max(created_at, executed_at), con orden de "
        "fuente para empates, proyectada a esos campos. Se exige IV finita en [0.03,3], "
        "bid>0, ask>bid, strike>0, tamaño>0 y tipo call/put; ejecución en horario regular, "
        "expiración no pasada y ambos relojes disponibles al cierre−120s. "
        "La unión diaria de contratos no equivale a la mediana del snapshot 0DTE del panel. "
        "Los relojes fuente siguen siendo proxies, no recepción demostrada por el cliente.",
        "",
        "[Fuentes: alias y hashes](sources.json) · [Recibo de ejecución](receipt.json) · "
        "[Proyección pública](publication_projection.json). Los hashes identifican entradas "
        "sin exponer rutas privadas; los registros por minuto se excluyen de esta proyección.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    root = ROOT / "artifacts/rp4_market_audit"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for name in ("summary.json", "coverage_weekday.csv", "expiry_daily.csv", "sources.json"):
        if sha256(root / name) != manifest["artifacts_sha256"][name]:
            raise ValueError("AUDIT_INPUT_CHANGED:" + name)
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    wide, first, days = aggregates(
        read_csv(root / "coverage_weekday.csv"), read_csv(root / "expiry_daily.csv")
    )
    payloads = {
        "coverage_public.csv": csv_bytes(wide),
        "expiry_first_observed.csv": csv_bytes(first),
        "expiry_daily_public.csv": csv_bytes(days),
        "REPORT.md": render(summary, wide, first, days).encode("utf-8"),
    }
    for name, payload in payloads.items():
        write_once(root / name, payload)
    allowed = [
        *payloads,
        "summary.json",
        "sources.json",
        "coverage_weekday.csv",
        "expiry_daily.csv",
    ]
    projection = {
        "status": "AGGREGATE_ONLY",
        "producer_sha256": sha256(Path(__file__)),
        "input_manifest_sha256": sha256(root / "manifest.json"),
        "allowed_artifacts_sha256": {name: sha256(root / name) for name in allowed},
        "excluded_local_artifacts": ["bar_event_windows.csv", "feature_daily.csv"],
        "exclusion_reason": "No minute-level provider-derived rows in the public projection.",
        "receipt_created_after_cli_exit": "receipt.json",
    }
    write_once(root / "publication_projection.json", json_bytes(projection))
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "tables": {"coverage": len(wide), "first_observed": len(first), "daily": len(days)},
                "report_sha256": sha256(root / "REPORT.md"),
                "projection_sha256": sha256(root / "publication_projection.json"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
