"""From-scratch Transformer encoder for zone-hourly demand (Phase 1, 5th
model-ladder rung, extends SPEC-006).

Same reference-library validation pattern as `algorithms/{spatial,graph,
timeseries}/` (see classical-algorithms skill): hand-roll multi-head
self-attention and the encoder block, then prove it matches
`nn.TransformerEncoderLayer`/`nn.TransformerEncoder` exactly (see
`validate_against_reference.py`). Used for real training here, not
discarded after validation, same as the other from-scratch algorithms.

Input is the same univariate 24h window as the LSTM (`lstm_model/dataset.py`,
`build_sequences`) -- one scalar (raw trip count) per timestep, no extra
engineered features, for a fair head-to-head with LSTM's FR-6 design.
"""

from __future__ import annotations

import math

import torch
from torch import nn


class MultiHeadSelfAttention(nn.Module):
    """Matches `nn.MultiheadAttention`'s self-attention computation exactly:
    combined in_proj_weight/bias (rows [0:d], [d:2d], [2d:3d] = Q, K, V),
    scaled dot-product attention per head, concat, out_proj."""

    def __init__(self, d_model: int, num_heads: int) -> None:
        super().__init__()
        if d_model % num_heads != 0:
            raise ValueError(f"d_model={d_model} not divisible by num_heads={num_heads}")
        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        self.in_proj_weight = nn.Parameter(torch.empty(3 * d_model, d_model))
        self.in_proj_bias = nn.Parameter(torch.empty(3 * d_model))
        self.out_proj = nn.Linear(d_model, d_model)
        nn.init.xavier_uniform_(self.in_proj_weight)
        nn.init.zeros_(self.in_proj_bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, D = x.shape
        qkv = torch.nn.functional.linear(x, self.in_proj_weight, self.in_proj_bias)
        q, k, v = qkv.chunk(3, dim=-1)

        def split_heads(t: torch.Tensor) -> torch.Tensor:
            return t.view(B, T, self.num_heads, self.head_dim).transpose(1, 2)

        q, k, v = split_heads(q), split_heads(k), split_heads(v)
        scores = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        attn = torch.softmax(scores, dim=-1)
        out = (attn @ v).transpose(1, 2).contiguous().view(B, T, D)
        return self.out_proj(out)


class TransformerEncoderLayer(nn.Module):
    """Matches `nn.TransformerEncoderLayer`'s default (norm_first=False,
    activation=relu) forward exactly:
        x = norm1(x + dropout1(self_attn(x)))
        x = norm2(x + dropout2(linear2(dropout(relu(linear1(x))))))
    """

    def __init__(self, d_model: int, num_heads: int, dim_feedforward: int, dropout: float) -> None:
        super().__init__()
        self.self_attn = MultiHeadSelfAttention(d_model, num_heads)
        self.linear1 = nn.Linear(d_model, dim_feedforward)
        self.linear2 = nn.Linear(dim_feedforward, d_model)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)
        self.dropout_ff = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.norm1(x + self.dropout1(self.self_attn(x)))
        ff = self.linear2(self.dropout_ff(torch.relu(self.linear1(x))))
        x = self.norm2(x + self.dropout2(ff))
        return x


class TransformerEncoder(nn.Module):
    """Sequential stack of independent `TransformerEncoderLayer`s, no final
    norm -- matches `nn.TransformerEncoder(layer, num_layers, norm=None)`."""

    def __init__(self, d_model: int, num_heads: int, num_layers: int, dim_feedforward: int, dropout: float) -> None:
        super().__init__()
        self.layers = nn.ModuleList(
            [TransformerEncoderLayer(d_model, num_heads, dim_feedforward, dropout) for _ in range(num_layers)]
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for layer in self.layers:
            x = layer(x)
        return x


class SinusoidalPositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int) -> None:
        super().__init__()
        position = torch.arange(0, max_len, dtype=torch.float32).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2, dtype=torch.float32) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[: x.size(1)]


class DemandTransformer(nn.Module):
    """input_proj (scalar -> d_model) + sinusoidal position -> encoder stack
    -> last-timestep representation -> linear head, same "last hidden state"
    convention as `lstm_model.train_lstm.DemandLSTM` for a fair comparison."""

    def __init__(
        self,
        d_model: int = 64,
        num_heads: int = 4,
        num_layers: int = 2,
        dim_feedforward: int | None = None,
        dropout: float = 0.1,
        window: int = 24,
    ) -> None:
        super().__init__()
        dim_feedforward = dim_feedforward or d_model * 4
        self.input_proj = nn.Linear(1, d_model)
        self.pos_encoding = SinusoidalPositionalEncoding(d_model, max_len=window)
        self.encoder = TransformerEncoder(d_model, num_heads, num_layers, dim_feedforward, dropout)
        self.head = nn.Linear(d_model, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_proj(x)
        x = self.pos_encoding(x)
        x = self.encoder(x)
        return self.head(x[:, -1, :]).squeeze(-1)
