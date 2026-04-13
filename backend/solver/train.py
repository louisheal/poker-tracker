"""Training pipeline for the poker solver transformer model.

Usage:
    cd backend
    python -m solver.train                  # full run (all files)
    python -m solver.train --max-files 20   # quick test with 20 files
    python -m solver.train --epochs 50      # override epoch count

Scans hand_histories/ for all .txt files (GG* and hhd_*), extracts
training examples from ALL heads-up postflop hands (not just showdowns),
caches to disk, and trains with on-the-fly suit + flop augmentation.
"""

from __future__ import annotations

import glob
import logging
import multiprocessing
import os
import sys
import time

import torch
import torch.nn as nn

from app.parsers.core import group_hands
from app.parsers.lexer import lex_hand
from solver.dataset import (
    TrainingExample,
    augment_batch_gpu,
    batch_iterator,
    compact_data,
    extract_training_examples,
    is_heads_up_postflop,
    hand_id_hash,
    prefetch_batch_iterator,
    tensorize_all,
)
from solver.model import SolverTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NUM_EPOCHS = 25
BATCH_SIZE = 1024
LEARNING_RATE = 1e-3
VAL_SPLIT_MOD = 10  # hand_id_hash % VAL_SPLIT_MOD == 0 -> validation
CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "checkpoints")
HAND_HISTORIES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "hand_histories")
CACHE_PATH = os.path.join(os.path.dirname(__file__), "checkpoints", "examples_cache.pt")


def scan_hand_files() -> list[str]:
    """Find all hand history .txt files."""
    pattern = os.path.join(HAND_HISTORIES_DIR, "*.txt")
    files = sorted(glob.glob(pattern))
    logger.info(f"Found {len(files)} hand history files")
    return files


NUM_PREFETCH_WORKERS = 4
NUM_PARSE_WORKERS = 8


def _parse_single_file(file_path: str) -> list[TrainingExample]:
    """Parse one file and return all training examples. Runs in a worker process."""
    examples: list[TrainingExample] = []
    for hand_lines in group_hands(file_path, include_multiway=False):
        ast = lex_hand(hand_lines)
        if ast is None:
            continue
        if not is_heads_up_postflop(ast):
            continue
        examples.extend(extract_training_examples(ast))
    return examples


def _parse_and_extract(files: list[str]) -> tuple[list[TrainingExample], list[TrainingExample]]:
    """Parse all files in parallel and split examples into train/val.

    Uses ALL heads-up postflop hands, not just showdowns.
    Hero hands: predict villain actions. Non-hero hands: predict all actions.
    """
    train_examples: list[TrainingExample] = []
    val_examples: list[TrainingExample] = []

    logger.info(f"Parsing {len(files)} files with {NUM_PARSE_WORKERS} workers...")

    with multiprocessing.Pool(NUM_PARSE_WORKERS) as pool:
        results = pool.imap_unordered(_parse_single_file, files, chunksize=8)
        done = 0
        for file_examples in results:
            done += 1
            if done % 50 == 0 or done == 1:
                total_so_far = len(train_examples) + len(val_examples)
                logger.info(f"Parsed {done}/{len(files)} files ({total_so_far} examples so far)")

            for ex in file_examples:
                if hand_id_hash(ex.hand_id) % VAL_SPLIT_MOD == 0:
                    val_examples.append(ex)
                else:
                    train_examples.append(ex)

    logger.info(f"Training examples: {len(train_examples)}")
    logger.info(f"Validation examples: {len(val_examples)}")

    return train_examples, val_examples


def load_or_extract(files: list[str], use_cache: bool = True) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
    """Load cached tensor data from disk, or parse, tensorize, and cache.

    Returns (train_data, val_data) where each is a dict of stacked tensors.
    """
    is_full_run = len(files) == len(glob.glob(os.path.join(HAND_HISTORIES_DIR, "*.txt")))
    cache_path = CACHE_PATH if is_full_run else None

    if use_cache and cache_path and os.path.isfile(cache_path):
        logger.info(f"Loading cached tensors from {cache_path}")
        data = torch.load(cache_path, weights_only=True)
        logger.info(
            f"Loaded {data['train']['labels'].shape[0]} train + "
            f"{data['val']['labels'].shape[0]} val examples from cache"
        )
        return data["train"], data["val"]

    logger.info("Parsing hand histories...")
    train_examples, val_examples = _parse_and_extract(files)

    logger.info("Tensorizing examples...")
    train_data = tensorize_all(train_examples)
    val_data = tensorize_all(val_examples)

    # Only cache if we parsed all files (not a subset)
    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        torch.save({"train": train_data, "val": val_data}, cache_path)
        logger.info(f"Cached tensors to {cache_path}")

    return train_data, val_data


def train(max_files: int | None = None, use_cache: bool = True) -> None:
    """Main training loop."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    files = scan_hand_files()
    if not files:
        logger.error(f"No hand history files found in {HAND_HISTORIES_DIR}")
        sys.exit(1)

    if max_files is not None:
        logger.info(f"Limiting to {max_files} files (of {len(files)} total)")
        files = files[:max_files]

    train_data, val_data = load_or_extract(files, use_cache=use_cache)

    if train_data["labels"].shape[0] == 0:
        logger.error("No training examples extracted. Need heads-up postflop hands.")
        sys.exit(1)

    # Device setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")
    if device.type == "cuda":
        # Limit CPU threads: our tensor ops are small (1024-row slices), so
        # parallelising them across all cores creates more overhead than benefit.
        # With 2 prefetch workers each using 1 ATen thread, we get true parallelism
        # without contention -- same pattern as DataLoader workers on Linux.
        torch.set_num_threads(1)
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    else:
        logger.warning("CUDA not available -- training on CPU (will be slow)")

    # Compact data to int8/float16 (~2.3 GB) and move to GPU
    logger.info("Compacting training data...")
    train_data = compact_data(train_data)
    val_data = compact_data(val_data)
    has_val = val_data["labels"].shape[0] > 0

    if device.type == "cuda":
        logger.info("Moving data to GPU...")
        train_data = {k: v.to(device) for k, v in train_data.items()}
        if has_val:
            val_data = {k: v.to(device) for k, v in val_data.items()}

    logger.info("Data ready.")

    model = SolverTransformer().to(device)
    param_count = sum(p.numel() for p in model.parameters())
    logger.info(f"Model parameters: {param_count:,}")
    logger.info(f"Train: {train_data['labels'].shape[0]:,} examples, "
                f"Val: {val_data['labels'].shape[0]:,} examples, "
                f"Batch size: {BATCH_SIZE}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")

    for epoch in range(NUM_EPOCHS):
        epoch_start = time.time()

        # Training -- accumulate loss/accuracy on GPU to avoid per-batch CUDA syncs
        model.train()
        train_loss_sum = torch.zeros(1, device=device)
        train_correct_sum = torch.zeros(1, device=device, dtype=torch.long)
        train_total = 0

        for batch in batch_iterator(train_data, BATCH_SIZE, shuffle=True):
            batch = augment_batch_gpu(batch)
            labels = batch.pop("labels")

            logits = model(batch)
            loss = criterion(logits, labels)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss_sum += loss.detach() * labels.size(0)
            train_correct_sum += (logits.argmax(dim=-1) == labels).sum()
            train_total += labels.size(0)

        # Single sync point per epoch
        avg_train_loss = train_loss_sum.item() / max(train_total, 1)
        train_acc = train_correct_sum.item() / max(train_total, 1)

        # Validation
        avg_val_loss = 0.0
        val_acc = 0.0
        if has_val:
            model.eval()
            val_loss_sum = torch.zeros(1, device=device)
            val_correct_sum = torch.zeros(1, device=device, dtype=torch.long)
            val_total = 0

            with torch.no_grad():
                for batch in batch_iterator(val_data, BATCH_SIZE, shuffle=False):
                    labels = batch.pop("labels")

                    logits = model(batch)
                    loss = criterion(logits, labels)

                    val_loss_sum += loss * labels.size(0)
                    val_correct_sum += (logits.argmax(dim=-1) == labels).sum()
                    val_total += labels.size(0)

            avg_val_loss = val_loss_sum.item() / max(val_total, 1)
            val_acc = val_correct_sum.item() / max(val_total, 1)

            # Save best model
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                best_path = os.path.join(CHECKPOINT_DIR, "best.pt")
                torch.save(model.state_dict(), best_path)
                logger.info(f"  Saved best model (val_loss={avg_val_loss:.4f})")

        elapsed = time.time() - epoch_start

        logger.info(
            f"Epoch {epoch + 1}/{NUM_EPOCHS} "
            f"train_loss={avg_train_loss:.4f} train_acc={train_acc:.3f} "
            f"val_loss={avg_val_loss:.4f} val_acc={val_acc:.3f} "
            f"({elapsed:.1f}s)"
        )

        # Save epoch checkpoint
        epoch_path = os.path.join(CHECKPOINT_DIR, f"epoch_{epoch + 1}.pt")
        torch.save(model.state_dict(), epoch_path)

    # If no validation was run, save final as best
    if not has_val:
        best_path = os.path.join(CHECKPOINT_DIR, "best.pt")
        torch.save(model.state_dict(), best_path)
        logger.info("Saved final model as best (no validation set)")

    logger.info("Training complete!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train the poker solver model")
    parser.add_argument("--max-files", type=int, default=None, help="Limit number of hand history files to parse")
    parser.add_argument("--epochs", type=int, default=NUM_EPOCHS, help=f"Number of training epochs (default: {NUM_EPOCHS})")
    parser.add_argument("--no-cache", action="store_true", help="Ignore cached examples and re-parse")
    args = parser.parse_args()

    if args.epochs != NUM_EPOCHS:
        NUM_EPOCHS = args.epochs

    train(max_files=args.max_files, use_cache=not args.no_cache)
