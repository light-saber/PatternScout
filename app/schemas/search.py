"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class SearchRequest(BaseModel):
    """Request to create a new search"""
    query: str
    num_results: Optional[int] = 10

class SearchResponse(BaseModel):
    """Response after creating a search"""
    job_id: int
    query: str
    status: str
    message: str

class JobStatus(BaseModel):
    """Status of a search job"""
    job_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    total_screenshots: int
    analyzed_screenshots: int
    error_message: Optional[str] = None

class TagResponse(BaseModel):
    """Tag information"""
    tag: str
    category: str
    confidence: float

class ScreenshotResponse(BaseModel):
    """Screenshot with analysis"""
    id: int
    image_url: str
    source_url: str
    title: Optional[str]
    source_type: str
    local_path: Optional[str]
    analysis_status: str
    description: Optional[str]
    tags: List[TagResponse]

class PatternCluster(BaseModel):
    """Cluster of similar patterns"""
    pattern_name: str
    count: int
    examples: List[int]  # Screenshot IDs
    common_tags: List[str]

class HybridRequest(BaseModel):
    """Request to generate a hybrid idea from selected screenshots."""
    screenshot_ids: Optional[List[int]] = None
    max_patterns: int = 3

class HybridIdea(BaseModel):
    """Generated hybrid pattern idea"""
    name: str
    description: str
    best_for: str
    key_features: List[str]
