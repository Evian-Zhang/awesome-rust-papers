---
name: analyzing-rust-papers
description: Queries, summarizes, and analyzes papers recorded in the Awesome Rust Papers repository using its read-only Python library. Use for collection-based topic searches, venue and year statistics, paper relationships, author or abstract lookups, literature synthesis, and paper or PDF links. Not for general Rust coding help or adding paper records.
---

# Analyzing Rust Papers

Answer questions about the papers recorded in this repository. The collection
is a manually curated catalogue, not a complete bibliographic database. State
coverage and statistics in terms of the collection. Keep analysis read-only;
do not update paper records or BibTeX files.

## Run an analysis

From the repository root, run Python directly so the local package is
importable without installation. The library uses only the standard library:

```bash
python3 -B -c '
from awesome_rust_papers import load_collection

collection = load_collection(".")
print(len(collection.papers))
'
```

Extend the Python block with the selection and analysis needed for the request.
The Python examples below assume `collection` has already been loaded. If using
a script located outside the repository, run it from the repository root with
`PYTHONPATH="$PWD" python3 -B /absolute/path/analysis.py`.

## Collection interface

- `collection.papers` contains all papers; `collection.get(id)` retrieves one.
- `collection.categories(papers)`, `tags(papers)`, and `venues(papers)`
  return observed vocabulary for a subset; omit the argument for the full
  collection. Categories are individual hierarchy nodes.
- `collection.resolve(value)` returns a `RelationTarget` with the original
  `value` and an optional `paper_id`. It matches exact, case-sensitive titles
  or aliases, not IDs or approximate names.
- `collection.outgoing(paper, kind)` returns relation targets;
  `collection.incoming(paper, kind)` returns source papers.
  Both accept a `Paper` or paper ID.
- `collection.incoming_value(value, kind)` finds source papers for an exact
  title, alias, or external name. A resolved title or alias includes sources
  using either name of that paper.

| Paper field | Type and meaning |
| --- | --- |
| `id` | Stable string ID from the info filename |
| `title`, `alias` | Full published title and optional short name |
| `year` | Recorded publication year (integer) |
| `venue` | Optional short name of a conference, journal, workshop, or preprint archive |
| `category` | Tuple forming a path from broadest to most specific category |
| `tag` | Tuple of independent labels |
| `link` | Optional canonical paper page, usually a DOI link |
| `pdf` | Optional direct PDF link |
| `repo` | Optional code or research artifact repository link |
| `relations` | Raw `reference`, `based`, and `compared` values |
| `info_path`, `bib_path` | Evidence path and optional BibTeX path |

Authors and abstracts are available only through optional BibTeX fields.
There are no structured full-text, global citation count, or acceptance-status
fields. Missing metadata means it is not recorded, not that it does not exist.

## Select papers for the user's question

For an **explicit metadata query**, preserve the requested filters. Inspect
the vocabulary to check spellings, then filter with ordinary Python. Treat
venue tracks separately unless the user asks for a broader grouping: for
example, `ICSE`, `ICSE-SEIP`, and `ICSE Companion` are distinct values.

For a **research topic**, translate the user's wording into relevant collection
terms and gather candidates across category paths, tags, titles, and aliases.
A topic can cross several categories: verification-related work can also be
classified under language or formalization. A failed exact tag match does
not establish that the collection has no relevant papers.

Inspect spelling and case variants when matching topics. Observed labels may
include variants such as `Agent` / `agent` or `ownership` / `onwership`.
Use case-insensitive matching and explicitly selected variants for candidate
discovery, retaining the original labels for evidence and exact-label counts.
Do not silently merge distinct concepts or change the stored data.

Check candidates against the question; use local abstracts when metadata is
insufficient. For broad topic searches, also consider abstract matches beyond
the initial metadata candidates. Keep selected paper IDs and the inclusion
rule. Distinguish papers selected by exact metadata from a reviewed thematic
selection.

When locating a named paper, inspect IDs, titles, and aliases for candidates.
Confirm the intended paper before using its ID in relation queries. Approximate
name matching is for discovery, not for constructing new relation edges.

## Count and compare

- Use `paper.year` for year filters, ordering, and counts.
- Choose the classification level: top-level category (`paper.category[0]`
  when present), complete path, or coverage of a particular node. Parent and
  child node counts overlap; independent tag counts can overlap too. Include
  unrecorded categories when presenting a distribution of all papers.
- For a specific branch, match the path prefix, such as
  `paper.category[:2] == ("security", "fuzzing")`.
- Include zero-count years throughout a requested interval. Sort timeline
  entries by year with a stable tie-breaker such as ID.
- State a proportion's numerator and denominator. An empty denominator is
  not applicable, not 0%. Counting nonempty `repo` fields measures recorded
  code or artifact links. For a question specifically about source-code
  availability, inspect the linked contents before classifying them as code.
- For citation statistics, distinguish the selected target papers from the
  set of citing papers being counted. Apply any requested year or topic
  constraints to the appropriate side and state both scopes.
- Count papers by ID unless the user requests tool/project groups. Several
  papers can describe one tool; a shared repository does not merge papers.
- Time trends describe the collection's recorded coverage. The current year
  may be incomplete; counts alone do not establish changes across the field.
  arXiv and CoRR preprints are selected partly by citation uptake, and accepted
  but unpublished versions are not added as formal publications. Account for
  these selection rules when interpreting recent-year or preprint coverage.

For example, an explicit request for ICSE coverage from 2021 through 2026:

```python
from collections import Counter

start, end = 2021, 2026
papers = [
    paper for paper in collection.papers
    if paper.venue == "ICSE" and start <= paper.year <= end
]
counts = Counter(paper.year for paper in papers)
print({year: counts[year] for year in range(start, end + 1)})
for paper in sorted(papers, key=lambda paper: (paper.year, paper.id)):
    print(paper.year, paper.id, paper.title, paper.info_path)
```

## Analyze relationships

All three relation kinds use string targets, with different meanings:

- `reference`: papers in this collection cited by the source paper. Works
  outside the collection are omitted, so this is not its full bibliography.
- `based`: work the source paper is built on.
- `compared`: experimental baselines and alternative tools compared against
  in the source paper's evaluation. Related-work discussion and comparisons
  only at the feature level are excluded.

The same target can appear in several relation kinds; preserve each relation's
meaning. In this table, `X` is a paper or its ID:

| User question | Library call |
| --- | --- |
| Which papers does X reference? | `outgoing(X, "reference")` |
| Which papers reference X? | `incoming(X, "reference")` |
| Which papers is X based on? | `outgoing(X, "based")` |
| Which papers are based on X? | `incoming(X, "based")` |
| Which works does X compare against in its evaluation? | `outgoing(X, "compared")` |
| Which papers compare against X in their evaluations? | `incoming(X, "compared")` |

An unresolved `based` or `compared` target is an external object; keep its
original name. External targets are also queryable:

```python
for kind in ("based", "compared"):
    for paper in collection.incoming_value("C2Rust", kind):
        print(kind, paper.id, paper.title, paper.info_path)
```

Report empty results as no matching relationship recorded in the collection.
The library represents both absent relation fields and explicit empty lists
as empty tuples; neither proves that a paper has no references, foundations,
or comparison objects.

Keep relation labels and directions in the answer. An incoming reference count
is a collection count. A comparison edge does not establish superiority.
Distinguish direct edges from multi-hop paths, and track visited IDs when
traversing the graph. Relations between tools and their papers do not by
themselves establish chronological technical progress from publication years.

## Read and synthesize evidence

For author or abstract lookup, technical synthesis, or obtaining usable PDF
content, read [Reading papers](references/reading-papers.md). It covers direct
BibTeX inspection, synthesis from local abstracts, and arXiv fallback when the
recorded PDF is unavailable or cannot be read.

A request for recorded paper or PDF links can be answered directly from the
metadata. Load the retrieval guidance when obtaining or reading a PDF is
needed.

## Present the answer

Adapt to the request: provide the requested list, counts, comparison, or
synthesis with its inclusion rule. Support material claims with the relevant
paper titles, IDs, years, and info paths; include BibTeX paths or PDF sources
when those supplied the evidence.

Retain the selected IDs for reproducibility without overwhelming a short
answer with every record. Explain material coverage gaps and distinguish
recorded metadata, claims supported by abstracts or full text, and your own
inferences. Phrase negative findings as limits of the searched records.
