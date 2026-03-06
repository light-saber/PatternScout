"""Google Custom Search API client for fetching UI screenshots"""
import logging
import re
from urllib.parse import urlparse

import requests
from typing import List, Dict, Optional
from app.core.config import settings

from scrapling.parser import Selector

logger = logging.getLogger(__name__)

class GoogleImagesClient:
    """Client for Google Custom Search API (Image search)"""
    
    BASE_URL = "https://www.googleapis.com/customsearch/v1"
    BLOCKED_DOMAINS = {
        "apps.apple.com",
        "play.google.com",
        "appadvice.com",
        "apkcombo.com",
        "apkpure.com",
        "uptodown.com",
    }
    STOPWORDS = {
        "a", "an", "and", "app", "design", "flow", "for", "in", "interface",
        "of", "page", "screen", "screenshot", "the", "to", "ui", "ux", "with",
    }
    
    def __init__(self, api_key: Optional[str] = None, cx: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.cx = cx or settings.GOOGLE_CX
        
        if not self.api_key or not self.cx:
            raise ValueError("GOOGLE_API_KEY and GOOGLE_CX must be set in environment")
    
    def search(
        self, 
        query: str, 
        num_results: int = 10,
        image_type: Optional[str] = None,  # Google values: clipart, face, lineart, news, photo, animated, stock
        safe: str = "active"
    ) -> List[Dict]:
        """
        Search for images using Google Custom Search API
        
        Args:
            query: Search query (e.g., "e-commerce checkout flow")
            num_results: Number of results to return (max 10 per API call)
            image_type: Filter by image type
            safe: Safe search setting
            
        Returns:
            List of image results with url, title, source
        """
        results = []
        ranked_results = []
        start_index = 1
        enriched_query = self._build_query(query)
        
        # Google API maxes at 10 results per call, 100 total
        while len(results) < num_results and start_index <= 91:
            params = {
                "key": self.api_key,
                "cx": self.cx,
                "q": enriched_query,
                "searchType": "image",
                "num": min(10, num_results - len(results)),
                "start": start_index,
                "safe": safe,
            }
            
            if image_type:
                params["imgType"] = image_type
            
            try:
                response = requests.get(self.BASE_URL, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                items = data.get("items", [])
                if not items:
                    break
                
                for item in items:
                    candidate = {
                        "title": item.get("title", ""),
                        "image_url": item.get("link", ""),
                        "source_url": item.get("image", {}).get("contextLink", ""),
                        "thumbnail_url": item.get("image", {}).get("thumbnailLink", ""),
                        "width": item.get("image", {}).get("width", 0),
                        "height": item.get("image", {}).get("height", 0),
                    }
                    score = self._score_result(query, candidate)
                    if score <= 0:
                        continue
                    ranked_results.append((score, candidate))
                    results.append(candidate)
                
                start_index += len(items)
                
                # Check if there are more results
                if "queries" in data and "nextPage" in data["queries"]:
                    continue
                else:
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Google API request failed: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error in Google search: {e}")
                break
        
        ranked_results.sort(key=lambda item: item[0], reverse=True)
        return [candidate for _, candidate in ranked_results[:num_results]]

    def extract_page_title(self, url: str) -> Optional[str]:
        """
        Fetch source page and parse title with Scrapling for cleaner context labels.
        """
        try:
            response = requests.get(
                url,
                timeout=10,
                headers={"User-Agent": "PatternScout/0.1"},
            )
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return None

            page = Selector(response.text, url=url)
            title = (page.css("title::text").get() or "").strip()
            return title or None
        except Exception:
            return None

    def download_image(self, image_url: str, local_path: str) -> bool:
        """Download an image to local storage"""
        try:
            response = requests.get(image_url, timeout=30, stream=True)
            response.raise_for_status()
            
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
        except Exception as e:
            logger.error(f"Failed to download image {image_url}: {e}")
            return False

    def _build_query(self, query: str) -> str:
        return f"{query} UI screenshot UX pattern"

    def _score_result(self, query: str, item: Dict[str, str]) -> int:
        title = item.get("title", "")
        source_url = item.get("source_url", "")
        image_url = item.get("image_url", "")

        if self._is_blocked_source(title, source_url, image_url):
            return 0

        haystack = " ".join([title, source_url, image_url]).lower()
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return 1

        overlap = sum(1 for token in query_tokens if token in haystack)
        if overlap == 0:
            return 0

        score = overlap * 3
        if "dribbble.com" in haystack or "behance.net" in haystack or "pageflows.com" in haystack:
            score += 2
        if "pinterest." in haystack:
            score -= 1
        return score

    def _is_blocked_source(self, title: str, source_url: str, image_url: str) -> bool:
        title_lower = (title or "").lower()
        if "app store" in title_lower or "google play" in title_lower:
            return True

        for raw_url in (source_url, image_url):
            hostname = urlparse(raw_url or "").hostname or ""
            hostname = hostname.lower()
            if hostname in self.BLOCKED_DOMAINS:
                return True

        return False

    def _tokenize(self, query: str) -> List[str]:
        tokens = [
            token for token in re.findall(r"[a-z0-9]+", (query or "").lower())
            if token not in self.STOPWORDS and len(token) > 2
        ]
        return list(dict.fromkeys(tokens))
