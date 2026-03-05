"""Google Custom Search API client for fetching UI screenshots"""
import requests
from typing import List, Dict, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class GoogleImagesClient:
    """Client for Google Custom Search API (Image search)"""
    
    BASE_URL = "https://www.googleapis.com/customsearch/v1"
    
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
        start_index = 1
        
        # Google API maxes at 10 results per call, 100 total
        while len(results) < num_results and start_index <= 91:
            params = {
                "key": self.api_key,
                "cx": self.cx,
                "q": query,
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
                    results.append({
                        "title": item.get("title", ""),
                        "image_url": item.get("link", ""),
                        "source_url": item.get("image", {}).get("contextLink", ""),
                        "thumbnail_url": item.get("image", {}).get("thumbnailLink", ""),
                        "width": item.get("image", {}).get("width", 0),
                        "height": item.get("image", {}).get("height", 0),
                    })
                
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
        
        return results[:num_results]
    
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
