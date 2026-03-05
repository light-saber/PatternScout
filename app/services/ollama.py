"""Ollama client for local LLM inference with Qwen2.5-VL and Qwen 3.5"""
import requests
import base64
from typing import Optional, Dict, Any, List
from pathlib import Path
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for Ollama local inference"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.vision_model = settings.OLLAMA_VISION_MODEL
        self.text_model = settings.OLLAMA_TEXT_MODEL
    
    def analyze_screenshot(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze a UI screenshot using Qwen2.5-VL
        
        Returns structured analysis including:
        - description: Overall UI description
        - components: List of UI components detected
        - layout: Layout pattern description
        - text: Any text visible in the image (OCR)
        """
        try:
            # Read and encode image
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            image_b64 = base64.b64encode(image_bytes).decode()
            
            # Construct prompt for UI analysis
            prompt = """Analyze this UI screenshot and provide a structured response in JSON format:

{
    "description": "Brief description of what this UI shows",
    "component_type": "Primary UI component (dropdown, swatches, modal, form, etc.)",
    "layout_pattern": "How elements are arranged (grid, list, stacked, etc.)",
    "interaction_type": "How user interacts (click, tap, select, etc.)",
    "key_elements": ["list", "of", "key", "ui", "elements"],
    "visible_text": "Any text visible in the UI (labels, buttons, etc.)",
    "design_pattern": "Named pattern if recognizable (e.g., 'Amazon-style dropdown')"
}

Be concise. Focus on UI/UX patterns."""
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                    "format": "json"
                },
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get("response", "{}")
            
            # Parse JSON response
            try:
                parsed = json.loads(response_text)
                return {
                    "success": True,
                    "description": parsed.get("description", ""),
                    "component_type": parsed.get("component_type", ""),
                    "layout_pattern": parsed.get("layout_pattern", ""),
                    "interaction_type": parsed.get("interaction_type", ""),
                    "key_elements": parsed.get("key_elements", []),
                    "visible_text": parsed.get("visible_text", ""),
                    "design_pattern": parsed.get("design_pattern", ""),
                    "raw": response_text
                }
            except json.JSONDecodeError:
                # Return raw text if JSON parsing fails
                return {
                    "success": True,
                    "description": response_text,
                    "raw": response_text
                }
                
        except Exception as e:
            logger.error(f"Ollama vision analysis failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def analyze_metadata(self, title: Optional[str], source_url: Optional[str]) -> Dict[str, Any]:
        """Generate a pattern description from text metadata only."""
        prompt = f"""You are analyzing a UI screenshot using metadata only.

Title: {title or "N/A"}
Source URL: {source_url or "N/A"}

Return concise JSON:
{{
  "description": "One short sentence describing likely UI pattern",
  "component_type": "primary component",
  "layout_pattern": "layout guess",
  "interaction_type": "interaction guess",
  "design_pattern": "named pattern if likely"
}}"""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.text_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=90
            )
            response.raise_for_status()
            result = response.json()
            response_text = result.get("response", "{}")

            try:
                parsed = json.loads(response_text)
                return {
                    "success": True,
                    "description": parsed.get("description", ""),
                    "component_type": parsed.get("component_type", ""),
                    "layout_pattern": parsed.get("layout_pattern", ""),
                    "interaction_type": parsed.get("interaction_type", ""),
                    "design_pattern": parsed.get("design_pattern", ""),
                    "raw": response_text,
                }
            except json.JSONDecodeError:
                return {"success": True, "description": response_text, "raw": response_text}
        except Exception as e:
            logger.error(f"Metadata analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    def extract_tags(self, description: str) -> List[Dict[str, Any]]:
        """
        Extract structured tags from a screenshot description
        Returns list of tags with categories
        """
        prompt = f"""Given this UI description, extract relevant tags for categorization.

Description: {description}

Return JSON array of tags:
[
    {{"tag": "dropdown", "category": "component", "confidence": 0.95}},
    {{"tag": "e-commerce", "category": "domain", "confidence": 0.90}}
]

Categories: component, layout, interaction, domain, platform
Confidence: 0.0 to 1.0"""
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.text_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            tags = json.loads(result.get("response", "[]"))
            return tags if isinstance(tags, list) else []
            
        except Exception as e:
            logger.error(f"Tag extraction failed: {e}")
            return []
    
    def generate_hybrid(self, patterns: List[str]) -> str:
        """
        Generate a hybrid UI idea combining multiple patterns
        """
        patterns_text = "\n".join([f"- {p}" for p in patterns])
        
        prompt = f"""Given these UI patterns, generate a novel hybrid approach:

Patterns:
{patterns_text}

Describe a new UI pattern that combines the best elements of these approaches.
Be specific about the interaction design. Keep it practical and implementable.

Response format:
{{
    "name": "Name of the hybrid pattern",
    "description": "Detailed description",
    "best_for": "When to use this pattern",
    "key_features": ["feature 1", "feature 2"]
}}"""
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.text_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=60
            )
            response.raise_for_status()
            
            return response.json().get("response", "")
            
        except Exception as e:
            logger.error(f"Hybrid generation failed: {e}")
            return ""
    
    def check_model_availability(self, model_name: str) -> bool:
        """Check if a model is available in Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            models = response.json().get("models", [])
            return any(m.get("name") == model_name for m in models)
        except Exception as e:
            logger.error(f"Failed to check model availability: {e}")
            return False
