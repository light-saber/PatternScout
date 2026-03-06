"""Direct scraping client for public design pattern sources."""
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin
import logging
import requests

from scrapling.parser import Selector

logger = logging.getLogger(__name__)


class DesignSitesClient:
    """Scrapes design pattern sources directly when API search is unavailable."""
    STOPWORDS = {
        "a", "an", "and", "app", "design", "flow", "for", "in", "interface",
        "of", "page", "screen", "screenshot", "the", "to", "ui", "ux", "with",
    }
    QUERY_ALIASES = {
        "search": ["results", "discover", "browse"],
        "results": ["search", "listing", "browse"],
        "filter": ["filters", "refine", "facets"],
        "sort": ["sorting", "rank", "ranked"],
        "checkout": ["cart", "payment", "billing"],
        "food": ["restaurant", "delivery", "menu", "eats"],
        "ordering": ["order", "delivery", "cart", "menu"],
        "order": ["ordering", "delivery", "cart", "menu"],
        "empty": ["blank", "zero", "no-results"],
        "state": ["status", "placeholder", "empty"],
        "onboarding": ["signup", "welcome", "getting-started"],
    }

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PatternScout/0.1"})

    def search_pageflows(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Search Pageflows and return screenshot candidates.
        Uses Pageflows post pages and extracts a representative screenshot URL.
        """
        seen: set[str] = set()
        ranked_results: List[tuple[int, Dict]] = []
        for search_query in self._query_variants(query):
            for post_url in self._search_pageflows_posts(search_query):
                if post_url in seen:
                    continue
                seen.add(post_url)

                extracted = self._extract_pageflows_post_image(post_url)
                if not extracted:
                    continue
                candidate = {
                    "title": extracted.get("title", ""),
                    "image_url": extracted["image_url"],
                    "source_url": post_url,
                    "source_type": "pageflows",
                }
                score = self._score_candidate(query, candidate)
                if score <= 0:
                    continue
                ranked_results.append((score, candidate))

                if len(ranked_results) >= num_results * 3:
                    break
            if len(ranked_results) >= num_results * 3:
                break

        ranked_results.sort(key=lambda item: item[0], reverse=True)
        return [candidate for _, candidate in ranked_results[:num_results]]

    def _search_pageflows_posts(self, query: str) -> List[str]:
        search_url = f"https://pageflows.com/search/?q={quote_plus(query)}"
        try:
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Pageflows search request failed for '{query}': {e}")
            return []

        page = Selector(response.text, url=search_url)
        post_links = page.css('a[href*="/post/"]')
        results: List[str] = []
        for link in post_links:
            href = link.attrib.get("href")
            if not href:
                continue
            results.append(urljoin(search_url, href))
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

    def _score_candidate(self, query: str, candidate: Dict[str, str]) -> int:
        haystack = " ".join(
            [
                candidate.get("title", ""),
                candidate.get("source_url", ""),
                candidate.get("image_url", ""),
            ]
        ).lower()
        tokens = self._tokenize(query)
        if not tokens:
            return 1

        overlap = sum(1 for token in tokens if token in haystack)
        alias_overlap = sum(1 for token in self._expand_tokens(tokens) if token in haystack)

        if overlap == 0 and alias_overlap == 0:
            return 0

        score = overlap * 5 + alias_overlap * 2
        if "/post/ios/" in haystack or "/post/android/" in haystack:
            score += 1
        return score

    def _tokenize(self, query: str) -> List[str]:
        tokens = [
            token for token in re.findall(r"[a-z0-9]+", (query or "").lower())
            if token not in self.STOPWORDS and len(token) > 2
        ]
        return list(dict.fromkeys(tokens))

    def _expand_tokens(self, tokens: List[str]) -> List[str]:
        expanded: List[str] = []
        for token in tokens:
            expanded.extend(self.QUERY_ALIASES.get(token, []))
        return list(dict.fromkeys(expanded))

    def _query_variants(self, query: str) -> List[str]:
        tokens = self._tokenize(query)
        aliases = self._expand_tokens(tokens)

        variants: List[str] = [query.strip()]
        if tokens:
            variants.append(" ".join(tokens))
            variants.extend(tokens[:3])
        variants.extend(aliases[:4])

        deduped: List[str] = []
        seen: set[str] = set()
        for variant in variants:
            cleaned = (variant or "").strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            deduped.append(cleaned)
        return deduped
