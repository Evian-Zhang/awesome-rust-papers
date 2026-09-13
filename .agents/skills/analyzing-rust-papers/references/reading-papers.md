# Reading papers

Use this guidance for authors, abstracts, technical synthesis, and PDF content.
The collection metadata and local BibTeX files are the starting evidence.

## Inspect local BibTeX

The library intentionally provides a `bib_path` rather than a BibTeX parser.
These files contain citation entries from first-party sources. Read the raw
file directly; no third-party BibTeX dependency is needed.

```python
paper = collection.get("rustbelt")
if paper.bib_path is None:
    print("No BibTeX file is recorded for this paper.")
else:
    print(paper.bib_path.read_text())
```

For authors, inspect the complete `author` field. Entries can span multiple
lines, use braces or quotes, and contain LaTeX escapes in names. Distinguish
authors from editors and names mentioned in the abstract. Consider name-order
and spelling variants when searching; a shared surname alone does not
establish that two names identify the same person.

For a collection-wide author or abstract query, consider all available
BibTeX files within the user's scope, not only papers whose titles match the
query. Inspect relevant fields in manageable batches and retain the IDs and
BibTeX paths of matches. For an individual author, count matching papers by
ID. For author rankings, state how name variants and ambiguous identities
were handled.

An absent `abstract` field or BibTeX file means the collection lacks that
evidence. It does not mean the paper has no abstract, or that its content fails
to match the topic. Report missing evidence when it affects search coverage.

## Synthesize from the available evidence

A user-requested comparison of methods or features can be synthesized from
the papers even when no `compared` edge is recorded. Identify it as your own
comparison, distinct from an experiment reported by a paper.

1. Define the comparison question and select candidates using the main skill's
   topic-search guidance.
2. Read available abstracts. Extract the dimensions relevant to the request,
   such as the research problem, technical approach, target programs, stated
   contributions, and limitations explicitly described by the source.
3. Group or compare papers using those observations, keeping each material
   statement connected to its paper ID and source. Mark your grouping as an
   interpretation when the papers do not name the categories themselves.
4. Use PDF content when the requested detail is not supported by the abstracts,
   for example experimental comparisons or precise supported language features.
   If the user restricts analysis to local records, state the evidence gap
   instead of retrieving external material.

Do not infer support for unsafe Rust, benchmark superiority, or other technical
properties solely from the presence or absence of a tag. For a progress review,
combine the publication timeline with supported changes in methods or results;
counts and relationship edges alone cannot establish technical advances.

## Obtain a usable PDF

The recorded `paper.pdf` may return a challenge page, fail to download, or
produce a file whose content cannot be extracted. A failed attempt does not
establish that no usable PDF exists.

1. If `paper.pdf` is recorded, try that link first. Check that the response is
   a PDF and that the content can be read, rather than assuming a successful
   HTTP response is sufficient.
2. If the link is missing, inaccessible, cannot be downloaded, or still cannot
   be read with available extraction tools, search arXiv using the exact title,
   DOI, or available author details.
3. Verify that the arXiv result describes the same paper using the title and,
   where available, authors and DOI. Preprint and publication years may differ;
   a year match alone does not establish identity. Check the relevant version
   when a claim depends on content that might have changed.
4. Retrieve and read the matching arXiv PDF. Cite the source actually used for
   technical claims, and continue using `paper.year` for collection statistics.
5. If neither source yields usable content, report that no usable PDF was
   obtained through the recorded link and arXiv fallback. Distinguish access
   or extraction failure from failing to find a matching paper. If network
   access is unavailable, report that limitation without claiming the search
   was completed.

Do not update the collection's PDF link or other records during retrieval.
