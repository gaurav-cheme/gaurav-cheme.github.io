"""
Pull the author's publication list from Google Scholar and merge any
NEW entries into publications.bib (never deletes or overwrites existing
entries -- dedup is by normalized title).

USAGE
-----
    cd _publications
    pip install scholarly bibtexparser pyyaml --break-system-packages
    python3 scholar_to_bib.py

Then regenerate the site pages from the updated bib file:
    python3 doi_pubs.py
    python3 fetch_toc_images.py

The Scholar id is read automatically from ../_config.yml
(author.googlescholar), or pass --scholar-id to override.

IMPORTANT CAVEATS -- PLEASE READ
----------------------------------
* Google Scholar has no official public API. The `scholarly` package
  works by scraping the public profile pages, so Google can (and
  periodically does) rate-limit or CAPTCHA-block automated requests
  from a given IP. If you see "Cannot Fetch from Google Scholar" or
  similar, try:
    - waiting 10-15 minutes and re-running
    - running with --use-proxy (routes requests through free rotating
      proxies -- slower and itself not 100% reliable, but sometimes
      unblocks things)
    - as a last resort: on your Scholar profile page, tick all papers,
      click "Export" -> "BibTeX", and paste the results directly into
      publications.bib yourself
* Scholar's own metadata can be messy: merged duplicate entries, wrong
  venue for preprints, truncated author lists. Skim publications.bib
  after running this, before regenerating the markdown pages.
* This script is strictly additive -- it will not touch or remove any
  entry already in publications.bib, even if Scholar's data for it has
  since changed.
"""
import argparse
import re
import sys

import yaml


def get_scholar_id_from_config(config_path="../_config.yml"):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    url = (cfg.get("author") or {}).get("googlescholar", "") or ""
    m = re.search(r"user=([\w-]+)", url)
    if not m:
        raise ValueError(
            f"Could not find a Google Scholar user id in {config_path} "
            "(expected author.googlescholar to contain '...?user=XXXX')"
        )
    return m.group(1)


def normalize_title(title):
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())


def fetch_scholar_publications(scholar_id, use_proxy=False):
    from scholarly import scholarly, ProxyGenerator

    if use_proxy:
        pg = ProxyGenerator()
        if pg.FreeProxies():
            scholarly.use_proxy(pg)
        else:
            print("  ! could not set up free proxies, continuing without.", file=sys.stderr)

    print(f"Looking up Scholar author id {scholar_id} ...")
    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=["publications"])
    stubs = author.get("publications", [])
    print(f"Scholar profile lists {len(stubs)} publications. Fetching details "
          f"for each (this can take a while -- Scholar is slow/rate-limited)...")

    pubs = []
    for i, stub in enumerate(stubs):
        try:
            pub = scholarly.fill(stub)
        except Exception as e:
            print(f"  ! could not fetch details for entry {i + 1}/{len(stubs)}: {e}", file=sys.stderr)
            continue
        bib = pub.get("bib", {})
        pubs.append(
            {
                "title": (bib.get("title") or "").strip(),
                "author": bib.get("author", ""),
                "year": str(bib.get("pub_year", "0000")),
                "journal": bib.get("journal") or bib.get("citation") or "Preprint",
                "abstract": bib.get("abstract", ""),
                "url": pub.get("pub_url", ""),
            }
        )
        if (i + 1) % 5 == 0:
            print(f"  ...{i + 1}/{len(stubs)} done")
    return pubs


def load_existing_titles(bib_path):
    import bibtexparser

    try:
        with open(bib_path, "r", encoding="utf-8") as f:
            db = bibtexparser.load(f)
    except FileNotFoundError:
        return set()
    return {normalize_title(e.get("title", "")) for e in db.entries}


def make_bib_key(title, year):
    base = re.sub(r"[^A-Za-z0-9]", "", title)[:24] or "entry"
    return f"{base}{year}"


def append_new_entries(bib_path, new_pubs, existing_titles, dry_run=False):
    added = []
    entries_text = []
    for p in new_pubs:
        norm = normalize_title(p["title"])
        if not norm or norm in existing_titles:
            continue
        key = make_bib_key(p["title"], p["year"])
        entry = (
            f"\n@article{{{key},\n"
            f"  title = {{{p['title']}}},\n"
            f"  author = {{{p['author']}}},\n"
            f"  year = {{{p['year']}}},\n"
            f"  journal = {{{p['journal']}}},\n"
            + (f"  abstract = {{{p['abstract']}}},\n" if p["abstract"] else "")
            + (f"  url = {{{p['url']}}},\n" if p["url"] else "")
            + "}\n"
        )
        entries_text.append(entry)
        existing_titles.add(norm)
        added.append(p["title"])

    if entries_text and not dry_run:
        with open(bib_path, "a", encoding="utf-8") as f:
            for entry in entries_text:
                f.write(entry)

    return added


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--bib", default="publications.bib")
    ap.add_argument("--config", default="../_config.yml")
    ap.add_argument("--scholar-id", default=None, help="Override the id read from _config.yml")
    ap.add_argument(
        "--use-proxy", action="store_true",
        help="Try free rotating proxies if Scholar blocks direct requests",
    )
    ap.add_argument("--dry-run", action="store_true", help="Show what would be added, don't write")
    args = ap.parse_args()

    scholar_id = args.scholar_id or get_scholar_id_from_config(args.config)

    existing_titles = load_existing_titles(args.bib)
    print(f"{len(existing_titles)} publications already in {args.bib}")

    pubs = fetch_scholar_publications(scholar_id, use_proxy=args.use_proxy)

    added = append_new_entries(args.bib, pubs, existing_titles, dry_run=args.dry_run)

    print(f"\n{'Would add' if args.dry_run else 'Added'} {len(added)} new entries "
          f"{'to' if not args.dry_run else 'to (dry run, nothing written)'} {args.bib}:")
    for t in added:
        print(f"  + {t}")
    if not added:
        print("  (nothing new -- publications.bib is already up to date)")
    elif not args.dry_run:
        print("\nNext steps:\n  python3 doi_pubs.py\n  python3 fetch_toc_images.py")


if __name__ == "__main__":
    main()
