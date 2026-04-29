"""CLI: train a forecaster (LGBM, PatchTST, or ensemble) for one tag.

Used both at Docker build time and from the Makefile for local re-training.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from noether_forecasting.ensemble import EnsembleForecaster
from noether_forecasting.features import FeatureSpec, build_features, train_val_test_split
from noether_forecasting.lightgbm_model import LightGBMForecaster
from noether_forecasting.patchtst import PatchTSTForecaster
from noether_forecasting.synthetic_dataset import generate_offline_panel


def _train_lgbm(panel, tag: str, horizon: int, seed: int, output: Path) -> dict:
    series = panel[tag]
    X, y = build_features(series, FeatureSpec(horizon_min=horizon))
    X_tr, X_va, X_te, y_tr, y_va, y_te = train_val_test_split(X, y)
    model = LightGBMForecaster(
        tag=tag,
        horizon_min=horizon,
        model_version=f"lgbm-v0-seed{seed}-h{horizon}",
    )
    model.fit(X_tr, y_tr, X_va, y_va)
    model.save(output)
    preds = model.predict_batch(X_te)
    mae = float(np.mean(np.abs(preds - y_te)))
    rmse = float(np.sqrt(np.mean((preds - y_te) ** 2)))
    return {"tag": tag, "model": "lgbm", "n_test": len(y_te), "mae": mae, "rmse": rmse}


def _train_patchtst(panel, tag: str, horizon: int, seed: int, output: Path, max_steps: int) -> dict:
    series = panel[tag]
    n = len(series)
    n_test = int(n * 0.15)
    n_val = int(n * 0.15)
    n_train = n - n_val - n_test
    s_train = series.iloc[:n_train]
    s_val = series.iloc[n_train : n_train + n_val]
    model = PatchTSTForecaster(
        tag=tag,
        horizon_min=horizon,
        model_version=f"patchtst-v0-seed{seed}-h{horizon}",
        max_steps=max_steps,
    )
    model.fit(s_train, s_val)
    model.save(output)
    return {"tag": tag, "model": "patchtst", "max_steps": max_steps}


def _train_ensemble(panel, tag: str, horizon: int, seed: int, output: Path, max_steps: int) -> dict:
    series = panel[tag]
    X, y = build_features(series, FeatureSpec(horizon_min=horizon))
    X_tr, X_va, _X_te, y_tr, y_va, _y_te = train_val_test_split(X, y)

    n = len(series)
    n_test = int(n * 0.15)
    n_val = int(n * 0.15)
    n_train = n - n_val - n_test
    s_train = series.iloc[:n_train]
    s_val = series.iloc[n_train : n_train + n_val]

    lgbm = LightGBMForecaster(
        tag=tag,
        horizon_min=horizon,
        model_version=f"lgbm-v0-seed{seed}-h{horizon}",
    )
    lgbm.fit(X_tr, y_tr, X_va, y_va)

    patchtst = PatchTSTForecaster(
        tag=tag,
        horizon_min=horizon,
        model_version=f"patchtst-v0-seed{seed}-h{horizon}",
        max_steps=max_steps,
    )
    patchtst.fit(s_train, s_val)

    # Weight fitting on the validation fold.
    y_val_arr = y_va.to_numpy()
    y_val_lgbm = lgbm.predict_batch(X_va)
    y_val_patchtst = patchtst.predict_batch(series.iloc[: n_train + n_val], X_va.index)

    ensemble = EnsembleForecaster(
        tag=tag,
        horizon_min=horizon,
        model_version=f"ensemble-v0-seed{seed}-h{horizon}",
        lgbm=lgbm,
        patchtst=patchtst,
    )
    ensemble.fit_weights(y_val_arr, y_val_lgbm, y_val_patchtst)
    ensemble.save(output)
    return {
        "tag": tag,
        "model": "ensemble",
        "weight_lgbm": ensemble.weight_lgbm,
        "weight_patchtst": ensemble.weight_patchtst,
        "val_mse": ensemble._val_mse,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train a forecaster for one tag")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--horizon", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hours", type=int, default=24 * 7)
    parser.add_argument("--model", choices=["lgbm", "patchtst", "ensemble"], default="lgbm")
    parser.add_argument("--max-steps", type=int, default=100, help="PatchTST CPU budget")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    panel = generate_offline_panel(seed=args.seed, duration_hours=args.hours)
    if args.tag not in panel.columns:
        print(f"unknown tag: {args.tag}", file=sys.stderr)
        return 2

    if args.model == "lgbm":
        info = _train_lgbm(panel, args.tag, args.horizon, args.seed, args.output)
    elif args.model == "patchtst":
        info = _train_patchtst(
            panel, args.tag, args.horizon, args.seed, args.output, args.max_steps
        )
    else:
        info = _train_ensemble(
            panel, args.tag, args.horizon, args.seed, args.output, args.max_steps
        )

    print(json.dumps(info))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
