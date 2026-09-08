"""Reproduce the two synthetic logistic checks; never read empirical datasets."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY = Path(
    "private-input/0ec5f26c567f416b9513"
)
PINNED = {
    "artifacts/rp4_v3_code/models.py":
        "006ffcb3663d0c9d4f17b2302fb30cfb784631781d3559b2ba8a0b2436abbc8e",
    "artifacts/rp4_v3_a1_empty_window/specification.json":
        "930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5",
    "artifacts/rp4_v3_a2/evaluation_release.json":
        "5e3046af023c9f41380307d62537aa4e8fc7514b23d51a95ea1f960ee23fe5bb",
}
ENVIRONMENT = {
    "UV_PROJECT_ENVIRONMENT":
        "private-input/4b06809c9ca2d51ba83b",
    "OPENBLAS_NUM_THREADS": "4",
    "OMP_NUM_THREADS": "4",
    "MKL_NUM_THREADS": "4",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources() -> dict[str, str]:
    hashes = {name: digest(REPOSITORY / name) for name in PINNED}
    assert hashes == PINNED, "FROZEN_SOURCE_OR_RELEASE_HASH_DRIFT"
    return hashes


def emit(value: dict) -> None:
    print(json.dumps(value, sort_keys=True, allow_nan=False), flush=True)


def worker() -> None:
    # All Python imports are source/library reads; no parquet or result reader is used.
    for name in ("", "src", "scripts", "artifacts/rp4_code"):
        sys.path.insert(0, str(REPOSITORY / name))
    from unittest.mock import patch

    import numpy as np
    import scipy
    from artifacts.rp4_v3_code import models
    from scipy.optimize import _numdiff
    from scipy.special import expit
    from threadpoolctl import threadpool_info, threadpool_limits

    hashes = verify_sources()
    rng = np.random.default_rng(20260907)
    n, width, penalty = 2000, 139, 0.0001
    z = rng.standard_normal((n, width))
    rotation, _ = np.linalg.qr(rng.standard_normal((width, width)))
    noise = rng.random(n)
    target = (noise < expit(-0.4 + 0.8 * z[:, 0] - 0.2 * z[:, 1])).astype(float)
    registered = dict(maxiter=1000, gtol=1e-8, ftol=1e-12)
    original_minimize = models.minimize
    expected_design_hashes = {
        "well_conditioned_gaussian":
            "85c4804ae90aa9d11d1190023d21d99f8443635dcf762ddcae80ea682b4644b8",
        "ill_conditioned_rotated_spectrum":
            "23db198e90e4a08fd125907c0f3f075b22a7f93f7095e7ebed6138ea669a7875",
    }
    target_sha = hashlib.sha256(target.tobytes()).hexdigest()
    assert target_sha == "ffe70e04cb27ff2ab09012258d5c300f5a15b6e2c0a9d9265eda0a89dcff4acd"
    with threadpool_limits(limits=4, user_api="blas"):
        pools = [
            {"api": item["internal_api"], "threads": item["num_threads"]}
            for item in threadpool_info() if item["user_api"] == "blas"
        ]
        assert pools and all(item["threads"] == 4 for item in pools)
        emit(dict(event="START", scope="SYNTHETIC_ONLY", N=n, raw_columns=width,
                  lambda_value=penalty, seed=20260907, registered_options=registered,
                  pools=pools, numpy_version=np.__version__, scipy_version=scipy.__version__,
                  source_hashes=hashes))
        for label, raw in (
            ("well_conditioned_gaussian", z),
            ("ill_conditioned_rotated_spectrum",
             (z * np.geomspace(1.0, 1e-4, width)) @ rotation.T),
        ):
            pre = models._ridge_design(raw, raw[:7], [])
            fitted = pre.fitted
            captured = {}

            def capture(fun, x0, **kwargs):
                assert kwargs["method"] == "L-BFGS-B" and kwargs["jac"] is True
                assert kwargs["options"] == registered
                captured["fun"], captured["start"] = fun, x0.copy()
                result = original_minimize(fun, x0, **kwargs)
                captured["result"] = result
                return result

            started = time.perf_counter()
            # Patch only this isolated process's callable to inspect its closure/results.
            with patch.object(models, "minimize", capture):
                try:
                    coefficient, diagnostics = models._logistic_coefficient(
                        fitted, target, penalty, registered
                    )
                    outcome = "CONVERGED"
                except models.ModelConvergenceError as error:
                    diagnostics = error.diagnostics
                    coefficient = np.asarray(captured["result"].x)
                    outcome = "NOT_CONVERGED"
            elapsed = time.perf_counter() - started
            objective = captured["fun"]
            probe = rng.normal(0.0, 0.2, fitted.shape[1])
            probe[0] = -0.3
            observed_value, analytic_gradient = objective(probe)
            numeric_gradient = _numdiff.approx_derivative(
                lambda beta: objective(beta)[0], probe, method="3-point", abs_step=1e-5
            ).reshape(-1)
            logits = fitted @ probe
            independent_value = (
                np.sum(np.where(target == 1, np.logaddexp(0, -logits),
                                np.logaddexp(0, logits)))
                + penalty * np.sum(probe[1:] ** 2)
            ) / n
            expected_gradient = fitted.T @ (expit(logits) - target) / n
            expected_gradient[1:] += 2 * penalty * probe[1:] / n
            objective_error = abs(observed_value - independent_value)
            gradient_error = float(np.max(np.abs(analytic_gradient - numeric_gradient)))
            algebra_error = float(np.max(np.abs(analytic_gradient - expected_gradient)))
            assert objective_error < 1e-12 and gradient_error < 1e-8 and algebra_error < 1e-12
            final_value, final_gradient = objective(coefficient)
            assert abs(final_value - diagnostics["objective_total_divided_by_n"]) < 1e-12
            assert abs(float(np.max(np.abs(final_gradient)))
                       - diagnostics["gradient_inf_norm_objective_over_n"]) < 1e-12
            assert np.max(np.abs(fitted[:, 1:])) <= 5.0
            assert np.array_equal(fitted[:, 0], np.ones(n))
            weights = expit(fitted @ coefficient)
            hessian = fitted.T @ ((weights * (1 - weights))[:, None] * fitted) / n
            hessian += np.diag(np.r_[0.0, np.full(fitted.shape[1] - 1, 2 * penalty / n)])
            eigenvalues = np.linalg.eigvalsh(hessian)
            design_sha = hashlib.sha256(fitted.tobytes()).hexdigest()
            assert design_sha == expected_design_hashes[label], "SYNTHETIC_DESIGN_DRIFT"
            if label == "well_conditioned_gaussian":
                assert diagnostics["converged"] and diagnostics["status"] == 0
            else:
                assert not diagnostics["converged"] and diagnostics["status"] == 1
                assert diagnostics["iterations"] == 1000
                assert "ITERATIONS REACHED LIMIT" in diagnostics["message"]
            emit(dict(
                event="CASE", label=label, status=outcome, elapsed_seconds=elapsed,
                design_columns=fitted.shape[1], removed_columns=len(pre.record["removed_columns"]),
                normalized_hessian_min_eigenvalue=float(eigenvalues[0]),
                normalized_hessian_condition=float(eigenvalues[-1] / eigenvalues[0]),
                finite_difference_max_absolute_error=gradient_error,
                objective_value_algebra_error=objective_error, gradient_algebra_error=algebra_error,
                diagnostics=diagnostics, design_sha256=design_sha, target_sha256=target_sha,
            ))
    assert verify_sources() == hashes
    emit(dict(event="END", verified_cases=2, production_files_modified=0,
              real_data_reads=0, real_fits=0))


def supervisor() -> int:
    directory = Path(__file__).resolve().parent
    output, receipt_path = directory / "stdout.log", directory / "receipt.json"
    if output.exists() or receipt_path.exists():
        raise FileExistsError("AUDIT_OUTPUT_ALREADY_EXISTS; never overwrite evidence")
    before = verify_sources()
    script_hash = digest(Path(__file__))
    command = [sys.executable, "-B", "-u", str(Path(__file__).resolve()), "--worker"]
    environment = {**os.environ, **ENVIRONMENT}
    started_utc = datetime.now(UTC).isoformat()
    started = time.perf_counter()
    completed = subprocess.run(
        command, cwd=REPOSITORY, env=environment, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    with output.open("xb") as stream:
        stream.write(completed.stdout)
    receipt = dict(
        schema_version="rp4-v3-logistic-synthetic-audit-v1",
        status="PASS_SYNTHETIC_AUDIT" if completed.returncode == 0 else "FAILED_SYNTHETIC_AUDIT",
        scope="SYNTHETIC_ONLY", command=subprocess.list2cmdline(command),
        invocation="uv run --offline --frozen --no-sync python -B "
                   + subprocess.list2cmdline([str(Path(__file__).resolve())]),
        workdir=str(REPOSITORY), environment=ENVIRONMENT,
        exit_code=completed.returncode, started_utc=started_utc,
        completed_utc=datetime.now(UTC).isoformat(), elapsed_seconds=time.perf_counter() - started,
        sources_before_sha256=before, sources_after_sha256=verify_sources(),
        artifacts_sha256={str(Path(__file__).resolve()): script_hash, str(output): digest(output)},
        real_data_reads=0, real_models_fitted=0, production_files_modified=0,
        empirical_observation={
            "source": "root agent report; not independently reopened in this audit",
            "reported": "Some running primary jump fits stop at registered maxiter=1000, status=1",
            "empirical_conditioning_verified": False,
        },
        conclusion=("No demonstrated objective/gradient/stop bug in these checks. "
                    "Poor conditioning causes nonconvergence within the unchanged cap in the "
                    "synthetic case only; this does not establish the empirical cause."),
        methodology_changed=False, completed_empirical_components_refitted=False,
        RESEARCH_ONLY=True, capital_go=False,
    )
    with receipt_path.open("xb") as stream:
        stream.write((json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    sys.stdout.buffer.write(completed.stdout)
    emit(dict(event="RECEIPT", path=str(receipt_path), sha256=digest(receipt_path),
              exit_code=completed.returncode))
    return completed.returncode


if __name__ == "__main__":
    if sys.argv[1:] == ["--worker"]:
        os.environ.update(ENVIRONMENT)
        worker()
    elif not sys.argv[1:]:
        raise SystemExit(supervisor())
    else:
        raise SystemExit("Only --worker (stdout-only) or no argument (immutable receipt) is supported")
