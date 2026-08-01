"""SQLAlchemy ORM models for Codebase Steward."""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class IndexStatusEnum(str, enum.Enum):
    """Status of repository indexing."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Repository(Base):
    """Repository metadata."""
    __tablename__ = "repositories"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    url = Column(String, unique=True, nullable=False)
    project = Column(String, nullable=True)
    status = Column(Enum(IndexStatusEnum), default=IndexStatusEnum.PENDING, index=True)
    last_indexed = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    snippets = relationship("CodeSnippet", back_populates="repository", cascade="all, delete-orphan")
    index_jobs = relationship("IndexJob", back_populates="repository", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Repository(id={self.id}, name={self.name}, status={self.status})>"


class CodeSnippet(Base):
    """Code snippets indexed from repositories."""
    __tablename__ = "code_snippets"
    
    id = Column(String, primary_key=True)
    repo_id = Column(String, ForeignKey("repositories.id"), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    language = Column(String, nullable=False)  # Python, Go, Java, etc.
    content = Column(Text, nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    
    # Metadata for ranking
    function_name = Column(String, nullable=True)
    class_name = Column(String, nullable=True)
    doc_string = Column(Text, nullable=True)
    
    # Vector embedding (stored in Milvus, ID reference here)
    embedding_id = Column(String, unique=True, nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    repository = relationship("Repository", back_populates="snippets")
    
    def __repr__(self):
        return f"<CodeSnippet(id={self.id}, file={self.file_path}, lines={self.start_line}-{self.end_line})>"


class IndexJob(Base):
    """Track indexing jobs for repositories."""
    __tablename__ = "index_jobs"
    
    id = Column(String, primary_key=True)
    repo_id = Column(String, ForeignKey("repositories.id"), nullable=False, index=True)
    status = Column(Enum(IndexStatusEnum), default=IndexStatusEnum.PENDING, index=True)
    celery_task_id = Column(String, unique=True, nullable=True)
    
    # Progress tracking
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    total_snippets = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    repository = relationship("Repository", back_populates="index_jobs")
    
    def __repr__(self):
        return f"<IndexJob(id={self.id}, repo_id={self.repo_id}, status={self.status})>"


class SuggestionRequest(Base):
    """Track code improvement suggestions."""
    __tablename__ = "suggestion_requests"
    
    id = Column(String, primary_key=True)
    snippet_id = Column(String, ForeignKey("code_snippets.id"), nullable=False, index=True)
    issue_type = Column(String, nullable=False)  # security, lint, performance, etc.
    issue_description = Column(Text, nullable=False)
    
    # Suggestion output
    suggested_fix = Column(Text, nullable=True)
    model_confidence = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SuggestionRequest(id={self.id}, issue_type={self.issue_type})>"
