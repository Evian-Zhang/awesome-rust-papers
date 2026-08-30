import argparse
import json
import difflib
import unicodedata

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INFOS_DIR = PROJECT_DIR / 'infos'

THRESHOLD = 0.845

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.lower().split())

def similarity(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()

def load_entries():
    entries = {}
    for file in INFOS_DIR.iterdir():
        with file.open("r") as f:
            entries[file.stem] = json.load(f)
    return entries

def candidates(entries):
    cands = []
    for base, payload in entries.items():
        if payload.get("title"):
            cands.append((base, payload.get("title")))
        if payload.get("alias"):
            cands.append((base, payload.get("alias")))
    return cands

def best_match(line, cands, entries, self_base):
    best = 0.0
    best_base = None
    for base, probe in cands:
        # Exclude self-referential
        if base == self_base:
            continue
        score = similarity(line, probe)
        if score > best:
            best = score
            best_base = base
    if best >= THRESHOLD and best_base is not None:
        return best_base, entries[best_base], best
    return None

def main():
    parser = argparse.ArgumentParser(
        description="Match a paper's references against all infos entries by string "
                    "similarity (>= THRESHOLD) and print the matched aliases/titles."
    )
    parser.add_argument("--json", metavar="PATH", required=True,
                        help="path to the paper's info JSON")
    parser.add_argument("--refs", metavar="PATH", required=True,
                        help="path to the reference list txt (one title per line)")
    args = parser.parse_args()

    json_path = Path(args.json).resolve()
    refs_path = Path(args.refs).resolve()

    if not json_path.exists():
        parser.error(f"{json_path} does not exist")
    if not refs_path.exists():
        parser.error(f"{refs_path} does not exist")

    self_base = json_path.stem
    with json_path.open("r") as f:
        self_payload = json.load(f)
    print(f"paper: {self_payload.get('title')}")

    entries = load_entries()
    cands = candidates(entries)

    with refs_path.open("r") as f:
        lines = f.read().splitlines()

    matched = []
    detail = []
    for line in lines:
        if not line.strip():
            continue
        result = best_match(line, cands, entries, self_base)
        if result:
            base, payload, score = result
            value = payload.get("alias") or payload.get("title")
            matched.append(value)
            detail.append((line, base, value, round(score, 3)))

    print()
    print(f"matched refs (threshold={THRESHOLD}): {len(matched)}")
    for value in matched:
        print(f"  - {value}")

    print()
    print("=== detail ===")
    for line, base, value, score in detail:
        print(f"  [{base}] ({score:.3f}): {line[:70]}")


if __name__ == "__main__":
    main()
