"""API endpoints for search and analysis"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from typing import List, Optional
from pathlib import Path
import logging
import json
import re

from app.core.database import get_db
from app.core.config import settings
from app.models.search import SearchJob, Screenshot, Tag
from app.schemas.search import (
    SearchRequest,
    SearchResponse,
    JobStatus,
    ScreenshotResponse,
    PatternCluster,
    HybridRequest,
    HybridIdea,
)
from app.scrapers.google_images import GoogleImagesClient
from app.scrapers.design_sites import DesignSitesClient
from app.services.ollama import OllamaClient
from app.services.clustering import ClusteringService

router = APIRouter()
logger = logging.getLogger(__name__)

# Ensure storage directory exists
SCREENSHOTS_DIR = Path(settings.SCREENSHOTS_DIR)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/search", response_model=SearchResponse)
async def create_search(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new search job
    Triggers background scraping and returns job ID
    """
    # Create search job
    job = SearchJob(
        query=request.query,
        status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Trigger background scraping
    background_tasks.add_task(
        scrape_and_analyze,
        job_id=job.id,
        query=request.query,
        num_results=request.num_results or 10
    )
    
    return SearchResponse(
        job_id=job.id,
        query=job.query,
        status=job.status,
        message="Search job created and processing"
    )

@router.get("/search/{job_id}/status", response_model=JobStatus)
async def get_search_status(job_id: int, db: Session = Depends(get_db)):
    """Get the status of a search job"""
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    screenshot_count = db.query(Screenshot).filter(
        Screenshot.search_job_id == job_id
    ).count()
    
    analyzed_count = db.query(Screenshot).filter(
        Screenshot.search_job_id == job_id,
        Screenshot.analysis_status == "completed"
    ).count()
    
    return JobStatus(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        total_screenshots=screenshot_count,
        analyzed_screenshots=analyzed_count,
        error_message=job.error_message
    )

@router.get("/search/{job_id}/results", response_model=List[ScreenshotResponse])
async def get_search_results(
    job_id: int,
    tag: Optional[str] = None,
    source_type: Optional[str] = None,
    analysis_status: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|title|source_type|analysis_status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """Get results for a completed search job"""
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    query = db.query(Screenshot).filter(Screenshot.search_job_id == job_id)
    
    if tag:
        query = query.join(Tag).filter(Tag.tag_name == tag)

    if source_type:
        query = query.filter(Screenshot.source_type == source_type)

    if analysis_status:
        query = query.filter(Screenshot.analysis_status == analysis_status)

    sort_column = {
        "created_at": Screenshot.created_at,
        "title": Screenshot.title,
        "source_type": Screenshot.source_type,
        "analysis_status": Screenshot.analysis_status,
    }[sort_by]
    sort_fn = asc if sort_order == "asc" else desc
    query = query.order_by(sort_fn(sort_column), desc(Screenshot.id))
    
    screenshots = query.all()
    
    return [
        ScreenshotResponse(
            id=s.id,
            image_url=s.image_url,
            source_url=s.source_url,
            title=s.title,
            source_type=s.source_type,
            local_path=s.local_path,
            analysis_status=s.analysis_status,
            description=s.raw_description,
            tags=[{"tag": t.tag_name, "category": t.tag_category, "confidence": t.confidence} 
                  for t in s.tags]
        )
        for s in screenshots
    ]


@router.get("/search/{job_id}/clusters", response_model=List[PatternCluster])
async def get_search_clusters(
    job_id: int,
    min_cluster_size: int = 2,
    max_clusters: int = 10,
    db: Session = Depends(get_db),
):
    """Get clustered patterns for analyzed results."""
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    screenshots = db.query(Screenshot).filter(
        Screenshot.search_job_id == job_id,
        Screenshot.analysis_status == "completed",
    ).all()

    service = ClusteringService()
    return service.cluster_screenshots(
        screenshots=screenshots,
        min_cluster_size=max(1, min_cluster_size),
        max_clusters=max(1, max_clusters),
    )


@router.post("/search/{job_id}/hybrid", response_model=HybridIdea)
async def generate_hybrid_idea(
    job_id: int,
    request: HybridRequest,
    db: Session = Depends(get_db),
):
    """Generate a hybrid idea using selected analyzed patterns."""
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    query = db.query(Screenshot).filter(
        Screenshot.search_job_id == job_id,
        Screenshot.analysis_status == "completed",
    )
    screenshots = query.all()
    if not screenshots:
        raise HTTPException(status_code=400, detail="No analyzed screenshots available")

    if request.screenshot_ids:
        selected = [s for s in screenshots if s.id in set(request.screenshot_ids)]
    else:
        selected = screenshots

    if not selected:
        raise HTTPException(status_code=400, detail="No matching screenshots found for selection")

    max_patterns = max(2, min(5, request.max_patterns))
    patterns = []
    for shot in selected[:max_patterns]:
        text = (shot.raw_description or "").strip() or (shot.title or "").strip() or shot.source_url
        if text:
            patterns.append(text)

    if len(patterns) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 patterns to generate hybrid")

    ollama = OllamaClient()
    raw = ollama.generate_hybrid(patterns)
    parsed = _parse_hybrid_payload(raw)
    if not parsed:
        parsed = ollama.fallback_hybrid(patterns)

    return HybridIdea(
        name=parsed.get("name", "Hybrid UI Pattern"),
        description=parsed.get("description", "A practical blend of selected UI patterns."),
        best_for=parsed.get("best_for", "Exploring alternative interaction approaches."),
        key_features=parsed.get("key_features", []),
    )

def scrape_and_analyze(job_id: int, query: str, num_results: int):
    """Background task: scrape images and analyze them"""
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
        if not job:
            return
        
        # Update status to scraping
        job.status = "scraping"
        db.commit()
        
        # Search for images via Google first, then direct scraping fallback.
        results = []
        google_scraper = None
        fallback_scraper = None
        try:
            google_scraper = GoogleImagesClient()
            results = google_scraper.search(query, num_results=num_results)
        except Exception as e:
            logger.warning(f"Google image search unavailable: {e}")

        if not results:
            fallback_scraper = DesignSitesClient()
            results = fallback_scraper.search_pageflows(query, num_results=num_results)
        
        if not results:
            job.status = "completed"
            job.error_message = "No images found"
            db.commit()
            return
        
        # Create screenshot records
        for result in results:
            title = result["title"]
            if not title or len(title.strip()) < 5:
                if google_scraper:
                    page_title = google_scraper.extract_page_title(result["source_url"])
                    if page_title:
                        title = page_title

            screenshot = Screenshot(
                search_job_id=job_id,
                source_url=result["source_url"],
                image_url=result["image_url"],
                title=title,
                source_type=result.get("source_type", "google_images")
            )
            db.add(screenshot)
        
        db.commit()
        
        # Download images
        job.status = "downloading"
        db.commit()
        
        for screenshot in db.query(Screenshot).filter(
            Screenshot.search_job_id == job_id
        ).all():
            local_path = SCREENSHOTS_DIR / f"{screenshot.id}.jpg"
            downloader = google_scraper or fallback_scraper
            if downloader is None:
                continue
            if downloader.download_image(screenshot.image_url, str(local_path)):
                screenshot.local_path = str(local_path)
                db.commit()
        
        # Analyze images
        job.status = "analyzing"
        db.commit()
        
        ollama = OllamaClient()
        
        for screenshot in db.query(Screenshot).filter(
            Screenshot.search_job_id == job_id,
            Screenshot.local_path.isnot(None)
        ).all():
            try:
                if settings.OLLAMA_USE_VISION:
                    analysis = ollama.analyze_screenshot(screenshot.local_path)
                else:
                    analysis = ollama.analyze_metadata(
                        title=screenshot.title,
                        source_url=screenshot.source_url,
                    )

                if not analysis.get("success"):
                    analysis = ollama.fallback_metadata_analysis(
                        title=screenshot.title,
                        source_url=screenshot.source_url,
                    )

                description = (analysis.get("description") or "").strip()
                if not description:
                    description = f"UI pattern from {screenshot.source_url}"
                screenshot.raw_description = description
                screenshot.analysis_status = "completed"

                # Extract and save tags
                tags = ollama.extract_tags(description)
                if not tags:
                    tags = ollama.fallback_tags(
                        title=screenshot.title,
                        source_url=screenshot.source_url,
                        description=description,
                    )
                for tag_data in tags:
                    tag = Tag(
                        screenshot_id=screenshot.id,
                        tag_name=tag_data.get("tag", ""),
                        tag_category=tag_data.get("category", "general"),
                        confidence=tag_data.get("confidence", 1.0)
                    )
                    db.add(tag)
                
                db.commit()
                
            except Exception as e:
                fallback = ollama.fallback_metadata_analysis(
                    title=screenshot.title,
                    source_url=screenshot.source_url,
                )
                screenshot.raw_description = fallback.get(
                    "description",
                    f"UI pattern from {screenshot.source_url}",
                )
                screenshot.analysis_status = "completed"
                for tag_data in ollama.fallback_tags(
                    title=screenshot.title,
                    source_url=screenshot.source_url,
                    description=screenshot.raw_description,
                ):
                    db.add(
                        Tag(
                            screenshot_id=screenshot.id,
                            tag_name=tag_data.get("tag", ""),
                            tag_category=tag_data.get("category", "general"),
                            confidence=tag_data.get("confidence", 1.0),
                        )
                    )
                db.commit()
                continue
        
        job.status = "completed"
        db.commit()
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()


def _parse_hybrid_payload(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return _sanitize_hybrid_payload(payload)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            payload = json.loads(match.group(0))
            if isinstance(payload, dict):
                return _sanitize_hybrid_payload(payload)
        except Exception:
            pass

    return {
        "name": "Hybrid UI Pattern",
        "description": text,
        "best_for": "Exploring alternative interaction approaches.",
        "key_features": [],
    }


def _sanitize_hybrid_payload(payload: dict) -> dict:
    key_features = payload.get("key_features", [])
    if not isinstance(key_features, list):
        key_features = []
    key_features = [str(f).strip() for f in key_features if str(f).strip()][:6]

    return {
        "name": str(payload.get("name", "Hybrid UI Pattern")).strip() or "Hybrid UI Pattern",
        "description": str(payload.get("description", "")).strip(),
        "best_for": str(payload.get("best_for", "")).strip() or "Exploring alternative interaction approaches.",
        "key_features": key_features,
    }
