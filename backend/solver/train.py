"""Training pipeline for the poker solver transformer model.

Usage:
    cd backend
    python -m solver.train

Scans hand_histories/ for .txt files, parses with lex_hand,
filters to showdown hands, augments training data, and trains
the SolverTransformer model.
"""

from __future__ import annotations

import glob
import logging
import os
import sys
import time

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from app.parsers.core import group_hands
from app.parsers.lexer import lex_hand
from solver.augmentation import augment_hand
from solver.dataset import (
    TrainingExample,
    PokerDataset,
    collate_fn,
    extract_training_examples,
    hand_id_hash,
)
from solver.model import SolverTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NUM_EPOCHS = 20
BATCH_SIZE = 64
LEARNING_RATE = 1e-4
VAL_SPLIT_MOD = 10  # hand_id_hash % VAL_SPLIT_MOD == 0 -> validation
AUGMENT_TRAIN = True
CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "checkpoints")
HAND_HISTORIES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "hand_histories")


def scan_hand_files() -> list[str]:
    """Find all hand history .txt files."""
    pattern = os.path.join(HAND_HISTORIES_DIR, "*.txt")
    files = sorted(glob.glob(pattern))
    logger.info(f"Found {len(files)} hand history files")
    return files


def extract_all_examples(files: list[str]) -> tuple[list[TrainingExample], list[TrainingExample]]:
    """Parse all files and split examples into train/val sets."""
    train_examples: list[TrainingExample] = []
    val_examples: list[TrainingExample] = []
    total_hands = 0
    showdown_hands = 0

    for file_path in files:
        for hand_lines in group_hands(file_path, include_multiway=False):
            ast = lex_hand(hand_lines)
            if ast is None:
                continue

            total_hands += 1

            # Need showdown hands where villain's cards are known
            if not ast.shown_cards:
                continue

            # Must have hero hole cards
            if ast.hero_hole_cards is None:
                continue

            # Check that at least one non-hero player showed
            has_villain_show = any(name != "Hero" for name in ast.shown_cards)
            if not has_villain_show:
                continue

            showdown_hands += 1

            is_val = hand_id_hash(ast.hand_id) % VAL_SPLIT_MOD == 0

            if is_val:
                # Validation: no augmentation
                examples = extract_training_examples(ast)
                val_examples.extend(examples)
            else:
                if AUGMENT_TRAIN:
                    # Training: augment each hand
                    variants = augment_hand(ast)
                    for variant in variants:
                        examples = extract_training_examples(variant)
                        train_examples.extend(examples)
                else:
                    examples = extract_training_examples(ast)
                    train_examples.extend(examples)

    logger.info(f"Total hands parsed: {total_hands}")
    logger.info(f"Showdown hands with villain cards: {showdown_hands}")
    logger.info(f"Training examples: {len(train_examples)}")
    logger.info(f"Validation examples: {len(val_examples)}")

    return train_examples, val_examples


def train() -> None:
    """Main training loop."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    # Scan and extract
    files = scan_hand_files()
    if not files:
        logger.error(f"No hand history files found in {HAND_HISTORIES_DIR}")
        sys.exit(1)

    train_examples, val_examples = extract_all_examples(files)

    if not train_examples:
        logger.error("No training examples extracted. Need showdown hands with villain cards shown.")
        sys.exit(1)

    # Build datasets
    train_dataset = PokerDataset(train_examples)
    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=0,
    )

    val_loader = None
    if val_examples:
        val_dataset = PokerDataset(val_examples)
        val_loader = DataLoader(
            val_dataset,
            batch_size=BATCH_SIZE,
            shuffle=False,
            collate_fn=collate_fn,
            num_workers=0,
        )

    # Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")
    if device.type == "cuda":
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"GPU memory: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB")
    else:
        logger.warning("CUDA not available -- training on CPU (will be slow)")

    model = SolverTransformer().to(device)
    param_count = sum(p.numel() for p in model.parameters())
    logger.info(f"Model parameters: {param_count:,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")

    for epoch in range(NUM_EPOCHS):
        epoch_start = time.time()

        # Training
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for batch in train_loader:
            batch_gpu = {k: v.to(device) for k, v in batch.items()}
            labels = batch_gpu.pop("labels")

            logits = model(batch_gpu)
            loss = criterion(logits, labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * labels.size(0)
            preds = logits.argmax(dim=-1)
            train_correct += (preds == labels).sum().item()
            train_total += labels.size(0)

        avg_train_loss = train_loss / max(train_total, 1)
        train_acc = train_correct / max(train_total, 1)

        # Validation
        avg_val_loss = 0.0
        val_acc = 0.0
        if val_loader:
            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0

            with torch.no_grad():
                for batch in val_loader:
                    batch_gpu = {k: v.to(device) for k, v in batch.items()}
                    labels = batch_gpu.pop("labels")

                    logits = model(batch_gpu)
                    loss = criterion(logits, labels)

                    val_loss += loss.item() * labels.size(0)
                    preds = logits.argmax(dim=-1)
                    val_correct += (preds == labels).sum().item()
                    val_total += labels.size(0)

            avg_val_loss = val_loss / max(val_total, 1)
            val_acc = val_correct / max(val_total, 1)

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
    if not val_loader:
        best_path = os.path.join(CHECKPOINT_DIR, "best.pt")
        torch.save(model.state_dict(), best_path)
        logger.info("Saved final model as best (no validation set)")

    logger.info("Training complete!")


if __name__ == "__main__":
    train()
