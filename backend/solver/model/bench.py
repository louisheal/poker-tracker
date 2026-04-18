"""Hyperparameter benchmarking script for the poker solver model.

Usage:
    cd backend
    python -m solver.model.bench --sweep model_size    # model dim/depth sweep
    python -m solver.model.bench --sweep batch_size    # batch size sweep
    python -m solver.model.bench --sweep dropout       # dropout sweep
    python -m solver.model.bench --sweep epochs        # epoch count sweep
    python -m solver.model.bench --sweep bet_mode      # % pot vs BB bet sizes
    python -m solver.model.bench --max-files 50        # override file count (default 50)
    python -m solver.model.bench --epochs 15           # override epoch count (default 15)

TODO: Stack feature sweep (--sweep stack_feature)
    Currently the model receives starting_bb (starting stack, normalized
    by /100). The model may benefit from seeing the remaining stack at each decision point
    instead of (or in addition to) the starting stack. Sweep these variants:
      - "starting"           : current behaviour — starting effective stack only
      - "remaining"           : hero's remaining uncommitted stack at the decision point
      - "starting+remaining" : both as separate features (needs 2-dim stack_proj)
      - "none"                : no stack feature at all
    This requires dataset.py changes to compute remaining_stack_bb per example and
    model changes to handle the different input dimensions. Current best val acc: 65.5%.

TODO: Label smoothing sweep (--sweep label_smoothing)
    The model is trained with hard labels (CrossEntropyLoss), but we use softmax outputs
    as probability distributions. Hard labels push the model toward overconfidence. Label
    smoothing softens targets (e.g., 0.9 correct / 0.025 others) which may produce better
    calibrated probabilities. Sweep these values:
      - 0.0   : current behaviour (hard labels)
      - 0.05  : light smoothing
      - 0.1   : moderate smoothing
      - 0.15  : heavy smoothing
      - 0.2   : aggressive smoothing
    Implementation: nn.CrossEntropyLoss(label_smoothing=X) — one-line change in train.py.

TODO: Temperature scaling sweep (--sweep temperature)
    Post-hoc calibration at inference time: divide logits by temperature T before softmax.
    T > 1 produces softer (less confident) distributions, T < 1 produces sharper ones.
    This doesn't require retraining — applied at inference in _batch_predict. Sweep:
      - 0.5   : sharper (more confident)
      - 0.75  : slightly sharper
      - 1.0   : current behaviour (no scaling)
      - 1.5   : softer
      - 2.0   : much softer
    Evaluate both accuracy AND calibration (how well probabilities match actual frequencies).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

import torch
import torch.nn as nn

from solver.model.dataset import augment_batch_gpu, batch_iterator
from solver.model.transformer import (
    MAX_SEQ_LEN,
    NUM_ACTIONS,
    NUM_RANKS,
    NUM_SUITS,
    NUM_STREET_MARKERS,
    NUM_TOKEN_TYPES,
)
from solver.model.train import load_or_extract, scan_hand_files

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class BenchTransformer(nn.Module):
    """Configurable version of SolverTransformer for benchmarking."""

    def __init__(self, model_dim=64, num_heads=4, num_layers=4, dropout=0.1,
                 bet_mode="pct"):
        super().__init__()
        self.bet_mode = bet_mode  # "pct", "bb", "both"
        self.rank_embed = nn.Embedding(NUM_RANKS, model_dim)
        self.suit_embed = nn.Embedding(NUM_SUITS, model_dim)
        self.action_embed = nn.Embedding(NUM_ACTIONS, model_dim)
        self.bet_size_proj = nn.Linear(1, model_dim)
        if bet_mode == "both":
            self.bet_bb_proj = nn.Linear(1, model_dim)
        self.street_embed = nn.Embedding(NUM_STREET_MARKERS, model_dim)
        self.type_embed = nn.Embedding(NUM_TOKEN_TYPES, model_dim)
        self.pos_embed = nn.Embedding(MAX_SEQ_LEN, model_dim)
        self.stack_proj = nn.Linear(1, model_dim)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=model_dim,
            nhead=num_heads,
            dim_feedforward=model_dim * 4,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer, num_layers=num_layers, enable_nested_tensor=False
        )
        self.output_head = nn.Linear(model_dim, NUM_ACTIONS)

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        bsz, seq_len = batch["token_types"].shape
        device = batch["token_types"].device
        positions = torch.arange(seq_len, device=device)

        card_emb = self.rank_embed(batch["ranks"]) + self.suit_embed(batch["suits"])

        # Bet size embedding depends on mode
        if self.bet_mode == "bb":
            bet_input = batch["bet_sizes_bb"].unsqueeze(-1)
        else:
            bet_input = batch["bet_sizes"].unsqueeze(-1)
        action_emb = self.action_embed(batch["actions"]) + self.bet_size_proj(bet_input)
        if self.bet_mode == "both":
            action_emb = action_emb + self.bet_bb_proj(batch["bet_sizes_bb"].unsqueeze(-1))

        street_emb = self.street_embed(batch["street_ids"])

        is_card = (batch["token_types"] == 0).unsqueeze(-1).float()
        is_action = (batch["token_types"] == 1).unsqueeze(-1).float()
        is_street = (batch["token_types"] == 2).unsqueeze(-1).float()

        token_emb = card_emb * is_card + action_emb * is_action + street_emb * is_street
        pad_mask = batch["padding_mask"].unsqueeze(-1).float()
        token_emb = token_emb * (1.0 - pad_mask)

        x = token_emb + self.type_embed(batch["token_types"]) + self.pos_embed(positions)
        if "stack_sizes" in batch:
            stack_emb = self.stack_proj(batch["stack_sizes"].unsqueeze(-1))
            x = x + stack_emb.unsqueeze(1)
        x = self.transformer(x, src_key_padding_mask=batch["padding_mask"])

        seq_lens = (~batch["padding_mask"]).sum(dim=1) - 1
        last_tokens = x[torch.arange(bsz, device=device), seq_lens]
        return self.output_head(last_tokens)


def run_single(
    train_data, val_data, device,
    model_dim=64, num_heads=4, num_layers=4, dropout=0.1,
    lr=1e-3, batch_size=2048, num_epochs=15, grad_clip=1.0,
    bet_mode="pct", label=""
):
    """Train one configuration and return results."""
    model = BenchTransformer(model_dim, num_heads, num_layers, dropout,
                             bet_mode=bet_mode).to(device)
    param_count = sum(p.numel() for p in model.parameters())

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    has_val = val_data["labels"].shape[0] > 0

    best_val_loss = float("inf")
    best_val_acc = 0.0
    best_epoch = 0
    total_time = 0.0

    for epoch in range(num_epochs):
        epoch_start = time.time()

        # Train
        model.train()
        train_loss_sum = torch.zeros(1, device=device)
        train_correct = torch.zeros(1, device=device, dtype=torch.long)
        train_total = 0

        for batch in batch_iterator(train_data, batch_size, shuffle=True):
            batch = augment_batch_gpu(batch)
            labels = batch.pop("labels")
            logits = model(batch)
            loss = criterion(logits, labels)
            optimizer.zero_grad()
            loss.backward()
            if grad_clip:
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)
            optimizer.step()
            train_loss_sum += loss.detach() * labels.size(0)
            train_correct += (logits.argmax(dim=-1) == labels).sum()
            train_total += labels.size(0)

        avg_train_loss = train_loss_sum.item() / max(train_total, 1)
        train_acc = train_correct.item() / max(train_total, 1)

        # Validate
        avg_val_loss = 0.0
        val_acc = 0.0
        if has_val:
            model.eval()
            val_loss_sum = torch.zeros(1, device=device)
            val_correct = torch.zeros(1, device=device, dtype=torch.long)
            val_total = 0
            with torch.no_grad():
                for batch in batch_iterator(val_data, batch_size, shuffle=False):
                    labels = batch.pop("labels")
                    logits = model(batch)
                    loss = criterion(logits, labels)
                    val_loss_sum += loss * labels.size(0)
                    val_correct += (logits.argmax(dim=-1) == labels).sum()
                    val_total += labels.size(0)
            avg_val_loss = val_loss_sum.item() / max(val_total, 1)
            val_acc = val_correct.item() / max(val_total, 1)

            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                best_val_acc = val_acc
                best_epoch = epoch + 1

        elapsed = time.time() - epoch_start
        total_time += elapsed

        logger.info(
            f"[{label}] Epoch {epoch+1}/{num_epochs} "
            f"train={avg_train_loss:.4f}/{train_acc:.3f} "
            f"val={avg_val_loss:.4f}/{val_acc:.3f} ({elapsed:.1f}s)"
        )

    return {
        "label": label,
        "params": param_count,
        "best_val_loss": best_val_loss,
        "best_val_acc": best_val_acc,
        "best_epoch": best_epoch,
        "final_val_loss": avg_val_loss,
        "final_val_acc": val_acc,
        "total_time": total_time,
        "sec_per_epoch": total_time / num_epochs,
    }


def get_sweep_configs(sweep_type: str, num_epochs: int):
    """Return list of (kwargs, label) for each sweep type."""
    base = dict(model_dim=96, num_heads=4, num_layers=4, dropout=0.1,
                lr=5e-4, batch_size=1024, num_epochs=num_epochs, grad_clip=1.0)

    if sweep_type == "model_size":
        configs = [
            ({**base, "model_dim": 32, "num_heads": 2, "num_layers": 2}, "Tiny-32d2L"),
            ({**base, "model_dim": 48, "num_heads": 4, "num_layers": 3}, "Small-48d3L"),
            ({**base}, "Current-96d4L"),
            ({**base, "model_dim": 96, "num_heads": 4, "num_layers": 4}, "Medium-96d4L"),
            ({**base, "model_dim": 128, "num_heads": 8, "num_layers": 6}, "Large-128d6L"),
            ({**base, "model_dim": 192, "num_heads": 8, "num_layers": 8}, "XL-192d8L"),
        ]
    elif sweep_type == "batch_size":
        configs = [
            ({**base, "batch_size": 512}, "BS-512"),
            ({**base, "batch_size": 1024}, "BS-1024"),
            ({**base}, "BS-2048"),
            ({**base, "batch_size": 4096}, "BS-4096"),
        ]
    elif sweep_type == "dropout":
        configs = [
            ({**base, "dropout": 0.0}, "Drop-0.0"),
            ({**base, "dropout": 0.05}, "Drop-0.05"),
            ({**base}, "Drop-0.1"),
            ({**base, "dropout": 0.2}, "Drop-0.2"),
            ({**base, "dropout": 0.3}, "Drop-0.3"),
        ]
    elif sweep_type == "epochs":
        configs = [
            ({**base, "num_epochs": 15}, "Ep-15"),
            ({**base, "num_epochs": 25}, "Ep-25"),
            ({**base, "num_epochs": 40}, "Ep-40"),
            ({**base, "num_epochs": 60}, "Ep-60"),
        ]
    elif sweep_type == "lr":
        configs = [
            ({**base, "lr": 2e-4}, "LR-2e-4"),
            ({**base, "lr": 5e-4}, "LR-5e-4"),
            ({**base}, "LR-1e-3"),
            ({**base, "lr": 2e-3}, "LR-2e-3"),
            ({**base, "lr": 5e-3}, "LR-5e-3"),
        ]
    elif sweep_type == "bet_mode":
        configs = [
            ({**base, "bet_mode": "pct"}, "Pct-only"),
            ({**base, "bet_mode": "bb"}, "BB-only"),
            ({**base, "bet_mode": "both"}, "Both-pct+bb"),
        ]
    else:
        raise ValueError(f"Unknown sweep type: {sweep_type}")

    return configs


def main():
    parser = argparse.ArgumentParser(description="Hyperparameter benchmarking")
    parser.add_argument("--sweep", required=True,
                        choices=["model_size", "batch_size", "dropout", "epochs", "lr", "bet_mode"],
                        help="Which hyperparameter to sweep")
    parser.add_argument("--max-files", type=int, default=50,
                        help="Number of hand history files to use (default: 50)")
    parser.add_argument("--epochs", type=int, default=15,
                        help="Epochs per run (default: 15, overridden by epochs sweep)")
    args = parser.parse_args()

    # Load data once
    files = scan_hand_files()[:args.max_files]
    train_data, val_data = load_or_extract(files, use_cache=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")
    if device.type == "cuda":
        torch.set_num_threads(1)
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")

    from solver.model.dataset import compact_data
    train_data = compact_data(train_data)
    val_data = compact_data(val_data)
    train_data = {k: v.to(device) for k, v in train_data.items()}
    val_data = {k: v.to(device) for k, v in val_data.items()}

    logger.info(f"Train: {train_data['labels'].shape[0]:,} examples, "
                f"Val: {val_data['labels'].shape[0]:,} examples")

    configs = get_sweep_configs(args.sweep, args.epochs)
    results = []

    for kwargs, label in configs:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {label}")
        logger.info(f"{'='*60}")
        result = run_single(train_data, val_data, device, label=label, **kwargs)
        results.append(result)
        # Clear GPU cache between runs
        if device.type == "cuda":
            torch.cuda.empty_cache()

    # Print summary
    print(f"\n{'='*80}")
    print(f"BENCHMARK SUMMARY: {args.sweep} sweep ({args.max_files} files)")
    print(f"{'='*80}")
    print(f"{'Config':<20} {'Params':>10} {'Best VLoss':>12} {'Best VAcc':>10} "
          f"{'Best Ep':>8} {'Sec/Ep':>8} {'Total':>8}")
    print("-" * 80)

    for r in results:
        print(f"{r['label']:<20} {r['params']:>10,} {r['best_val_loss']:>12.4f} "
              f"{r['best_val_acc']:>9.1%} {r['best_epoch']:>8} "
              f"{r['sec_per_epoch']:>7.1f}s {r['total_time']:>7.0f}s")

    # Find best
    best = min(results, key=lambda r: r["best_val_loss"])
    print(f"\nBest: {best['label']} (val_loss={best['best_val_loss']:.4f}, "
          f"val_acc={best['best_val_acc']:.1%})")


if __name__ == "__main__":
    main()
