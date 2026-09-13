#!/usr/bin/env python3
"""Build the web data file for the awesome-rust-papers website.

Reads infos/*.json (the single source of truth) and generates a normalized
JSON file (papers.json) consumed by the SvelteKit frontend, written to the
directory given by the required --out argument.

Resolution rules (agreed with the data maintainers):
- Paper ID = infos file stem.
- `reference` values are resolved against exact title OR alias of any entry.
- `based` / `compared` values are resolved against:
    * the alias of entries that have an alias, or
    * the title of entries that have no alias
  Anything that does not resolve is kept as an external codename
  (e.g. "LLVM", "AFL++"), in `*External` arrays.
- Reverse relations (referencedBy / basedBy / comparedBy) and the
  collection citation count (`citedBy`) are computed here, never maintained
  by hand.
- BibTeX files are intentionally NOT parsed: author information is out of
  scope for the first version of the website.
- `addedAt` (when an entry's infos file first entered the collection) is
  derived from git history instead of being maintained by hand. Every
  infos file must be committed and the full history must be available
  (actions/checkout fetch-depth: 0); the script exits with an error
  otherwise, so builds never silently lack add dates.

Run:  python3 scripts/build-web-data.py --out <dir>
"""

import argparse
import json
import subprocess
import sys

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INFOS_DIR = PROJECT_DIR / "infos"
BIBS_DIR = PROJECT_DIR / "bibs"

RESOLVABLE_RELATION_KEYS = ("based", "compared")
EXTERNAL_SUFFIX = "External"


def load_bib(pid):
    bib_path = BIBS_DIR / f"{pid}.bib"
    if bib_path.exists():
        return bib_path.read_text().strip()
    return None


def load_entries():
    entries = {}
    for path in sorted(INFOS_DIR.glob("*.json")):
        with path.open() as f:
            entries[path.stem] = json.load(f)
    return entries


def load_added_dates():
    """Map paper id -> ISO 8601 author date of the commit that first added
    infos/<id>.json. Exits with an error when git history is unusable.
    """
    try:
        shallow = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
        )
    except OSError:
        sys.exit("git is required to resolve addedAt dates")
    if shallow.returncode != 0:
        sys.exit("addedAt dates need git history, but this is not a git repository")
    if shallow.stdout.strip() == "true":
        sys.exit(
            "addedAt dates need full git history: shallow clone detected, "
            "run `git fetch --unshallow`"
        )

    result = subprocess.run(
        [
            "git",
            "log",
            "--diff-filter=A",
            "--format=C:%aI",
            "--name-only",
            "--reverse",
            "--",
            "infos/",
        ],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"git log failed while resolving addedAt dates: {result.stderr.strip()}")

    added = {}
    current_date = None
    for line in result.stdout.splitlines():
        if line.startswith("C:"):
            current_date = line[2:]
        elif current_date and line.endswith(".json"):
            added.setdefault(Path(line).stem, current_date)
    return added


def build_lookups(entries):
    """Return (alias_map, no_alias_title_map, title_or_alias_map).

    alias_map / no_alias_title_map are used for based/compared values.
    title_or_alias_map is used for reference values.
    """
    alias_map = {}
    no_alias_title_map = {}
    title_or_alias_map = {}
    for pid, payload in entries.items():
        alias = payload.get("alias")
        title = payload["title"]
        if alias:
            alias_map[alias] = pid
        else:
            no_alias_title_map[title] = pid
        title_or_alias_map.setdefault(title, pid)
        if alias:
            title_or_alias_map.setdefault(alias, pid)
    return alias_map, no_alias_title_map, title_or_alias_map


def resolve_values(values, lookup):
    resolved = []
    external = []
    for value in values:
        pid = lookup.get(value)
        if pid is not None:
            if pid not in resolved:
                resolved.append(pid)
        elif value not in external:
            external.append(value)
    return resolved, external


def main():
    parser = argparse.ArgumentParser(
        description="Normalize infos/*.json into the web data file."
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        required=True,
        help="output directory (papers.json is written there)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_path = out_dir / "papers.json"

    entries = load_entries()
    if not entries:
        sys.exit("no infos/*.json found")

    added_dates = load_added_dates()

    uncommitted = sorted(pid for pid in entries if pid not in added_dates)
    if uncommitted:
        listing = "\n  ".join(f"infos/{pid}.json" for pid in uncommitted)
        sys.exit("infos files without a git history entry, commit them first:\n  " + listing)

    alias_map, no_alias_title_map, ref_map = build_lookups(entries)

    # First pass: resolve forward relations.
    papers = {}
    for pid, payload in entries.items():
        references, _ = resolve_values(payload.get("reference", []), ref_map)
        based_on, based_external = resolve_values(
            payload.get("based", []), {**no_alias_title_map, **alias_map}
        )
        compared_with, compared_external = resolve_values(
            payload.get("compared", []), {**no_alias_title_map, **alias_map}
        )
        papers[pid] = {
            "id": pid,
            "title": payload["title"],
            "alias": payload.get("alias"),
            "venue": payload.get("venue"),
            "year": payload["year"],
            "addedAt": added_dates.get(pid),
            "categories": list(payload.get("category", [])),
            "tags": list(payload.get("tag", [])),
            "links": {
                "link": payload.get("link"),
                "pdf": payload.get("pdf"),
                "repo": payload.get("repo"),
                "further": list(payload.get("further", [])),
            },
            "relations": {
                "references": references,
                "referencedBy": [],
                "basedOn": based_on,
                "basedOnExternal": based_external,
                "basedBy": [],
                "comparedWith": compared_with,
                "comparedWithExternal": compared_external,
                "comparedBy": [],
            },
            "citedBy": 0,
            "bib": load_bib(pid),
        }

    # Second pass: reverse relations + collection citation count.
    for pid, paper in papers.items():
        for target in paper["relations"]["references"]:
            papers[target]["relations"]["referencedBy"].append(pid)
            papers[target]["citedBy"] += 1
        for target in paper["relations"]["basedOn"]:
            papers[target]["relations"]["basedBy"].append(pid)
        for target in paper["relations"]["comparedWith"]:
            papers[target]["relations"]["comparedBy"].append(pid)

    paper_list = []
    stats = {
        "categories": {},
        "tags": {},
        "venues": {},
        "years": {},
    }
    for pid in sorted(papers):
        paper = papers[pid]
        for rel in ("referencedBy", "basedBy", "comparedBy"):
            paper["relations"][rel].sort()
        paper_list.append(paper)
        for cat in paper["categories"]:
            stats["categories"][cat] = stats["categories"].get(cat, 0) + 1
        for tag in paper["tags"]:
            stats["tags"][tag] = stats["tags"].get(tag, 0) + 1
        if paper["venue"]:
            stats["venues"][paper["venue"]] = (
                stats["venues"].get(paper["venue"], 0) + 1
            )
        year = paper["year"]
        stats["years"][year] = stats["years"].get(year, 0) + 1

    for key in stats:
        stats[key] = dict(sorted(stats[key].items(), key=lambda kv: (-kv[1], kv[0])))

    output = {
        "totalPapers": len(paper_list),
        "stats": stats,
        "papers": paper_list,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(output, ensure_ascii=False, indent=1, sort_keys=False)
    with open(out_path, "w") as f:
        f.write(payload + "\n")

    external_count = sum(
        len(p["relations"]["basedOnExternal"]) + len(p["relations"]["comparedWithExternal"])
        for p in paper_list
    )
    print(f"papers: {len(paper_list)}")
    print(f"external codenames in based/compared: {external_count}")
    print(f"addedAt dates resolved from git: {sum(1 for p in paper_list if p['addedAt'])}")
    print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
