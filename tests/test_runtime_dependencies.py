from __future__ import annotations

import importlib.util


def test_jieba_is_available_for_sparse_and_bm25_processing() -> None:
    assert importlib.util.find_spec("jieba") is not None
