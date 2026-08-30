import json
import sys
import tomllib

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INFOS_DIR = PROJECT_DIR / 'infos'
BIBS_DIR = PROJECT_DIR / 'bibs'
ASSERTION_TOML = PROJECT_DIR / 'assertion.toml'

def basenames(directory):
    return { file.stem for file in directory.iterdir() }

def read_asserted_titles():
    with ASSERTION_TOML.open("rb") as f:
        assertion = tomllib.load(f)
    return set(assertion["no_bib"])

def infos_title(filename):
    payload = INFOS_DIR / f"{filename}.json"
    with payload.open("r") as f:
        return json.load(f)["title"]

def main():
    infos = basenames(INFOS_DIR)
    bibs = basenames(BIBS_DIR)
    asserted_titles = read_asserted_titles()

    infos_without_bibs = sorted(infos - bibs)
    bibs_without_infos = sorted(bibs - infos)

    missing = []
    for name in infos_without_bibs:
        if infos_title(name) in asserted_titles:
            continue
        missing.append(name)

    print(f"infos files: {len(infos)}")
    print(f"bibs files:  {len(bibs)}")
    print()

    everything_ok = True

    print("=== in infos/ but missing from bibs/ ===")
    if missing:
        everything_ok = False
        for name in missing:
            print(f"  {name}")
        print()
        print("  You should either add corresponding bibs, or assert that it has no bib in assertion.toml.")
    else:
        print("  (none)")

    print()
    print("=== in bibs/ but missing from infos/ ===")
    if bibs_without_infos:
        everything_ok = False
        for name in bibs_without_infos:
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
