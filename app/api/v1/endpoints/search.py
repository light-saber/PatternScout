"""API endpoints for search and analysis"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
from pathlib import Path

from app.core.database import get_db
from app.core.config import settings
from app.models.search import SearchJob, Screenshot, Tag, Embedding
from app.schemas.search import SearchRequest, SearchResponse, JobStatus, ScreenshotResponse
from app.scrapers.google_images import GoogleImagesClient
from app.services.ollama import OllamaClient

router = APIRouter()

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
    db: Session = Depends(get_db)
):
    """Get results for a completed search job"""
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    query = db.query(Screenshot).filter(Screenshot.search_job_id == job_id)
    
    if tag:
        query = query.join(Tag).filter(Tag.tag_name == tag)
    
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

async def scrape_and_analyze(job_id: int, query: str, num_results: int):
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
        
        # Initialize scraper
        scraper = GoogleImagesClient()
        
        # Search for images
        results = scraper.search(query, num_results=num_results)
        
        if not results:
            job.status = "completed"
            job.error_message = "No images found"
            db.commit()
            return
        
        # Create screenshot records
        for result in results:
            screenshot = Screenshot(
                search_job_id=job_id,
                source_url=result["source_url"],
                image_url=result["image_url"],
                title=result["title"],
                source_type="google_images"
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
            if scraper.download_image(screenshot.image_url, str(local_path)):
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
                analysis = ollama.analyze_screenshot(screenshot.local_path)
                
                if analysis.get("success"):
                    screenshot.raw_description = analysis.get("description", "")
                    screenshot.analysis_status = "completed"
                    
                    # Extract and save tags
                    tags = ollama.extract_tags(screenshot.raw_description)
                    for tag_data in tags:
                        tag = Tag(
                            screenshot_id=screenshot.id,
                            tag_name=tag_data.get("tag", ""),
                            tag_category=tag_data.get("category", "general"),
                            confidence=tag_data.get("confidence", 1.0)
                        )
                        db.add(tag)
                else:
                    screenshot.analysis_status = "failed"
                
                db.commit()
                
            except Exception as e:
                screenshot.analysis_status = "failed"
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
