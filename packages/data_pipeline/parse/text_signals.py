from __future__ import annotations

import re
from functools import lru_cache
from typing import Mapping, Sequence


SignalAliases = Mapping[str, Sequence[str]]


def contains_signal(text: str, signal: str, *, aliases: Sequence[str] = ()) -> bool:
    """Return whether text contains a boundary-safe signal or an explicit alias."""
    candidates = (signal, *aliases)
    return any(_signal_pattern(candidate).search(text) is not None for candidate in candidates)


def matching_signals(
    text: str,
    signals: Sequence[str],
    *,
    aliases: SignalAliases | None = None,
) -> list[str]:
    """Return canonical signals found in text while preserving input order."""
    aliases = aliases or {}
    return [
        signal
        for signal in signals
        if contains_signal(text, signal, aliases=aliases.get(signal, ()))
    ]


@lru_cache(maxsize=512)
def _signal_pattern(signal: str) -> re.Pattern[str]:
    normalized = signal.strip()
    if not normalized:
        raise ValueError("text signals must not be empty")

    # Alphanumeric boundaries prevent short biology aliases such as LTR, ARS,
    # CEN, and TRE from matching inside unrelated longer words. Deliberate
    # families such as GFP -> EGFP must be supplied as explicit aliases.
    phrase = r"\s+".join(re.escape(part) for part in normalized.split())
    return re.compile(rf"(?<![a-z0-9]){phrase}(?![a-z0-9])", flags=re.IGNORECASE)
