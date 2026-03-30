"""Transformer model for predicting villain actions at poker decision points.

Input sequence format:
  [preflop actions..., FLOP_MARKER, card, card, card, flop actions...,
   TURN_MARKER, card, turn actions..., RIVER_MARKER, card, river actions...]

No hole cards are included. Preflop actions encode pot type and position context.
"""

import torch
import torch.nn as nn

NUM_RANKS = 13
NUM_SUITS = 4
NUM_ACTIONS = 5  # F, X, C, B, R
NUM_STREET_MARKERS = 3  # FLOP, TURN, RIVER
NUM_TOKEN_TYPES = 3  # card=0, action=1, street=2

MODEL_DIM = 64
NUM_HEADS = 4
NUM_LAYERS = 4
MAX_SEQ_LEN = 64
DROPOUT = 0.1


class SolverTransformer(nn.Module):
    """Small transformer that processes a sequence of heterogeneous tokens
    (cards, actions, street markers) and outputs a 5-way action distribution.

    Input: preflop actions + board cards with street markers + postflop actions.
    No hole cards -- the model learns pot type and position from action patterns.

    Token types:
      0 = card    -> uses rank_embed + suit_embed
      1 = action  -> uses action_embed + bet_size_proj
      2 = street  -> uses street_embed
    """

    def __init__(self) -> None:
        super().__init__()

        # Card embeddings: rank + suit summed
        self.rank_embed = nn.Embedding(NUM_RANKS, MODEL_DIM)
        self.suit_embed = nn.Embedding(NUM_SUITS, MODEL_DIM)

        # Action embedding + continuous bet size projection
        self.action_embed = nn.Embedding(NUM_ACTIONS, MODEL_DIM)
        self.bet_size_proj = nn.Linear(1, MODEL_DIM)

        # Street marker embedding
        self.street_embed = nn.Embedding(NUM_STREET_MARKERS, MODEL_DIM)

        # Token type embedding (card=0, action=1, street=2)
        self.type_embed = nn.Embedding(NUM_TOKEN_TYPES, MODEL_DIM)

        # Positional encoding
        self.pos_embed = nn.Embedding(MAX_SEQ_LEN, MODEL_DIM)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=MODEL_DIM,
            nhead=NUM_HEADS,
            dim_feedforward=MODEL_DIM * 4,
            dropout=DROPOUT,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=NUM_LAYERS,
        )

        # Output head: 5-way action prediction
        self.output_head = nn.Linear(MODEL_DIM, NUM_ACTIONS)

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        """Forward pass.

        batch keys:
            token_types:  (B, S) int  -- 0=card, 1=action, 2=street
            ranks:        (B, S) int  -- rank index (valid for cards)
            suits:        (B, S) int  -- suit index (valid for cards)
            actions:      (B, S) int  -- action index (valid for actions)
            bet_sizes:    (B, S) float -- pct of pot (valid for actions)
            street_ids:   (B, S) int  -- 0=FLOP,1=TURN,2=RIVER (valid for markers)
            padding_mask: (B, S) bool -- True for padding positions

        Returns: (B, NUM_ACTIONS) logits
        """
        bsz, seq_len = batch["token_types"].shape
        device = batch["token_types"].device
        positions = torch.arange(seq_len, device=device)

        # Build embeddings for each token type
        card_emb = self.rank_embed(batch["ranks"]) + self.suit_embed(batch["suits"])
        action_emb = self.action_embed(batch["actions"]) + self.bet_size_proj(
            batch["bet_sizes"].unsqueeze(-1)
        )
        street_emb = self.street_embed(batch["street_ids"])

        # Mask-select embedding by token type
        is_card = (batch["token_types"] == 0).unsqueeze(-1).float()
        is_action = (batch["token_types"] == 1).unsqueeze(-1).float()
        is_street = (batch["token_types"] == 2).unsqueeze(-1).float()

        token_emb = card_emb * is_card + action_emb * is_action + street_emb * is_street

        # Add type + positional embeddings
        x = token_emb + self.type_embed(batch["token_types"]) + self.pos_embed(positions)

        # Transformer encoder
        x = self.transformer(x, src_key_padding_mask=batch["padding_mask"])

        # Pool: take the last non-padded token
        seq_lens = (~batch["padding_mask"]).sum(dim=1) - 1
        last_tokens = x[torch.arange(bsz, device=device), seq_lens]

        return self.output_head(last_tokens)
