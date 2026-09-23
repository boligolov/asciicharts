#!/usr/bin/env python3
"""Screenshot the site's social preview card (site/src/pages/og.astro) into site/public/og.png,
the og:image / twitter:image every link preview shows.

    cd site && npm run dev                          # in another terminal
    python scripts/og_image.py                      # or: python scripts/og_image.py http://localhost:4321/og/

Needs Playwright with Chromium (pip install playwright && playwright install chromium) — a tool for
this one-off job, not a dependency of the project. Re-run it when the card or its hero chart changes,
and commit og.png.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "site" / "public" / "og.png"


def main(argv):
    url = argv[0] if argv else "http://localhost:4321/og/"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        page.goto(url, wait_until="networkidle")  # the dev server injects its CSS after load
        page.evaluate("document.fonts.ready")
        page.evaluate("document.querySelector('astro-dev-toolbar')?.remove()")
        page.screenshot(path=str(OUT))
        browser.close()
    print(f"wrote {OUT.relative_to(OUT.parents[2])} from {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
