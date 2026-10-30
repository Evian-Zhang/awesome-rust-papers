import json
import sys
import tomllib

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INFOS_DIR = PROJECT_DIR / 'infos'
BIBS_DIR = PROJECT_DIR / 'bibs'
ASSERTION_TOML = PROJECT_DIR / 'assertion.toml'

def read_asserted_titles():
    with ASSERTION_TOML.open("rb") as f:
        assertion = tomllib.load(f)
    return set(assertion["no_bib"])

def load_infos():
    infos = {}
    for file in sorted(INFOS_DIR.glob("*.json")):
        with file.open("r") as f:
            infos[file.stem] = json.load(f)
    return infos

def further_bib_names(payload):
    """BibTeX file names declared by the entry's `further` publications."""
    names = []
    for item in payload.get("further", []):
        if not isinstance(item, dict):
            continue
        name = item.get("bib")
        if isinstance(name, str) and name:
            names.append(name)
    return names

def main():
    infos = load_infos()
    bibs = { file.name for file in BIBS_DIR.iterdir() if file.is_file() }
    asserted_titles = read_asserted_titles()

    referenced = set()
    missing_main = []
    missing_further = []
    for name, payload in infos.items():
        main_bib = f"{name}.bib"
        if main_bib in bibs:
            referenced.add(main_bib)
        elif payload.get("title") not in asserted_titles:
            missing_main.append(name)

        for further_bib in further_bib_names(payload):
            referenced.add(further_bib)
            if further_bib not in bibs:
                missing_further.append((name, further_bib))

    orphans = sorted(bibs - referenced)

    print(f"infos files:          {len(infos)}")
    print(f"bibs files:           {len(bibs)}")
    print(f"referenced bibs:      {len(referenced)}")
    print()

    everything_ok = True

    print("=== in infos/ but missing from bibs/ ===")
    if missing_main:
        everything_ok = False
        for name in missing_main:
            print(f"  {name}")
        print()
        print("  You should either add corresponding bibs, or assert that it has no bib in assertion.toml.")
    else:
        print("  (none)")

    print()
    print("=== further entries pointing to missing bibs/ ===")
    if missing_further:
        everything_ok = False
        for name, further_bib in missing_further:
            print(f"  {name}: {further_bib}")
        print()
        print("  Every further `bib` is a file name under bibs/; add it or drop the key.")
    else:
        print("  (none)")

    print()
    print("=== in bibs/ but not referenced from infos/ ===")
    if orphans:
        everything_ok = False
        for name in orphans:
            print(f"  {name}")
        print()
        print("  This is unexpected.")
    else:
        print("  (none)")

    if not everything_ok:
        sys.exit(1)

    print()
    print("Everything OK!")

if __name__ == "__main__":
    main()
