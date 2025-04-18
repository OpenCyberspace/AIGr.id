# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Tuple

import torch
from torch import nn, Tensor


class KVCache(nn.Module):

    def __init__(
        self,
        batch_size: int,
        max_seq_len: int,
        num_heads: int,
        head_dim: int,
        dtype: torch.dtype,
    ) -> None:
        super().__init__()
        cache_shape = (batch_size, num_heads, max_seq_len, head_dim)
        self.register_buffer(
            "k_cache", torch.zeros(cache_shape, dtype=dtype), persistent=False
        )
        self.register_buffer(
            "v_cache", torch.zeros(cache_shape, dtype=dtype), persistent=False
        )
        self.batch_size = batch_size


def reset(self) -> None:
    self.k_cache.zero_()
    self.v_cache.zero_()


def update(
    self, input_pos: Tensor, k_val: Tensor, v_val: Tensor
) -> Tuple[Tensor, Tensor]:
    assert input_pos.shape[0] == k_val.shape[2]

    k_out = self.k_cache
    v_out = self.v_cache
    k_out[:, :, input_pos] = k_val
    v_out[:, :, input_pos] = v_val

    return k_out, v_out
