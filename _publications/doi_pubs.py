import bibtexparser
import os
import requests
import time

import pub_utils as pu

def get_metadata_from_doi(doi):
    """Queries Crossref API for both DOI and Abstract."""
    if not doi:
        return None, None
    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            message = response.json().get('message', {})
            abstract = message.get('abstract', '')
            # Clean Crossref JATS XML tags
            clean_abstract = abstract.replace('<jats:p>', '').replace('</jats:p>', '').replace('<jats:title>Abstract</jats:title>', '')
            return doi, clean_abstract
    except Exception as e:
        print(f"Error fetching metadata for DOI {doi}: {e}")
    return doi, None

def get_doi_from_title(title, authors):
    try:
        url = "https://api.crossref.org/works"
        params = {"query.title": title, "query.author": authors, "rows": 1}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            items = response.json().get('message', {}).get('items', [])
            if items:
                doi = items[0].get('DOI')
                return get_metadata_from_doi(doi)
    except:
        pass
    return None, None

def generate_markdown_from_bib(bib_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(bib_file, 'r', encoding='utf-8') as f:
        bib_database = bibtexparser.load(f)

    entries = sorted(bib_database.entries, key=lambda x: x.get('year', '0000'), reverse=True)

    for entry in entries:
        title = entry.get('title', 'Untitled').replace('{', '').replace('}', '')
        year = entry.get('year', '0000')
        authors = entry.get('author', 'Unknown').replace('{', '').replace('}', '')
        venue = entry.get('journal', entry.get('booktitle', entry.get('school', 'Preprint')))
        
        # Priority: Check .bib for DOI/Abstract first, then hit the API
        doi = entry.get('doi')
        abstract = entry.get('abstract')
        
        if not doi or not abstract:
            print(f"Fetching metadata for: {title[:50]}...")
            found_doi, found_abstract = get_doi_from_title(title, authors)
            doi = doi or found_doi
            abstract = abstract or found_abstract
            time.sleep(0.2)

        paper_url = f"https://doi.org/{doi}" if doi else entry.get('url', '#')

        # Format long filename base and corresponding image path
        clean_title = "".join(x for x in title if x.isalnum() or x == " ")
        title_slug = clean_title.replace(' ', '-').lower()[:50]
        base_filename = f"{year}-01-01-{title_slug}"

        filename = f"{base_filename}.md"
        filepath = os.path.join(output_dir, filename)
        image_path = f"/images/publications/{base_filename}.png"

        # Preserve existing custom front matter fields if updating existing files
        extra_fm_lines = []
        if os.path.exists(filepath):
            try:
                old_fm_text, old_fm, _ = pu.read_pub_file(filepath)
                known_fields = {"title", "collection", "permalink", "date", "venue", "paperurl", "citation", "image"}
                for line in old_fm_text.splitlines():
                    field = line.split(":", 1)[0].strip()
                    if field and field not in known_fields:
                        extra_fm_lines.append(line)
            except Exception as e:
                print(f"  ! could not read existing {filename}, will overwrite fully: {e}")

        extra_fm_block = ("\n" + "\n".join(extra_fm_lines)) if extra_fm_lines else ""

        # Markdown output with long-filename image entry in front matter
        md_content = f"""---
title: "{title}"
collection: publications
permalink: /publication/{base_filename}
date: {year}-01-01
venue: '{venue}'
paperurl: '{paper_url}'
citation: '{authors}. ({year}). &quot;{title}.&quot; <i>{venue}</i>.'
image: '{image_path}'{extra_fm_block}
---

<details>
  <summary><b>Click to view Abstract</b></summary>
  <blockquote>
    {abstract if abstract else 'Abstract not available.'}
  </blockquote>
</details>

[Access Full Paper Here]({paper_url})
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        if extra_fm_lines:
            print(f"  (kept {len(extra_fm_lines)} existing field(s), e.g. {extra_fm_lines[0].split(':')[0]}, for {filename})")

    print(f"Done! Check the _publications folder.")

if __name__ == "__main__":
    generate_markdown_from_bib('publications.bib', '../_publications')