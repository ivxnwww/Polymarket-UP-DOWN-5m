from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "seconds_remaining",
    "distance_to_strike",
    "z_score",
    "sigma_per_sqrt_second",
    "p_up_base",
    "reversal_probability",
    "up_bid",
    "up_ask",
    "down_bid",
    "down_ask",
    "spread_up",
    "spread_down",
    "data_age_ms",
    "exchange_latency_ms",
]


def time_split(df: pd.DataFrame, train_ratio: float = 0.75) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values("timestamp").reset_index(drop=True)
    cut = int(len(df) * train_ratio)
    return df.iloc[:cut].copy(), df.iloc[cut:].copy()


def train(input_csv: Path, output_model: Path) -> None:
    df = pd.read_csv(input_csv)
    df = df.dropna(subset=["result_up"])
    df["result_up"] = df["result_up"].astype(int)

    train_df, test_df = time_split(df)
    x_train = train_df[FEATURES]
    y_train = train_df["result_up"]
    x_test = test_df[FEATURES]
    y_test = test_df["result_up"]

    base_model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("logistic", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    )

    model = CalibratedClassifierCV(base_model, method="isotonic", cv=3)
    model.fit(x_train, y_train)

    proba = model.predict_proba(x_test)[:, 1]
    print("Rows train/test:", len(train_df), len(test_df))
    print("Brier:", brier_score_loss(y_test, proba))
    print("LogLoss:", log_loss(y_test, proba))
    if len(set(y_test)) > 1:
        print("ROC AUC:", roc_auc_score(y_test, proba))

    output_model.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES}, output_model)
    print("Modelo guardado en", output_model)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path, help="CSV con features y result_up")
    parser.add_argument("--output", default=Path("models/logistic_calibrated.joblib"), type=Path)
    args = parser.parse_args()
    train(args.input, args.output)


if __name__ == "__main__":
    main()
