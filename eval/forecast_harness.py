"""Forecast eval harness.

Compares a naive last-value baseline against the LightGBM forecaster on a
held-out slice of synthetic TEP data. Prints a Markdown table to stdout and
writes structured results to `eval/results/forecast.json`.

This is the M1 deliverable (SPEC section 8): "Forecast eval harness runs and prints
MAE/RMSE." PatchTST + ensemble columns land in a follow-up.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from noether_forecasting.features import FeatureSpec, build_features, train_val_test_split
from noether_forecasting.lightgbm_model import LightGBMForecaster
from noether_forecasting.synthetic_dataset import generate_offline_panel


@dataclass(frozen=True)
class TagResult:
    tag: str
    horizon_min: int
    n_test: int
    naive_mae: float
    naive_rmse: float
    lgbm_mae: float
    lgbm_rmse: float


def _evaluate_tag(panel: pd.DataFrame, tag: str, horizon_min: int) -> TagResult:
    series = panel[tag]
    spec = FeatureSpec(horizon_min=horizon_min)
    X, y = build_features(series, spec)
    X_tr, X_va, X_te, y_tr, y_va, y_te = train_val_test_split(X, y)

    # Naive: predict y(t+h) = value at t, i.e. last observed value.
    naive_pred = X_te["lag_1"].to_numpy()
    naive_mae = float(np.mean(np.abs(naive_pred - y_te)))
    naive_rmse = float(np.sqrt(np.mean((naive_pred - y_te) ** 2)))

    model = LightGBMForecaster(tag=tag, horizon_min=horizon_min)
    model.fit(X_tr, y_tr, X_va, y_va)
    lgbm_pred = np.asarray(
        model._booster.predict(  # type: ignore[union-attr]
            X_te[model._feature_cols],  # type: ignore[index]
            num_iteration=model._booster.best_iteration,  # type: ignore[union-attr]
        )
    )
    lgbm_mae = float(np.mean(np.abs(lgbm_pred - y_te)))
    lgbm_rmse = float(np.sqrt(np.mean((lgbm_pred - y_te) ** 2)))

    return TagResult(
        tag=tag,
        horizon_min=horizon_min,
        n_test=len(y_te),
        naive_mae=naive_mae,
        naive_rmse=naive_rmse,
        lgbm_mae=lgbm_mae,
        lgbm_rmse=lgbm_rmse,
    )


def _markdown_table(results: list[TagResult]) -> str:
    header = "| tag | horizon | n_test | naive MAE | naive RMSE | LGBM MAE | LGBM RMSE |\n"
    sep = "|---|---|---|---|---|---|---|\n"
    rows = "".join(
        f"| {r.tag} | {r.horizon_min}m | {r.n_test} | {r.naive_mae:.3f} | "
        f"{r.naive_rmse:.3f} | {r.lgbm_mae:.3f} | {r.lgbm_rmse:.3f} |\n"
        for r in results
    )
    return header + sep + rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Forecast eval harness")
    parser.add_argument("--tags", nargs="+", default=["XMEAS_1", "XMEAS_7", "XMEAS_13"])
    parser.add_argument("--horizon", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hours", type=int, default=24 * 7)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/results/forecast.json"),
    )
    args = parser.parse_args(argv)

    panel = generate_offline_panel(seed=args.seed, duration_hours=args.hours)
    results = [_evaluate_tag(panel, tag, args.horizon) for tag in args.tags]

    md = _markdown_table(results)
    print(md)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps([r.__dict__ for r in results], indent=2),
        encoding="utf-8",
    )
    print(f"\nwrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
