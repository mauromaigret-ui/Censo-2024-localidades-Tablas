from __future__ import annotations

from typing import Dict, List


def _tokenize(name: str) -> List[str]:
    return [t for t in name.split("_") if t]


def group_columns(columns: List[str]) -> Dict[str, List[str]]:
    tokens_map = {col: _tokenize(col) for col in columns}
    prefix_counts: Dict[str, int] = {}

    for col, tokens in tokens_map.items():
        if len(tokens) < 3:
            continue
        for length in range(2, len(tokens)):
            prefix = "_".join(tokens[:length])
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1

    groups: Dict[str, List[str]] = {}
    for col, tokens in tokens_map.items():
        best_prefix = None
        if len(tokens) >= 3:
            for length in range(2, len(tokens)):
                prefix = "_".join(tokens[:length])
                if prefix_counts.get(prefix, 0) >= 2:
                    best_prefix = prefix
            if best_prefix:
                groups.setdefault(best_prefix, []).append(col)
                continue
        groups.setdefault(col, []).append(col)

    return groups
