"""Direct scraping client for public design pattern sources."""
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin
import logging
import requests

from scrapling.parser import Selector

logger = logging.getLogger(__name__)


class DesignSitesClient:
    """Scrapes design pattern sources directly when API search is unavailable."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PatternScout/0.1"})

    def search_pageflows(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Search Pageflows and return screenshot candidates.
        Uses Pageflows post pages and extracts a representative screenshot URL.
        """
        search_url = f"https://pageflows.com/search/?q={quote_plus(query)}"
        try:
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Pageflows search request failed: {e}")
            return []

        page = Selector(response.text, url=search_url)
        post_links = page.css('a[href*="/post/"]')
        if not post_links:
            return []

        seen: set[str] = set()
        results: List[Dict] = []

        for link in post_links:
            href = link.attrib.get("href")
            if not href:
                continue

            post_url = urljoin(search_url, href)
            if post_url in seen:
                continue
            seen.add(post_url)

            extracted = self._extract_pageflows_post_image(post_url)
            if not extracted:
                continue

            results.append(
                {
                    "title": extracted.get("title", ""),
                    "image_url": extracted["image_url"],
                    "source_url": post_url,
                    "source_type": "pageflows",
                }
            )

            if len(results) >= num_results:
                break

        return results

    def _extract_pageflows_post_image(self, post_url: str) -> Optional[Dict[str, str]]:
        """Extract a likely screenshot URL from a Pageflows post page."""
        try:
            response = self.session.get(post_url, timeout=30)
            response.raise_for_status()
            page = Selector(response.text, url=post_url)
        except Exception as e:
            logger.debug(f"Failed to fetch Pageflows post {post_url}: {e}")
            return None

        title = (page.css("title::text").get() or "").strip()

        # Poster frames are usually representative screenshots.
        poster = page.css("video::attr(poster)").get()
        image_url = self._normalize_image_url(post_url, poster)
        if image_url:
            return {"title": title, "image_url": image_url}

        # Fallback: scan image tags for media-hosted screenshots.
        for raw in page.css("img::attr(src), img::attr(data-src)").getall():
            candidate = self._normalize_image_url(post_url, raw)
            if not candidate:
                continue
            if "/static/website/images/" in candidate:
                continue
            if "/media/logos/" in candidate:
                continue
            if "/media/" in candidate:
                return {"title": title, "image_url": candidate}

        return None

    def download_image(self, image_url: str, local_path: str) -> bool:
        """Download an image to local storage."""
        try:
            response = self.session.get(image_url, timeout=30, stream=True)
            response.raise_for_status()

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True
        except Exception as e:
            logger.error(f"Failed to download image {image_url}: {e}")
            return False

    @staticmethod
    def _normalize_image_url(base_url: str, raw_url: Optional[str]) -> Optional[str]:
        if not raw_url:
            return None

        url = raw_url.strip()
        if not url:
            return None

        if url.startswith("data:"):
            return None

        return urljoin(base_url, url)
