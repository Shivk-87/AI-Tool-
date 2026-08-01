"""Database and vector store initialization."""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# PostgreSQL Engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,  # Test connections before using
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class MilvusVectorStore:
    """Wrapper for Milvus vector database operations."""
    
    def __init__(self):
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.db_name = settings.MILVUS_DB_NAME
        self.collection_name = settings.MILVUS_COLLECTION_NAME
        self.embedding_dim = settings.EMBEDDING_DIM
        self.collection = None
    
    def connect(self):
        """Establish connection to Milvus."""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
                db_name=self.db_name
            )
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise
    
    def create_collection_if_not_exists(self):
        """Create collection schema for code embeddings."""
        try:
            from pymilvus import utility
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"Collection {self.collection_name} already exists")
                return
            
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
                FieldSchema(name="repo_id", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="file_path", dtype=DataType.VARCHAR, max_length=512),
                FieldSchema(name="language", dtype=DataType.VARCHAR, max_length=32),
                FieldSchema(name="function_name", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="class_name", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="start_line", dtype=DataType.INT32),
                FieldSchema(name="end_line", dtype=DataType.INT32),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
            ]
            
            schema = CollectionSchema(fields=fields, description="Code snippet embeddings")
            self.collection = Collection(self.collection_name, schema=schema)
            
            self.collection.create_index(
                field_name="embedding",
                index_params={"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
            )
            
            logger.info(f"Created collection {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to create Milvus collection: {e}")
            raise
    
    def insert_embeddings(self, data: list) -> int:
        """Insert embeddings into Milvus."""
        try:
            if not self.collection:
                raise RuntimeError("Collection not initialized")
            
            ids = []
            repo_ids = []
            file_paths = []
            languages = []
            function_names = []
            class_names = []
            start_lines = []
            end_lines = []
            embeddings = []
            
            for item in data:
                ids.append(item["id"])
                repo_ids.append(item["repo_id"])
                file_paths.append(item["file_path"])
                languages.append(item["language"])
                function_names.append(item.get("function_name", ""))
                class_names.append(item.get("class_name", ""))
                start_lines.append(item["start_line"])
                end_lines.append(item["end_line"])
                embeddings.append(item["embedding"])
            
            entities = [
                ids, repo_ids, file_paths, languages, function_names,
                class_names, start_lines, end_lines, embeddings
            ]
            
            self.collection.insert(entities)
            self.collection.flush()
            
            logger.info(f"Inserted {len(data)} embeddings into Milvus")
            return len(data)
        except Exception as e:
            logger.error(f"Failed to insert embeddings: {e}")
            raise
    
    def search_similar(self, embedding: list, top_k: int = 10, repo_id: str = None) -> list:
        """Search for similar code snippets."""
        try:
            if not self.collection:
                raise RuntimeError("Collection not initialized")
            
            self.collection.load()
            
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            expr = f'repo_id == "{repo_id}"' if repo_id else None
            
            results = self.collection.search(
                [embedding],
                "embedding",
                search_params,
                limit=top_k,
                expr=expr,
                output_fields=["id", "repo_id", "file_path", "language", "function_name", "class_name", "start_line", "end_line"]
            )
            
            hits = []
            for hit in results[0]:
                hits.append({
                    "id": hit.id,
                    "distance": hit.distance,
                    "repo_id": hit.entity.get("repo_id"),
                    "file_path": hit.entity.get("file_path"),
                    "language": hit.entity.get("language"),
                    "function_name": hit.entity.get("function_name"),
                    "class_name": hit.entity.get("class_name"),
                    "start_line": hit.entity.get("start_line"),
                    "end_line": hit.entity.get("end_line"),
                })
            
            return hits
        except Exception as e:
            logger.error(f"Failed to search embeddings: {e}")
            raise
    
    def delete_by_repo(self, repo_id: str):
        """Delete all embeddings for a repository."""
        try:
            if not self.collection:
                raise RuntimeError("Collection not initialized")
            
            expr = f'repo_id == "{repo_id}"'
            self.collection.delete(expr)
            self.collection.flush()
            logger.info(f"Deleted embeddings for repo {repo_id}")
        except Exception as e:
            logger.error(f"Failed to delete embeddings: {e}")
            raise


milvus_store = MilvusVectorStore()


def init_db():
    """Initialize database connections and create tables."""
    from models import Base
    
    Base.metadata.create_all(bind=engine)
    logger.info("Created/verified PostgreSQL tables")
    
    milvus_store.connect()
    milvus_store.create_collection_if_not_exists()
    logger.info("Initialized Milvus vector store")
