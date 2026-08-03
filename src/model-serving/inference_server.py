"""Production model serving with vLLM and embeddings."""
import logging
import os
import torch
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Codebase Steward - Model Serving",
    version="0.1.0",
    description="High-performance inference server for code analysis"
)


# ============================================================================
# Configuration
# ============================================================================

class ModelConfig:
    """Model server configuration."""
    
    # Model selection
    MODEL_ID = os.getenv(
        "MODEL_ID",
        "meta-llama/Llama-2-13b-hf"  # Use CodeLlama for better code performance
    )
    EMBEDDING_MODEL_ID = os.getenv(
        "EMBEDDING_MODEL_ID",
        "BAAI/bge-large-en-v1.5"  # BGE for semantic search
    )
    
    # Quantization
    USE_QUANTIZATION = os.getenv("USE_QUANTIZATION", "true").lower() == "true"
    QUANTIZATION_TYPE = os.getenv("QUANTIZATION_TYPE", "int8")  # int4 or int8
    
    # Inference settings
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16"))
    MAX_MODEL_LEN = int(os.getenv("MAX_MODEL_LEN", "2048"))
    GPU_MEMORY_FRACTION = float(os.getenv("GPU_MEMORY_FRACTION", "0.9"))
    
    # Server settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8001"))
    WORKERS = int(os.getenv("WORKERS", "1"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


config = ModelConfig()


# ============================================================================
# Request/Response Models
# ============================================================================

class EmbeddingRequest(BaseModel):
    """Request for embedding generation."""
    text: Optional[str] = None
    texts: Optional[List[str]] = None
    instruction: Optional[str] = None  # For instruction-based embeddings


class EmbeddingResponse(BaseModel):
    """Response with embeddings."""
    embedding: Optional[List[float]] = None
    embeddings: Optional[List[List[float]]] = None
    model: str
    tokens_used: int
    processing_time_ms: float


class GenerateRequest(BaseModel):
    """Request for text generation."""
    prompt: str
    max_tokens: int = 500
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    stream: bool = False


class GenerateResponse(BaseModel):
    """Response with generated text."""
    generated_text: str
    model: str
    tokens_used: int
    processing_time_ms: float


class BatchInferRequest(BaseModel):
    """Batch inference request."""
    texts: List[str]
    task: str = "embeddings"  # embeddings or completions
    max_tokens: Optional[int] = 500


class BatchInferResponse(BaseModel):
    """Batch inference response."""
    results: List[Dict[str, Any]]
    batch_size: int
    processing_time_ms: float
    model: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    gpu_available: bool
    gpu_name: Optional[str] = None
    gpu_memory_total_gb: Optional[float] = None
    gpu_memory_used_gb: Optional[float] = None
    models_loaded: List[str]
    current_load: float  # 0.0 to 1.0
    queue_length: int
    uptime_seconds: int


# ============================================================================
# Model Management
# ============================================================================

class ModelManager:
    """Manage loaded models and inference."""
    
    def __init__(self):
        self.generation_model = None
        self.embedding_model = None
        self.embedding_tokenizer = None
        self.tokenizer = None
        self.device = None
        self.start_time = datetime.utcnow()
        self.request_queue = asyncio.Queue()
        self.current_batch_size = 0
    
    def initialize(self):
        """Initialize models on startup."""
        logger.info("Initializing model server...")
        
        # Check GPU availability
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
            logger.info(f"GPU available: {torch.cuda.get_device_name(0)}")
            logger.info(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        else:
            self.device = torch.device("cpu")
            logger.warning("GPU not available, using CPU (inference will be slow)")
        
        # Load generation model
        self._load_generation_model()
        
        # Load embedding model
        self._load_embedding_model()
        
        logger.info("Model server initialized successfully")
    
    def _load_generation_model(self):
        """Load LLM for text generation."""
        try:
            logger.info(f"Loading generation model: {config.MODEL_ID}")
            
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(config.MODEL_ID)
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Model kwargs
            model_kwargs = {
                "torch_dtype": torch.float16,
                "device_map": "auto" if self.device.type == "cuda" else None,
            }
            
            # Add quantization if enabled
            if config.USE_QUANTIZATION and self.device.type == "cuda":
                if config.QUANTIZATION_TYPE == "int8":
                    model_kwargs["load_in_8bit"] = True
                elif config.QUANTIZATION_TYPE == "int4":
                    from transformers import BitsAndBytesConfig
                    bnb_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_compute_dtype=torch.bfloat16
                    )
                    model_kwargs["quantization_config"] = bnb_config
            
            self.generation_model = AutoModelForCausalLM.from_pretrained(
                config.MODEL_ID,
                **model_kwargs
            )
            
            logger.info(f"Generation model loaded: {config.MODEL_ID}")
        except Exception as e:
            logger.error(f"Failed to load generation model: {e}")
            raise
    
    def _load_embedding_model(self):
        """Load embedding model."""
        try:
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL_ID}")
            
            from transformers import AutoModel, AutoTokenizer
            
            self.embedding_tokenizer = AutoTokenizer.from_pretrained(
                config.EMBEDDING_MODEL_ID
            )
            self.embedding_model = AutoModel.from_pretrained(
                config.EMBEDDING_MODEL_ID,
                torch_dtype=torch.float16
            ).to(self.device)
            
            self.embedding_model.eval()
            logger.info(f"Embedding model loaded: {config.EMBEDDING_MODEL_ID}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    async def generate_embedding(self, text: str, instruction: str = None) -> List[float]:
        """Generate embedding for text."""
        try:
            # Prepare input
            if instruction:
                text = f"Instruct: {instruction}\nQuery: {text}"
            
            # Tokenize
            inputs = self.embedding_tokenizer(
                text,
                return_tensors="pt",
                max_length=512,
                truncation=True
            ).to(self.device)
            
            # Generate embedding
            with torch.no_grad():
                outputs = self.embedding_model(**inputs)
            
            # Mean pooling
            embeddings = outputs.last_hidden_state
            mask = inputs['attention_mask']
            mask_expanded = mask.unsqueeze(-1).expand(embeddings.size()).float()
            sum_embeddings = torch.sum(embeddings * mask_expanded, 1)
            sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9)
            embedding = sum_embeddings / sum_mask
            
            # Convert to list
            return embedding[0].cpu().tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    async def generate_text(self, prompt: str, max_tokens: int, temperature: float, top_p: float) -> str:
        """Generate text using LLM."""
        try:
            # Tokenize prompt
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            # Generate
            with torch.no_grad():
                output_ids = self.generation_model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode
            generated_text = self.tokenizer.decode(
                output_ids[0][inputs['input_ids'].shape[-1]:],
                skip_special_tokens=True
            )
            
            return generated_text.strip()
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise
    
    def get_gpu_memory_stats(self) -> Dict[str, float]:
        """Get GPU memory statistics."""
        if torch.cuda.is_available():
            total = torch.cuda.get_device_properties(0).total_memory / 1e9
            used = torch.cuda.memory_allocated(0) / 1e9
            return {"total_gb": total, "used_gb": used, "utilization": used / total}
        return {"total_gb": 0, "used_gb": 0, "utilization": 0}


# Initialize model manager
model_manager = ModelManager()


# ============================================================================
# Endpoints
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize models on startup."""
    model_manager.initialize()


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    gpu_stats = model_manager.get_gpu_memory_stats()
    uptime = (datetime.utcnow() - model_manager.start_time).total_seconds()
    
    return HealthResponse(
        status="healthy",
        gpu_available=torch.cuda.is_available(),
        gpu_name=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        gpu_memory_total_gb=gpu_stats.get("total_gb"),
        gpu_memory_used_gb=gpu_stats.get("used_gb"),
        models_loaded=[config.MODEL_ID, config.EMBEDDING_MODEL_ID],
        current_load=gpu_stats.get("utilization", 0),
        queue_length=model_manager.request_queue.qsize(),
        uptime_seconds=int(uptime)
    )


@app.post("/embeddings", response_model=EmbeddingResponse)
async def embeddings(request: EmbeddingRequest):
    """Generate embeddings for text(s)."""
    try:
        import time
        start_time = time.time()
        
        if request.text:
            # Single embedding
            embedding = await model_manager.generate_embedding(
                request.text,
                request.instruction
            )
            
            elapsed = (time.time() - start_time) * 1000
            return EmbeddingResponse(
                embedding=embedding,
                model=config.EMBEDDING_MODEL_ID,
                tokens_used=len(request.text.split()),
                processing_time_ms=elapsed
            )
        
        elif request.texts:
            # Batch embeddings
            embeddings = []
            total_tokens = 0
            
            for text in request.texts:
                emb = await model_manager.generate_embedding(
                    text,
                    request.instruction
                )
                embeddings.append(emb)
                total_tokens += len(text.split())
            
            elapsed = (time.time() - start_time) * 1000
            return EmbeddingResponse(
                embeddings=embeddings,
                model=config.EMBEDDING_MODEL_ID,
                tokens_used=total_tokens,
                processing_time_ms=elapsed
            )
        
        else:
            raise HTTPException(status_code=400, detail="Either 'text' or 'texts' required")
    
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate text based on prompt."""
    try:
        import time
        start_time = time.time()
        
        generated_text = await model_manager.generate_text(
            request.prompt,
            request.max_tokens,
            request.temperature,
            request.top_p
        )
        
        elapsed = (time.time() - start_time) * 1000
        
        return GenerateResponse(
            generated_text=generated_text,
            model=config.MODEL_ID,
            tokens_used=len(generated_text.split()),
            processing_time_ms=elapsed
        )
    
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch_infer", response_model=BatchInferResponse)
async def batch_infer(request: BatchInferRequest):
    """Process batch of texts."""
    try:
        import time
        start_time = time.time()
        
        results = []
        
        if request.task == "embeddings":
            for i, text in enumerate(request.texts):
                embedding = await model_manager.generate_embedding(text)
                results.append({
                    "id": i,
                    "embedding": embedding
                })
        
        elif request.task == "completions":
            for i, text in enumerate(request.texts):
                generated = await model_manager.generate_text(
                    text,
                    request.max_tokens or 500,
                    0.7,
                    0.9
                )
                results.append({
                    "id": i,
                    "text": generated
                })
        
        elapsed = (time.time() - start_time) * 1000
        
        return BatchInferResponse(
            results=results,
            batch_size=len(request.texts),
            processing_time_ms=elapsed,
            model=config.MODEL_ID if request.task == "completions" else config.EMBEDDING_MODEL_ID
        )
    
    except Exception as e:
        logger.error(f"Batch inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models")
async def get_models():
    """Get information about loaded models."""
    gpu_stats = model_manager.get_gpu_memory_stats()
    
    return {
        "generation_model": {
            "id": config.MODEL_ID,
            "type": "causal-lm",
            "parameters": "13b",
            "quantized": config.USE_QUANTIZATION
        },
        "embedding_model": {
            "id": config.EMBEDDING_MODEL_ID,
            "type": "embedding",
            "dimension": 1024,
            "pooling": "mean"
        },
        "gpu": gpu_stats,
        "batch_size": config.BATCH_SIZE,
        "max_model_length": config.MAX_MODEL_LEN
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format="[%(asctime)s] %(levelname)s: %(message)s"
    )
    
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        workers=config.WORKERS
    )
