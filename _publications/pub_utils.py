"""
Shared helpers used by the publications pipeline scripts
(doi_pubs.py, fetch_toc_images.py, scholar_to_bib.py).

Handles reading/writing the YAML front matter of a _publications/*.md
file WITHOUT touching the rest of the file's formatting -- this matters
because doi_pubs.py regenerates files from publications.bib, and we
don't want that to wipe out a `teaser:` image path that
fetch_toc_images.py already added.
"""
import os
import re

import yaml

FRONT_MATTER_RE = re.compile(r"\A---\n(.*?\n)---\n(.*)\Z", re.DOTALL)


def split_front_matter(text):
    """Return (raw_front_matter_text, parsed_dict, body_text)."""
    m = FRONT_MATTER_RE.match(text)
    if not m:
        raise ValueError("File does not start with a '---' YAML front matter block")
    fm_text, body = m.group(1), m.group(2)
    fm = yaml.safe_load(fm_text) or {}
    return fm_text, fm, body


def read_pub_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return split_front_matter(text)


def write_pub_file(path, fm_text, body):
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(fm_text)
        f.write("---\n")
        f.write(body)


def slug_from_path(path):
    return os.path.splitext(os.path.basename(path))[0]


def get_field_line(fm_text, field):
    """Return the raw line for `field:` if present in the front matter text."""
    for line in fm_text.splitlines():
        if line.startswith(f"{field}:"):
            return line
    return None


def upsert_field_line(fm_text, field, new_line, after_fields=("paperurl:", "permalink:")):
    """
    Insert or replace a single `field: value` line in the raw front-matter
    text, preserving everything else exactly as-is. If the field doesn't
    exist yet, it's inserted right after the first of `after_fields` found
    (falls back to appending at the end).
    """
    lines = fm_text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"{field}:"):
            lines[i] = new_line
            return "\n".join(lines) + "\n"

    for anchor in after_fields:
        for i, line in enumerate(lines):
            if line.startswith(anchor):
                lines.insert(i + 1, new_line)
                return "\n".join(lines) + "\n"

    lines.append(new_line)
    return "\n".join(lines) + "\n"
