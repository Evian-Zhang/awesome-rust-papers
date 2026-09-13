import json
import sys

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INFOS_DIR = PROJECT_DIR / 'infos'

def load_entries():
    entries = []
    for file in sorted(INFOS_DIR.glob("*.json")):
        try:
            payload = json.loads(file.read_text())
        except json.JSONDecodeError as e:
            print(f"{file}: invalid JSON: {e}")
            continue
        if not isinstance(payload, dict):
            print(f"{file}: top-level value must be a JSON object")
            continue
        entries.append((file, payload))
    return entries

def canonical_map(entries):
    canon = {}
    for _, payload in entries:
        value = payload.get("alias") or payload.get("title")
        if not value:
            continue
        if payload.get("title"):
            canon[payload["title"]] = value
        if payload.get("alias"):
            canon[payload["alias"]] = value
    return canon

def main():
    entries = load_entries()
    canon = canonical_map(entries)

    duplicates = []
    for file, payload in entries:
        refs = payload.get("reference", [])
        if not isinstance(refs, list):
            continue
        seen = {}
        for ref in refs:
            key = canon.get(ref, ref)
            seen.setdefault(key, []).append(ref)
        for key, variants in seen.items():
            if len(variants) > 1:
                duplicates.append((file, key, variants))

    if not duplicates:
        print(f"checked {len(entries)} files")
        print("No duplicate references found.")
        return

    for file, key, variants in duplicates:
        print(f"{file}: duplicate reference '{key}':")
        for variant in variants:
            print(f"  - {variant}")

    print(f"checked {len(entries)} files, found {len(duplicates)} duplicate references")
    sys.exit(1)

if __name__ == "__main__":
    main()
