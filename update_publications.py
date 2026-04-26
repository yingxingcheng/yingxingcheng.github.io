#!/usr/bin/env python3
"""Fetch publications from ORCID + CrossRef and update content.json."""

import json
import sys
import time
import requests

ORCID = "0000-0002-0209-7147"
ORCID_URL = f"https://pub.orcid.org/v3.0/{ORCID}/works"
CROSSREF_URL = "https://api.crossref.org/works"
# Polite pool: identify ourselves to CrossRef
CROSSREF_HEADERS = {"User-Agent": "yingxingcheng-website/1.0 (chengyx@ms.xjb.ac.cn)"}


def fetch_orcid_dois():
    resp = requests.get(ORCID_URL, headers={"Accept": "application/json"}, timeout=15)
    resp.raise_for_status()
    dois = []
    for group in resp.json().get("group", []):
        for summary in group.get("work-summary", []):
            for eid in summary.get("external-ids", {}).get("external-id", []):
                if eid["external-id-type"] == "doi":
                    dois.append(eid["external-id-value"].strip().lower())
    # deduplicate, preserve order
    return list(dict.fromkeys(dois))


def fetch_crossref(doi):
    try:
        resp = requests.get(
            f"{CROSSREF_URL}/{doi}", headers=CROSSREF_HEADERS, timeout=15
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json().get("message", {})
    except requests.RequestException as e:
        print(f"  Warning: could not fetch CrossRef for {doi}: {e}")
        return None


def format_authors(author_list):
    names = []
    for a in author_list:
        given = a.get("given", "")
        family = a.get("family", "")
        names.append(f"{given} {family}".strip() if given else family)
    if len(names) == 0:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]}, {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def crossref_to_pub(meta, doi):
    authors = format_authors(meta.get("author", []))
    title = (meta.get("title") or [""])[0]

    journal = (meta.get("container-title") or [""])[0]

    date = meta.get("published") or meta.get("published-print") or meta.get("published-online") or {}
    parts = (date.get("date-parts") or [[""]])[0]
    year = str(parts[0]) if parts else ""

    volume = meta.get("volume", "")
    pages = meta.get("page") or meta.get("article-number") or ""

    return {
        "authors": authors,
        "title": title,
        "journal": journal,
        "volume": volume,
        "pages": pages,
        "year": year,
        "link": f"https://doi.org/{doi}",
    }


def known_dois(pubs):
    result = set()
    for p in pubs:
        link = p.get("link", "")
        if "doi.org/" in link:
            result.add(link.split("doi.org/")[-1].strip().lower())
    return result


def sort_pubs(pubs):
    def key(p):
        try:
            return int(p.get("year", 0))
        except ValueError:
            return 0
    return sorted(pubs, key=key, reverse=True)


def main():
    with open("content.json", encoding="utf-8") as f:
        content = json.load(f)

    en_pubs = content["en"]["sections"]["publications"]["items"]
    zh_pubs = content["zh"]["sections"]["publications"]["items"]
    existing = known_dois(en_pubs)
    print(f"Existing publications: {len(en_pubs)}")

    orcid_dois = fetch_orcid_dois()
    print(f"Works on ORCID: {len(orcid_dois)}")

    new_pubs = []
    for doi in orcid_dois:
        if doi in existing:
            continue
        print(f"New DOI: {doi} — fetching metadata...")
        meta = fetch_crossref(doi)
        if not meta:
            continue
        pub = crossref_to_pub(meta, doi)
        print(f"  -> [{pub['year']}] {pub['title'][:60]}...")
        new_pubs.append(pub)
        time.sleep(0.5)  # be polite to CrossRef

    if not new_pubs:
        print("No new publications found. content.json unchanged.")
        sys.exit(0)

    print(f"\nAdding {len(new_pubs)} new publication(s).")
    merged_en = sort_pubs(en_pubs + new_pubs)
    merged_zh = sort_pubs(zh_pubs + new_pubs)

    content["en"]["sections"]["publications"]["items"] = merged_en
    content["zh"]["sections"]["publications"]["items"] = merged_zh

    with open("content.json", "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=4)

    print("content.json updated.")


if __name__ == "__main__":
    main()
