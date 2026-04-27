"""CLI: train a baseline LightGBM forecaster for one tag and save to disk.

Used both at Docker build time (to bake a baseline model into the inference
image) and from the Makefile for local re-training.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from noether_forecasting.features import FeatureSpec, build_features, train_val_test_split
from noether_forecasting.lightgbm_model import LightGBMForecaster
from noether_forecasting.synthetic_dataset import generate_offline_panel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train baseline LightGBM forecaster")
    parser.add_argument("--tag", required=True, help="Tag name e.g. XMEAS_1")
    parser.add_argument("--horizon", type=int, default=30, help="Forecast horizon (minutes)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hours", type=int, default=24 * 7, help="Training data hours")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    panel = generate_offline_panel(seed=args.seed, duration_hours=args.hours)
    if args.tag not in panel.columns:
        print(f"unknown tag: {args.tag}", file=sys.stderr)
        return 2

    series = panel[args.tag]
    X, y = build_features(series, FeatureSpec(horizon_min=args.horizon))
    X_tr, X_va, X_te, y_tr, y_va, y_te = train_val_test_split(X, y)

    model = LightGBMForecaster(
        tag=args.tag,
        horizon_min=args.horizon,
        model_version=f"lgbm-v0-seed{args.seed}-h{args.horizon}",
    )
    model.fit(X_tr, y_tr, X_va, y_va)
    model.save(args.output)

    # Print eval summary so the build log shows whether training worked.
    test_preds = np.asarray(
        model._booster.predict(  # type: ignore[union-attr]
            X_te[model._feature_cols],  # type: ignore[index]
            num_iteration=model._booster.best_iteration,  # type: ignore[union-attr]
        )
    )
    mae = float(np.mean(np.abs(test_preds - y_te)))
    rmse = float(np.sqrt(np.mean((test_preds - y_te) ** 2)))
    print(
        json.dumps(
            {"tag": args.tag, "horizon": args.horizon, "n_test": len(y_te), "mae": mae, "rmse": rmse}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
