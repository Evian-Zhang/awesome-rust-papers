import json
import sys

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INFOS_DIR = PROJECT_DIR / 'infos'
BIBS_DIR = PROJECT_DIR / 'bibs'
TEMPLATE = PROJECT_DIR / 'README.template.md'
README = PROJECT_DIR / 'README.md'
CITATION = PROJECT_DIR / 'CITATION.bib'

PAPERS_PLACEHOLDER = '<!-- PAPERS -->'
CITATION_PLACEHOLDER = '<!-- CITATION -->'

def load_entries():
    entries = []
    for file in INFOS_DIR.iterdir():
        with file.open("r") as f:
            payload = json.load(f)
        bib = (BIBS_DIR / file.stem).with_suffix(".bib")
        payload["_bib"] = bib if bib.exists() else None
        entries.append(payload)
    return entries

def category_path(category):
    if isinstance(category, str):
        return [category]
    if isinstance(category, dict):
        key = next(iter(category))
        return [key] + category_path(category[key])
    print("Unexpected!")
    sys.exit(1)

def build_tree(entries):
    root = {"papers": [], "children": {}}
    for payload in entries:
        node = root
        for part in category_path(payload["category"]):
            node = node["children"].setdefault(part, {"papers": [], "children": {}})
        node["papers"].append(payload)
    return root

def paper_url(payload):
    for key in ("link", "pdf"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None

def render_paper(payload):
    lines = []

    title = payload["title"]
    url = payload.get("link")
    if url:
        lines.append(f"* [{title}]({url})")
    else:
        lines.append(f"* {title}")

    venue = payload.get("venue")
    year = payload["year"]
    if venue:
        publish = f"{venue} {year}"
    else:
        publish = f"{year}"
    info_line = publish

    pdf = payload.get("pdf")
    if pdf:
        info_line += f" [PDF]({pdf})"
    repo = payload.get("repo")
    if repo:
        info_line += f" [Code]({repo})"

    bib = payload.get("_bib")
    if bib:
        info_line += f" [Bib](./bibs/{bib.name})"

    lines.append(f"\n   {info_line}")

    if payload['_cited_by'] != 0:
        lines.append(f"\n   Cited by {payload['_cited_by']} papers in this awesome collection.")

    return "\n".join(lines)

def render_node(node, heading_level, title=None):
    lines = []

    if title is not None:
        lines.append(f"{'#' * heading_level} {title}")
        lines.append("")

    for payload in sorted(node["papers"], key=lambda p: (-p["year"], p.get("venue"), p["title"])):
        lines.append(render_paper(payload))
        lines.append("")

    for name, child in sorted(node["children"].items()):
        child_title = f"{name} @ {title}" if title else name
        lines.extend(render_node(child, heading_level + 1, child_title))

    return lines

def render_tree(root):
    lines = []
    for name, node in sorted(root["children"].items()):
        lines.extend(render_node(node, 3, name))
    return "\n".join(lines).rstrip() + "\n"

def paper_identifier(payload):
    return payload.get("alias", payload["title"])

def compute_cited_by(entries):
    by_identifier = {}
    for payload in entries:
        by_identifier[paper_identifier(payload)] = payload

    counts = {}
    for payload in entries:
        for ref in payload.get("reference", []):
            target = by_identifier.get(ref)
            if target is None:
                continue
            counts[paper_identifier(target)] = counts.get(paper_identifier(target), 0) + 1

    for payload in entries:
        payload["_cited_by"] = counts.get(paper_identifier(payload), 0)

def build_papers(entries):
    compute_cited_by(entries)
    return render_tree(build_tree(entries))

def main():
    template_text = TEMPLATE.read_text()

    entries = load_entries()
    papers = build_papers(entries)
    with open(CITATION, 'r') as f:
        citation = f.read().strip()

    output = template_text.replace(PAPERS_PLACEHOLDER, papers)
    output = output.replace(CITATION_PLACEHOLDER, citation)
    README.write_text(output)

    print(f"generated {README} with {len(entries)} papers")


if __name__ == "__main__":
    main()
