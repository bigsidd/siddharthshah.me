#!/usr/bin/env python3
"""Update the homepage <lastmod> in public/sitemap.xml."""
import re
import sys
from datetime import date
from pathlib import Path

SITEMAP_PATH = Path(__file__).parent / "public" / "sitemap.xml"
HOMEPAGE_LOC = "https://siddharthshah.me/"


def main():
    new_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    text = SITEMAP_PATH.read_text()

    pattern = re.compile(
        r"(<url>\s*<loc>" + re.escape(HOMEPAGE_LOC) + r"</loc>\s*<lastmod>)"
        r"[^<]*"
        r"(</lastmod>)"
    )
    updated, count = pattern.subn(r"\g<1>" + new_date + r"\g<2>", text)
    if count == 0:
        print("Homepage entry not found; no changes made.")
        return

    if updated == text:
        print(f"lastmod already {new_date}; no changes made.")
        return

    SITEMAP_PATH.write_text(updated)
    print(f"Updated homepage lastmod to {new_date}")


if __name__ == "__main__":
    main()
