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
CHUNK_SIZE = 50
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

def referenced_work_ids(work_id):
    params = urllib.parse.urlencode({
        'select': 'referenced_works',
    })
    data = http_json(f'{BASE_URL}/{work_id}?{params}')
    return data.get('referenced_works') or []

def referenced_titles(work_ids):
    short_ids = [w.rsplit('/', 1)[-1] for w in work_ids]
    titles = []
    for i in range(0, len(short_ids), CHUNK_SIZE):
        chunk = short_ids[i:i + CHUNK_SIZE]
        params = urllib.parse.urlencode({
            'filter': 'openalex:' + '|'.join(chunk),
            'per-page': 100,
            'select': 'id,display_name',
        })
        data = http_json(f'{BASE_URL}?{params}')
        for work in data.get('results', []):
            titles.append(work.get('display_name') or '')
        if i + CHUNK_SIZE < len(short_ids) and PAGE_DELAY:
            time.sleep(PAGE_DELAY)
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
        description="Find papers that the given paper (under infos/) cites via the OpenAlex API, "
                    "and add every reference that also exists in infos/ "
                    "to the given paper's reference list."
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

    work_ids = referenced_work_ids(work_id)
    print(f"references (OpenAlex): {len(work_ids)}")
    if not work_ids:
        return

    titles = referenced_titles(work_ids)

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
            value = paper_identifier(entries[base])
            if base not in matched:
                matched.append(base)
                detail.append((line, base, round(score, 3), value))

    print(f"matched in infos/: {len(matched)}")

    refs = self_payload.setdefault("reference", [])
    changed = False
    for line, base, score, value in detail:
        if value in refs:
            continue
        refs.append(value)
        changed = True
        print(f"  added: {value}")

    if changed:
        with json_path.open("w") as f:
            json.dump(self_payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print()
        print(f"updated {json_path}")
    else:
        print()
        print("nothing to add")

    print()
    print("=== detail ===")
    for line, base, score, value in detail:
        print(f"  [{base}] ({score:.3f}): {line[:70]}")

if __name__ == "__main__":
    main()
