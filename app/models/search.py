from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class SearchJob(Base):
    """Tracks a search query and its status"""
    __tablename__ = "search_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, scraping, analyzing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    screenshots = relationship("Screenshot", back_populates="search_job", cascade="all, delete-orphan")

class Screenshot(Base):
    """Individual screenshot from a search"""
    __tablename__ = "screenshots"
    
    id = Column(Integer, primary_key=True, index=True)
    search_job_id = Column(Integer, ForeignKey("search_jobs.id"), nullable=False)
    
    # Source info
    source_url = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    source_type = Column(String, default="google_images")  # google_images, mobbin, etc.
    
    # Local storage
    local_path = Column(String, nullable=True)
    
    # Analysis status
    analysis_status = Column(String, default="pending")  # pending, completed, failed
    
    # Raw analysis from Qwen2.5-VL
    raw_description = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)  # OCR results
    
    # Structured data
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    search_job = relationship("SearchJob", back_populates="screenshots")
    tags = relationship("Tag", back_populates="screenshot", cascade="all, delete-orphan")
    embedding = relationship("Embedding", back_populates="screenshot", uselist=False, cascade="all, delete-orphan")

class Tag(Base):
    """UI pattern tags extracted from screenshots"""
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    screenshot_id = Column(Integer, ForeignKey("screenshots.id"), nullable=False)
    
    tag_name = Column(String, nullable=False)  # e.g., "dropdown", "swatches", "modal"
    tag_category = Column(String, nullable=True)  # e.g., "component", "layout", "interaction"
    confidence = Column(Float, default=1.0)  # 0.0 to 1.0
    
    screenshot = relationship("Screenshot", back_populates="tags")

class Embedding(Base):
    """Vector embeddings for similarity search"""
    __tablename__ = "embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    screenshot_id = Column(Integer, ForeignKey("screenshots.id"), nullable=False, unique=True)
    
    # Store as JSON array or use sqlite-vec if available
    vector = Column(JSON, nullable=True)  # Fallback JSON storage
    
    screenshot = relationship("Screenshot", back_populates="embedding")
