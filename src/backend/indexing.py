"""Code indexing pipeline."""
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import List, Dict, Any
import ast
from datetime import datetime

import git
from sqlalchemy.orm import Session

from models import Repository, CodeSnippet, IndexStatusEnum, IndexJob
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SUPPORTED_LANGUAGES = {".py": "Python", ".go": "Go", ".js": "JavaScript", ".ts": "TypeScript", ".java": "Java"}
IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".pytest_cache"}
IGNORE_FILES = {".gitignore", ".env", ".env.local", "package-lock.json", "yarn.lock"}


def is_ignored(path: Path, is_dir: bool = False) -> bool:
    """Check if path should be ignored."""
    name = path.name
    
    if is_dir:
        return name in IGNORE_DIRS or name.startswith(".")
    
    if name in IGNORE_FILES:
        return True
    if name.startswith("."):
        return True
    
    return False


class CodeParser:
    """Parse code files and extract semantic chunks."""
    
    @staticmethod
    def parse_python(content: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse Python file and extract functions, classes, and docstrings.
        
        Returns:
            List of chunks with start_line, end_line, content, function_name, class_name, doc_string
        """
        chunks = []
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            # Return entire file as single chunk on error
            return [{
                "start_line": 1,
                "end_line": len(content.split("\n")),
                "content": content,
                "function_name": None,
                "class_name": None,
                "doc_string": None,
            }]
        
        lines = content.split("\n")
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                chunk = {
                    "start_line": node.lineno,
                    "end_line": node.end_lineno or node.lineno,
                    "content": "\n".join(lines[node.lineno - 1:node.end_lineno or node.lineno]),
                    "function_name": node.name,
                    "class_name": None,
                    "doc_string": ast.get_docstring(node),
                }
                chunks.append(chunk)
            
            elif isinstance(node, ast.ClassDef):
                chunk = {
                    "start_line": node.lineno,
                    "end_line": node.end_lineno or node.lineno,
                    "content": "\n".join(lines[node.lineno - 1:node.end_lineno or node.lineno]),
                    "function_name": None,
                    "class_name": node.name,
                    "doc_string": ast.get_docstring(node),
                }
                chunks.append(chunk)
        
        # If no functions/classes found, treat entire file as one chunk
        if not chunks:
            chunks.append({
                "start_line": 1,
                "end_line": len(lines),
                "content": content,
                "function_name": None,
                "class_name": None,
                "doc_string": None,
            })
        
        return chunks
    
    @staticmethod
    def parse_generic(content: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Generic parser for non-Python files: chunk by size.
        """
        lines = content.split("\n")
        chunks = []
        chunk_size = settings.MAX_CHUNK_SIZE
        chunk_overlap = settings.CHUNK_OVERLAP
        
        for i in range(0, len(lines), chunk_size - chunk_overlap):
            end_idx = min(i + chunk_size, len(lines))
            chunk = {
                "start_line": i + 1,
                "end_line": end_idx,
                "content": "\n".join(lines[i:end_idx]),
                "function_name": None,
                "class_name": None,
                "doc_string": None,
            }
            chunks.append(chunk)
        
        return chunks
    
    @staticmethod
    def parse_file(file_path: str, content: str) -> List[Dict[str, Any]]:
        """Parse file and return chunks."""
        suffix = Path(file_path).suffix.lower()
        
        if suffix == ".py":
            return CodeParser.parse_python(content, file_path)
        else:
            return CodeParser.parse_generic(content, file_path)


class RepositoryIndexer:
    """Handle repository cloning and indexing."""
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = CodeParser()
    
    def clone_repository(self, repo_url: str) -> str:
        """
        Clone repository to temporary directory.
        
        Returns:
            Path to cloned repository
        """
        temp_dir = tempfile.mkdtemp()
        
        try:
            git.Repo.clone_from(repo_url, temp_dir, depth=1)
            logger.info(f"Cloned {repo_url} to {temp_dir}")
            return temp_dir
        except Exception as e:
            logger.error(f"Failed to clone {repo_url}: {e}")
            raise
    
    def discover_code_files(self, root_path: str) -> List[str]:
        """Find all code files in repository."""
        code_files = []
        root = Path(root_path)
        
        for file_path in root.rglob("*"):
            if file_path.is_dir():
                if is_ignored(file_path, is_dir=True):
                    continue
            else:
                if is_ignored(file_path, is_dir=False):
                    continue
                
                if file_path.suffix.lower() in SUPPORTED_LANGUAGES:
                    code_files.append(str(file_path))
        
        return code_files
    
    def index_repository(self, repo_url: str, project: str = None) -> Dict[str, Any]:
        """
        Full indexing pipeline.
        
        Returns:
            Dict with indexing results
        """
        # Create repository record
        repo_id = str(uuid.uuid4())
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        
        repo = Repository(
            id=repo_id,
            name=repo_name,
            url=repo_url,
            project=project,
            status=IndexStatusEnum.PENDING
        )
        self.db.add(repo)
        self.db.commit()
        
        # Create index job
        job_id = str(uuid.uuid4())
        index_job = IndexJob(
            id=job_id,
            repo_id=repo_id,
            status=IndexStatusEnum.RUNNING,
            started_at=datetime.utcnow()
        )
        self.db.add(index_job)
        self.db.commit()
        
        try:
            # Clone repository
            repo_path = self.clone_repository(repo_url)
            
            # Discover code files
            code_files = self.discover_code_files(repo_path)
            index_job.total_files = len(code_files)
            self.db.commit()
            
            logger.info(f"Found {len(code_files)} code files in {repo_name}")
            
            # Process each file
            snippets_created = 0
            for file_path in code_files:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    
                    # Get relative path
                    rel_path = os.path.relpath(file_path, repo_path)
                    file_language = SUPPORTED_LANGUAGES.get(Path(file_path).suffix.lower(), "Unknown")
                    
                    # Parse file into chunks
                    chunks = self.parser.parse_file(rel_path, content)
                    
                    # Create snippet records
                    for chunk in chunks:
                        snippet_id = str(uuid.uuid4())
                        snippet = CodeSnippet(
                            id=snippet_id,
                            repo_id=repo_id,
                            file_path=rel_path,
                            language=file_language,
                            content=chunk["content"],
                            start_line=chunk["start_line"],
                            end_line=chunk["end_line"],
                            function_name=chunk["function_name"],
                            class_name=chunk["class_name"],
                            doc_string=chunk["doc_string"],
                            embedding_id=snippet_id,  # Will be updated after embedding
                        )
                        self.db.add(snippet)
                        snippets_created += 1
                    
                    index_job.processed_files += 1
                    self.db.commit()
                
                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {e}")
                    continue
            
            # Cleanup
            import shutil
            shutil.rmtree(repo_path, ignore_errors=True)
            
            # Mark job as completed
            index_job.total_snippets = snippets_created
            index_job.status = IndexStatusEnum.COMPLETED
            index_job.completed_at = datetime.utcnow()
            
            repo.status = IndexStatusEnum.COMPLETED
            repo.last_indexed = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Indexing complete: {snippets_created} snippets created")
            
            return {
                "repo_id": repo_id,
                "job_id": job_id,
                "files_processed": index_job.processed_files,
                "snippets_created": snippets_created,
                "status": "completed"
            }
        
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            index_job.status = IndexStatusEnum.FAILED
            index_job.error_message = str(e)
            index_job.completed_at = datetime.utcnow()
            repo.status = IndexStatusEnum.FAILED
            self.db.commit()
            
            return {
                "repo_id": repo_id,
                "job_id": job_id,
                "status": "failed",
                "error": str(e)
            }
