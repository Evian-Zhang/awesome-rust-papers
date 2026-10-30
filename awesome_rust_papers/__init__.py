"""Read-only access to the Awesome Rust Papers collection."""

from .collection import (
    RELATION_KINDS,
    Collection,
    FurtherEntry,
    Paper,
    RelationKind,
    RelationTarget,
    load_collection,
)

__all__ = [
    "RELATION_KINDS",
    "Collection",
    "FurtherEntry",
    "Paper",
    "RelationKind",
    "RelationTarget",
    "load_collection",
]
