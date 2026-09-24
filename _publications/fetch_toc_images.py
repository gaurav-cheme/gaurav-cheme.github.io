"""
Fetch a graphical-abstract / TOC image for every paper in _publications
and store it locally, recording the path as `teaser:` in each file's
front matter.

USAGE
-----
    cd _publications
    pip install requests beautifulsoup4 pyyaml --break-system-packages
    python3 fetch_toc_images.py

Re-run any time -- files that already have a `teaser:` are skipped, so
it's safe (and cheap) to run this after every doi_pubs.py regeneration.
Use --force to re-fetch everything.

HOW IT WORKS
------------
Most publishers (ACS, RSC, Wiley, Elsevier, Springer, Nature...) put a
preview image in the <meta property="og:image"> tag of the article's
landing page -- the same image that shows up when you paste the paper
link into Slack/X/etc. For a lot of journals that preview image *is*
the TOC/graphical abstract, so this script pulls that instead of trying
to scrape figures out of the article body (unreliable and often behind
a paywall). It falls back to twitter:image if og:image isn't present.

LIMITATIONS -- PLEASE READ
---------------------------
* Not every publisher sets a per-article og:image; some just show a
  generic journal logo, and a few show nothing at all. Those are logged
  under "no-og-image" / "no-usable-image" so you can add an image by
  hand (see below).
* Many publisher sites rate-limit or block scripted requests, especially
  if you run this a lot in a short time. If you see a wave of
  "fetch-failed", wait a bit and re-run -- already-successful entries
  will be skipped automatically.
* This only reads whatever image the publisher already exposes publicly
  for link-previews. It does not bypass any paywall or access-control.
* If a publisher's og:image is just their logo (common for some journals
  behind strict paywalls), the script has no way to tell that apart from
  a real graphical abstract -- skim images/publications/ after running
  and delete/replace any that aren't actually useful, then re-run with
  --force on just that one file if needed.

TO ADD AN IMAGE MANUALLY instead of relying on this script:
    1. Save the image to images/publications/<slug>.jpg
       (slug = the .md filename without the .md extension)
    2. Add this line to that file's front matter:
       teaser: "publications/<slug>.jpg"
"""
import argparse
import os
import sys
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

import pub_utils as pu

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

META_CANDIDATES = [
    ("meta", {"property": "og:image"}),
    ("meta", {"name": "og:image"}),
    ("meta", {"name": "twitter:image"}),
    ("meta", {"name": "twitter:image:src"}),
]

# Some publishers' og:image is always a generic masthead/logo rather than
# a per-article graphic. Skip anything whose URL matches these patterns.
JUNK_IMAGE_PATTERNS = ("logo", "masthead", "default-cover", "placeholder")


def find_image_url(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag, attrs in META_CANDIDATES:
        el = soup.find(tag, attrs=attrs)
        if el and el.get("content"):
            url = el["content"].strip()
            if url and not any(p in url.lower() for p in JUNK_IMAGE_PATTERNS):
                return url
    return None


def resolve_url(img_url, page_url):
    if img_url.startswith("//"):
        return "https:" + img_url
    if img_url.startswith("/"):
        parsed = urlparse(page_url)
        return f"{parsed.scheme}://{parsed.netloc}{img_url}"
    return img_url


def download_image(url, dest_noext, session):
    r = session.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    ctype = r.headers.get("Content-Type", "")
    ext = ".jpg"
    if "png" in ctype:
        ext = ".png"
    elif "webp" in ctype:
        ext = ".webp"
    elif "gif" in ctype:
        ext = ".gif"
    dest_path = dest_noext + ext
    with open(dest_path, "wb") as f:
        f.write(r.content)
    return dest_path


def process_file(path, images_dir, session, force=False):
    fm_text, fm, body = pu.read_pub_file(path)
    slug = pu.slug_from_path(path)

    if fm.get("teaser") and not force:
        return "skip-existing", None

    paperurl = fm.get("paperurl")
    if not paperurl or paperurl == "#":
        return "no-url", None

    try:
        resp = session.get(paperurl, headers=HEADERS, timeout=20, allow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        return f"fetch-failed ({e})", None

    img_url = find_image_url(resp.text)
    if not img_url:
        return "no-usable-image", None

    img_url = resolve_url(img_url, resp.url)

    try:
        dest_noext = os.path.join(images_dir, slug)
        saved_path = download_image(img_url, dest_noext, session)
    except Exception as e:
        return f"download-failed ({e})", None

    rel_path = f"publications/{os.path.basename(saved_path)}"
    new_line = f'teaser: "{rel_path}"'
    new_fm_text = pu.upsert_field_line(fm_text, "teaser", new_line)
    pu.write_pub_file(path, new_fm_text, body)
    return "ok", rel_path


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--pubs-dir", default=".", help="Path to _publications directory")
    ap.add_argument(
        "--images-dir",
        default="../images/publications",
        help="Where to store downloaded images (default: ../images/publications)",
    )
    ap.add_argument("--force", action="store_true", help="Re-fetch even if a teaser already exists")
    ap.add_argument("--delay", type=float, default=2.0, help="Seconds to wait between requests")
    ap.add_argument("--only", default=None, help="Only process filenames containing this substring")
    args = ap.parse_args()

    os.makedirs(args.images_dir, exist_ok=True)
    session = requests.Session()

    files = sorted(f for f in os.listdir(args.pubs_dir) if f.endswith(".md"))
    if args.only:
        files = [f for f in files if args.only in f]

    results = {}
    for fname in files:
        path = os.path.join(args.pubs_dir, fname)
        status, detail = process_file(path, args.images_dir, session, force=args.force)
        results[fname] = status
        label = f"{status} -> {detail}" if detail else status
        print(f"{label:55s} {fname}")
        if status not in ("skip-existing",):
            time.sleep(args.delay)

    ok = sum(1 for s in results.values() if s == "ok" or s == "skip-existing")
    print("\n---- Summary ----")
    print(f"{ok} / {len(results)} papers now have a teaser image")
    failed = {f: s for f, s in results.items() if s not in ("ok", "skip-existing")}
    if failed:
        print("Needs manual attention:")
        for f, s in failed.items():
            print(f"  - {f}: {s}")


if __name__ == "__main__":
    main()
