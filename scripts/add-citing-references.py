import argparse
import difflib
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import urllib.error

from pathlib import Path
from urllib.error import HTTPError

PROJECT_DIR = Path(__file__).resolve().parent.parent
INFOS_DIR = PROJECT_DIR / 'infos'

THRESHOLD = 0.845
BASE_URL = 'https://api.openalex.org/works'
PER_PAGE = 100
PAGE_DELAY = 1.0

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.lower().split())

def similarity(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()

def http_json(url):
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)

def resolve_work_id(payload):
    link = payload.get("link") or ""
    m = re.search(r'doi\.org/(.+?)/?$', link)
    if m:
        doi = m.group(1).rstrip('/')
        data = http_json(f'{BASE_URL}/https://doi.org/{doi}')
        return data.get('id'), True
    title = payload.get("title") or ""
    target = norm(title)
    words = [w for w in (re.sub(r'[^a-z0-9]+', '', w) or '' for w in target.split()) if w]
    num_tokens = len(words)

    def search(query):
        params = urllib.parse.urlencode({
            'filter': 'title.search:"' + query + '"',
            'per-page': 10,
        })
        return http_json(f'{BASE_URL}?{params}').get('results', [])

    queries = [' '.join(words)]
    queries += [' '.join(words[:n]) for n in (8, 6, 4, 3, 2) if n < num_tokens]

    for query in queries:
        for work in search(query):
            if norm(work.get('display_name')) == target:
                return work.get('id'), False
    return None, False

def citing_titles(work_id):
    titles = []
    params = urllib.parse.urlencode({
        'filter': f'cites:{work_id}',
        'per-page': PER_PAGE,
        'cursor': '*',
    })
    url = f'{BASE_URL}?{params}'
    while url:
        data = http_json(url)
        for work in data.get('results', []):
            titles.append(work.get('display_name') or '')
        next_cursor = data.get('meta', {}).get('next_cursor')
        if not next_cursor:
            break
        if PAGE_DELAY:
            time.sleep(PAGE_DELAY)
        url = f'{BASE_URL}?{urllib.parse.urlencode({
            'filter': f'cites:{work_id}',
            'per-page': PER_PAGE,
            'cursor': next_cursor,
        })}' if next_cursor else None
    return titles

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

def best_match(line, cands, self_base):
    best = 0.0
    best_base = None
    for base, probe in cands:
        if base == self_base:
            continue
        score = similarity(line, probe)
        if score > best:
            best = score
            best_base = base
    if best >= THRESHOLD and best_base is not None:
        return best_base, best
    return None

def paper_identifier(payload):
    return payload.get("alias") or payload.get("title")

def main():
    parser = argparse.ArgumentParser(
        description="Find papers in infos/ that cite the given paper via the OpenAlex API, "
                    "and add the given paper to each matching paper's reference list."
    )
    parser.add_argument("--json", metavar="PATH", required=True,
                        help="path to the paper's info JSON (under infos/)")
    args = parser.parse_args()

    json_path = Path(args.json).resolve()
    if not json_path.exists():
        parser.error(f"{json_path} does not exist")

    self_base = json_path.stem
    with json_path.open("r") as f:
        self_payload = json.load(f)
    self_value = paper_identifier(self_payload)
    print(f"paper: {self_value}")

    try:
        work_id, by_doi = resolve_work_id(self_payload)
    except HTTPError as e:
        if e.code == 429:
            print("skipped: OpenAlex rate limit (429); nothing done")
        else:
            print(f"skipped: OpenAlex error {e.code}; nothing done")
        return
    if not work_id:
        sys.exit("cannot resolve the paper on OpenAlex (no DOI and no title match); nothing to do")
    print(f"resolved via {'DOI' if by_doi else 'title search'}: {work_id}")

    titles = citing_titles(work_id)
    print(f"cited by (OpenAlex): {len(titles)}")

    entries = load_entries()
    cands = candidates(entries)

    matched = []
    detail = []
    for line in titles:
        if not line:
            continue
        result = best_match(line, cands, self_base)
        if result:
            base, score = result
            matched.append(base)
            detail.append((line, base, round(score, 3)))

    unique_matched = []
    for base in matched:
        if base not in unique_matched:
            unique_matched.append(base)

    print(f"matched in infos/: {len(unique_matched)}")

    changed = []
    for base in unique_matched:
        payload = entries[base]
        refs = payload.setdefault("reference", [])
        if self_value in refs:
            continue
        refs.append(self_value)
        changed.append(base)
        print(f"  added to {base}: {self_value}")

    for base in changed:
        path = INFOS_DIR / f"{base}.json"
        with path.open("w") as f:
            json.dump(entries[base], f, indent=2, ensure_ascii=False)
            f.write("\n")

    print()
    print(f"updated {len(changed)} file(s)")

    print()
    print("=== detail ===")
    for line, base, score in detail:
        print(f"  [{base}] ({score:.3f}): {line[:70]}")

if __name__ == "__main__":
    main()
