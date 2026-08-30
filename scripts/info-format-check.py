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

def category_ok(category):
    if isinstance(category, str):
        return True
    elif isinstance(category, dict):
        if len(category) != 1:
            return False
        for key, value in category.items():
            if not isinstance(key, str):
                return False
            if not category_ok(value):
                return False
        return True
    return False

def read_asserted_no_venue():
    with ASSERTION_TOML.open("rb") as f:
        assertion = tomllib.load(f)
    return set(assertion["no_venue"])

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
        if not isinstance(payload["further"], list) or not all(isinstance(item, str) for item in payload["further"]):
            errors.append(f"{path}: invalid further")
    if "base" in payload:
        if not isinstance(payload["base"], list) or not all(isinstance(item, str) for item in payload["base"]):
            errors.append(f"{path}: invalid base")
    if "compared" in payload:
        if not isinstance(payload["compared"], list) or not all(isinstance(item, str) for item in payload["compared"]):
            errors.append(f"{path}: invalid compared")
    if "tag" in payload:
        if not isinstance(payload["tag"], list) or not all(isinstance(item, str) for item in payload["tag"]):
            errors.append(f"{path}: invalid tag")

    if "category" in payload:
        if not category_ok(payload["category"]):
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
