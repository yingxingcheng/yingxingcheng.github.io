#!/usr/bin/env python3
"""Synchronize verified ORCID publications without replacing curated citations."""

import argparse
import copy
import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ORCID = "0000-0002-0209-7147"
ORCID_URL = f"https://pub.orcid.org/v3.0/{ORCID}/works"
CROSSREF_URL = "https://api.crossref.org/works"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "yingxingcheng-website/2.0 (mailto:chengyx@ms.xjb.ac.cn)",
}
TIMEOUT = (10, 30)
DOI_PATTERN = re.compile(r"10\.\d{4,9}/\S+", re.IGNORECASE)


class PublicationError(Exception):
    """A source could not be checked completely; do not publish a partial update."""


def normalize_doi(value):
    """Accept bare DOIs, doi: prefixes, and canonical DOI resolver URLs."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if value.lower().startswith(("https://", "http://")):
        url = urlsplit(value)
        if url.hostname not in {"doi.org", "dx.doi.org"}:
            return None
        value = unquote(url.path.lstrip("/"))
    elif value.lower().startswith("doi:"):
        value = value[4:].strip()
    return value.lower() if DOI_PATTERN.fullmatch(value) else None


def make_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods={"GET"},
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def get_json(session, url, **kwargs):
    try:
        response = session.get(url, timeout=TIMEOUT, **kwargs)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        raise PublicationError(f"Could not read {url}: {error}") from error
    if not isinstance(data, dict):
        raise PublicationError(f"Expected a JSON object from {url}")
    return data


def fetch_orcid_dois(session):
    data = get_json(session, ORCID_URL)
    if not isinstance(data.get("group"), list):
        raise PublicationError("ORCID response has no valid works list")
    dois = set()
    for group in data["group"]:
        if not isinstance(group, dict) or not isinstance(group.get("work-summary"), list):
            raise PublicationError("ORCID returned an invalid work group")
        for summary in group["work-summary"]:
            if not isinstance(summary, dict) or not isinstance(summary.get("type"), str):
                raise PublicationError("ORCID returned an invalid work summary")
            # This site's publications list contains journal articles, not datasets or reviews.
            if summary.get("type") != "journal-article":
                continue
            identifiers = summary.get("external-ids")
            if not isinstance(identifiers, dict) or not isinstance(
                identifiers.get("external-id"), list
            ):
                raise PublicationError("ORCID returned invalid external identifiers")
            for external_id in identifiers["external-id"]:
                if not isinstance(external_id, dict):
                    raise PublicationError("ORCID returned an invalid external identifier")
                if external_id.get("external-id-type", "").lower() != "doi":
                    continue
                # A DOI of a related work is not necessarily a publication by this author.
                if external_id.get("external-id-relationship") != "self":
                    continue
                doi = normalize_doi(external_id.get("external-id-value"))
                if not doi:
                    raise PublicationError("ORCID supplied an invalid publication DOI")
                dois.add(doi)
    return dois


def has_author_orcid(meta):
    for author in meta.get("author", []):
        value = author.get("ORCID", "")
        if not isinstance(value, str):
            continue
        value = value.strip().rstrip("/")
        if value.startswith(("https://", "http://")):
            url = urlsplit(value)
            if url.hostname != "orcid.org":
                continue
            value = url.path.lstrip("/")
        if value == ORCID:
            return True
    return False


def fetch_crossref_works(session):
    """Supplement ORCID with exact author-ORCID matches; never match by name alone."""
    works = {}
    cursor = "*"
    seen_cursors = set()
    while True:
        data = get_json(
            session,
            CROSSREF_URL,
            params={
                "filter": f"orcid:{ORCID},type:journal-article",
                "rows": 1000,
                "cursor": cursor,
            },
        ).get("message", {})
        items = data.get("items")
        if not isinstance(items, list):
            raise PublicationError("Crossref response has no valid works list")
        for meta in items:
            if meta.get("type") != "journal-article" or not has_author_orcid(meta):
                continue
            doi = normalize_doi(meta.get("DOI"))
            if not doi:
                raise PublicationError("Crossref supplied an invalid publication DOI")
            works[doi] = meta
        if len(items) < 1000:
            return works
        next_cursor = data.get("next-cursor")
        if not next_cursor or next_cursor in seen_cursors:
            raise PublicationError("Crossref pagination did not advance")
        seen_cursors.add(next_cursor)
        cursor = next_cursor


def fetch_crossref(session, doi):
    meta = get_json(session, f"{CROSSREF_URL}/{quote(doi, safe='')}").get("message")
    if not isinstance(meta, dict) or normalize_doi(meta.get("DOI")) != doi:
        raise PublicationError(f"Crossref returned mismatched or missing metadata for {doi}")
    return meta


class MetadataText(HTMLParser):
    """Convert Crossref's inline XML/HTML markup and entities to plain citation text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def clean_text(value):
    parser = MetadataText()
    parser.feed(str(value or ""))
    return " ".join(unescape("".join(parser.parts)).split())


def format_authors(author_list):
    if not isinstance(author_list, list):
        raise PublicationError("Crossref authors must be a list")
    names = []
    for author in author_list:
        if not isinstance(author, dict):
            raise PublicationError("Crossref returned an invalid author")
        name = (
            author.get("name")
            or " ".join(str(author.get(part) or "").strip() for part in ("given", "family")).strip()
        )
        name = clean_text(name)
        if name:
            names.append(name)
    return ", ".join(names[:-1]) + f", and {names[-1]}" if len(names) > 2 else ", ".join(names)


def metadata_title(meta, field, doi):
    values = meta.get(field)
    if not isinstance(values, list) or not values or not isinstance(values[0], str):
        raise PublicationError(f"Missing or invalid Crossref {field} for {doi}")
    result = clean_text(values[0])
    if not result:
        raise PublicationError(f"Empty Crossref {field} for {doi}")
    return result


def crossref_to_pub(meta, doi):
    if meta.get("type") != "journal-article":
        raise PublicationError(f"Crossref DOI is not a journal article: {doi}")
    title = metadata_title(meta, "title", doi)
    journal = metadata_title(meta, "container-title", doi)
    authors = format_authors(meta.get("author", []))
    year = ""
    for field in ("published", "published-print", "published-online", "issued"):
        parts = (meta.get(field) or {}).get("date-parts") or []
        if parts and parts[0] and re.fullmatch(r"[1-9]\d{3}", str(parts[0][0])):
            year = str(parts[0][0])
            break
    if not isinstance(title, str) or not clean_text(title) or not authors or not year:
        raise PublicationError(f"Incomplete Crossref citation (title, authors, or year) for {doi}")
    return {
        "authors": authors,
        "title": clean_text(title),
        "journal": journal,
        "volume": clean_text(meta.get("volume")),
        "pages": clean_text(meta.get("page") or meta.get("article-number")),
        "year": year,
        "link": f"https://doi.org/{quote(doi, safe='/():;')}",
        "source": "crossref",
    }


def known_dois(pubs):
    return {doi for pub in pubs if (doi := normalize_doi(pub.get("link")))}


def sort_pubs(pubs):
    def key(pub):
        try:
            return int(pub.get("year") or 0)
        except (ValueError, TypeError):
            return 0

    return sorted(pubs, key=key, reverse=True)


def update_content(content, session):
    """Fetch everything before changing either language; failures leave input intact."""
    orcid_dois = fetch_orcid_dois(session)
    crossref_works = fetch_crossref_works(session)
    candidates = orcid_dois | crossref_works.keys()
    existing = {
        lang: known_dois(content[lang]["sections"]["publications"]["items"])
        for lang in ("en", "zh")
    }
    missing = candidates - (existing["en"] & existing["zh"])
    additions = {}
    for doi in sorted(missing):
        meta = crossref_works.get(doi) or fetch_crossref(session, doi)
        additions[doi] = crossref_to_pub(meta, doi)
    result = copy.deepcopy(content)
    counts = {}
    for lang in ("en", "zh"):
        pubs = result[lang]["sections"]["publications"]["items"]
        new = [pub for doi, pub in additions.items() if doi not in existing[lang]]
        if new:
            result[lang]["sections"]["publications"]["items"] = sort_pubs(pubs + new)
        counts[lang] = len(new)
    return result, counts, {"orcid": len(orcid_dois), "crossref": len(crossref_works)}


def write_json(path, data):
    # Replace a complete file only after the entire API check and validation succeeded.
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content", type=Path, default=Path("content.json"))
    parser.add_argument("--status", type=Path, default=Path(".github/publication-sync.json"))
    parser.add_argument(
        "--check-only", action="store_true", help="Report results without writing files"
    )
    args = parser.parse_args(argv)
    try:
        content = json.loads(args.content.read_text(encoding="utf-8"))
        with make_session() as session:
            updated, counts, sources = update_content(content, session)
        print(f"Checked ORCID ({sources['orcid']}) and Crossref ({sources['crossref']}) works.")
        print(f"New citations: English {counts['en']}, Chinese {counts['zh']}.")
        if args.check_only:
            print("Check only: no files written.")
            return 0
        if updated != content:
            write_json(args.content, updated)
        else:
            print("No new publications. content.json unchanged.")
        # A dated success record provides an audit trail even when there are no new works.
        # Meaningful monthly commits help prevent GitHub's public-repo inactivity timeout.
        status = {
            "last_successful_check": datetime.now(timezone.utc).date().isoformat(),
            "orcid": ORCID,
            "source_counts": sources,
            "publication_counts": {
                lang: len(updated[lang]["sections"]["publications"]["items"])
                for lang in ("en", "zh")
            },
        }
        args.status.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.status, status)
        return 0
    except (PublicationError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"Publication check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
