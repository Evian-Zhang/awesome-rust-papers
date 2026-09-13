# Contributing to Awesome Rust Papers

All collection data lives in `infos/<id>.json` (metadata) and `bibs/<id>.bib`
(citation). The README and the website are generated from these files, so edit
the data — not the generated output.

## Scope

* One entry per academic paper (conference, journal, workshop, preprint, or
  technical report) about the Rust programming language, its ecosystem, or
  tools and techniques around it. arXiv and CoRR preprints are included only
  once they have attracted a certain number of citations.
* Every entry must be verifiable: an official link and/or an openly accessible
  PDF, plus the BibTeX entry when one exists.
* If you use an LLM to generate an entry, you must manually verify that every
  piece of information is correct.

## Repository layout

| Path | Purpose |
| --- | --- |
| `infos/<id>.json` | Metadata for one paper — the single source of truth |
| `bibs/<id>.bib` | BibTeX for the same paper |
| `assertion.toml` | Documented exceptions (`no_bib`, `no_venue`) |
| `scripts/` | Format checks and generators |
| `awesome_rust_papers/` | Read-only Python library used by AI agents |

`<id>` is the file name stem, for example `aeneas` or
`rust-for-linux-empirical`. Pick a short, lowercase, hyphen-separated name,
usually the tool or system name. It must be unique and permanent — the website
uses it as the paper's identifier — and the `.bib` file uses the same stem.

## Adding a paper

1. Choose an `<id>`.
2. Add `infos/<id>.json` — see the key reference below.
3. Add `bibs/<id>.bib` with the BibTeX downloaded from the first-party source
   — the page the DOI resolves to, or the arXiv page for preprints. If the
   source offers no BibTeX, list the paper under `no_bib` in `assertion.toml`
   instead.
4. Regenerate the README: `python3 scripts/generate-readme.py`.
5. Run the checks (see [Checks](#checks)).
6. Open a pull request.

If the paper has been accepted but not yet published, please wait until the
published version is out before opening a pull request — the final venue,
year, title, and citation can still change.

## `infos/<id>.json` key reference

All keys are optional except `title` and `year`; unknown keys are rejected by
the format check.

| Key | Type | What to write |
| --- | --- | --- |
| `title` | string | Full official title |
| `alias` | string | Short display name, usually the tool/system |
| `year` | integer | Year of the official publication |
| `venue` | string | Venue short name |
| `link` | string | Canonical page, usually a DOI link |
| `pdf` | string | Openly accessible PDF |
| `repo` | string | Code or artifact repository |
| `further` | array of strings | Further reading links (rarely used) |
| `category` | array of strings | One hierarchical topic path |
| `tag` | array of strings | Independent labels |
| `reference` | array of strings | Collection papers cited by this paper |
| `based` | array of strings | Work this paper is based on |
| `compared` | array of strings | Work this paper compares with |

### `title`

The full title as published, for example
`"Aeneas: Rust Verification by Functional Translation"`. It is used for display
and is one of the two ways other entries reference this paper (see
[`reference`](#reference)).

### `alias`

A short, widely used name — usually the tool or system the paper introduces,
for example `"Aeneas"` or `"Verus"`. When set, the website displays the alias
instead of the title. Other entries must use the alias in `based` / `compared`;
the full title of a paper that has an alias does not resolve there.

Only add an alias when the paper introduces a tool or system that has a name.
If the paper does not propose one, or the tool or system is unnamed, omit the
key.

### `year`

The year of the conference or journal the paper belongs to, not necessarily
the year in its BibTeX entry. The two can differ: a TASE 2026 paper may carry
`year = {2027}` in its BibTeX but is recorded as `2026`; a journal article
published online in 2017 that belongs to a 2018 issue is recorded as `2018`.

If a preprint was later published, use the published version's year and venue.

### `venue`

The commonly used short name, for example `"PLDI"`, `"ICSE"`, `"OOPSLA"`,
`"ICLR"`, `"ACM TOSEM"`, `"IEEE S&P"`, or `"arXiv"` for preprints. Reuse the
spelling already used for the same venue. Omit the key when the paper has no
venue, and add its title under `no_venue` in `assertion.toml`.

### `link`

Canonical page for the paper. Prefer a DOI link (`https://doi.org/...`);
otherwise use the publisher page or the arXiv abstract page. Only add links
that resolve.

### `pdf`

Direct link to a publicly available PDF: readers must be able to open it
without a subscription, purchase, or login. Prefer the one provided by the
first-party source — the publisher page the DOI resolves to, or the arXiv page
for preprints. An author copy is acceptable when the first-party source does
not offer an open PDF. Omit the key when no public PDF exists.

### `repo`

Source code or artifact repository (GitHub, Zenodo, …) associated with the
paper or its tool.

### `category`

A single hierarchical path, from broadest to most specific:

```json
"category": ["security", "fuzzing"]
```

Exactly one path per paper. Reuse existing nodes; the current top-level nodes
are `c2rust`, `ecosystem`, `formalization`, `language`, `product`,
`program analysis`, `security`, and `verification`, with sub-nodes such as
`security/fuzzing`, `verification/proof generation`, and
`product/operating system`. Browse `infos/` for the full vocabulary before
inventing a new node.

### `tag`

Independent labels, for example `"unsafe"`, `"memory safety"`,
`"borrow checker"`, or `"LLM"`. Reuse existing tags whenever possible: if the
collection already has `"data-flow analysis"`, do not add a near-synonym such
as `"dataflow propagation"`. Browse `infos/` for the current vocabulary, match
existing spellings, and aim for 2–5 tags per paper.

### `reference`

Papers **in this collection** that this paper cites. Every value must exactly
match the `title` or the `alias` (case-sensitive) of an existing entry; the
format check rejects anything else, so works outside the collection are simply
omitted. Prefer the alias when the target has one. Never list the same paper
twice — the duplicate check treats the title and the alias of one paper as the
same target.

"Cited by" counts on the website are computed from this automatically; do not
add reverse references.

Reference lists can be filled in with the helper scripts (network access
required). Both query [OpenAlex](https://openalex.org/) and mutate `infos/` in
place — review the result before submitting:

* `python3 scripts/add-references.py --json infos/<id>.json` — the works this
  paper cites: adds every cited work that exists in the collection to this
  paper's `reference` list.
* `python3 scripts/add-citing-references.py --json infos/<id>.json` — the works
  citing this paper: adds this paper to the `reference` list of every matching
  collection entry.

Both resolve the paper by its DOI, falling back to a title search, and print
match scores for review.

### `based`

Work this paper is built on: the tools, systems, or formalisms it directly
extends. A value may be

* an entry in this collection — use its `alias` if it has one, otherwise its
  exact `title`; or
* an external name such as `"TLA+"` or `"LLVM"`, kept as an unlinked label.

### `compared`

Work the paper compares against in its evaluation — experimental baselines and
alternative tools. Related work discussed in prose, or tools compared only at
the feature level, does not count. Same rules as [`based`](#based).

The same paper may appear in `reference` and in `based` / `compared`: citing it
and building on it are independent facts.

### `further`

Supplementary links, shown as "Further reading" on the website. This key is
rarely used: its main purpose is the extended journal version of a conference
paper. The journal version is not added as a separate entry — put its link
here, under the conference paper, instead. The main publication belongs in
`link`, not here.

## BibTeX (`bibs/<id>.bib`)

* One file per paper, named `<id>.bib` to match the info file.
* Download the entry directly from the first-party source and paste it as-is:
  the page the DOI resolves to (ACM DL, IEEE Xplore, Springer, …), or the
  arXiv page for preprints. Do not copy entries from aggregators or reference
  managers (Google Scholar, Semantic Scholar, DBLP, …), and do not write or
  reformat one by hand.
* Papers without an official citation get no `.bib` file; list them under
  `no_bib` in `assertion.toml` instead.

## `assertion.toml`

Documented exceptions:

```toml
no_bib = [
    # NDSS paper, no official citation
    "Cross-Language Attacks",
]
no_venue = [
    # No venue found
    "Patina: A Formalization of the Rust Programming Language",
]
```

* `no_bib` — titles (exact strings) of papers that intentionally have no
  `.bib` file.
* `no_venue` — titles of papers that have no venue.

Add a short comment giving the reason.

## Checks

Run these from the repository root before opening a pull request:

```bash
python3 scripts/info-format-check.py
python3 scripts/info-bib-consistency-check.py
python3 scripts/info-duplicate-reference-check.py
```

* `info-format-check.py` — allowed keys, value types, and that every
  `reference` resolves to an existing entry.
* `info-bib-consistency-check.py` — every entry has a matching `.bib` unless
  listed in `no_bib`, and there are no orphan `.bib` files.
* `info-duplicate-reference-check.py` — no duplicate `reference` values,
  including the same paper referenced by both its title and its alias.

These checks run in CI on every push and pull request.

## Style

* JSON files use 2-space indentation (Python `json.dump(..., indent=2)` style)
  and UTF-8; the helper scripts in `scripts/` write this format.
* There is no enforced key order, but grouping related keys (links together,
  relations together) reads well.
* `README.md` is generated from `README.template.md` and `infos/` by
  `scripts/generate-readme.py`, and the website data is generated by
  `scripts/build-web-data.py`. Do not edit generated output by hand.

## License

This repository is licensed under [CC BY 4.0](./LICENSE). By contributing, you
agree that your contributions are released under the same license.
