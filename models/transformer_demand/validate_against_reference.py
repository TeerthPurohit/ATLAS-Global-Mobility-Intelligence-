"""Reference-library validation (classical-algorithms skill pattern):
copy PyTorch's own `nn.TransformerEncoderLayer` weights into our from-scratch
`TransformerEncoderLayer`/`TransformerEncoder`, run the same input through
both in eval mode with dropout=0, assert the outputs match to <1e-6.

Run in float64 for the comparison -- float32 accumulation error across
several stacked attention+FFN blocks would obscure whether a <1e-6 gap is
"real" or just rounding, same reasoning as gradient-checking in float64.
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transformer import TransformerEncoderLayer  # noqa: E402


def _copy_layer(ref: nn.TransformerEncoderLayer, ours: TransformerEncoderLayer) -> None:
    with torch.no_grad():
        ours.self_attn.in_proj_weight.copy_(ref.self_attn.in_proj_weight)
        ours.self_attn.in_proj_bias.copy_(ref.self_attn.in_proj_bias)
        ours.self_attn.out_proj.weight.copy_(ref.self_attn.out_proj.weight)
        ours.self_attn.out_proj.bias.copy_(ref.self_attn.out_proj.bias)
        ours.linear1.weight.copy_(ref.linear1.weight)
        ours.linear1.bias.copy_(ref.linear1.bias)
        ours.linear2.weight.copy_(ref.linear2.weight)
        ours.linear2.bias.copy_(ref.linear2.bias)
        ours.norm1.weight.copy_(ref.norm1.weight)
        ours.norm1.bias.copy_(ref.norm1.bias)
        ours.norm2.weight.copy_(ref.norm2.weight)
        ours.norm2.bias.copy_(ref.norm2.bias)


def validate_single_layer(d_model: int = 64, num_heads: int = 4, dim_feedforward: int = 256) -> float:
    torch.manual_seed(0)
    ref = nn.TransformerEncoderLayer(
        d_model, num_heads, dim_feedforward, dropout=0.0, activation="relu", batch_first=True
    ).double()
    ours = TransformerEncoderLayer(d_model, num_heads, dim_feedforward, dropout=0.0).double()
    _copy_layer(ref, ours)
    ref.eval()
    ours.eval()

    x = torch.randn(4, 24, d_model, dtype=torch.float64)
    with torch.no_grad():
        out_ref = ref(x)
        out_ours = ours(x)
    max_diff = (out_ref - out_ours).abs().max().item()
    assert max_diff < 1e-6, f"single-layer max diff {max_diff} >= 1e-6"
    return max_diff


def validate_full_stack(d_model: int = 64, num_heads: int = 4, num_layers: int = 3, dim_feedforward: int = 256) -> float:
    torch.manual_seed(1)
    ref_stack = nn.TransformerEncoder(
        nn.TransformerEncoderLayer(d_model, num_heads, dim_feedforward, dropout=0.0, activation="relu", batch_first=True),
        num_layers=num_layers,
    ).double()
    # nn.TransformerEncoder clones the given layer, so every layer starts
    # identical -- reinitialize each clone independently for a non-degenerate
    # stack, same as a real model would have.
    for layer in ref_stack.layers:
        nn.init.xavier_uniform_(layer.self_attn.in_proj_weight)
        nn.init.zeros_(layer.self_attn.in_proj_bias)
        nn.init.xavier_uniform_(layer.self_attn.out_proj.weight)
        nn.init.zeros_(layer.self_attn.out_proj.bias)
        nn.init.xavier_uniform_(layer.linear1.weight)
        nn.init.zeros_(layer.linear1.bias)
        nn.init.xavier_uniform_(layer.linear2.weight)
        nn.init.zeros_(layer.linear2.bias)

    ours_layers = [
        TransformerEncoderLayer(d_model, num_heads, dim_feedforward, dropout=0.0).double() for _ in range(num_layers)
    ]
    for ref_layer, ours_layer in zip(ref_stack.layers, ours_layers):
        _copy_layer(ref_layer, ours_layer)

    ref_stack.eval()
    for layer in ours_layers:
        layer.eval()

    x = torch.randn(4, 24, d_model, dtype=torch.float64)
    with torch.no_grad():
        out_ref = ref_stack(x)
        out_ours = x
        for layer in ours_layers:
            out_ours = layer(out_ours)
    max_diff = (out_ref - out_ours).abs().max().item()
    assert max_diff < 1e-6, f"full-stack max diff {max_diff} >= 1e-6"
    return max_diff


def demo() -> None:
    d1 = validate_single_layer()
    print(f"single-layer max diff vs nn.TransformerEncoderLayer: {d1:.2e}")
    d2 = validate_full_stack()
    print(f"{3}-layer stack max diff vs nn.TransformerEncoder:  {d2:.2e}")
    print("validate_against_reference OK: from-scratch encoder matches PyTorch's to <1e-6")


if __name__ == "__main__":
    demo()
