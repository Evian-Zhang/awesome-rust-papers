"""A small, read-only interface to the collection's paper metadata.

The source of truth remains ``infos/*.json`` and ``bibs/*.bib``.  This
module only loads and normalizes that data for local analysis; it never
modifies collection files.
"""

from __future__ import annotations

import json

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Literal, Mapping

RelationKind = Literal["reference", "based", "compared"]
RELATION_KINDS: tuple[RelationKind, ...] = ("reference", "based", "compared")


@dataclass(frozen=True)
class Paper:
    """One normalized record from ``infos/<id>.json``.

    ``id`` is the info filename stem and is the collection's stable primary
    key.  Relation values retain their source representation: strings that
    name another paper by title or alias, or an external object.

    ``category`` is an ordered path from the broadest category to the most
    specific one; ``tag`` contains independent labels.  ``year`` is the
    recorded publication year used for filtering, ordering, and statistics.
    ``venue`` can identify a conference, journal, workshop, or preprint archive.

    ``link`` is the canonical paper page, usually a DOI link; ``pdf`` is a
    recorded direct PDF link.  ``repo`` can point to source code or other
    research artifacts, so its presence alone does not establish that source
    code is available.

    ``reference`` lists cited papers in this collection, omitting works outside
    it.  ``based`` records work the paper is built on.  ``compared`` records
    experimental baselines or alternative tools compared in the paper's
    evaluation, excluding related-work discussion and feature-only comparisons.
    Empty relation tuples mean no relation is recorded, not that none exists.
    """

    id: str
    title: str
    alias: str | None
    link: str | None
    pdf: str | None
    repo: str | None
    venue: str | None
    year: int
    category: tuple[str, ...]
    tag: tuple[str, ...]
    relations: Mapping[RelationKind, tuple[str, ...]]
    info_path: Path
    bib_path: Path | None

    def relation(self, kind: RelationKind) -> tuple[str, ...]:
        """Return the raw values for one kind of outgoing relation."""
        _check_relation_kind(kind)
        return self.relations[kind]


@dataclass(frozen=True)
class RelationTarget:
    """A relation value and its optional resolution in this collection."""

    value: str
    paper_id: str | None

    @property
    def is_internal(self) -> bool:
        """Whether ``value`` identifies a paper in this collection."""
        return self.paper_id is not None


class Collection:
    """A read-only view of all papers and their resolvable relations.

    Each paper's relation lists are assumed to contain unique targets,
    including when a target can be named by either its title or its alias.
    """

    def __init__(self, papers: Iterable[Paper]):
        self.papers = tuple(papers)
        self.by_id = MappingProxyType({paper.id: paper for paper in self.papers})
        if len(self.by_id) != len(self.papers):
            raise ValueError("duplicate paper id")

        by_name: dict[str, Paper] = {}
        for paper in self.papers:
            for name in (paper.title, paper.alias):
                if not name:
                    continue
                previous = by_name.setdefault(name, paper)
                if previous.id != paper.id:
                    raise ValueError(
                        f"ambiguous paper title or alias {name!r}: "
                        f"{previous.id!r} and {paper.id!r}"
                    )
        self._by_name = MappingProxyType(by_name)

        incoming: dict[RelationKind, dict[str, list[Paper]]] = {
            kind: defaultdict(list) for kind in RELATION_KINDS
        }
        for paper in self.papers:
            for kind in RELATION_KINDS:
                for value in paper.relation(kind):
                    target = self.resolve(value)
                    if target.paper_id is not None:
                        incoming[kind][target.paper_id].append(paper)
        self._incoming = {
            kind: MappingProxyType(
                {target: tuple(sources) for target, sources in targets.items()}
            )
            for kind, targets in incoming.items()
        }

    def get(self, paper_id: str) -> Paper:
        """Return a paper by stable ID, raising ``KeyError`` if it is absent."""
        return self.by_id[paper_id]

    def categories(self, papers: Iterable[Paper] | None = None) -> tuple[str, ...]:
        """Return sorted distinct category nodes, optionally for a subset."""
        return _vocabulary(papers if papers is not None else self.papers, "category")

    def tags(self, papers: Iterable[Paper] | None = None) -> tuple[str, ...]:
        """Return sorted distinct tags, optionally for a subset."""
        return _vocabulary(papers if papers is not None else self.papers, "tag")

    def venues(self, papers: Iterable[Paper] | None = None) -> tuple[str, ...]:
        """Return sorted distinct non-empty venues, optionally for a subset."""
        selected = papers if papers is not None else self.papers
        return tuple(sorted({paper.venue for paper in selected if paper.venue}))

    def resolve(self, value: str) -> RelationTarget:
        """Resolve an exact, case-sensitive title or alias when possible.

        This does not search by ID, normalize names, or perform fuzzy matching.
        Unresolved values retain their original text and have no paper ID.
        """
        paper = self._by_name.get(value)
        return RelationTarget(value=value, paper_id=paper.id if paper else None)

    def outgoing(
        self, paper: Paper | str, kind: RelationKind
    ) -> tuple[RelationTarget, ...]:
        """Return one paper's outgoing relation values and their resolution."""
        _check_relation_kind(kind)
        source = self.get(paper) if isinstance(paper, str) else paper
        return tuple(self.resolve(value) for value in source.relation(kind))

    def incoming(self, paper: Paper | str, kind: RelationKind) -> tuple[Paper, ...]:
        """Return sources targeting a collection paper; strings are paper IDs."""
        _check_relation_kind(kind)
        target_id = paper if isinstance(paper, str) else paper.id
        if target_id not in self.by_id:
            raise KeyError(target_id)
        return self._incoming[kind].get(target_id, ())

    def incoming_value(self, value: str, kind: RelationKind) -> tuple[Paper, ...]:
        """Return sources targeting an exact title, alias, or external name.

        For a resolved title or alias, include sources using either name of
        that paper.  For an external name, match the raw relation value
        exactly.  An empty result means no matching relation is recorded.
        Use ``incoming`` to look up a target by paper ID instead.
        """
        _check_relation_kind(kind)
        target = self.resolve(value)
        if target.paper_id is not None:
            return self.incoming(target.paper_id, kind)
        return tuple(paper for paper in self.papers if value in paper.relation(kind))


def load_collection(root: str | Path = ".") -> Collection:
    """Load ``infos/*.json`` and optional matching ``bibs/*.bib`` under root.

    The function is deliberately read-only.  It validates only the local
    shape required to construct the Python objects; collection-wide data
    validation remains the responsibility of the existing check scripts.
    """
    root = Path(root)
    infos_dir = root / "infos"
    bibs_dir = root / "bibs"
    if not infos_dir.is_dir():
        raise FileNotFoundError(f"missing infos directory: {infos_dir}")

    papers = []
    for info_path in sorted(infos_dir.glob("*.json")):
        try:
            raw = json.loads(info_path.read_text())
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON in {info_path}: {error}") from error
        if not isinstance(raw, dict):
            raise ValueError(f"top-level value in {info_path} must be an object")

        paper_id = info_path.stem
        bib_path = bibs_dir / f"{paper_id}.bib"
        papers.append(
            Paper(
                id=paper_id,
                title=_required_string(raw, "title", info_path),
                alias=_optional_string(raw, "alias", info_path),
                link=_optional_string(raw, "link", info_path),
                pdf=_optional_string(raw, "pdf", info_path),
                repo=_optional_string(raw, "repo", info_path),
                venue=_optional_string(raw, "venue", info_path),
                year=_required_year(raw, info_path),
                category=_string_tuple(raw, "category", info_path),
                tag=_string_tuple(raw, "tag", info_path),
                relations=MappingProxyType(
                    {
                        "reference": _string_tuple(raw, "reference", info_path),
                        "based": _string_tuple(raw, "based", info_path),
                        "compared": _string_tuple(raw, "compared", info_path),
                    }
                ),
                info_path=info_path,
                bib_path=bib_path if bib_path.is_file() else None,
            )
        )
    return Collection(papers)


def _check_relation_kind(kind: str) -> None:
    if kind not in RELATION_KINDS:
        allowed = ", ".join(RELATION_KINDS)
        raise ValueError(f"unknown relation kind {kind!r}; expected one of: {allowed}")


def _vocabulary(papers: Iterable[Paper], field: Literal["category", "tag"]) -> tuple[str, ...]:
    return tuple(sorted({value for paper in papers for value in getattr(paper, field)}))


def _required_string(raw: dict[str, object], key: str, path: Path) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{path}: {key} must be a string")
    return value


def _optional_string(raw: dict[str, object], key: str, path: Path) -> str | None:
    if key not in raw:
        return None
    value = raw[key]
    if not isinstance(value, str):
        raise ValueError(f"{path}: {key} must be a string")
    return value


def _string_tuple(raw: dict[str, object], key: str, path: Path) -> tuple[str, ...]:
    if key not in raw:
        return ()
    value = raw[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{path}: {key} must be an array of strings")
    return tuple(value)


def _required_year(raw: dict[str, object], path: Path) -> int:
    value = raw.get("year")
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{path}: year must be an integer")
    return value
