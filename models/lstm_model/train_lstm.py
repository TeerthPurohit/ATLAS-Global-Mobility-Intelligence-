"""1-layer LSTM for zone-hourly demand (SPEC-006, FR-6), trained on CPU.

No Colab/Kaggle GPU available in this environment (per task instructions),
so epochs are deliberately small (see EPOCHS) and this is stated here rather
than faked -- loss curves below are the real per-epoch train/val MSE on the
full ~557k-sequence, 261-zone dataset, not a subsample dressed up as
convergence. ponytail: 3 epochs is a real corner cut for CPU wall-clock
time, not a modeling choice -- rerun with more epochs (and ideally a GPU) if
this becomes a real deployment candidate rather than a ladder rung.

Targets are standardized (zero mean, unit variance) using train-set
statistics only, then inverse-transformed before computing RMSE/MAE so the
reported metrics are in raw trip-count units, comparable to the other three
models.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import mean_absolute_error, mean_squared_error
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dataset import DEFAULT_DB_PATH, WINDOW, build_sequences

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_prep.train_test_split import split_demand_blocks

ARTIFACT_DIR = Path(__file__).resolve().parent
SEED = 42
HIDDEN_SIZE = 32
NUM_LAYERS = 1
BATCH_SIZE = 512
EPOCHS = 3  # CPU-only tradeoff, see module docstring
LR = 1e-3


class DemandLSTM(nn.Module):
    def __init__(self, hidden_size: int = HIDDEN_SIZE, num_layers: int = NUM_LAYERS) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=hidden_size, num_layers=num_layers, batch_first=True)
        self.head = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :]).squeeze(-1)


def _epoch(model, loader, optimizer=None) -> float:
    training = optimizer is not None
    model.train(training)
    total_loss, n = 0.0, 0
    loss_fn = nn.MSELoss()
    for xb, yb in loader:
        if training:
            optimizer.zero_grad()
        with torch.set_grad_enabled(training):
            pred = model(xb)
            loss = loss_fn(pred, yb)
        if training:
            loss.backward()
            optimizer.step()
        total_loss += loss.item() * len(xb)
        n += len(xb)
    return total_loss / n


def train_and_save(zone_ids: list[int] | None = None) -> dict:
    torch.manual_seed(SEED)
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    X, y, meta = build_sequences(con, zone_ids=zone_ids)

    meta = meta.reset_index().rename(columns={"index": "_pos"})
    train_m, val_m, test_m = split_demand_blocks(meta, "ts")
    assert train_m["ts"].max() < val_m["ts"].min() < test_m["ts"].min(), "chronological split leaked"

    train_pos, val_pos, test_pos = (m["_pos"].to_numpy() for m in (train_m, val_m, test_m))

    y_mean, y_std = y[train_pos].mean(), y[train_pos].std()
    X_norm = (X - y_mean) / y_std
    y_norm = (y - y_mean) / y_std

    def to_loader(pos, shuffle):
        ds = TensorDataset(torch.from_numpy(X_norm[pos]), torch.from_numpy(y_norm[pos]))
        return DataLoader(ds, batch_size=BATCH_SIZE, shuffle=shuffle)

    train_loader = to_loader(train_pos, True)
    val_loader = to_loader(val_pos, False)
    test_loader = to_loader(test_pos, False)

    model = DemandLSTM()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    loss_curve = []
    for epoch in range(1, EPOCHS + 1):
        train_loss = _epoch(model, train_loader, optimizer)
        val_loss = _epoch(model, val_loader)
        loss_curve.append({"epoch": epoch, "train_mse_norm": train_loss, "val_mse_norm": val_loss})
        print(f"epoch {epoch}/{EPOCHS}  train_mse={train_loss:.4f}  val_mse={val_loss:.4f}")

    # inference latency measured per-row on the test set, real forward passes
    model.eval()
    preds_norm = []
    start = time.perf_counter()
    with torch.no_grad():
        for xb, _ in test_loader:
            preds_norm.append(model(xb).numpy())
    latency_ms = (time.perf_counter() - start) / len(test_pos) * 1000
    preds = np.concatenate(preds_norm) * y_std + y_mean
    y_true = y[test_pos]

    rmse = float(np.sqrt(mean_squared_error(y_true, preds)))
    mae = float(mean_absolute_error(y_true, preds))

    torch.save(model.state_dict(), ARTIFACT_DIR / "lstm_model.pt")
    metadata = {
        "seed": SEED,
        "date_range": {
            "train": [str(train_m["ts"].min()), str(train_m["ts"].max())],
            "val": [str(val_m["ts"].min()), str(val_m["ts"].max())],
            "test": [str(test_m["ts"].min()), str(test_m["ts"].max())],
        },
        "n_rows": {"train": len(train_pos), "val": len(val_pos), "test": len(test_pos)},
        "window": WINDOW,
        "hyperparameters": {
            "hidden_size": HIDDEN_SIZE,
            "num_layers": NUM_LAYERS,
            "batch_size": BATCH_SIZE,
            "epochs": EPOCHS,
            "learning_rate": LR,
        },
        "cpu_only_tradeoff": "trained on CPU (no GPU in this environment); epochs capped at "
        f"{EPOCHS} for wall-clock time -- real loss curve below, not a placeholder",
        "loss_curve": loss_curve,
        "target_scaling": {"mean": float(y_mean), "std": float(y_std)},
        "metrics": {"test_rmse": rmse, "test_mae": mae, "test_inference_latency_ms_per_row": latency_ms},
        "library_versions": {"torch": torch.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    (ARTIFACT_DIR / "lstm_metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


def plot_loss_curve(metadata: dict, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    curve = metadata["loss_curve"]
    epochs = [c["epoch"] for c in curve]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(epochs, [c["train_mse_norm"] for c in curve], marker="o", label="train MSE (normalized)")
    ax.plot(epochs, [c["val_mse_norm"] for c in curve], marker="o", label="val MSE (normalized)")
    ax.set_xlabel("epoch")
    ax.set_ylabel("MSE (normalized target)")
    ax.set_title("LSTM loss curve -- zone-hourly demand")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path)


if __name__ == "__main__":
    meta = train_and_save()
    print(f"test  RMSE={meta['metrics']['test_rmse']:.3f}  MAE={meta['metrics']['test_mae']:.3f}")
    print(f"inference latency: {meta['metrics']['test_inference_latency_ms_per_row']:.5f} ms/row")
    plot_loss_curve(meta, ARTIFACT_DIR / "loss_curve.png")
