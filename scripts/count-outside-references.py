import json
import re
import difflib

from pathlib import Path
from collections import defaultdict

PROJECT_DIR = Path(__file__).resolve().parent.parent
INFOS_DIR = PROJECT_DIR / 'infos'
REFS_DIR = PROJECT_DIR / 'refs'

MIN_CITING = 10
THRESHOLD = 0.845


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


def similarity(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def tokens(s):
    return set(norm(s).split())


def main():
    infos_probes = []      # (norm_string, token_set, basename)
    for file in INFOS_DIR.glob('*.json'):
        payload = json.loads(file.read_text(encoding='utf-8'))
        base = file.stem
        for probe in (payload.get("title"), payload.get("alias")):
            if probe:
                infos_probes.append((norm(probe), tokens(probe), base))

    def in_infos(text):
        lt = tokens(text)
        for k, ts, _ in infos_probes:
            if lt & ts and similarity(text, k) >= THRESHOLD:
                return True
        return False

    cited = defaultdict(set)      # normalized cited title -> set of citing paper basenames
    example = {}                  # normalized cited title -> a representative raw line
    for file in sorted(REFS_DIR.glob('*.txt')):
        citing = file.stem
        if not (INFOS_DIR / f'{citing}.json').exists():
            continue
        seen = set()
        for line in file.read_text(encoding='utf-8', errors='ignore').splitlines():
            text = line.strip()
            if not text:
                continue
            key = norm(text)
            if in_infos(text):
                continue
            if key in seen:
                continue
            seen.add(key)
            cited[key].add(citing)
            example.setdefault(key, text)

    rows = [(key, len(papers), example[key])
            for key, papers in cited.items() if len(papers) > MIN_CITING]
    rows.sort(key=lambda r: -r[1])

    print(f"cited papers NOT in infos, each cited by more than {MIN_CITING} papers: {len(rows)}")
    print()
    for key, count, text in rows:
        print(f"  {count:3}  {text[:80]}")


if __name__ == "__main__":
    main()
