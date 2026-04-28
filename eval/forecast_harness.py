"""Forecast eval harness.

Backtests naive (last-value), LightGBM, PatchTST, and a 2-model ensemble on
a held-out slice of the synthetic TEP panel. Writes per-(model, tag) MAE,
RMSE, and SMAPE to `eval/results/forecast.json` and prints a Markdown table.

Usage:

    python -m eval.forecast_harness                  # all four models
    python -m eval.forecast_harness --skip patchtst  # smoke run, naive + LGBM only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from noether_forecasting.ensemble import EnsembleForecaster
from noether_forecasting.features import FeatureSpec, build_features, train_val_test_split
from noether_forecasting.lightgbm_model import LightGBMForecaster
from noether_forecasting.patchtst import PatchTSTForecaster
from noether_forecasting.synthetic_dataset import generate_offline_panel


@dataclass
class ModelResult:
    tag: str
    model: str
    n_test: int
    mae: float
    rmse: float
    smape: float
    extras: dict = field(default_factory=dict)


def _smape(yhat: np.ndarray, y: np.ndarray) -> float:
    eps = 1e-9
    denom = (np.abs(y) + np.abs(yhat) + eps) / 2.0
    return float(np.mean(np.abs(yhat - y) / denom) * 100.0)


def _metrics(yhat: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    mask = np.isfinite(yhat) & np.isfinite(y)
    yhat, y = yhat[mask], y[mask]
    mae = float(np.mean(np.abs(yhat - y)))
    rmse = float(np.sqrt(np.mean((yhat - y) ** 2)))
    return mae, rmse, _smape(yhat, y)


def _evaluate_tag(
    panel: pd.DataFrame,
    tag: str,
    horizon_min: int,
    skip: set[str],
    max_steps: int,
) -> list[ModelResult]:
    results: list[ModelResult] = []
    series = panel[tag]
    spec = FeatureSpec(horizon_min=horizon_min)
    X, y = build_features(series, spec)
    X_tr, X_va, X_te, y_tr, y_va, y_te = train_val_test_split(X, y)
    y_te_arr = y_te.to_numpy()

    # Naive: predict y(t+h) = value at t.
    naive_pred = X_te["lag_1"].to_numpy()
    mae, rmse, smape = _metrics(naive_pred, y_te_arr)
    results.append(
        ModelResult(tag=tag, model="naive", n_test=len(y_te), mae=mae, rmse=rmse, smape=smape)
    )

    # LightGBM.
    lgbm = LightGBMForecaster(tag=tag, horizon_min=horizon_min)
    lgbm.fit(X_tr, y_tr, X_va, y_va)
    lgbm_pred = lgbm.predict_batch(X_te)
    mae, rmse, smape = _metrics(lgbm_pred, y_te_arr)
    results.append(
        ModelResult(tag=tag, model="lgbm", n_test=len(y_te), mae=mae, rmse=rmse, smape=smape)
    )

    if "patchtst" in skip and "ensemble" in skip:
        return results

    # PatchTST trains on train+val series; evaluation uses walk-forward over X_te.index.
    n = len(series)
    n_test = int(n * 0.15)
    n_val = int(n * 0.15)
    n_train = n - n_val - n_test
    s_train = series.iloc[:n_train]
    s_val = series.iloc[n_train : n_train + n_val]

    patchtst_pred: np.ndarray | None = None
    if "patchtst" not in skip:
        patchtst = PatchTSTForecaster(tag=tag, horizon_min=horizon_min, max_steps=max_steps)
        patchtst.fit(s_train, s_val)
        patchtst_pred = patchtst.predict_batch(series.iloc[: n_train + n_val + n_test], X_te.index)
        mae, rmse, smape = _metrics(patchtst_pred, y_te_arr)
        results.append(
            ModelResult(
                tag=tag,
                model="patchtst",
                n_test=len(y_te),
                mae=mae,
                rmse=rmse,
                smape=smape,
                extras={"max_steps": max_steps},
            )
        )

    if "ensemble" not in skip and patchtst_pred is not None:
        # Weight fitting on val fold.
        y_val_lgbm = lgbm.predict_batch(X_va)
        # Best-effort: use train+val series as context for PatchTST val preds.
        y_val_patchtst = patchtst.predict_batch(series.iloc[: n_train + n_val], X_va.index)
        ensemble = EnsembleForecaster(
            tag=tag,
            horizon_min=horizon_min,
            lgbm=lgbm,
            patchtst=patchtst,
        )
        ensemble.fit_weights(y_va.to_numpy(), y_val_lgbm, y_val_patchtst)
        ens_pred = ensemble.weight_lgbm * lgbm_pred + ensemble.weight_patchtst * patchtst_pred
        mae, rmse, smape = _metrics(ens_pred, y_te_arr)
        results.append(
            ModelResult(
                tag=tag,
                model="ensemble",
                n_test=len(y_te),
                mae=mae,
                rmse=rmse,
                smape=smape,
                extras={
                    "weight_lgbm": round(ensemble.weight_lgbm, 4),
                    "weight_patchtst": round(ensemble.weight_patchtst, 4),
                },
            )
        )

    return results


def _markdown_table(results: list[ModelResult]) -> str:
    header = "| tag | model | n_test | MAE | RMSE | SMAPE % |\n|---|---|---|---|---|---|\n"
    rows = "".join(
        f"| {r.tag} | {r.model} | {r.n_test} | {r.mae:.3f} | {r.rmse:.3f} | {r.smape:.2f} |\n"
        for r in results
    )
    return header + rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Forecast eval harness")
    parser.add_argument("--tags", nargs="+", default=["XMEAS_1", "XMEAS_7", "XMEAS_13"])
    parser.add_argument("--horizon", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hours", type=int, default=24 * 7)
    parser.add_argument("--max-steps", type=int, default=100, help="PatchTST CPU budget")
    parser.add_argument(
        "--skip",
        nargs="*",
        choices=["patchtst", "ensemble"],
        default=[],
        help="Skip specific model columns (smoke runs).",
    )
    parser.add_argument("--output", type=Path, default=Path("eval/results/forecast.json"))
    args = parser.parse_args(argv)
    skip: set[str] = set(args.skip)
    if "patchtst" in skip and "ensemble" not in skip:
        # Ensemble depends on PatchTST.
        skip.add("ensemble")

    panel = generate_offline_panel(seed=args.seed, duration_hours=args.hours)
    all_results: list[ModelResult] = []
    for tag in args.tags:
        all_results.extend(_evaluate_tag(panel, tag, args.horizon, skip, args.max_steps))

    expected = (
        {"naive", "lgbm"}
        | ({"patchtst"} if "patchtst" not in skip else set())
        | ({"ensemble"} if "ensemble" not in skip else set())
    )
    seen_per_tag = {tag: {r.model for r in all_results if r.tag == tag} for tag in args.tags}
    missing = {tag: expected - models for tag, models in seen_per_tag.items()}
    incomplete = {tag: m for tag, m in missing.items() if m}
    if incomplete:
        print(
            f"FAIL: incomplete results — missing models per tag: {incomplete}",
            file=sys.stderr,
        )
        return 1

    print(_markdown_table(all_results))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "skipped": sorted(skip),
                "results": [asdict(r) for r in all_results],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
