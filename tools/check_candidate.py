#!/usr/bin/env python3
"""Conservative preflight for music candidates.

Rebuilds a lookup from the live country JSON ledger *and* curated Markdown.
It is not a history of previous ChatGPT conversations and cannot prove
that an unlisted candidate has never been heard.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


def norm(value):
    value = unicodedata.normalize("NFKC", str(value)).casefold()
    value = value.replace("’", "'").replace("‘", "'")
    return " ".join(re.findall(r"\w+", value, flags=re.UNICODE))


def contains(haystack, needle):
    h, n = norm(haystack), norm(needle)
    return bool(n) and (" " + n + " ") in (" " + h + " ")


def main():
    parser = argparse.ArgumentParser(
        description="Check the country ledger and Markdown before recommending music."
    )
    parser.add_argument("--country", default="Australia")
    parser.add_argument("--artist")
    parser.add_argument("--label")
    parser.add_argument("--release")
    parser.add_argument("--track")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    terms = {k: getattr(args, k) for k in ("artist", "label", "release", "track")
             if getattr(args, k)}
    if not terms:
        parser.error("Provide at least one of --artist, --label, --release or --track.")

    repo = args.repo.resolve()
    ledger = json.loads((repo / "research" / f"{args.country}.json").read_text(encoding="utf-8"))
    markdown = (repo / f"{args.country}.md").read_text(encoding="utf-8")
    matched_records = []
    confirmed_prior_material = False

    for field in ("labels", "artist_provenance", "listening", "open_tasks"):
        for entry in ledger.get(field, []):
            record = {"name": entry, "status": "open_task"} if isinstance(entry, str) else entry
            # Search all known aliases, verdicts, notes and open tasks.
            hay = json.dumps(record, ensure_ascii=False)
            found = [name for name, term in terms.items() if contains(hay, term)]
            if not found:
                continue
            matched_records.append((field, record, found))
            if field == "listening" and any(
                k in found for k in ("release", "track")
            ):
                confirmed_prior_material = True

    md_hits = []
    for line_no, line in enumerate(markdown.splitlines(), 1):
        found = [key for key, term in terms.items() if contains(line, term)]
        if found:
            md_hits.append((line_no, line.strip()[:280], found))

    print(f"COUNTRY: {args.country}  |  ledger revision: {ledger.get('revision', '?')}")
    print(f"QUERY: {json.dumps(terms, ensure_ascii=False)}")
    print(f"Structured matches: {len(matched_records)}")
    for field, record, found in matched_records[:35]:
        label = record.get("release") or record.get("name") or "(unnamed)"
        print(f"  {field}: {label}  [{record.get('status', 'no status')}]  matching: {','.join(found)}")
    if len(matched_records) > 35:
        print(f"  ... and {len(matched_records) - 35} more")
    print(f"Markdown mentions: {len(md_hits)}")
    for line_no, line, found in md_hits[:25]:
        print(f"  {args.country}.md:{line_no}  {line}  matching: {','.join(found)}")
    if len(md_hits) > 25:
        print(f"  ... and {len(md_hits) - 25} more")

    if confirmed_prior_material:
        print("RESULT: PRIOR MATERIAL REFERENCED — inspect the recorded verdict; do not reassign.")
    elif matched_records or md_hits:
        print("RESULT: EXISTING CONTEXT — check specific release and aliases before proceeding.")
    else:
        print("RESULT: NOT FOUND IN REPOSITORY — NOT proof of newness.")
    print("REQUIRED: also check retrievable previous project conversations. "
          "No access / incomplete search means historical coverage is uncertain.")
    return 2 if confirmed_prior_material else 1 if matched_records or md_hits else 0


if __name__ == "__main__":
    sys.exit(main())
