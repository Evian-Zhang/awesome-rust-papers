import json
import sys
import tomllib

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INFOS_DIR = PROJECT_DIR / 'infos'
ASSERTION_TOML = PROJECT_DIR / 'assertion.toml'

ALLOWED_KEYS = {
    "title",
    "alias",
    "link",
    "pdf",
    "repo",
    "further",
    "based",
    "compared",
    "venue",
    "year",
    "category",
    "tag",
    "reference"
}

# `further` lists supplementary publications, usually the journal version of
# the main entry. Each item carries its own metadata and the BibTeX file name
# under bibs/.
FURTHER_KEYS = {
    "title",
    "link",
    "pdf",
    "venue",
    "year",
    "bib",
}

FURTHER_REQUIRED_KEYS = ("title", "link", "venue", "year", "bib")

def read_asserted_no_venue():
    with ASSERTION_TOML.open("rb") as f:
        assertion = tomllib.load(f)
    return set(assertion["no_venue"])

def validate_further(items, path):
    errors = []

    if not isinstance(items, list):
        return [f"{path}: invalid further"]

    for index, item in enumerate(items):
        where = f"{path}: further[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: invalid further")
            continue

        for key in FURTHER_REQUIRED_KEYS:
            if key not in item:
                errors.append(f"{where}: invalid {key}")

        if "title" in item and not isinstance(item["title"], str):
            errors.append(f"{where}: invalid title")
        if "link" in item and not isinstance(item["link"], str):
            errors.append(f"{where}: invalid link")
        if "pdf" in item and not isinstance(item["pdf"], str):
            errors.append(f"{where}: invalid pdf")
        if "venue" in item and not isinstance(item["venue"], str):
            errors.append(f"{where}: invalid venue")
        if "year" in item and not isinstance(item["year"], int):
            errors.append(f"{where}: invalid year")
        if "bib" in item and not isinstance(item["bib"], str):
            errors.append(f"{where}: invalid bib")

        for key in sorted(set(item) - FURTHER_KEYS):
            errors.append(f"{where}: unknown key '{key}'")

    return errors

def validate(payload, path, no_venue, titles, aliases):
    errors = []

    if "title" not in payload or not isinstance(payload["title"], str):
        errors.append(f"{path}: invalid title")
    if payload["title"] not in no_venue and "venue" in payload and not isinstance(payload["venue"], str):
        errors.append(f"{path}: invalid venue")
    if "year" not in payload or not isinstance(payload["year"], int):
        errors.append(f"{path}: invalid year")

    if "alias" in payload and not isinstance(payload["alias"], str):
        errors.append(f"{path}: invalid alias")
    if "link" in payload and not isinstance(payload["link"], str):
        errors.append(f"{path}: invalid link")
    if "pdf" in payload and not isinstance(payload["pdf"], str):
        errors.append(f"{path}: invalid pdf")
    if "repo" in payload and not isinstance(payload["repo"], str):
        errors.append(f"{path}: invalid repo")
    if "further" in payload:
        errors.extend(validate_further(payload["further"], path))
    if "based" in payload:
        if not isinstance(payload["based"], list) or not all(isinstance(item, str) for item in payload["based"]):
            errors.append(f"{path}: invalid base")
    if "compared" in payload:
        if not isinstance(payload["compared"], list) or not all(isinstance(item, str) for item in payload["compared"]):
            errors.append(f"{path}: invalid compared")
    if "tag" in payload:
        if not isinstance(payload["tag"], list) or not all(isinstance(item, str) for item in payload["tag"]):
            errors.append(f"{path}: invalid tag")
    if "category" in payload:
        if not isinstance(payload["category"], list) or not all(isinstance(item, str) for item in payload["category"]):
            errors.append(f"{path}: invalid category")

    if "reference" in payload:
        if not isinstance(payload["reference"], list):
            errors.append(f"{path}: invalid reference")
        for ref in payload["reference"]:
            if not isinstance(ref, str):
                errors.append(f"{path}: invalid reference")
                continue
            if ref not in aliases and ref not in titles:
                errors.append(f"{path}: invalid reference {ref}")

    for key in sorted(set(payload) - ALLOWED_KEYS):
        errors.append(f"{path}: unknown key '{key}'")

    return errors

def main():
    files = sorted(INFOS_DIR.glob("*.json"))
    no_venue = read_asserted_no_venue()

    everything_ok = True

    titles = set()
    aliases = set()
    for file in files:
        try:
            payload = json.loads(file.read_text())
        except:
            pass
        if "title" in payload:
            titles.add(payload["title"])
        if "alias" in payload:
            aliases.add(payload["alias"])

    for file in files:
        try:
            payload = json.loads(file.read_text())
        except json.JSONDecodeError as e:
            everything_ok = False
            print(f"{file}: invalid JSON: {e}")
            continue

        if not isinstance(payload, dict):
            everything_ok = False
            print(f"{file}: top-level value must be a JSON object")
            continue

        for violation in validate(payload, str(file), no_venue, titles, aliases):
            everything_ok = False
            print(f"  {violation}")

    print(f"checked {len(files)}")
    if not everything_ok:
        sys.exit(1)

    print("Everything OK!")

if __name__ == "__main__":
    main()
