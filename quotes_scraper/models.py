from __future__ import annotations

from dataclasses import dataclass


# This small model gives the rest of the project a consistent record shape for
# writing JSON, CSV, and uploading the final artifact.
@dataclass(frozen=True)
class QuoteRecord:
    quote: str
    author: str
    tags: tuple[str, ...]
