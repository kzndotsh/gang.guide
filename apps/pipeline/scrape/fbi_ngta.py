"""Scrape FBI National Gang Threat Assessment (NGTA) and National Gang Report (NGR) PDFs.

Sources:
  - 2009 NGTA: DOJ/NDIC archive (9.4MB, 48 pages)
  - 2011 NGTA: FBI file-repository (5.2MB, 100 pages)
  - 2015 NGR:  FBI file-repository (5.3MB, 68 pages)

Note: 2013 NGR PDF is not publicly archived. The 2011 NGTA is the most
comprehensive edition with the most named org data.

These are thematic intelligence reports, not per-org profiles. Each PDF
is saved as a single content.txt for pipeline extraction. The LLM will
extract orgs, founding years, membership estimates, and alliance/rivalry
data from the narrative text.

Usage:
    python -m apps.pipeline.scrape.fbi_ngta
    python -m apps.pipeline.scrape.fbi_ngta --force
"""

import argparse

import pypdf

from .common import DATA_RAW, fetch_with_retry, get_client, page_exists

SOURCE = "fbi_ngta"

PDF_SOURCES = [
    {
        "slug": "ngta-2009",
        "url": "https://www.justice.gov/ndic/pubs32/32146/32146p.pdf",
        "title": "FBI/NDIC: National Gang Threat Assessment 2009",
        "fallback_url": "https://web.archive.org/web/2010/https://www.justice.gov/ndic/pubs32/32146/32146p.pdf",
    },
    {
        "slug": "ngta-2011",
        "url": "https://www.fbi.gov/file-repository/stats-services-publications-2011-national-gang-threat-assessment-2011%20national%20gang%20threat%20assessment%20%20emerging%20trends.pdf",
        "title": "FBI: National Gang Threat Assessment 2011 — Emerging Trends",
    },
    {
        "slug": "ngr-2015",
        "url": "https://www.fbi.gov/file-repository/reports-and-publications/stats-services-publications-national-gang-report-2015.pdf",
        "title": "FBI: National Gang Report 2015",
    },
]


def extract_pdf_text(pdf_path: str) -> str | None:
    """Extract plain text from a PDF file using pypdf."""
    try:
        reader = pypdf.PdfReader(pdf_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(p.strip() for p in pages if p.strip())
    except Exception as e:
        print(f"  [pdf] extraction error: {e}")
        return None


def save_content(slug: str, url: str, content: str) -> None:
    out_dir = DATA_RAW / SOURCE / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "content.txt").write_text(content, encoding="utf-8")
    (out_dir / "url.txt").write_text(url + "\n", encoding="utf-8")


def scrape(force: bool = False) -> None:
    client = get_client()

    for doc in PDF_SOURCES:
        slug = doc["slug"]
        pdf_path = DATA_RAW / SOURCE / f"{slug}.pdf"

        if not force and page_exists(SOURCE, slug):
            print(f"  [skip] {slug}")
            continue

        # Download PDF if not cached
        if not pdf_path.exists():
            url = doc["url"]
            resp = fetch_with_retry(client, url)
            if not resp or not resp.content.startswith(b"%PDF"):
                # Try fallback URL if available
                fallback = doc.get("fallback_url")
                if fallback:
                    resp = fetch_with_retry(client, fallback)
                if not resp or not resp.content.startswith(b"%PDF"):
                    print(f"  [fail] {slug} — could not download PDF")
                    continue
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(resp.content)
            print(f"  [dl] {slug} ({len(resp.content) // 1024}KB)")

        # Extract text
        text = extract_pdf_text(str(pdf_path))
        if not text:
            print(f"  [fail] {slug} — text extraction failed")
            continue

        content = f"{doc['title']}\n\n{text}"
        save_content(slug, doc["url"], content)
        words = len(text.split())
        print(f"  [ok] {slug} ({words:,} words)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape FBI National Gang Threat Assessment PDFs")
    parser.add_argument("--force", action="store_true", help="Re-scrape already-saved pages")
    args = parser.parse_args()
    scrape(force=args.force)


if __name__ == "__main__":
    main()
