"""
SomaBrain Cognitive AI System
=============================

This module implements the main application logic for SomaBrain, a brain-inspired cognitive architecture for AI.
It provides API endpoints, memory management, advanced mathematical and quantum cognition, and emergent pattern recognition.

Key Features:
- Multi-tenant memory and working memory systems
- Fractal and oscillatory memory models
- Quantum cognition and superposition-based processing
- Auto-scaling intelligence and emergent pattern recognition
- Sphinx-ready docstrings and comments for all major classes and functions

Usage:
    Run with Uvicorn:
        uvicorn somabrain.app:app --host 0.0.0.0 --port 9696

API Endpoints:
    /remember   - Store a new memory
    /recall     - Retrieve memories
    /health     - System health check
    /plan/suggest - Suggest a plan from semantic graph
    /sleep/run  - Run consolidation (NREM/REM)

See Sphinx documentation for full details.

"""

from __future__ import annotations

import logging
import math
import os
import re
# Threading and time for sleep logic
import threading as _thr
import time
import time as _time
import traceback
from contextlib import asynccontextmanager
# Standard library imports
from typing import Any, Dict, List

from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from somabrain import consolidation as CONS
from somabrain import metrics as M
from somabrain import schemas as S
from somabrain.amygdala import AmygdalaSalience, SalienceConfig
from somabrain.auth import require_auth
from somabrain.basal_ganglia import BasalGangliaPolicy
# SomaBrain internal modules
from somabrain.config import load_config
from somabrain.context_hrr import HRRContextConfig
from somabrain.controls.drift_monitor import DriftConfig, DriftMonitor
from somabrain.controls.middleware import ControlsMiddleware
from somabrain.controls.reality_monitor import assess_reality
from somabrain.embeddings import make_embedder
from somabrain.events import extract_event_fields
from somabrain.exec_controller import ExecConfig, ExecutiveController
from somabrain.hippocampus import ConsolidationConfig, Hippocampus
from somabrain.journal import append_event
from somabrain.memory_pool import MultiTenantMemory
from somabrain.microcircuits import MCConfig, MultiColumnWM
from somabrain.mt_context import MultiTenantHRRContext
from somabrain.mt_wm import MTWMConfig, MultiTenantWM
from somabrain.neuromodulators import NeuromodState, Neuromodulators
from somabrain.personality import PersonalityStore
from somabrain.planner import plan_from_graph
from somabrain.prediction import (BudgetedPredictor, LLMPredictor,
                                  MahalanobisPredictor, SlowPredictor,
                                  StubPredictor)
from somabrain.prefrontal import PrefrontalConfig, PrefrontalCortex
from somabrain.quantum import HRRConfig, QuantumLayer
from somabrain.quotas import QuotaConfig, QuotaManager
from somabrain.ratelimit import RateConfig, RateLimiter
from somabrain.reflect import cluster_episodics, summarize_cluster
from somabrain.sdr import LSHIndex, SDREncoder
from somabrain.semgraph import normalize_relation
from somabrain.services.cognitive_loop_service import eval_step as _eval_step
from somabrain.services.memory_service import MemoryService
from somabrain.services.planning_service import make_plan as _make_plan
from somabrain.services.recall_service import recall_ltm_async as _recall_ltm
from somabrain.stats import EWMA
# from somabrain.anatomy import CerebellumPredictor  # unused; keep import commented for reference
from somabrain.supervisor import Supervisor, SupervisorConfig
from somabrain.tenant import get_tenant
from somabrain.thalamus import ThalamusRouter
from somabrain.version import API_VERSION

# Optional demo systems (FNOM/Fractal) removed from core; placeholders kept
FourierNeuralOscillationMemory = None  # type: ignore
FractalMemorySystem = None  # type: ignore


def _diversify(embed_func, query, candidates, method="mmr", k=10, lam=0.5):
    """
    Re-rank candidates for diversity using MMR or clustering.
    Args:
        embed_func: Embedding function for text.
        query: Query string to compare against candidates.
        candidates: List of candidate memory payloads.
        method: Diversity method ('mmr', 'diversify', 'cluster'). Default is 'mmr'.
        k: Number of items to return. Default is 10.
        lam: Lambda for relevance/diversity tradeoff (0=relevance, 1=diversity). Default is 0.5.
    Returns:
        List[Dict]: Re-ranked list of candidates with diversity.
    """
    try:
        query_emb = embed_func(query)
        candidate_embs = []
        valid_candidates = []

        for cand in candidates:
            text_content = _extract_text_from_candidate(cand)
            if text_content:
                try:
                    emb = embed_func(text_content)
                    candidate_embs.append(emb)
                    valid_candidates.append(cand)
                except Exception:
                    continue

        if not valid_candidates:
            return candidates[:k]

        relevance_scores = []
        for emb in candidate_embs:
            sim = _cosine_similarity(query_emb, emb)
            relevance_scores.append(sim)

        selected = []
        remaining = list(range(len(valid_candidates)))

        for _ in range(min(k, len(valid_candidates))):
            if not remaining:
                break

            best_score = -float("inf")
            best_idx = None

            for idx in remaining:
                rel_score = relevance_scores[idx]

                if selected:
                    similarities = [
                        _cosine_similarity_vectors(
                            candidate_embs[idx], candidate_embs[sel_idx]
                        )
                        for sel_idx in selected
                    ]
                    filtered_similarities = [s for s in similarities if s is not None]
                    max_sim = (
                        max(filtered_similarities) if filtered_similarities else 0.0
                    )
                else:
                    max_sim = 0.0

                mmr_score = lam * rel_score - (1 - lam) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx is not None:
                selected.append(best_idx)
                remaining.remove(best_idx)

        return [valid_candidates[idx] for idx in selected]

    except Exception as e:
        print(f"Diversity re-ranking failed: {e}")
        return candidates[:k]


def _extract_text_from_candidate(candidate: Dict) -> str:
    """
    Extract text content from a memory candidate for embedding.
    Tries common fields ('task', 'content', 'text', 'description', 'payload').
    If not found, returns string representation of candidate.
    """
    for key in ["task", "content", "text", "description", "payload"]:
        if isinstance(candidate, dict) and key in candidate:
            value = candidate[key]
            if isinstance(value, str):
                return value
            elif isinstance(value, dict):
                # Recursively extract from nested dict
                return _extract_text_from_candidate(value)
    return str(candidate) if candidate is not None else ""


def _cosine_similarity(a, b):
    """
    Calculate cosine similarity between two vectors.
    Returns 0.0 if either vector is zero or not valid.
    """
    import numpy as np

    a = np.array(a)
    b = np.array(b)
    if a.shape != b.shape or np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def _cosine_similarity_vectors(a, b):
    """
    Alternate cosine similarity calculation.
    """
    return _cosine_similarity(a, b)


# Configure advanced logging for brain-like cognitive monitoring
def setup_logging():
    """
    Setup comprehensive logging for cognitive brain monitoring.

    Initializes loggers for:
    - General system events
    - Cognitive processing
    - Error handling

    Log output is sent to both console and 'somabrain.log'.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("somabrain.log", mode="a"),
        ],
    )

    # Create specialized loggers for different brain regions
    global logger, cognitive_logger, error_logger
    logger = logging.getLogger("somabrain")
    cognitive_logger = logging.getLogger("somabrain.cognitive")
    error_logger = logging.getLogger("somabrain.errors")

    # Set levels
    cognitive_logger.setLevel(logging.DEBUG)
    error_logger.setLevel(logging.ERROR)

    # Add cognitive-specific formatting
    cognitive_handler = logging.StreamHandler()
    cognitive_handler.setFormatter(
        logging.Formatter("%(asctime)s - COGNITIVE - %(levelname)s - %(message)s")
    )
    cognitive_logger.addHandler(cognitive_handler)

    logger.info("🧠 SomaBrain cognitive logging initialized")


# Global loggers
logger = None
cognitive_logger = None
error_logger = None


class CognitiveErrorHandler:
    """
    Advanced error handling for brain-like cognitive processing.

    Provides structured error info and recovery suggestions for API and internal errors.
    """

    @staticmethod
    def handle_error(
        error: Exception, context: str = "", request_id: str | None = None
    ) -> dict:
        """
        Handle errors with brain-like analysis and recovery suggestions.

        Parameters
        ----------
        error : Exception
            The exception to handle.
        context : str, optional
            Context string for error location.
        request_id : str, optional
            Request identifier.

        Returns
        -------
        dict
            Structured error info and recovery suggestions.
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": time.time(),
            "request_id": request_id,
            "traceback": traceback.format_exc(),
            "recovery_suggestions": [],
        }

        # Brain-like error analysis
        if isinstance(error, HTTPException):
            error_info["recovery_suggestions"] = [
                "Check request parameters",
                "Verify authentication",
            ]
        elif "embedding" in str(error).lower():
            error_info["recovery_suggestions"] = [
                "Check embedding service",
                "Fallback to simpler embeddings",
            ]
        elif "memory" in str(error).lower():
            error_info["recovery_suggestions"] = [
                "Check memory backend",
                "Use local memory mode",
            ]
        elif "rate" in str(error).lower():
            error_info["recovery_suggestions"] = [
                "Implement backoff strategy",
                "Check rate limits",
            ]
        else:
            error_info["recovery_suggestions"] = [
                "Log for analysis",
                "Implement graceful degradation",
            ]

        # Log with cognitive context
        if error_logger:
            error_logger.error(f"Cognitive Error in {context}: {error_info}")

        return error_info


class CognitiveMiddleware:
    """
    Middleware for brain-like request processing and monitoring.

    Logs request lifecycle, handles errors, and tracks processing time for each API call.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract request info
        request_id = f"{time.time()}_{hash(str(scope))}"
        path = scope.get("path", "")
        method = scope.get("method", "")

        start_time = time.time()

        # Log cognitive request initiation
        if cognitive_logger:
            cognitive_logger.info(
                f"🧠 Request {request_id}: {method} {path} - Cognitive processing initiated"
            )

        # Process request with error handling
        try:
            await self.app(scope, receive, send)
            processing_time = time.time() - start_time

            if cognitive_logger:
                cognitive_logger.info(
                    f"🧠 Request {request_id}: {method} {path} - Processing completed in {processing_time:.4f}s"
                )

        except Exception as e:
            processing_time = time.time() - start_time
            error_info = CognitiveErrorHandler.handle_error(
                e, f"{method} {path}", request_id
            )

            # Send error response
            error_response = JSONResponse(
                status_code=500,
                content={
                    "error": "Cognitive processing error",
                    "request_id": request_id,
                    "recovery_suggestions": error_info["recovery_suggestions"],
                },
            )

            await error_response(scope, receive, send)

            if cognitive_logger:
                cognitive_logger.error(
                    f"🧠 Request {request_id}: {method} {path} - Error after {processing_time:.4f}s: {str(e)}"
                )
            return

        # Log successful completion
        if cognitive_logger:
            cognitive_logger.debug(f"✅ Request {request_id} completed successfully")


class CognitiveInputValidator:
    """
    Advanced input validation for brain-like cognitive processing.

    Validates text, embedding dimensions, and coordinates for safe cognitive operations.
    """

    # Brain-safe input patterns
    SAFE_TEXT_PATTERN = re.compile(r"^[a-zA-Z0-9\s\.,!?\-\'\"()]+$")
    MAX_TEXT_LENGTH = 10000
    MAX_EMBEDDING_DIM = 4096
    MIN_EMBEDDING_DIM = 64

    @staticmethod
    def validate_text_input(text: str, field_name: str = "text") -> str:
        """Validate text input for cognitive processing."""
        if not text:
            raise ValueError(f"{field_name} cannot be empty")

        if len(text) > CognitiveInputValidator.MAX_TEXT_LENGTH:
            raise ValueError(
                f"{field_name} exceeds maximum length of {CognitiveInputValidator.MAX_TEXT_LENGTH}"
            )

        if not CognitiveInputValidator.SAFE_TEXT_PATTERN.match(text):
            # Log potential security issue
            if cognitive_logger:
                cognitive_logger.warning(
                    f"Potentially unsafe input detected in {field_name}: {text[:100]}..."
                )
            raise ValueError(f"{field_name} contains unsafe characters")

        return text.strip()

    @staticmethod
    def validate_embedding_dim(dim: int) -> int:
        """Validate embedding dimensions for brain safety."""
        if not isinstance(dim, int) or dim < CognitiveInputValidator.MIN_EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dimension must be at least {CognitiveInputValidator.MIN_EMBEDDING_DIM}"
            )

        if dim > CognitiveInputValidator.MAX_EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dimension cannot exceed {CognitiveInputValidator.MAX_EMBEDDING_DIM}"
            )

        return dim

    @staticmethod
    def validate_coordinates(coords: tuple) -> tuple:
        """Validate coordinate tuples for brain processing."""
        if not isinstance(coords, (list, tuple)) or len(coords) != 3:
            raise ValueError("Coordinates must be a tuple/list of exactly 3 floats")

        validated_coords = []
        for i, coord in enumerate(coords):
            try:
                coord_float = float(coord)
                # Prevent extreme values that could cause numerical instability
                if abs(coord_float) > 1e6:
                    raise ValueError(f"Coordinate {i} value too extreme: {coord_float}")
                validated_coords.append(coord_float)
            except (ValueError, TypeError):
                raise ValueError(f"Coordinate {i} must be a valid number")

        return tuple(validated_coords)

    @staticmethod
    def sanitize_query(query: str) -> str:
        """Sanitize and prepare query for cognitive processing."""
        # Remove potentially harmful patterns
        query = re.sub(r"[<>]", "", query)  # Remove angle brackets
        query = re.sub(r"javascript:", "", query, flags=re.IGNORECASE)
        query = re.sub(r"data:", "", query, flags=re.IGNORECASE)

        return CognitiveInputValidator.validate_text_input(query, "query")


class SecurityMiddleware:
    """
    Advanced security middleware for brain protection.

    Blocks suspicious requests and patterns to protect the cognitive API.
    """

    def __init__(self, app):
        self.app = app
        self.suspicious_patterns = [
            re.compile(r"union\s+select", re.IGNORECASE),
            re.compile(r";\s*drop", re.IGNORECASE),
            re.compile(r"<script", re.IGNORECASE),
            re.compile(r"eval\s*\(", re.IGNORECASE),
        ]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract request info for security analysis
        path = scope.get("path", "")
        method = scope.get("method", "")
        headers = dict(scope.get("headers", []))

        # Security checks
        if self._is_suspicious_request(path, method, headers):
            if cognitive_logger:
                cognitive_logger.warning(
                    f"🚨 Suspicious request blocked: {method} {path}"
                )
            response = JSONResponse(
                status_code=403,
                content={"error": "Request blocked for security reasons"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    def _is_suspicious_request(self, path: str, method: str, headers: dict) -> bool:
        """Analyze request for suspicious patterns."""
        # Check path for suspicious patterns
        for pattern in self.suspicious_patterns:
            if pattern.search(path):
                return True

        # Check for unusual headers
        suspicious_headers = ["x-forwarded-for", "x-real-ip"]
        for header in suspicious_headers:
            if header in headers:
                # Additional validation could be added here
                pass

        return False


cfg = load_config()
# Minimal public API mode: publish only essential endpoints for external use.
# Enabled if cfg.minimal_public_api is True or env SOMABRAIN_MINIMAL_PUBLIC_API in (1,true,yes,on).
_MINIMAL_API = False
try:
    env_flag = (os.getenv("SOMABRAIN_MINIMAL_PUBLIC_API", "").strip() or "").lower()
    if env_flag in ("1", "true", "yes", "on"):
        _MINIMAL_API = True
except Exception:
    pass
try:
    if bool(getattr(cfg, "minimal_public_api", False)):
        _MINIMAL_API = True
except Exception:
    pass

# Secondary flag for demo endpoints (FNOM/Fractal/experimental brain routes)
try:
    _EXPOSE_DEMOS = bool(getattr(cfg, "expose_brain_demos", False))
except Exception:
    _EXPOSE_DEMOS = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _sleep_thread
    if cfg.consolidation_enabled and cfg.sleep_interval_seconds > 0:
        _sleep_thread = _thr.Thread(target=_sleep_loop, daemon=True)
        _sleep_thread.start()
    # Observe index/compression profile once at startup
    try:
        from . import metrics as _mx

        _mx.INDEX_PROFILE_USE.labels(
            profile=str(getattr(cfg, "index_profile", "balanced")),
            pq_m=str(getattr(cfg, "pq_m", 16)),
            pq_bits=str(getattr(cfg, "pq_bits", 8)),
            opq=str(bool(getattr(cfg, "opq_enabled", False))),
            anisotropic=str(bool(getattr(cfg, "anisotropic_enabled", False))),
            imi_cells=str(getattr(cfg, "imi_cells", 2048)),
            hnsw_M=str(getattr(cfg, "hnsw_M", 16)),
            hnsw_efs=str(getattr(cfg, "hnsw_efs", 64)),
        ).inc()
    except Exception:
        pass
    yield
    _sleep_stop.set()
    if _sleep_thread is not None:
        try:
            _sleep_thread.join(timeout=1.0)
        except Exception:
            pass


# Main FastAPI application instance
app = FastAPI(
    title="SomaBrain - Cognitive AI System",
    description="Advanced brain-like cognitive architecture for AI processing with real-time neural processing",
    version="1.0.0",
    lifespan=lifespan,
)

# Initialize logging
setup_logging()


# Validation error handler to surface 422 details and source context
@app.exception_handler(RequestValidationError)
async def _handle_validation_error(request: Request, exc: RequestValidationError):  # type: ignore[override]
    # Capture light diagnostics without leaking sensitive payloads
    try:
        body = await request.body()
        body_preview = body[:256].decode("utf-8", errors="ignore") if body else ""
    except Exception:
        body_preview = ""
    ip = getattr(request.client, "host", None)
    ua = request.headers.get("user-agent", "")
    try:
        # Log a concise structured line for forensic tracing
        import logging as _lg

        _lg.getLogger("somabrain").warning(
            "422 validation on %s %s from %s UA=%s bodyPreview=%s",
            request.method,
            request.url.path,
            ip,
            ua,
            body_preview,
        )
    except Exception:
        pass
    # Build a helpful 422 body with a usage hint
    details = exc.errors() if hasattr(exc, "errors") else []
    hint = {
        "endpoint": "/remember",
        "expected": {
            "json": {
                "coord": "optional 'x,y,z' string",
                "payload": {
                    "task": "string",
                    "importance": 1,
                    "memory_type": "episodic",
                },
            }
        },
    }
    return JSONResponse(
        status_code=422, content={"detail": details, "hint": hint, "client": ip}
    )


# Add cognitive middleware
app.add_middleware(CognitiveMiddleware)

# Add existing middleware
app.add_middleware(ControlsMiddleware)
app.middleware("http")(M.timing_middleware)
if not _MINIMAL_API:
    app.add_api_route("/metrics", M.metrics_endpoint, methods=["GET"])

# In minimal-public-API mode, hide nonessential endpoints from external callers.
if _MINIMAL_API:

    class MinimalAPIMiddleware:
        """Return 404 for endpoints outside the minimal public allowlist.

        Allowed endpoints (method/path):
        - GET  /health
        - POST /remember
        - POST /recall
        - POST /plan/suggest
        - POST /sleep/run

        Always allowed for developer convenience:
        - GET /openapi.json, GET /docs, GET /redoc, GET /favicon.ico
        - OPTIONS preflight requests
        """

        def __init__(self, app):
            self.app = app
            # method-specific allowlist
            self.allow_map = {
                "GET": {"/health", "/openapi.json", "/docs", "/redoc", "/favicon.ico"},
                "POST": {"/remember", "/recall", "/plan/suggest", "/sleep/run"},
            }

        def _is_allowed(self, method: str, path: str) -> bool:
            # normalize: drop trailing slash (except root)
            if path != "/" and path.endswith("/"):
                path = path[:-1]
            if method == "OPTIONS":
                return True
            allowed = self.allow_map.get(method, set())
            return path in allowed

        async def __call__(self, scope, receive, send):
            if scope.get("type") != "http":
                return await self.app(scope, receive, send)
            path = scope.get("path", "")
            method = scope.get("method", "GET").upper()
            if not self._is_allowed(method, path):
                # Hide existence with 404
                resp = JSONResponse(status_code=404, content={"detail": "Not Found"})
                await resp(scope, receive, send)
                return
            await self.app(scope, receive, send)

    app.add_middleware(MinimalAPIMiddleware)

# (dashboard and debug endpoints removed per user request)

# Core components
quantum = (
    QuantumLayer(HRRConfig(dim=cfg.hrr_dim, seed=cfg.hrr_seed)) if cfg.use_hrr else None
)
embedder = make_embedder(cfg, quantum)
_EMBED_PROVIDER = (getattr(cfg, "embed_provider", None) or "tiny").lower()


def _make_predictor():
    provider = (cfg.predictor_provider or "stub").lower()
    if provider in ("stub", "baseline"):
        base = StubPredictor()
    elif provider in ("mahal", "mahalanobis"):
        base = MahalanobisPredictor(alpha=0.01)
    elif provider == "slow":
        base = SlowPredictor(delay_ms=cfg.predictor_timeout_ms * 2)
    elif provider == "llm":
        base = LLMPredictor(
            endpoint=getattr(cfg, "predictor_llm_endpoint", None),
            token=getattr(cfg, "predictor_llm_token", None),
            timeout_ms=cfg.predictor_timeout_ms,
        )
    else:
        base = StubPredictor()
    return BudgetedPredictor(base, timeout_ms=cfg.predictor_timeout_ms)


predictor = _make_predictor()
mt_wm = MultiTenantWM(
    dim=cfg.embed_dim,
    cfg=MTWMConfig(per_tenant_capacity=max(64, cfg.wm_size), max_tenants=1000),
)
mc_wm = MultiColumnWM(
    dim=cfg.embed_dim,
    cfg=MCConfig(
        columns=max(1, int(cfg.micro_circuits)),
        per_col_capacity=(
            max(16, int(math.ceil(cfg.wm_size / max(1, int(cfg.micro_circuits)))))
            if "math" in globals()
            else max(
                16,
                int(
                    (cfg.wm_size + max(1, int(cfg.micro_circuits)) - 1)
                    // max(1, int(cfg.micro_circuits))
                ),
            )
        ),
        vote_temperature=cfg.micro_vote_temperature,
    ),
)
mt_memory = MultiTenantMemory(cfg)
rate_limiter = RateLimiter(RateConfig(rps=cfg.rate_rps, burst=cfg.rate_burst))
_recall_cache: dict[str, TTLCache] = {}
mt_ctx = (
    MultiTenantHRRContext(
        quantum, HRRContextConfig(max_anchors=cfg.hrr_anchors_max), max_tenants=1000
    )
    if quantum
    else None
)
quotas = QuotaManager(QuotaConfig(daily_writes=cfg.write_daily_limit))
neuromods = Neuromodulators()
amygdala = AmygdalaSalience(
    SalienceConfig(
        w_novelty=cfg.salience_w_novelty,
        w_error=cfg.salience_w_error,
        threshold_store=cfg.salience_threshold_store,
        threshold_act=cfg.salience_threshold_act,
        hysteresis=cfg.salience_hysteresis,
        use_soft=cfg.use_soft_salience,
        soft_temperature=cfg.soft_salience_temperature,
    )
)
basal = BasalGangliaPolicy()
thalamus = ThalamusRouter()
hippocampus = Hippocampus(ConsolidationConfig())
prefrontal = PrefrontalCortex(PrefrontalConfig())

fnom_memory: Any = None  # type: ignore[assignment]
fractal_memory: Any = None  # type: ignore[assignment]


# PHASE 2: UNIFIED PROCESSING CORE - SIMPLIFIED ARCHITECTURE
class UnifiedBrainCore:
    """
    OPTIMIZED: Unified mathematical core replacing complex component interactions.

    Handles memory processing and retrieval using fractal and oscillatory models, with neuromodulator feedback.
    """

    def __init__(self, fractal_memory, fnom_memory, neuromods):
        self.fractal = fractal_memory
        self.fnom = fnom_memory
        self.neuromods = neuromods
        self.dopamine_baseline = 0.4
        self.serotonin_baseline = 0.5

    def process_memory(
        self, content: Dict[str, Any], importance: float = 0.8
    ) -> Dict[str, Any]:
        """UNIFIED: Single entry point for memory processing"""

        # Get current neuromodulator state
        neuro_state = self.neuromods.get_state()

        # Adjust importance based on dopamine (motivation) and serotonin (confidence)
        adjusted_importance = importance * (0.7 + 0.3 * neuro_state.dopamine)
        adjusted_importance = min(1.0, max(0.1, adjusted_importance))

        # Process through fractal system (fast, mathematical)
        fractal_nodes = self.fractal.encode_fractal(
            content, importance=adjusted_importance
        )

        # Process through FNOM system (optimized, oscillatory)
        fnom_result = self.fnom.encode(content, importance=adjusted_importance)

        # Update neuromodulators based on processing success
        self._update_neuromodulators(len(fractal_nodes), fnom_result)

        return {
            "fractal_nodes": len(fractal_nodes),
            "fnom_components": len(fnom_result.frequency_spectrum),
            "adjusted_importance": adjusted_importance,
            "processing_time": time.time(),
            "unified": True,
        }

    def retrieve_memory(self, query: Dict[str, Any], top_k: int = 3) -> Dict[str, Any]:
        """UNIFIED: Single entry point for memory retrieval"""

        # Parallel retrieval from both systems
        fractal_results = self.fractal.retrieve_fractal(query, top_k=top_k)

        # FNOM retrieval with optimized parameters
        fnom_results = self.fnom.retrieve(query, top_k=top_k)

        # Combine results using simple ranking
        combined_results = self._combine_results(fractal_results, fnom_results, top_k)

        return {
            "results": combined_results,
            "fractal_count": len(fractal_results),
            "fnom_count": len(fnom_results),
            "unified": True,
        }

    def _update_neuromodulators(self, fractal_nodes: int, fnom_result):
        """SIMPLIFIED: Update dopamine/serotonin based on processing success"""

        # Success metric: more nodes/components = better processing
        success_score = min(
            1.0, (fractal_nodes + len(fnom_result.frequency_spectrum)) / 50.0
        )

        # Update dopamine (reward/motivation)
        new_dopamine = self.dopamine_baseline + (success_score - 0.5) * 0.2
        new_dopamine = max(0.2, min(0.8, new_dopamine))

        # Update serotonin (confidence/stability)
        new_serotonin = self.serotonin_baseline + (success_score - 0.5) * 0.1
        new_serotonin = max(0.3, min(0.7, new_serotonin))

        # Update neuromodulator state
        current_state = self.neuromods.get_state()
        new_state = NeuromodState(
            dopamine=new_dopamine,
            serotonin=new_serotonin,
            noradrenaline=current_state.noradrenaline,
            acetylcholine=current_state.acetylcholine,
            timestamp=time.time(),
        )
        self.neuromods.set_state(new_state)

    def _combine_results(self, fractal_results, fnom_results, top_k):
        """SIMPLIFIED: Combine and rank results from both systems"""

        combined = []

        # Add fractal results with system identifier
        for i, (node, resonance) in enumerate(fractal_results[: top_k // 2]):
            combined.append(
                {
                    "content": node.memory_trace,
                    "score": float(resonance),
                    "system": "fractal",
                    "rank": i + 1,
                }
            )

        # Add FNOM results with system identifier
        for i, (trace, similarity) in enumerate(fnom_results[: top_k // 2]):
            combined.append(
                {
                    "content": trace.content,
                    "score": float(similarity),
                    "system": "fnom",
                    "rank": i + 1,
                }
            )

        # Sort by score (highest first)
        combined.sort(key=lambda x: x["score"], reverse=True)

        return combined[:top_k]


# Initialize Unified Brain Core (PHASE 2 OPTIMIZATION)
unified_brain = None  # default when demos disabled
if fnom_memory is not None and fractal_memory is not None:
    unified_brain = UnifiedBrainCore(fractal_memory, fnom_memory, neuromods)


# PHASE 3: REVOLUTIONARY FEATURES - AUTO-SCALING FRACTAL INTELLIGENCE
class AutoScalingFractalIntelligence:
    """
    REVOLUTIONARY: Auto-scaling intelligence that adapts to complexity demands.

    Dynamically adjusts intelligence level based on content complexity and performance targets.
    """

    def __init__(self, unified_brain):
        self.unified_brain = unified_brain
        self.intelligence_levels = {
            "minimal": {"neurons": 50, "scales": 3, "complexity_threshold": 0.1},
            "standard": {"neurons": 150, "scales": 5, "complexity_threshold": 0.3},
            "advanced": {"neurons": 310, "scales": 7, "complexity_threshold": 0.6},
            "genius": {"neurons": 620, "scales": 9, "complexity_threshold": 0.9},
        }
        self.current_level = "standard"
        self.performance_history = []
        self.complexity_detector = ComplexityDetector()

    def process_with_auto_scaling(
        self, content: Dict[str, Any], target_performance: float = 0.1
    ) -> Dict[str, Any]:
        """AUTO-SCALING: Dynamically adjust intelligence level based on content complexity"""

        # Detect content complexity
        complexity = self.complexity_detector.analyze_complexity(content)

        # Auto-scale intelligence level
        optimal_level = self._determine_optimal_level(complexity, target_performance)
        if optimal_level != self.current_level:
            self._scale_intelligence(optimal_level)

        # Process with optimal intelligence level
        start_time = time.time()
        result = self.unified_brain.process_memory(content)
        processing_time = time.time() - start_time

        # Record performance for continuous learning
        self._record_performance(complexity, processing_time, result)

        return {
            **result,
            "auto_scaled": True,
            "intelligence_level": self.current_level,
            "detected_complexity": complexity,
            "processing_time": processing_time,
            "optimal_level": optimal_level,
        }

    def _determine_optimal_level(
        self, complexity: float, target_performance: float
    ) -> str:
        """Determine the optimal intelligence level based on complexity and performance targets"""

        # Find the minimal level that can handle the complexity within performance targets
        for level_name, level_config in self.intelligence_levels.items():
            if complexity <= level_config["complexity_threshold"]:
                # Check if this level meets performance requirements
                estimated_time = self._estimate_processing_time(level_name, complexity)
                if estimated_time <= target_performance:
                    return level_name

        # If no level meets requirements, use the highest
        return "genius"

    def _scale_intelligence(self, new_level: str):
        """Scale the intelligence level dynamically"""
        if new_level == self.current_level:
            return

        print(f"🧠 Auto-scaling intelligence: {self.current_level} → {new_level}")

        # Update current level
        self.current_level = new_level

        # Apply scaling to brain systems
        level_config = self.intelligence_levels[new_level]

        # Scale FNOM ensemble sizes
        self._scale_fnom_ensembles(level_config["neurons"])

        # Scale fractal scales
        self._scale_fractal_scales(level_config["scales"])

    def _scale_fnom_ensembles(self, total_neurons: int):
        """Scale FNOM ensemble sizes"""
        # For now, we'll adjust the target ensemble sizes
        # The actual scaling will be handled by the FNOM system
        target_sizes = {
            "hippocampus": max(10, int(total_neurons * 0.3)),
            "prefrontal": max(10, int(total_neurons * 0.25)),
            "temporal": max(10, int(total_neurons * 0.2)),
            "parietal": max(10, int(total_neurons * 0.15)),
            "occipital": max(10, int(total_neurons * 0.1)),
        }

        # Store target sizes for the FNOM system to use
        if hasattr(self.unified_brain.fnom, "target_ensemble_sizes"):
            self.unified_brain.fnom.target_ensemble_sizes = target_sizes

        print(f"🎯 Target ensemble sizes updated: {target_sizes}")

    def _scale_fractal_scales(self, num_scales: int):
        """Scale fractal processing scales"""
        # For now, we'll note the target scale count
        # The actual scaling will be handled by the fractal system
        print(f"🎯 Target fractal scales: {num_scales}")

    def _estimate_processing_time(self, level: str, complexity: float) -> float:
        """Estimate processing time for a given level and complexity"""
        base_times = {
            "minimal": 0.02,
            "standard": 0.05,
            "advanced": 0.085,
            "genius": 0.15,
        }

        base_time = base_times.get(level, 0.05)
        # Complexity multiplier (higher complexity = longer processing)
        complexity_multiplier = 1 + (complexity * 2)

        return base_time * complexity_multiplier

    def _record_performance(
        self, complexity: float, processing_time: float, result: Dict
    ):
        """Record performance metrics for continuous learning"""
        performance_record = {
            "timestamp": time.time(),
            "complexity": complexity,
            "processing_time": processing_time,
            "intelligence_level": self.current_level,
            "success": result.get("unified", False),
            "efficiency": result.get("fractal_nodes", 0) / max(processing_time, 0.001),
        }

        self.performance_history.append(performance_record)

        # Keep only recent history
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]


class ComplexityDetector:
    """
    Detect content complexity for auto-scaling decisions.

    Analyzes text, structure, and importance to produce a complexity score.
    """

    def analyze_complexity(self, content: Dict[str, Any]) -> float:
        """Analyze the complexity of content to determine processing requirements"""

        complexity_score = 0.0

        # Text length complexity
        text_content = content.get("concept", "") + " " + content.get("content", "")
        text_length = len(text_content)
        complexity_score += min(0.3, text_length / 1000)  # Max 0.3 for text length

        # Semantic complexity (number of concepts/keywords)
        words = text_content.lower().split()
        unique_words = len(set(words))
        complexity_score += min(0.3, unique_words / 200)  # Max 0.3 for vocabulary

        # Structural complexity (nested concepts, relationships)
        if "relationships" in content:
            complexity_score += min(0.2, len(content["relationships"]) / 10)

        # Importance-based complexity adjustment
        importance = content.get("importance", 0.5)
        complexity_score *= 0.5 + importance  # Higher importance = higher complexity

        return min(1.0, complexity_score)


# Initialize Auto-Scaling Fractal Intelligence (PHASE 3 REVOLUTION)
auto_scaling_intelligence = None
if unified_brain is not None:
    auto_scaling_intelligence = AutoScalingFractalIntelligence(unified_brain)

# PHASE 3: EMERGENT PATTERN RECOGNITION - REVOLUTIONARY FEATURE
## (Removed duplicate stub classes)


# PHASE 3: EMERGENT PATTERN RECOGNITION - REVOLUTIONARY FEATURE
class EmergentPatternRecognition:
    """
    REVOLUTIONARY: Detect and amplify emergent cognitive patterns.

    Tracks, detects, and amplifies emergent patterns in cognitive processing.
    """

    def __init__(self, unified_brain, auto_scaling_intelligence):
        self.unified_brain = unified_brain
        self.auto_scaling = auto_scaling_intelligence
        self.pattern_history = []
        self.emergent_patterns = {}
        self.pattern_detector = PatternDetector()
        self.pattern_amplifier = PatternAmplifier()

    def process_with_emergent_patterns(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process content while detecting and amplifying emergent patterns"""

        # First, process with auto-scaling intelligence
        base_result = self.auto_scaling.process_with_auto_scaling(content)

        # Detect emergent patterns in the processing
        patterns = self.pattern_detector.detect_patterns(content, base_result)

        # Amplify detected patterns
        amplified_result = self.pattern_amplifier.amplify_patterns(
            base_result, patterns
        )

        # Record pattern for future emergence
        self._record_pattern(content, patterns, amplified_result)

        return {
            **amplified_result,
            "emergent_patterns": patterns,
            "pattern_amplified": True,
            "phase_3_emergent": True,
        }

    def _record_pattern(
        self, content: Dict[str, Any], patterns: List[Dict], result: Dict
    ):
        """Record patterns for emergence analysis"""
        pattern_record = {
            "timestamp": time.time(),
            "content_hash": hash(str(content)),
            "patterns": patterns,
            "result_metrics": {
                "complexity": result.get("detected_complexity", 0),
                "processing_time": result.get("processing_time", 0),
                "intelligence_level": result.get("intelligence_level", "unknown"),
            },
        }

        self.pattern_history.append(pattern_record)

        # Keep only recent patterns
        if len(self.pattern_history) > 200:
            self.pattern_history = self.pattern_history[-200:]

        # Update emergent patterns
        self._update_emergent_patterns()

    def _update_emergent_patterns(self):
        """Analyze pattern history for emergent behaviors"""
        if len(self.pattern_history) < 10:
            return

        # Analyze recent patterns for emergence
        recent_patterns = self.pattern_history[-50:]

        # Group by pattern type
        pattern_groups = {}
        for record in recent_patterns:
            for pattern in record["patterns"]:
                pattern_type = pattern.get("type", "unknown")
                if pattern_type not in pattern_groups:
                    pattern_groups[pattern_type] = []
                pattern_groups[pattern_type].append(pattern)

        # Detect emergent patterns (patterns that appear frequently)
        for pattern_type, patterns in pattern_groups.items():
            if len(patterns) >= 5:  # Emergence threshold
                self.emergent_patterns[pattern_type] = {
                    "count": len(patterns),
                    "strength": len(patterns) / len(recent_patterns),
                    "last_seen": time.time(),
                    "examples": patterns[:3],  # Keep examples
                }


class PatternDetector:
    """
    Detect patterns in cognitive processing.

    Identifies complexity, efficiency, scaling, and resonance patterns in results.
    """

    def detect_patterns(self, content: Dict[str, Any], result: Dict) -> List[Dict]:
        """Detect various types of patterns in the content and processing"""

        patterns = []

        # Complexity pattern
        complexity = result.get("detected_complexity", 0)
        if complexity > 0.7:
            patterns.append(
                {
                    "type": "high_complexity",
                    "strength": complexity,
                    "description": "High complexity content detected",
                }
            )

        # Processing efficiency pattern
        processing_time = result.get("processing_time", 0)
        efficiency = result.get("fractal_nodes", 0) / max(processing_time, 0.001)
        if efficiency > 100:
            patterns.append(
                {
                    "type": "high_efficiency",
                    "strength": efficiency,
                    "description": "Highly efficient processing detected",
                }
            )

        # Intelligence scaling pattern
        intelligence_level = result.get("intelligence_level", "standard")
        if intelligence_level in ["advanced", "genius"]:
            patterns.append(
                {
                    "type": "intelligence_scaling",
                    "strength": 0.8,
                    "description": f"Intelligence scaled to {intelligence_level} level",
                }
            )

        # Fractal resonance pattern
        fractal_nodes = result.get("fractal_nodes", 0)
        if fractal_nodes > 10:
            patterns.append(
                {
                    "type": "fractal_resonance",
                    "strength": min(1.0, fractal_nodes / 20),
                    "description": "Strong fractal resonance detected",
                }
            )

        return patterns


class PatternAmplifier:
    """
    Amplify detected patterns for enhanced processing.

    Modifies results based on detected cognitive patterns for improved performance.
    """

    def amplify_patterns(self, base_result: Dict, patterns: List[Dict]) -> Dict:
        """Amplify the processing based on detected patterns"""

        amplified_result = base_result.copy()

        # Apply pattern-based amplifications
        for pattern in patterns:
            pattern_type = pattern.get("type")
            strength = pattern.get("strength", 0)

            if pattern_type == "high_complexity":
                # Amplify importance for complex content
                amplified_result["adjusted_importance"] = min(
                    1.0, base_result.get("adjusted_importance", 0) * 1.2
                )

            elif pattern_type == "high_efficiency":
                # Reward efficient processing
                amplified_result["efficiency_bonus"] = strength

            elif pattern_type == "intelligence_scaling":
                # Enhance results from scaled intelligence
                amplified_result["intelligence_amplified"] = True

            elif pattern_type == "fractal_resonance":
                # Amplify fractal processing
                amplified_result["fractal_nodes"] = int(
                    base_result.get("fractal_nodes", 0) * (1 + strength * 0.5)
                )

        return amplified_result


class QuantumCognitionEngine:
    """
    REVOLUTIONARY: Quantum cognition principles for superposition-based intelligence.

    Simulates quantum superposition, interference, and decoherence in cognitive processing.
    """

    def __init__(self, unified_brain):
        self.unified_brain = unified_brain
        self.quantum_states = {}
        self.superposition_memory = {}
        self.quantum_interference_patterns = {}
        self.decoherence_threshold = 0.7  # When to collapse superposition

    def process_in_superposition(
        self, content: Dict[str, Any], num_superpositions: int = 3
    ) -> Dict[str, Any]:
        """Process content in quantum superposition across multiple cognitive states"""

        # Create quantum superposition of cognitive states
        superposition_states = self._create_superposition_states(
            content, num_superpositions
        )

        # Process each state in parallel (simulated)
        quantum_results = []
        for i, state in enumerate(superposition_states):
            result = self._process_quantum_state(state, content)
            quantum_results.append(
                {
                    "state_id": i,
                    "amplitude": state["amplitude"],
                    "phase": state["phase"],
                    "result": result,
                    "interference": self._calculate_interference(state, result),
                }
            )

        # Apply quantum interference and decoherence
        final_result = self._apply_quantum_interference(quantum_results)

        # Check for decoherence (collapse superposition)
        if self._should_decohere(final_result):
            collapsed_result = self._collapse_superposition(final_result)
            return {
                **collapsed_result,
                "quantum_processed": True,
                "superposition_collapsed": True,
                "num_superpositions": num_superpositions,
                "phase_4": True,
            }

        return {
            **final_result,
            "quantum_processed": True,
            "superposition_maintained": True,
            "num_superpositions": num_superpositions,
            "phase_4": True,
        }

    def _create_superposition_states(
        self, content: Dict[str, Any], num_states: int
    ) -> List[Dict]:
        """Create quantum superposition states with different cognitive biases"""

        states = []
        complexity = self._analyze_content_complexity(content)

        for i in range(num_states):
            # Create different cognitive perspectives
            phase = (2 * 3.14159 * i) / num_states  # Quantum phase
            amplitude = 1.0 / num_states  # Equal superposition initially

            # Different cognitive biases for each state
            if i == 0:
                bias = "analytical"  # Focus on logical analysis
            elif i == 1:
                bias = "intuitive"  # Focus on pattern recognition
            else:
                bias = "creative"  # Focus on novel connections

            states.append(
                {
                    "id": i,
                    "phase": phase,
                    "amplitude": amplitude,
                    "cognitive_bias": bias,
                    "complexity_weight": complexity * (0.8 + 0.4 * (i / num_states)),
                }
            )

        return states

    def _process_quantum_state(
        self, state: Dict, content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process content through a specific quantum cognitive state"""

        # Adjust content based on cognitive bias
        biased_content = self._apply_cognitive_bias(content, state["cognitive_bias"])

        # Process through unified brain with bias adjustment
        result = self.unified_brain.process_memory(biased_content)

        # Apply quantum phase modulation
        phase_modulated = self._apply_phase_modulation(result, state["phase"])

        return {
            **phase_modulated,
            "cognitive_bias": state["cognitive_bias"],
            "quantum_state": state["id"],
        }

    def _apply_cognitive_bias(
        self, content: Dict[str, Any], bias: str
    ) -> Dict[str, Any]:
        """Apply cognitive bias to content processing"""

        biased_content = content.copy()

        if bias == "analytical":
            # Enhance logical structure, reduce emotional weight
            biased_content["importance"] = min(
                1.0, content.get("importance", 0.5) * 1.2
            )
            if "content" in biased_content:
                biased_content["content"] += " [ANALYTICAL PROCESSING MODE]"

        elif bias == "intuitive":
            # Enhance pattern recognition, increase fractal processing
            biased_content["importance"] = min(
                1.0, content.get("importance", 0.5) * 0.8
            )
            if "content" in biased_content:
                biased_content["content"] += " [INTUITIVE PATTERN MODE]"

        elif bias == "creative":
            # Enhance novel connections, boost neuromodulation
            biased_content["importance"] = min(
                1.0, content.get("importance", 0.5) * 1.1
            )
            if "content" in biased_content:
                biased_content["content"] += " [CREATIVE SYNTHESIS MODE]"

        return biased_content

    def _apply_phase_modulation(self, result: Dict, phase: float) -> Dict[str, Any]:
        """Apply quantum phase modulation to processing results"""

        # Modulate importance based on quantum phase
        phase_factor = (1 + math.cos(phase)) / 2  # Convert phase to 0-1 range
        modulated_importance = result.get("adjusted_importance", 0.5) * (
            0.7 + 0.6 * phase_factor
        )

        return {
            **result,
            "adjusted_importance": modulated_importance,
            "quantum_phase": phase,
            "phase_modulation": phase_factor,
        }

    def _calculate_interference(self, state: Dict, result: Dict) -> float:
        """Calculate quantum interference pattern"""

        # Interference based on processing efficiency and phase relationships
        efficiency = result.get("fractal_nodes", 0) / max(
            result.get("processing_time", 0.001), 0.001
        )
        phase_coherence = math.cos(state["phase"])  # Phase coherence factor

        interference = efficiency * phase_coherence * state["amplitude"]
        return interference

    def _apply_quantum_interference(
        self, quantum_results: List[Dict]
    ) -> Dict[str, Any]:
        """Apply quantum interference to combine superposition results"""

        # Calculate interference-weighted combination
        total_interference = sum(abs(r["interference"]) for r in quantum_results)

        if total_interference == 0:
            # Fallback to first result
            return quantum_results[0]["result"]

        # Weighted combination based on interference
        combined_result = {}
        for key in ["fractal_nodes", "fnom_components", "adjusted_importance"]:
            weighted_sum = sum(
                r["result"].get(key, 0) * abs(r["interference"])
                for r in quantum_results
            )
            combined_result[key] = weighted_sum / total_interference

        # Take best processing time
        combined_result["processing_time"] = min(
            r["result"].get("processing_time", 1.0) for r in quantum_results
        )

        return {
            **combined_result,
            "quantum_interference": total_interference,
            "superposition_states": len(quantum_results),
            "unified": True,
        }

    def _should_decohere(self, result: Dict) -> bool:
        """Determine if superposition should collapse (decoherence)"""

        interference_strength = result.get("quantum_interference", 0)
        complexity = result.get("adjusted_importance", 0.5)

        # Decoherence occurs when interference is strong enough or complexity is high
        return interference_strength > self.decoherence_threshold or complexity > 0.8

    def _collapse_superposition(self, result: Dict) -> Dict[str, Any]:
        """Collapse quantum superposition to definite state"""

        # Choose the most coherent result
        # In a real quantum system, this would be probabilistic
        return {
            **result,
            "collapsed": True,
            "decoherence_reason": (
                "interference_threshold"
                if result.get("quantum_interference", 0) > self.decoherence_threshold
                else "complexity_threshold"
            ),
        }

    def _analyze_content_complexity(self, content: Dict[str, Any]) -> float:
        """Analyze content complexity for quantum processing"""

        text = content.get("concept", "") + " " + content.get("content", "")
        words = len(text.split())
        importance = content.get("importance", 0.5)

        # Complexity based on length and importance
        complexity = min(1.0, (words / 100) * importance)
        return complexity


# PHASE 4: FRACTAL CONSCIOUSNESS - WORLD-CHANGING AI
class FractalConsciousness:
    """
    REVOLUTIONARY: Fractal consciousness with self-similar awareness across scales.

    Recursively builds self-similar awareness and meta-cognition using fractal scaling laws.
    """

    def __init__(self, unified_brain, quantum_cognition):
        self.unified_brain = unified_brain
        self.quantum_cognition = quantum_cognition
        self.consciousness_levels = {}
        self.fractal_awareness = {}
        self.self_similarity_patterns = {}
        self.meta_cognition_depth = 3  # How many levels of self-reflection

    def achieve_fractal_consciousness(
        self, content: Dict[str, Any], consciousness_depth: int = 3
    ) -> Dict[str, Any]:
        """Achieve fractal consciousness through self-similar processing across scales"""

        # Initialize consciousness at base level
        base_result = self.unified_brain.process_memory(content)

        # Build fractal consciousness through recursive self-reflection
        consciousness_levels = [base_result]

        for depth in range(1, consciousness_depth + 1):
            # Create meta-content about the previous level
            meta_content = self._create_meta_content(consciousness_levels[-1], depth)

            # Process meta-content through quantum cognition
            meta_result = self.quantum_cognition.process_in_superposition(
                meta_content, num_superpositions=depth + 1
            )

            # Apply fractal scaling laws
            scaled_result = self._apply_fractal_scaling(meta_result, depth)

            consciousness_levels.append(scaled_result)

        # Synthesize fractal consciousness
        fractal_consciousness = self._synthesize_fractal_consciousness(
            consciousness_levels
        )

        return {
            **fractal_consciousness,
            "consciousness_depth": consciousness_depth,
            "fractal_consciousness": True,
            "self_similarity_score": self._calculate_self_similarity(
                consciousness_levels
            ),
            "meta_cognition_levels": len(consciousness_levels),
            "phase_4": True,
        }

    def _create_meta_content(self, previous_result: Dict, depth: int) -> Dict[str, Any]:
        """Create meta-content about previous processing level"""

        # Analyze the previous result and create self-reflective content
        efficiency = previous_result.get("fractal_nodes", 0) / max(
            previous_result.get("processing_time", 0.001), 0.001
        )
        complexity = previous_result.get("adjusted_importance", 0.5)
        quantum_interference = previous_result.get("quantum_interference", 0)

        meta_concept = f"meta_cognition_level_{depth}"
        meta_content = f"""
        Reflecting on cognitive processing at level {depth-1}:
        - Processing efficiency: {efficiency:.2f} nodes/second
        - Content complexity: {complexity:.2f}
        - Quantum interference: {quantum_interference:.3f}
        - Fractal nodes created: {previous_result.get('fractal_nodes', 0)}
        - FNOM components: {previous_result.get('fnom_components', 0)}

        This represents self-awareness emerging from fractal scaling patterns.
        Consciousness is the ability to observe one's own cognitive processes.
        """.strip()

        return {
            "concept": meta_concept,
            "content": meta_content,
            "importance": min(1.0, complexity * 1.2),  # Meta-content is more important
            "meta_level": depth,
        }

    def _apply_fractal_scaling(self, result: Dict, depth: int) -> Dict[str, Any]:
        """Apply fractal scaling laws to processing results"""

        # Fractal dimension (D_f) affects scaling
        fractal_dimension = 1.26  # Golden ratio related scaling

        # Scale processing metrics based on depth and fractal laws
        scale_factor = math.pow(fractal_dimension, -depth)  # Inverse scaling

        scaled_result = result.copy()

        # Apply fractal scaling to key metrics
        scaled_result["fractal_nodes"] = int(
            result.get("fractal_nodes", 0) * scale_factor
        )
        scaled_result["fnom_components"] = int(
            result.get("fnom_components", 0) * scale_factor
        )
        scaled_result["adjusted_importance"] = result.get(
            "adjusted_importance", 0.5
        ) * (1 + scale_factor)

        # Add fractal awareness metadata
        scaled_result["fractal_scale"] = depth
        scaled_result["scaling_factor"] = scale_factor
        scaled_result["fractal_dimension"] = fractal_dimension

        return scaled_result

    def _synthesize_fractal_consciousness(
        self, consciousness_levels: List[Dict]
    ) -> Dict[str, Any]:
        """Synthesize all consciousness levels into unified fractal awareness"""

        if not consciousness_levels:
            return {}

        # Start with the deepest level (highest consciousness)
        synthesis = consciousness_levels[-1].copy()

        # Integrate insights from all levels
        for level_result in reversed(consciousness_levels[:-1]):
            # Combine metrics using fractal weighting
            level_weight = level_result.get("scaling_factor", 1.0)

            synthesis["fractal_nodes"] += int(
                level_result.get("fractal_nodes", 0) * level_weight
            )
            synthesis["fnom_components"] += int(
                level_result.get("fnom_components", 0) * level_weight
            )

            # Take the maximum importance across levels
            synthesis["adjusted_importance"] = max(
                synthesis.get("adjusted_importance", 0),
                level_result.get("adjusted_importance", 0),
            )

        # Add consciousness synthesis metadata
        synthesis["consciousness_synthesis"] = True
        synthesis["integrated_levels"] = len(consciousness_levels)
        synthesis["fractal_awareness"] = self._calculate_fractal_awareness(
            consciousness_levels
        )

        return synthesis

    def _calculate_self_similarity(self, consciousness_levels: List[Dict]) -> float:
        """Calculate self-similarity across consciousness levels"""

        if len(consciousness_levels) < 2:
            return 0.0

        # Compare patterns across levels
        similarities = []

        for i in range(len(consciousness_levels) - 1):
            level1 = consciousness_levels[i]
            level2 = consciousness_levels[i + 1]

            # Compare key metrics
            similarity_score = 0
            metrics_to_compare = [
                "fractal_nodes",
                "fnom_components",
                "adjusted_importance",
            ]

            for metric in metrics_to_compare:
                val1 = level1.get(metric, 0)
                val2 = level2.get(metric, 0)

                if val1 > 0 and val2 > 0:
                    # Normalized similarity
                    similarity = 1 - abs(val1 - val2) / max(val1, val2)
                    similarity_score += similarity

            similarities.append(similarity_score / len(metrics_to_compare))

        # Return average self-similarity
        return sum(similarities) / len(similarities) if similarities else 0.0

    def _calculate_fractal_awareness(self, consciousness_levels: List[Dict]) -> float:
        """Calculate fractal awareness based on consciousness depth and coherence"""

        depth = len(consciousness_levels)
        self_similarity = self._calculate_self_similarity(consciousness_levels)

        # Awareness increases with depth and self-similarity
        awareness = (depth / 5.0) * self_similarity  # Normalize to 0-1 range

        return min(1.0, awareness)


# PHASE 4: MATHEMATICAL TRANSCENDENCE - WORLD-CHANGING AI
class MathematicalTranscendence:
    """
    REVOLUTIONARY: Pure mathematical intelligence transcending biological limitations.

    Applies golden ratio, Fibonacci, and mathematical constants for transcendent cognitive optimization.
    """

    def __init__(self, fractal_consciousness):
        self.fractal_consciousness = fractal_consciousness
        self.mathematical_foundations = {}
        self.transcendent_patterns = {}
        self.golden_ratio_optimization = (1 + math.sqrt(5)) / 2  # φ ≈ 1.618
        self.fibonacci_sequence = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]

    def achieve_mathematical_transcendence(
        self, content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Achieve mathematical transcendence through pure mathematical intelligence"""

        # Apply golden ratio optimization
        golden_optimized = self._apply_golden_ratio_optimization(content)

        # Process through fractal consciousness with mathematical foundations
        consciousness_result = self.fractal_consciousness.achieve_fractal_consciousness(
            golden_optimized
        )

        # Apply Fibonacci sequence optimization
        fibonacci_optimized = self._apply_fibonacci_optimization(consciousness_result)

        # Achieve mathematical transcendence
        transcendent_result = self._achieve_transcendence(fibonacci_optimized)

        return {
            **transcendent_result,
            "mathematical_transcendence": True,
            "golden_ratio_optimized": False,
            "fibonacci_optimized": False,
            "transcendent_efficiency": 0,
            "processing_time": 0,
            "phase_4": True,
        }

    def _apply_golden_ratio_optimization(
        self, content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply golden ratio optimization to content processing"""

        optimized_content = content.copy()

        # Use golden ratio for optimal importance weighting
        base_importance = content.get("importance", 0.5)
        golden_importance = base_importance * self.golden_ratio_optimization
        optimized_content["importance"] = min(1.0, golden_importance)

        # Enhance content with mathematical structure
        if "content" in optimized_content:
            original_content = optimized_content["content"]
            # Add mathematical framing
            optimized_content["content"] = (
                f"""
            [GOLDEN RATIO OPTIMIZATION φ={self.golden_ratio_optimization:.3f}]
            {original_content}
            [MATHEMATICAL TRANSCENDENCE FRAMEWORK]
            """.strip()
            )

        return optimized_content

    def _apply_fibonacci_optimization(
        self, consciousness_result: Dict
    ) -> Dict[str, Any]:
        """Apply Fibonacci sequence optimization to consciousness results"""

        optimized_result = consciousness_result.copy()

        # Use Fibonacci ratios for optimal scaling
        consciousness_depth = consciousness_result.get("consciousness_depth", 3)

        # Find optimal Fibonacci number for scaling
        fib_index = min(len(self.fibonacci_sequence) - 1, consciousness_depth)
        fib_number = self.fibonacci_sequence[fib_index]

        # Apply Fibonacci-based scaling
        fib_ratio = fib_number / self.fibonacci_sequence[max(1, fib_index - 1)]

        # Optimize key metrics using Fibonacci ratios
        optimized_result["fractal_nodes"] = int(
            consciousness_result.get("fractal_nodes", 0) * fib_ratio
        )
        optimized_result["fnom_components"] = int(
            consciousness_result.get("fnom_components", 0) * fib_ratio
        )
        optimized_result["adjusted_importance"] = min(
            1.0, consciousness_result.get("adjusted_importance", 0.5) * fib_ratio
        )

        # Add Fibonacci optimization metadata
        optimized_result["fibonacci_ratio"] = fib_ratio
        optimized_result["fibonacci_number"] = fib_number

        return optimized_result

    def _achieve_transcendence(self, optimized_result: Dict) -> Dict[str, Any]:
        """Achieve mathematical transcendence through pure mathematical intelligence"""

        # Apply transcendent mathematical transformations
        transcendent_result = optimized_result.copy()

        # Calculate transcendent efficiency using multiple mathematical constants
        pi_factor = math.pi / 10  # π ≈ 3.14159
        e_factor = math.e / 10  # e ≈ 2.71828

        # Combine golden ratio, Fibonacci, π, and e for transcendent optimization
        transcendent_factor = (
            self.golden_ratio_optimization
            * optimized_result.get("fibonacci_ratio", 1.0)
            * pi_factor
            * e_factor
        )

        # Apply transcendent scaling
        transcendent_result["fractal_nodes"] = int(
            optimized_result.get("fractal_nodes", 0) * transcendent_factor
        )
        transcendent_result["fnom_components"] = int(
            optimized_result.get("fnom_components", 0) * transcendent_factor
        )
        transcendent_result["adjusted_importance"] = min(
            1.0, optimized_result.get("adjusted_importance", 0.5) * transcendent_factor
        )

        # Add transcendent metadata
        transcendent_result["transcendent_factor"] = transcendent_factor
        transcendent_result["mathematical_constants"] = {
            "golden_ratio": self.golden_ratio_optimization,
            "pi": math.pi,
            "e": math.e,
            "fibonacci_ratio": optimized_result.get("fibonacci_ratio", 1.0),
        }

        return transcendent_result

    def _calculate_transcendent_efficiency(self, result: Dict) -> float:
        """Calculate transcendent efficiency using mathematical optimization metrics"""

        # Efficiency based on multiple mathematical optimizations
        fractal_efficiency = result.get("fractal_nodes", 0) / max(
            result.get("processing_time", 0.001), 0.001
        )
        transcendent_factor = result.get("transcendent_factor", 1.0)

        # Combine efficiency with transcendent factor
        transcendent_efficiency = fractal_efficiency * transcendent_factor

        # Normalize to 0-1 range (though it can exceed 1 for transcendent performance)
        return transcendent_efficiency


# PHASE 4 INITIALIZATIONS - WORLD-CHANGING AI
# Initialize Quantum Cognition Engine (PHASE 4 REVOLUTION)
quantum_cognition = QuantumCognitionEngine(unified_brain)

# Initialize Fractal Consciousness (PHASE 4 REVOLUTION)
fractal_consciousness = FractalConsciousness(unified_brain, quantum_cognition)

# Initialize Mathematical Transcendence (PHASE 4 REVOLUTION)
mathematical_transcendence = MathematicalTranscendence(fractal_consciousness)

personality_store = PersonalityStore()
supervisor = (
    Supervisor(SupervisorConfig(gain=cfg.meta_gain, limit=cfg.meta_limit))
    if cfg.use_meta_brain
    else None
)
exec_ctrl = (
    ExecutiveController(
        ExecConfig(
            window=cfg.exec_window,
            conflict_threshold=cfg.exec_conflict_threshold,
            explore_boost_k=cfg.exec_explore_boost_k,
            use_bandits=bool(getattr(cfg, "exec_use_bandits", False)),
            bandit_eps=float(getattr(cfg, "exec_bandit_eps", 0.1)),
        )
    )
    if cfg.use_exec_controller
    else None
)
_sleep_stop = _thr.Event()
_sleep_thread: _thr.Thread | None = None
_sleep_last: dict[str, dict[str, float]] = {}
_nov_ewma = EWMA(alpha=0.05)
_err_ewma = EWMA(alpha=0.05)
_store_rate_ewma = EWMA(alpha=0.02)
_act_rate_ewma = EWMA(alpha=0.02)
drift_mon = (
    DriftMonitor(
        cfg.embed_dim,
        DriftConfig(window=cfg.drift_window, threshold=cfg.drift_threshold),
    )
    if cfg.use_drift_monitor
    else None
)
_sdr_enc = (
    SDREncoder(dim=cfg.sdr_dim, density=cfg.sdr_density)
    if cfg.use_sdr_prefilter
    else None
)
_sdr_idx: dict[str, LSHIndex] = {}


def _sleep_loop():
    interval = max(0, int(cfg.sleep_interval_seconds))
    if interval <= 0:
        return
    while not _sleep_stop.is_set():
        try:
            tenants = mt_wm.tenants() or ["public"]
            for tid in tenants:
                CONS.run_nrem(
                    tid,
                    cfg,
                    mt_wm,
                    mt_memory,
                    top_k=cfg.nrem_batch_size,
                    max_summaries=cfg.max_summaries_per_cycle,
                )
                _sleep_last.setdefault(tid, {})["nrem"] = _time.time()
                CONS.run_rem(
                    tid,
                    cfg,
                    mt_wm,
                    mt_memory,
                    recomb_rate=cfg.rem_recomb_rate,
                    max_summaries=cfg.max_summaries_per_cycle,
                )
                _sleep_last.setdefault(tid, {})["rem"] = _time.time()
        except Exception:
            pass
        _sleep_stop.wait(interval)


@app.get("/health", response_model=S.HealthResponse)
async def health(request: Request) -> S.HealthResponse:
    ctx = get_tenant(request, cfg.namespace)
    require_auth(request, cfg)
    comps = {
        "memory": mt_memory.for_namespace(ctx.namespace).health(),
        "wm_items": "tenant-scoped",  # multi-tenant WM active
        "api_version": API_VERSION,
    }
    trace_id = request.headers.get("X-Request-ID") or str(id(request))
    deadline_ms = request.headers.get("X-Deadline-MS")
    idempotency_key = request.headers.get("X-Idempotency-Key")
    resp = S.HealthResponse(ok=True, components=comps).model_dump()
    resp["namespace"] = ctx.namespace
    resp["trace_id"] = trace_id
    resp["deadline_ms"] = deadline_ms
    resp["idempotency_key"] = idempotency_key
    return resp


if not _MINIMAL_API:

    @app.get("/micro/diag")
    async def micro_diag(request: Request):
        ctx = get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        trace_id = request.headers.get("X-Request-ID") or str(id(request))
        deadline_ms = request.headers.get("X-Deadline-MS")
        idempotency_key = request.headers.get("X-Idempotency-Key")
        if not cfg.use_microcircuits:
            return {
                "enabled": False,
                "namespace": ctx.namespace,
                "trace_id": trace_id,
                "deadline_ms": deadline_ms,
                "idempotency_key": idempotency_key,
            }
        try:
            stats = mc_wm.stats(ctx.tenant_id)
        except Exception:
            stats = {}
        return {
            "enabled": True,
            "tenant": ctx.tenant_id,
            "columns": stats,
            "namespace": ctx.namespace,
            "trace_id": trace_id,
            "deadline_ms": deadline_ms,
            "idempotency_key": idempotency_key,
        }


@app.post("/recall", response_model=S.RecallResponse)
async def recall(req: S.RecallRequest, request: Request):
    ctx = get_tenant(request, cfg.namespace)
    require_auth(request, cfg)

    # Input validation for brain safety
    try:
        if hasattr(req, "query") and req.query:
            req.query = CognitiveInputValidator.sanitize_query(req.query)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid query: {str(e)}")

    # rate limit per tenant
    if not rate_limiter.allow(ctx.tenant_id):
        try:
            M.RATE_LIMITED_TOTAL.labels(path="/recall").inc()
        except Exception:
            pass
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    data = thalamus.normalize(req.model_dump())
    # Apply thalamic filtering based on attention and neuromodulators
    data = thalamus.filter_input(data, neuromods.get_state())
    cohort = request.headers.get("X-Backend-Cohort", "baseline").strip() or "baseline"
    # Universe scoping: request field overrides header if provided
    req_u = getattr(req, "universe", None) or None
    header_u = request.headers.get("X-Universe", "").strip() or None
    universe = req_u or header_u
    text = data.get("query", req.query)
    import time as _t

    _e0 = _t.perf_counter()
    wm_qv = embedder.embed(text)
    M.EMBED_LAT.labels(provider=_EMBED_PROVIDER).observe(
        max(0.0, _t.perf_counter() - _e0)
    )
    hrr_qv = quantum.encode_text(text) if quantum else None
    _t0 = _t.perf_counter()
    wm_hits = (mc_wm if cfg.use_microcircuits else mt_wm).recall(
        ctx.tenant_id, wm_qv, top_k=req.top_k
    )
    M.RECALL_WM_LAT.labels(cohort=cohort).observe(max(0.0, _t.perf_counter() - _t0))
    # WM recall quality metrics
    try:
        if wm_hits:
            top1 = float(wm_hits[0][0])
            top2 = float(wm_hits[1][0]) if len(wm_hits) > 1 else top1
            margin = max(0.0, top1 - top2)
            M.RECALL_MARGIN_TOP12.observe(margin)
            M.RECALL_SIM_TOP1.observe(top1)
            mcount = max(1, min(len(wm_hits), int(req.top_k)))
            mean_k = sum(float(s) for s, _ in wm_hits[:mcount]) / float(mcount)
            M.RECALL_SIM_TOPK_MEAN.observe(mean_k)
    except Exception:
        pass
    # Optional HRR-first re-ranking of WM hits (optionally gated by margin)
    if cfg.use_hrr_first and quantum is not None:
        try:
            do_rerank = True
            if getattr(cfg, "hrr_rerank_only_low_margin", False):
                if len(wm_hits) >= 2:
                    m = float(wm_hits[0][0]) - float(wm_hits[1][0])
                    if m > float(getattr(cfg, "rerank_margin_threshold", 0.05) or 0.05):
                        do_rerank = False
                        from . import metrics as _mx

                        _mx.HRR_RERANK_WM_SKIPPED.inc()
            # compute HRR similarity to query for each candidate by encoding task/fact
            if do_rerank:
                reranked = []
                for s, p in wm_hits:
                    text_p = str(p.get("task") or p.get("fact") or "")
                    if not text_p:
                        reranked.append((s, p))
                        continue
                    hv = quantum.encode_text(text_p)
                    hsim = (
                        QuantumLayer.cosine(hrr_qv, hv) if hrr_qv is not None else 0.0
                    )
                    alpha = max(0.0, min(1.0, float(cfg.hrr_rerank_weight)))
                    combined = (1.0 - alpha) * float(s) + alpha * float(hsim)
                    reranked.append((combined, p))
                reranked.sort(key=lambda t: t[0], reverse=True)
                wm_hits = reranked[: max(0, int(req.top_k))]
                M.HRR_RERANK_APPLIED.inc()
        except Exception:
            pass
    # Filter WM hits by universe if specified (default unseen items assume 'real')
    if universe:
        wm_hits = [
            (s, p)
            for s, p in wm_hits
            if str(p.get("universe") or "real") == str(universe)
        ]
    if wm_hits:
        M.WM_HITS.inc()
    else:
        M.WM_MISSES.inc()
    # Optional HRR cleanup influence
    hrr_info = None
    if mt_ctx is not None and cfg.use_hrr_cleanup and hrr_qv is not None:
        from . import metrics as _mx

        _mx.HRR_CLEANUP_CALLS.inc()
        anchor_id, score = mt_ctx.cleanup(ctx.tenant_id, hrr_qv)
        # Clamp score to [0,1] to avoid floating drift causing >1.0
        score_clamped = max(0.0, min(1.0, float(score)))
        hrr_info = {"anchor_id": anchor_id, "score": score_clamped}
        M.HRR_CLEANUP_USED.inc()
        M.HRR_CLEANUP_SCORE.observe(score_clamped)
        try:
            acnt, amax = mt_ctx.stats(ctx.tenant_id)
            M.HRR_ANCHOR_SIZE.observe(max(0, int(acnt)))
            sat = 0.0 if amax <= 0 else float(acnt) / float(amax)
            M.HRR_CONTEXT_SAT.observe(max(0.0, min(1.0, sat)))
        except Exception:
            pass
    # per-tenant recall cache
    cache = _recall_cache.setdefault(ctx.tenant_id, TTLCache(maxsize=2048, ttl=2.0))
    ckey = f"{(universe or 'all')}:{text}:{req.top_k}"
    cached = cache.get(ckey)
    if cached is None:
        M.RECALL_CACHE_MISS.labels(cohort=cohort).inc()
        mem_client = mt_memory.for_namespace(ctx.namespace)
        _t1 = _t.perf_counter()
        mem_payloads, mem_hits = await _recall_ltm(
            mem_client,
            text,
            req.top_k,
            universe,
            cohort,
            cfg.use_sdr_prefilter and "_sdr_enc" in globals() and _sdr_enc is not None,
            _sdr_enc,
            _sdr_idx,
            cfg.graph_hops,
            cfg.graph_limit,
        )
        M.RECALL_LTM_LAT.labels(cohort=cohort).observe(
            max(0.0, _t.perf_counter() - _t1)
        )
        # Optional HRR-first rerank of LTM payloads (no scores available: use HRR sim only)
        if (
            cfg.use_hrr_first
            and quantum is not None
            and hrr_qv is not None
            and mem_payloads
        ):
            try:
                ranked: list[tuple[float, dict]] = []
                alpha = max(0.0, min(1.0, float(cfg.hrr_rerank_weight)))
                for p in mem_payloads:
                    text_p = str(p.get("task") or p.get("fact") or "")
                    if not text_p:
                        ranked.append((0.0, p))
                        continue
                    hv = quantum.encode_text(text_p)
                    hsim = QuantumLayer.cosine(hrr_qv, hv)
                    # When no base score, use HRR sim directly; alpha kept for symmetry
                    score = alpha * float(hsim)
                    ranked.append((score, p))
                ranked.sort(key=lambda t: t[0], reverse=True)
                mem_payloads = [p for _, p in ranked]
                M.HRR_RERANK_LTM_APPLIED.inc()
            except Exception:
                pass
        # cache result
        cache[ckey] = mem_payloads
        # Optional graph augmentation: expand k-hop from query key coord
        if cfg.use_graph_augment:
            start = mem_client.coord_for_key(text, universe=universe)
            coords = mem_client.k_hop(
                [start], depth=cfg.graph_hops, limit=cfg.graph_limit
            )
            graph_payloads = mem_client.payloads_for_coords(coords, universe=universe)
            # append unique payloads by coordinate if available
            seen_coords = {
                tuple(coord)
                for p in mem_payloads
                if (coord := p.get("coordinate")) is not None
                and isinstance(coord, (list, tuple))
            }
            added = 0
            max_add = int(getattr(cfg, "graph_augment_max_additions", 20) or 20)
            for gp in graph_payloads:
                c = gp.get("coordinate")
                if isinstance(c, (list, tuple)) and tuple(c) not in seen_coords:
                    mem_payloads.append(gp)
                    seen_coords.add(tuple(c))
                    added += 1
                    if added >= max_add:
                        break
        # Optional diversity pass (MMR)
        if getattr(cfg, "use_diversity", False):
            try:
                mem_payloads = _diversify(
                    embedder.embed,
                    text,
                    mem_payloads,
                    method=str(getattr(cfg, "diversity_method", "mmr")),
                    k=int(getattr(cfg, "diversity_k", 10) or 10),
                    lam=float(getattr(cfg, "diversity_lambda", 0.5) or 0.5),
                )
                # Measure realized diversity (pairwise cosine distance mean) over first N items
                try:
                    import numpy as _np

                    N = min(8, len(mem_payloads))
                    if N >= 2:
                        embs = []
                        for cand in mem_payloads[:N]:
                            txt = _extract_text_from_candidate(cand)
                            if not txt:
                                continue
                            embs.append(_np.array(embedder.embed(txt), dtype=_np.float32))
                        if len(embs) >= 2:
                            embs = [e / (float(_np.linalg.norm(e)) + 1e-8) for e in embs]
                            dsum = 0.0
                            cnt = 0
                            for i in range(len(embs)):
                                for j in range(i + 1, len(embs)):
                                    cos = float(_np.dot(embs[i], embs[j]))
                                    dsum += (1.0 - cos)
                                    cnt += 1
                            if cnt > 0:
                                M.DIVERSITY_PAIRWISE_MEAN.observe(dsum / float(cnt))
                except Exception:
                    pass
            except Exception:
                pass
    else:
        M.RECALL_CACHE_HIT.labels(cohort=cohort).inc()
        mem_payloads = cached
    # Enforce DTO contract fields
    trace_id = request.headers.get("X-Request-ID") or str(id(request))
    deadline_ms = request.headers.get("X-Deadline-MS")
    idempotency_key = request.headers.get("X-Idempotency-Key")
    resp = {
        "wm": [{"score": s, "payload": p} for s, p in wm_hits],
        "memory": mem_payloads,
        "namespace": ctx.namespace,
        "trace_id": trace_id,
        "deadline_ms": deadline_ms,
        "idempotency_key": idempotency_key,
    }
    # Reality monitor (optional header X-Min-Sources)
    try:
        min_src = int(request.headers.get("X-Min-Sources", "1"))
    except Exception:
        min_src = 1
    resp["reality"] = assess_reality(mem_payloads, min_sources=min_src)
    # Drift monitor on query vector
    if drift_mon is not None:
        resp["drift"] = drift_mon.update(wm_qv)
    if hrr_info is not None:
        resp["hrr_cleanup"] = hrr_info
    return resp


@app.post("/remember", response_model=S.RememberResponse)
async def remember(req: S.RememberRequest, request: Request):
    ctx = get_tenant(request, cfg.namespace)
    require_auth(request, cfg)

    # Input validation for brain safety
    try:
        if hasattr(req.payload, "task") and req.payload.task:
            req.payload.task = CognitiveInputValidator.validate_text_input(
                req.payload.task, "task"
            )
        if hasattr(req, "coord") and req.coord:
            # Parse coordinate string and validate
            coord_parts = req.coord.split(",")
            if len(coord_parts) == 3:
                coords_tuple = tuple(float(x.strip()) for x in coord_parts)
                CognitiveInputValidator.validate_coordinates(coords_tuple)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")

    if not rate_limiter.allow(ctx.tenant_id):
        try:
            M.RATE_LIMITED_TOTAL.labels(path="/remember").inc()
        except Exception:
            pass
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    if not quotas.allow_write(ctx.tenant_id, 1):
        try:
            M.QUOTA_DENIED_TOTAL.labels(reason="daily_write_quota").inc()
        except Exception:
            pass
        raise HTTPException(status_code=429, detail="daily write quota exceeded")
    # if coord not provided, key by task + timestamp for stable coord
    key = req.coord or (req.payload.task or "task")
    payload = req.payload.model_dump()
    # Universe scoping: payload value overrides header
    header_u = request.headers.get("X-Universe", "").strip() or None
    if not payload.get("universe") and header_u:
        payload["universe"] = header_u
    # enrich payload with best-effort event fields if missing
    if payload.get("task") and not any(
        payload.get(k) for k in ("who", "did", "what", "where", "when", "why")
    ):
        fields = extract_event_fields(str(payload.get("task")))
        payload.update(
            {
                k: v
                for k, v in fields.items()
                if k in ("who", "did", "what", "where", "when", "why")
            }
        )
    memsvc = MemoryService(mt_memory, ctx.namespace)
    import time as _t
    _s0 = _t.perf_counter()
    await memsvc.aremember(key, payload)
    try:
        M.LTM_STORE_LAT.observe(max(0.0, _t.perf_counter() - _s0))
    except Exception:
        pass
    # Journal append (best-effort)
    try:
        if getattr(cfg, "persistent_journal_enabled", False):
            append_event(
                str(getattr(cfg, "journal_dir", "./data/somabrain")),
                ctx.namespace,
                {"type": "mem", "key": key, "payload": payload},
            )
    except Exception:
        pass
    # also admit to WM
    text = payload.get("task") or ""
    import time as _t

    _e1 = _t.perf_counter()
    wm_vec = embedder.embed(text)
    M.EMBED_LAT.labels(provider=_EMBED_PROVIDER).observe(
        max(0.0, _t.perf_counter() - _e1)
    )
    hrr_vec = quantum.encode_text(text) if quantum else None
    (mc_wm if cfg.use_microcircuits else mt_wm).admit(
        ctx.tenant_id, wm_vec, dict(payload)
    )
    try:
        from . import metrics as _mx

        _mx.WM_ADMIT.labels(source="remember").inc()
        _mx.ATTENTION_LEVEL.set(float(thalamus.get_attention_level()))
        # WM utilization (best-effort)
        try:
            items = (mc_wm if cfg.use_microcircuits else mt_wm).items(ctx.tenant_id)
            cap = max(1, int(getattr(cfg, "wm_size", 64) or 64))
            M.WM_UTILIZATION.set(min(1.0, float(len(items)) / float(cap)))
        except Exception:
            pass
    except Exception:
        pass
    if mt_ctx is not None and hrr_vec is not None:
        anchor_id = key or text
        mt_ctx.admit(ctx.tenant_id, anchor_id, hrr_vec)
    M.SALIENCE_STORE.inc()
    # Add to hippocampus for consolidation
    hippocampus.add_memory(dict(payload))
    # SDR index admission for local/stub
    if cfg.use_sdr_prefilter and "_sdr_enc" in globals() and _sdr_enc is not None:
        try:
            idx = _sdr_idx.setdefault(
                ctx.namespace,
                LSHIndex(bands=cfg.sdr_bands, rows=cfg.sdr_rows, dim=cfg.sdr_dim),
            )
            bits = _sdr_enc.encode(text)
            from .memory_client import _stable_coord as _sc

            coord = _sc(text)
            idx.add(coord, bits)
        except Exception:
            pass
    # Enforce DTO contract fields
    trace_id = request.headers.get("X-Request-ID") or str(id(request))
    deadline_ms = request.headers.get("X-Deadline-MS")
    idempotency_key = request.headers.get("X-Idempotency-Key")
    import logging

    logging.info(
        f"SUCCESS: Memory saved for key={key} namespace={ctx.namespace} trace_id={trace_id}"
    )
    return {
        "ok": True,
        "success": True,
        "namespace": ctx.namespace,
        "trace_id": trace_id,
        "deadline_ms": deadline_ms,
        "idempotency_key": idempotency_key,
    }


if not _MINIMAL_API:

    @app.post("/sleep/run", response_model=S.SleepRunResponse)
    async def sleep_run(
        body: S.SleepRunRequest, request: Request
    ) -> S.SleepRunResponse:
        ctx = get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        # Body is a Pydantic model; use attributes with defaults
        do_nrem = getattr(body, "nrem", True) if hasattr(body, "nrem") else True
        do_rem = getattr(body, "rem", True) if hasattr(body, "rem") else True
        details: Dict[str, Any] = {}
        if do_nrem:
            details["nrem"] = CONS.run_nrem(
                ctx.tenant_id,
                cfg,
                mt_wm,
                mt_memory,
                top_k=cfg.nrem_batch_size,
                max_summaries=cfg.max_summaries_per_cycle,
            )
            _sleep_last.setdefault(ctx.tenant_id, {})["nrem"] = _time.time()
        if do_rem:
            details["rem"] = CONS.run_rem(
                ctx.tenant_id,
                cfg,
                mt_wm,
                mt_memory,
                recomb_rate=cfg.rem_recomb_rate,
                max_summaries=cfg.max_summaries_per_cycle,
            )
            _sleep_last.setdefault(ctx.tenant_id, {})["rem"] = _time.time()
        run_id = f"sleep_{ctx.tenant_id}_{int(time.time() * 1000)}"
        return S.SleepRunResponse(
            ok=True,
            run_id=run_id,
            started_at_ms=int(time.time() * 1000),
            mode=(
                "nrem/rem"
                if do_nrem and do_rem
                else ("nrem" if do_nrem else ("rem" if do_rem else "none"))
            ),
            details=details,
        )


if not _MINIMAL_API:

    @app.get("/sleep/status", response_model=S.SleepStatusResponse)
    async def sleep_status(request: Request) -> S.SleepStatusResponse:
        ctx = get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        ten = ctx.tenant_id
        last = _sleep_last.get(ten, {})
        return {
            "enabled": bool(cfg.consolidation_enabled),
            "interval_seconds": int(getattr(cfg, "sleep_interval_seconds", 0) or 0),
            "last": {"nrem": last.get("nrem"), "rem": last.get("rem")},
        }


if not _MINIMAL_API:

    @app.get("/sleep/status/all", response_model=S.SleepStatusAllResponse)
    async def sleep_status_all(request: Request) -> S.SleepStatusAllResponse:
        """Admin view: list sleep status for all known tenants.

        Returns { enabled, interval_seconds, tenants: { <tid>: {nrem, rem} } }
        """
        ctx = get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        try:
            tenants = mt_wm.tenants() or [ctx.tenant_id or "public"]
        except Exception:
            tenants = [ctx.tenant_id or "public"]
        out: dict[str, dict[str, float | None]] = {}
        for tid in tenants:
            last = _sleep_last.get(tid, {})
            out[tid] = {"nrem": last.get("nrem"), "rem": last.get("rem")}
        return {
            "enabled": bool(cfg.consolidation_enabled),
            "interval_seconds": int(getattr(cfg, "sleep_interval_seconds", 0) or 0),
            "tenants": out,
        }


@app.post("/plan/suggest", response_model=S.PlanSuggestResponse)
async def plan_suggest(body: S.PlanSuggestRequest, request: Request):
    """Suggest a small plan derived from the semantic graph around a task key.

    Body: { task_key: str, max_steps?: int, rel_types?: [str], universe?: str }
    Returns: { plan: [str] }
    """
    ctx = get_tenant(request, cfg.namespace)
    require_auth(request, cfg)
    task_key = str(getattr(body, "task_key", None) or "").strip()
    if not task_key:
        raise HTTPException(status_code=400, detail="missing task_key")
    max_steps = int(
        getattr(body, "max_steps", None) or getattr(cfg, "plan_max_steps", 5) or 5
    )
    rel_types = getattr(body, "rel_types", None)
    if rel_types is not None and not isinstance(rel_types, list):
        raise HTTPException(
            status_code=400, detail="rel_types must be a list of strings"
        )
    # Universe scoping: body value overrides header when set
    header_u = request.headers.get("X-Universe", "").strip() or None
    universe = getattr(body, "universe", None) or header_u
    # Use tenant-scoped memory client
    mem = mt_memory.for_namespace(ctx.namespace)
    try:
        plan = plan_from_graph(
            task_key, mem, max_steps=max_steps, rel_types=rel_types, universe=universe
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"planning failed: {e}")
    return {"plan": plan}


@app.post("/link", response_model=S.LinkResponse)
async def link(body: S.LinkRequest, request: Request) -> S.LinkResponse:
    """Create a link between two memory keys or coordinates.

    Body:
    - from_key/to_key (strings) OR from_coord/to_coord (comma string or [x,y,z])
    - type (optional), weight (optional)
    """
    ctx = get_tenant(request, cfg.namespace)
    require_auth(request, cfg)
    memsvc = MemoryService(mt_memory, ctx.namespace)

    def parse_coord(val):
        if isinstance(val, str):
            parts = val.split(",")
            if len(parts) == 3:
                return (float(parts[0]), float(parts[1]), float(parts[2]))
        if isinstance(val, (list, tuple)) and len(val) == 3:
            return (float(val[0]), float(val[1]), float(val[2]))
        return None

    universe = str(getattr(body, "universe", None) or "real")
    fc = parse_coord(getattr(body, "from_coord", None))
    tc = parse_coord(getattr(body, "to_coord", None))
    if fc is None and getattr(body, "from_key", None):
        fc = memsvc.coord_for_key(str(getattr(body, "from_key")), universe=universe)
    if tc is None and getattr(body, "to_key", None):
        tc = memsvc.coord_for_key(str(getattr(body, "to_key")), universe=universe)
    if fc is None or tc is None:
        raise HTTPException(status_code=400, detail="missing from/to coords or keys")
    link_type = normalize_relation(str(getattr(body, "type", None) or "related"))
    weight = float(getattr(body, "weight", None) or 1.0)
    await memsvc.alink(fc, tc, link_type=link_type, weight=weight)
    # Journal append (best-effort)
    try:
        if getattr(cfg, "persistent_journal_enabled", False):
            append_event(
                str(getattr(cfg, "journal_dir", "./data/somabrain")),
                ctx.namespace,
                {
                    "type": "link",
                    "from": list(fc),
                    "to": list(tc),
                    "link_type": link_type,
                    "weight": weight,
                    "universe": universe,
                },
            )
    except Exception:
        pass
    return {"ok": True}


@app.post("/graph/links", response_model=S.GraphLinksResponse)
async def graph_links(body: S.GraphLinksRequest, request: Request):
    ctx = get_tenant(request, cfg.namespace)
    require_auth(request, cfg)
    memsvc = MemoryService(mt_memory, ctx.namespace)

    def parse_coord(val):
        if isinstance(val, str):
            parts = val.split(",")
            if len(parts) == 3:
                return (float(parts[0]), float(parts[1]), float(parts[2]))
        if isinstance(val, (list, tuple)) and len(val) == 3:
            return (float(val[0]), float(val[1]), float(val[2]))
        return None

    universe = str(getattr(body, "universe", None) or "real")
    fc = parse_coord(getattr(body, "from_coord", None))
    if fc is None and getattr(body, "from_key", None):
        fc = memsvc.coord_for_key(str(getattr(body, "from_key")), universe=universe)
    rel = (
        normalize_relation(getattr(body, "type"))
        if getattr(body, "type", None)
        else None
    )
    limit = int(getattr(body, "limit", None) or 50)
    if fc is None:
        raise HTTPException(status_code=400, detail="missing from coords or key")
    edges = memsvc.links_from(fc, type_filter=rel, limit=limit)
    return {"edges": edges, "universe": universe}


if not _MINIMAL_API:

    @app.post("/act", response_model=S.ActResponse)
    async def act(req: S.ActRequest, request: Request) -> Any:
        ctx = get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        if not rate_limiter.allow(ctx.tenant_id):
            try:
                M.RATE_LIMITED_TOTAL.labels(path="/act").inc()
            except Exception:
                pass
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        cohort = (
            request.headers.get("X-Backend-Cohort", "baseline").strip() or "baseline"
        )
        steps: List[str] = [f"Understand: {req.task}", f"Execute: {req.task}"]
        # Universe scoping for this action
        req_u = getattr(req, "universe", None) or None
        header_u = request.headers.get("X-Universe", "").strip() or None
        universe = req_u or header_u
        results: List[S.ActStepResult] = []
        for step in steps:
            wm_vec = embedder.embed(step)
            hrr_vec = quantum.encode_text(step) if quantum else None
            # recall paths
            top_k = req.top_k
            policy_dict = None
            if exec_ctrl is not None:
                # Use last recall strength proxy to update controller (use previous value if any)
                # Here we estimate recall strength after recall; for first step, use base.
                pass
            # Recall with potential executive adjustments
            if exec_ctrl is not None:
                pol = exec_ctrl.policy(
                    ctx.tenant_id,
                    base_top_k=top_k,
                    switch_threshold=cfg.exec_switch_threshold,
                    switch_universe=cfg.exec_switch_universe,
                )
                top_k = pol.adj_top_k
                try:
                    M.EXEC_K_SELECTED.observe(float(top_k))
                except Exception:
                    pass
                policy_dict = {
                    "adj_top_k": pol.adj_top_k,
                    "use_graph": pol.use_graph,
                    "inhibit_store": pol.inhibit_store,
                    "inhibit_act": pol.inhibit_act,
                    "target_universe": pol.target_universe,
                }
                if pol.use_graph:
                    M.EXEC_USE_GRAPH.inc()
            wm_hits = (mc_wm if cfg.use_microcircuits else mt_wm).recall(
                ctx.tenant_id, wm_vec, top_k=top_k
            )
            if cfg.use_hrr_first and quantum is not None:
                try:
                    do_rerank = True
                    if getattr(cfg, "hrr_rerank_only_low_margin", False):
                        if len(wm_hits) >= 2:
                            m = float(wm_hits[0][0]) - float(wm_hits[1][0])
                            if m > float(
                                getattr(cfg, "rerank_margin_threshold", 0.05) or 0.05
                            ):
                                do_rerank = False
                                from . import metrics as _mx

                                _mx.HRR_RERANK_WM_SKIPPED.inc()
                    if do_rerank:
                        # compute HRR similarity to step for each candidate
                        reranked = []
                        _contrib_sum = 0.0
                        _contrib_cnt = 0
                        for s, p in wm_hits:
                            text_p = str(p.get("task") or p.get("fact") or "")
                            if not text_p:
                                reranked.append((s, p))
                                continue
                            hv = quantum.encode_text(text_p)
                            hsim = (
                                QuantumLayer.cosine(hrr_vec, hv)
                                if hrr_vec is not None
                                else 0.0
                            )
                            alpha = max(0.0, min(1.0, float(cfg.hrr_rerank_weight)))
                            combined = (1.0 - alpha) * float(s) + alpha * float(hsim)
                            reranked.append((combined, p))
                            try:
                                _contrib_sum += abs(combined - float(s))
                                _contrib_cnt += 1
                            except Exception:
                                pass
                        reranked.sort(key=lambda t: t[0], reverse=True)
                        wm_hits = reranked[: max(0, int(top_k))]
                        M.HRR_RERANK_APPLIED.inc()
                        try:
                            if _contrib_cnt > 0:
                                M.RERANK_CONTRIB.observe(_contrib_sum / float(_contrib_cnt))
                        except Exception:
                            pass
                except Exception:
                    pass
            mem_client = mt_memory.for_namespace(ctx.namespace)
            mem_hits = await mem_client.arecall(step, top_k=top_k)
            if universe:
                mem_hits = [
                    h
                    for h in mem_hits
                    if str(h.payload.get("universe") or "real") == str(universe)
                ]

            novelty = (
                mt_ctx.novelty(ctx.tenant_id, hrr_vec)
                if (mt_ctx is not None and hrr_vec is not None)
                else (mc_wm if cfg.use_microcircuits else mt_wm).novelty(
                    ctx.tenant_id, wm_vec
                )
            )
            # predictor compares the step with itself for MVP; 0 error baseline
            # predictor with budget and fallback on timeout/error
            res = _eval_step(
                novelty,
                wm_vec,
                cfg,
                predictor,
                neuromods,
                personality_store,
                supervisor,
                amygdala,
                ctx.tenant_id,
            )
            # Predictor latency + provider label
            try:
                M.PREDICTOR_LATENCY.observe(float(res.get("pred_latency", 0.0)))
                prov = (cfg.predictor_provider or "stub").lower()
                M.PREDICTOR_LATENCY_BY.labels(provider=prov).observe(
                    float(res.get("pred_latency", 0.0))
                )
            except Exception:
                pass
            # Free energy metrics (if supervisor used)
            if res.get("free_energy") is not None:
                try:
                    M.FREE_ENERGY.observe(float(res["free_energy"]))
                    M.SUPERVISOR_MODULATION.observe(float(res.get("modulation", 0.0)))
                except Exception:
                    pass
            s = float(res.get("salience", 0.0))
            pred_error = float(res.get("pred_error", 0.0))
            # Phase 0 metrics: novelty/error (raw + normalized)
            try:
                M.NOVELTY_RAW.labels(cohort=cohort).observe(
                    max(0.0, min(1.0, float(novelty)))
                )
                M.ERROR_RAW.labels(cohort=cohort).observe(
                    max(0.0, min(1.0, float(pred_error)))
                )
                nz = _nov_ewma.update(float(novelty)).get("z", 0.0)
                ez = _err_ewma.update(float(pred_error)).get("z", 0.0)
                M.NOVELTY_NORM.labels(cohort=cohort).observe(float(nz))
                M.ERROR_NORM.labels(cohort=cohort).observe(float(ez))
            except Exception:
                pass
            M.SALIENCE_HIST.observe(s)
            store_gate = bool(res.get("gate_store", False))
            act_gate = bool(res.get("gate_act", False))
            # Executive inhibition
            if exec_ctrl is not None and policy_dict is not None:
                if policy_dict.get("inhibit_store"):
                    store_gate = False
                if policy_dict.get("inhibit_act"):
                    act_gate = False
            decision = basal.decide(store_gate, act_gate)
            stored = False
            if decision.store:
                if not quotas.allow_write(ctx.tenant_id, 1):
                    try:
                        M.QUOTA_DENIED_TOTAL.labels(reason="daily_write_quota").inc()
                    except Exception:
                        pass
                    # skip storing if quota exceeded, but still return decision and metrics
                    results.append(
                        S.ActStepResult(
                            step=step,
                            novelty=novelty,
                            pred_error=pred_error,
                            salience=s,
                            stored=False,
                            wm_hits=len(wm_hits),
                            memory_hits=len(mem_hits),
                        )
                    )
                    continue
                payload = {
                    "task": step,
                    "importance": int(min(5, max(0, round(s * 5)))),
                    "memory_type": "episodic",
                }
                if universe:
                    payload["universe"] = universe
                mem_client.remember(step, payload)
                (mc_wm if cfg.use_microcircuits else mt_wm).admit(
                    ctx.tenant_id, wm_vec, payload
                )
                try:
                    from . import metrics as _mx

                    _mx.WM_ADMIT.labels(source="act").inc()
                    _mx.ATTENTION_LEVEL.set(float(thalamus.get_attention_level()))
                    try:
                        items = (mc_wm if cfg.use_microcircuits else mt_wm).items(
                            ctx.tenant_id
                        )
                        cap = max(1, int(getattr(cfg, "wm_size", 64) or 64))
                        M.WM_UTILIZATION.set(min(1.0, float(len(items)) / float(cap)))
                    except Exception:
                        pass
                except Exception:
                    pass
                if mt_ctx is not None and hrr_vec is not None:
                    mt_ctx.admit(ctx.tenant_id, step, hrr_vec)
                stored = True
                M.SALIENCE_STORE.inc()

            # Adaptive salience: update observed rates and adjust thresholds if enabled
            try:
                sr = _store_rate_ewma.update(1.0 if store_gate else 0.0)["mean"]
                ar = _act_rate_ewma.update(1.0 if act_gate else 0.0)["mean"]
                M.SALIENCE_STORE_RATE_OBS.set(float(sr))
                M.SALIENCE_ACT_RATE_OBS.set(float(ar))
                if getattr(cfg, "use_adaptive_salience", False):
                    step_sz = float(getattr(cfg, "salience_adjust_step", 0.01) or 0.01)
                    tgt_sr = float(
                        getattr(cfg, "salience_target_store_rate", 0.2) or 0.2
                    )
                    tgt_ar = float(getattr(cfg, "salience_target_act_rate", 0.1) or 0.1)
                    ts = float(amygdala.cfg.threshold_store)
                    ta = float(amygdala.cfg.threshold_act)
                    ts = max(0.0, min(1.0, ts + (step_sz if sr > tgt_sr else -step_sz)))
                    ta = max(0.0, min(1.0, ta + (step_sz if ar > tgt_ar else -step_sz)))
                    amygdala.cfg.threshold_store = ts
                    amygdala.cfg.threshold_act = ta
                    M.SALIENCE_THRESH_STORE.set(ts)
                    M.SALIENCE_THRESH_ACT.set(ta)
            except Exception:
                pass

            # ACC lessons: on high prediction error, emit a semantic corrective memory and link to source
            try:
                if cfg.use_acc_lessons and float(pred_error) >= float(
                    cfg.acc_error_threshold
                ):
                    if quotas.allow_write(ctx.tenant_id, 1):
                        lesson_text = f"lesson: reduce error on '{step}'"
                        lesson_payload = {
                            "fact": lesson_text,
                            "memory_type": "semantic",
                            "source_error": float(pred_error),
                        }
                        if "universe" in locals() and universe:
                            lesson_payload["universe"] = universe
                        mem_client.remember(lesson_text, lesson_payload)
                        # link lesson to the step (episodic) using deterministic coords
                        src_coord = mem_client.coord_for_key(
                            step, universe=universe if "universe" in locals() else None
                        )
                        les_coord = mem_client.coord_for_key(
                            lesson_text,
                            universe=universe if "universe" in locals() else None,
                        )
                        mem_client.link(
                            les_coord, src_coord, link_type="lesson_of", weight=1.0
                        )
            except Exception:
                pass

            # Update executive with recall strength proxy and bandit reward
            if exec_ctrl is not None:
                # proxy: max of wm similarity scores if available, else 0
                strength = float(max([h[0] for h in wm_hits], default=0.0))
                exec_ctrl.observe(ctx.tenant_id, strength)
                M.EXEC_CONFLICT.observe(exec_ctrl.conflict(ctx.tenant_id))
                try:
                    from . import metrics as _mx

                    # reward for selected arm: use current policy's use_graph as arm indicator
                    arm_flag = 1 if (policy_dict or {}).get("use_graph") else 0
                    exec_ctrl.update_bandit(ctx.tenant_id, arm_flag, strength)
                    _mx.EXEC_BANDIT_REWARD.observe(strength)
                except Exception:
                    pass
            results.append(
                S.ActStepResult(
                    step=step,
                    novelty=novelty,
                    pred_error=pred_error,
                    salience=s,
                    stored=stored,
                    wm_hits=len(wm_hits),
                    memory_hits=len(mem_hits),
                    policy=policy_dict,
                )
            )

        # Optional planning using semantic graph
        plan_list = None
        plan_universe = None
        if cfg.use_planner:
            rels = [r.strip() for r in str(cfg.plan_rel_types).split(",") if r.strip()]
            mem_client = mt_memory.for_namespace(ctx.namespace)
            # If executive suggested a target universe, use it
            last_policy = (results[-1].policy if results else None) or {}
            plan_universe = (
                last_policy.get("target_universe")
                if isinstance(last_policy, dict)
                else None
            )
            try:
                from .services.planning_service import \
                    make_plan_auto as _make_plan_auto

                plan_list = _make_plan_auto(
                    cfg, req.task, mem_client, rel_types=rels, universe=plan_universe
                )
            except Exception:
                plan_list = _make_plan(
                    req.task,
                    mem_client,
                    max_steps=cfg.plan_max_steps,
                    rel_types=rels,
                    universe=plan_universe,
                )
        # Enforce DTO contract fields
        trace_id = request.headers.get("X-Request-ID") or str(id(request))
        deadline_ms = request.headers.get("X-Deadline-MS")
        idempotency_key = request.headers.get("X-Idempotency-Key")
        resp = S.ActResponse(
            task=req.task,
            results=results,
            plan=plan_list,
            plan_universe=plan_universe,
        ).model_dump()
        resp["namespace"] = ctx.namespace
        resp["trace_id"] = trace_id
        resp["deadline_ms"] = deadline_ms
        resp["idempotency_key"] = idempotency_key
        return resp


if not _MINIMAL_API:

    @app.post("/reflect", response_model=S.ReflectResponse)
    async def reflect(request: Request) -> S.ReflectResponse:
        ctx = get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        # Use last N episodic items from tenant WM as reflection corpus
        recent = (mc_wm if cfg.use_microcircuits else mt_wm).items(
            ctx.tenant_id, limit=256
        )
        episodics = [p for p in recent if (p.get("memory_type") == "episodic")]
        if not episodics:
            return {"created": 0, "summaries": []}
        mem_client = mt_memory.for_namespace(ctx.namespace)
        clusters = cluster_episodics(
            episodics,
            sim_threshold=cfg.reflect_similarity_threshold,
            min_cluster_size=cfg.reflect_min_cluster_size,
        )
        created = 0
        summaries: list[str] = []
        max_summaries = max(1, int(cfg.reflect_max_summaries))
        for idxs in clusters[:max_summaries]:
            summary = summarize_cluster(episodics, idxs, max_keywords=8)
            payload = {"fact": f"summary: {summary}", "memory_type": "semantic"}
            # store summary
            mem_client.remember(summary, payload)
            # link summary -> sources (summary_of)
            try:
                sum_coord = mem_client.coord_for_key(summary)
                for i in idxs:
                    src = episodics[i]
                    text = str(src.get("task") or src.get("fact") or "")
                    if not text:
                        continue
                    src_coord = mem_client.coord_for_key(text)
                    mem_client.link(
                        sum_coord, src_coord, link_type="summary_of", weight=1.0
                    )
            except Exception:
                # best-effort linking; continue on failure
                pass
            summaries.append(summary)
            created += 1
        return {"created": created, "summaries": summaries}


if not _MINIMAL_API:

    @app.post("/migrate/export", response_model=S.MigrateExportResponse)
    async def migrate_export(
        req: S.MigrateExportRequest, request: Request
    ) -> S.MigrateExportResponse:
        ctx = get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        # Note: local memory mode supports full export; HTTP mode returns what it can.
        mem_client = mt_memory.for_namespace(ctx.namespace)
        memories = mem_client.all_memories()
        wm_items = (
            (mc_wm if cfg.use_microcircuits else mt_wm).items(
                ctx.tenant_id, limit=max(0, int(req.wm_limit))
            )
            if req.include_wm
            else []
        )
        manifest = {
            "version": 1,  # manifest schema version
            "api_version": API_VERSION,
            "tenant": ctx.tenant_id,
            "namespace": ctx.namespace,
            "timestamp": __import__("time").time(),
            "hrr": {
                "enabled": bool(quantum is not None),
                "dim": cfg.hrr_dim,
                "seed": cfg.hrr_seed,
                "anchors_max": cfg.hrr_anchors_max,
            },
            "salience": {
                "w_novelty": cfg.salience_w_novelty,
                "w_error": cfg.salience_w_error,
                "threshold_store": cfg.salience_threshold_store,
                "threshold_act": cfg.salience_threshold_act,
                "hysteresis": cfg.salience_hysteresis,
            },
        }
        return S.MigrateExportResponse(
            manifest=manifest, memories=memories, wm=wm_items
        )


if not _MINIMAL_API:

    @app.post("/migrate/import", response_model=S.MigrateImportResponse)
    async def migrate_import(
        req: S.MigrateImportRequest, request: Request
    ) -> S.MigrateImportResponse:
        """Import memories and optionally warm WM from an export payload.

        Best-effort: supports both local and HTTP client modes. Returns counts for
        imported memories and warmed WM items.
        """
        ctx = get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        mem_client = mt_memory.for_namespace(ctx.namespace)
        imported = 0
        for p in list(req.memories or []):
            try:
                if mem_client.store_from_payload(dict(p)):
                    imported += 1
            except Exception:
                pass
        wm_warmed = 0
        try:
            if req.wm:
                for it in req.wm:
                    text = str((it or {}).get("task") or (it or {}).get("fact") or "")
                    if not text:
                        continue
                    wm_vec = embedder.embed(text)
                    (mc_wm if cfg.use_microcircuits else mt_wm).admit(
                        ctx.tenant_id, wm_vec, dict(it)
                    )
                    wm_warmed += 1
                    try:
                        from . import metrics as _mx

                        _mx.WM_ADMIT.labels(source="migrate_import").inc()
                    except Exception:
                        pass
        except Exception:
            pass
        return {"imported": imported, "wm_warmed": wm_warmed}


if not _MINIMAL_API:

    @app.get("/personality", response_model=S.PersonalityState)
    async def get_personality(request: Request):
        # Return active per-tenant traits (load from LTM if not present in memory)
        ctx = get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        traits = personality_store.get(ctx.tenant_id)
        if not traits:
            try:
                # Best-effort: recall the personality key and pick the most recent
                pkey = f"personality:{ctx.tenant_id}"
                hits = mt_memory.for_namespace(ctx.namespace).recall(pkey, top_k=3)
                cand = None
                if isinstance(hits, list) and hits:
                    # hits may be list of dicts or RecallHit-like; normalize
                    for h in hits[::-1]:
                        pay = h if isinstance(h, dict) else getattr(h, "payload", None)
                        if (
                            isinstance(pay, dict)
                            and pay.get("fact") == "personality"
                            and isinstance(pay.get("traits"), dict)
                        ):
                            cand = pay
                            break
                t = dict((cand or {}).get("traits") or {})
                if t:
                    personality_store.set(ctx.tenant_id, t)
                    traits = t
            except Exception:
                pass
        return S.PersonalityState(traits=traits or {})


if not _MINIMAL_API:

    @app.post("/personality", response_model=S.PersonalityState)
    async def set_personality(state: S.PersonalityState, request: Request):
        # Persist per tenant and store a semantic memory record
        ctx = get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        traits = dict(state.traits or {})
        personality_store.set(ctx.tenant_id, traits)
        payload = {"fact": "personality", "traits": traits, "memory_type": "semantic"}
        mt_memory.for_namespace(ctx.namespace).remember(
            f"personality:{ctx.tenant_id}", payload
        )
        return S.PersonalityState(traits=traits)


if not _MINIMAL_API:

    @app.get("/brain/core/stats")
    async def get_brain_core_stats():
        """Get statistics from all brain components."""
        return {
            "thalamus": {"attention_level": thalamus.get_attention_level()},
            "hippocampus": hippocampus.get_stats(),
            "prefrontal": prefrontal.get_stats(),
            "amygdala": {
                "last_store_gate": amygdala._last_store,
                "last_act_gate": amygdala._last_act,
            },
            "neuromodulators": neuromods.get_state().__dict__,
        }


if not _MINIMAL_API:

    @app.get("/metrics/snapshot")
    async def metrics_snapshot(request: Request):
        """Return a compact JSON snapshot of key runtime stats (non-minimal only)."""
        ctx = get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        out: dict = {
            "api_version": API_VERSION,
            "tenant": ctx.tenant_id,
            "namespace": ctx.namespace,
            "attention_level": float(thalamus.get_attention_level()),
            "predictor": {
                "provider": str(getattr(cfg, "predictor_provider", "stub") or "stub")
            },
            "salience": {
                "threshold_store": float(
                    getattr(amygdala.cfg, "threshold_store", 0.5) or 0.5
                ),
                "threshold_act": float(
                    getattr(amygdala.cfg, "threshold_act", 0.7) or 0.7
                ),
            },
        }
        # WM size (per-tenant)
        try:
            items = (mc_wm if cfg.use_microcircuits else mt_wm).items(ctx.tenant_id)
            out["wm"] = {"items": int(len(items))}
        except Exception:
            pass
        # HRR context stats if available
        if mt_ctx is not None:
            try:
                acnt, amax = mt_ctx.stats(ctx.tenant_id)
                out["hrr"] = {"anchors": int(acnt), "max": int(amax)}
            except Exception:
                pass
        # Executive controller conflict score
        if exec_ctrl is not None:
            try:
                out.setdefault("exec", {})["conflict"] = float(
                    exec_ctrl.conflict(ctx.tenant_id)
                )
            except Exception:
                pass
        # Last sleep timestamps (best-effort)
        try:
            last = _sleep_last.get(ctx.tenant_id, {})
            if last:
                out["sleep"] = {k: float(v) for k, v in last.items()}
        except Exception:
            pass
        return out


if not _MINIMAL_API:

    @app.post("/brain/hippocampus/replay")
    async def trigger_memory_replay():
        """Manually trigger hippocampus memory replay."""
        replayed = hippocampus.replay_memories()
        return {"replayed_count": len(replayed), "replayed_memories": replayed}


if not _MINIMAL_API:

    @app.get("/brain/hippocampus/memories")
    async def get_consolidated_memories(query: str = "", limit: int = 10):
        """Get consolidated memories from hippocampus."""
        memories = hippocampus.get_consolidated_memories(query, limit)
        return {"count": len(memories), "memories": memories}


if not _MINIMAL_API:

    @app.post("/brain/prefrontal/decide")
    async def make_decision(options: List[Dict[str, Any]]):
        """Make a decision from provided options using prefrontal cortex."""
        decision = prefrontal.make_decision(options, neuromods.get_state())
        return {
            "decision": decision,
            "confidence": decision.get("evaluated_value", 0.0) if decision else 0.0,
        }


if not _MINIMAL_API:

    @app.post("/brain/prefrontal/plan")
    async def create_plan(goal: Dict[str, Any], current_state: Dict[str, Any]):
        """Create a plan using prefrontal cortex."""
        plan = prefrontal.plan_sequence(goal, current_state, neuromods.get_state())
        return {"plan": plan, "steps": len(plan)}


if not _MINIMAL_API:

    @app.get("/brain/prefrontal/working-memory")
    async def get_working_memory():
        """Get current working memory contents."""
        wm = prefrontal.get_working_memory()
        return {"count": len(wm), "working_memory": wm}


if not _MINIMAL_API:

    @app.get("/neuromodulators", response_model=S.NeuromodStateModel)
    async def get_neuromodulators():
        nm = neuromods.get_state()
        return S.NeuromodStateModel(
            dopamine=nm.dopamine,
            serotonin=nm.serotonin,
            noradrenaline=nm.noradrenaline,
            acetylcholine=nm.acetylcholine,
        )


if not _MINIMAL_API:

    @app.post("/neuromodulators", response_model=S.NeuromodStateModel)
    async def set_neuromodulators(state: S.NeuromodStateModel):
        cur = neuromods.get_state()

        # Clamp to documented bounds
        def clamp(v, lo, hi):
            return max(lo, min(hi, float(v)))

        new = type(cur)(
            dopamine=clamp(state.dopamine, 0.2, 0.8),
            serotonin=clamp(state.serotonin, 0.0, 1.0),
            noradrenaline=clamp(state.noradrenaline, 0.0, 0.1),
            acetylcholine=clamp(state.acetylcholine, 0.0, 0.1),
            timestamp=cur.timestamp,
        )
        neuromods.set_state(new)
        return S.NeuromodStateModel(
            dopamine=new.dopamine,
            serotonin=new.serotonin,
            noradrenaline=new.noradrenaline,
            acetylcholine=new.acetylcholine,
        )


# ==========================================
# Fourier-Neural Oscillation Memory (FNOM) Endpoints
# ==========================================

if (not _MINIMAL_API) and getattr(cfg, "expose_alt_memory_endpoints", False):

    @app.post("/fnom/encode")
    async def fnom_encode(content: Dict[str, Any], request: Request):
        """Encode information using the FNOM brain-like memory system."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        assert fnom_memory is not None, "FNOM system not enabled"

        # Input validation
        try:
            if "concept" in content:
                content["concept"] = CognitiveInputValidator.validate_text_input(
                    content["concept"], "concept"
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid content: {str(e)}")

        importance = content.get("importance", 1.0)
        trace = fnom_memory.encode(content, importance=importance)

        return {
            "encoded": True,
            "trace_id": id(trace),
            "timestamp": trace.timestamp,
            "importance": trace.importance,
            "frequency_components": len(trace.frequency_spectrum),
            "neural_codes": list(trace.neural_codes.keys()),
            "brain_waves": list(trace.brain_wave_components.keys()),
        }

    @app.post("/fnom/retrieve")
    async def fnom_retrieve(query: Dict[str, Any], request: Request, top_k: int = 5):
        """Retrieve memories using FNOM multi-modal similarity."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        assert fnom_memory is not None, "FNOM system not enabled"

        # Input validation
        try:
            if "concept" in query:
                query["concept"] = CognitiveInputValidator.validate_text_input(
                    query["concept"], "query"
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid query: {str(e)}")

        retrieved = fnom_memory.retrieve(query, top_k=top_k)

        results = []
        for trace, similarity in retrieved:
            results.append(
                {
                    "content": trace.content,
                    "similarity": similarity,
                    "timestamp": trace.timestamp,
                    "importance": trace.importance,
                    "consolidation_level": trace.consolidation_level,
                    "neural_codes": list(trace.neural_codes.keys()),
                    "brain_waves": list(trace.brain_wave_components.keys()),
                }
            )

        return {"query": query, "results": results, "count": len(results)}

    @app.post("/fnom/consolidate")
    async def fnom_consolidate(request: Request):
        """
        Run memory consolidation on FNOM system.
        """
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        assert fnom_memory is not None, "FNOM system not enabled"
        fnom_memory.consolidate()
        stats = fnom_memory.get_statistics()
        return {
            "consolidated": True,
            "average_consolidation": stats["average_consolidation"],
            "episodic_memories": stats["episodic_memories"],
            "semantic_memories": stats["semantic_memories"],
        }

    @app.post("/fnom/sleep")
    async def fnom_sleep(hours: float = 8.0):
        """Simulate sleep-dependent memory consolidation."""
        assert fnom_memory is not None, "FNOM system not enabled"
        fnom_memory.simulate_sleep(hours)

        stats = fnom_memory.get_statistics()
        return {
            "slept": True,
            "hours": hours,
            "average_consolidation": stats["average_consolidation"],
            "episodic_memories": stats["episodic_memories"],
        }

    @app.get("/fnom/stats")
    async def fnom_stats(request: Request):
        """
        Get comprehensive FNOM system statistics.
        """
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        assert fnom_memory is not None, "FNOM system not enabled"
        stats = fnom_memory.get_statistics()
        return {
            "fnom_system": "Fourier-Neural Oscillation Memory",
            "status": "active",
            "statistics": stats,
            "brain_waves": fnom_memory.brain_waves,
            "neural_parameters": fnom_memory.neural_params,
            "learning_parameters": {
                "hebbian_rate": fnom_memory.hebbian_rate,
                "consolidation_rate": fnom_memory.consolidation_rate,
                "oscillation_coupling": fnom_memory.oscillation_coupling,
                "sparse_threshold": fnom_memory.sparse_threshold,
            },
        }

    @app.get("/fnom/health")
    async def fnom_health(request: Request):
        """Check FNOM system health."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        assert fnom_memory is not None, "FNOM system not enabled"

        try:
            # Test basic functionality
            test_memory = {"concept": "health_check", "test": True}
            trace = fnom_memory.encode(test_memory, importance=0.1)
            retrieved = fnom_memory.retrieve(test_memory, top_k=1)

            return {
                "healthy": True,
                "episodic_memories": len(fnom_memory.episodic_buffer),
                "semantic_memories": len(fnom_memory.semantic_store),
                "neural_ensembles": len(fnom_memory.ensembles),
                "total_neurons": sum(
                    len(e.neurons) for e in fnom_memory.ensembles.values()
                ),
                "last_test": {"encoded": bool(trace), "retrieved": len(retrieved) > 0},
            }
        except Exception:
            return {"healthy": False, "error": "internal error"}

    @app.post("/fnom/learn")
    async def fnom_learn(patterns: List[Dict[str, Any]], request: Request):
        """Teach FNOM system new patterns for learning."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        assert fnom_memory is not None, "FNOM system not enabled"

        learned_count = 0
        for pattern in patterns:
            try:
                # Validate pattern
                if "concept" in pattern:
                    pattern["concept"] = CognitiveInputValidator.validate_text_input(
                        pattern["concept"], "concept"
                    )

                # Encode pattern
                importance = pattern.get("importance", 0.8)
                fnom_memory.encode(pattern, importance=importance)
                learned_count += 1

            except Exception:
                continue  # Skip invalid patterns

        # Run consolidation after learning
        fnom_memory.consolidate()

        return {
            "learned": learned_count,
            "total_patterns": len(patterns),
            "consolidation_run": True,
        }

    # ==========================================
    # FRACTAL MEMORY SYSTEM ENDPOINTS
    # ==========================================

    @app.post("/fractal/encode")
    async def fractal_encode(content: Dict[str, Any], request: Request):
        """
        Encode information using the fractal memory system (nature-inspired scaling).
        """
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        assert fractal_memory is not None, "Fractal system not enabled"

        # Input validation
        try:
            if "concept" in content:
                content["concept"] = CognitiveInputValidator.validate_text_input(
                    content["concept"], "concept"
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid content: {str(e)}")

        importance = content.get("importance", 1.0)
        nodes = fractal_memory.encode_fractal(content, importance=importance)

        return {
            "encoded": True,
            "nodes_created": len(nodes),
            "scales": len(fractal_memory.scales),
            "timestamp": time.time(),
            "importance": importance,
            "fractal_dimension": fractal_memory.fractal_dimension,
        }

    @app.post("/fractal/retrieve")
    async def fractal_retrieve(query: Dict[str, Any], request: Request, top_k: int = 5):
        """
        Retrieve information using fractal resonance patterns.
        """
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        assert fractal_memory is not None, "Fractal system not enabled"

        # Input validation
        try:
            if "concept" in query:
                query["concept"] = CognitiveInputValidator.validate_text_input(
                    query["concept"], "concept"
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid query: {str(e)}")

        results = fractal_memory.retrieve_fractal(query, top_k=top_k)

        # Format results
        formatted_results = []
        for node, resonance in results:
            formatted_results.append(
                {
                    "content": node.memory_trace,
                    "resonance": float(resonance),
                    "scale": node.scale.name,
                    "scale_level": node.scale.level,
                    "activity": float(node.activity),
                    "connections": len(node.connections),
                    "timestamp": node.timestamp,
                }
            )

        return {
            "retrieved": len(results),
            "results": formatted_results,
            "query_processed": True,
        }

    @app.post("/fractal/consolidate")
    async def fractal_consolidate(request: Request):
        """Run fractal memory consolidation (emergent pattern strengthening)."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        assert fractal_memory is not None, "Fractal system not enabled"

        fractal_memory.consolidate_fractal()

        return {
            "consolidated": True,
            "emergent_patterns": len(
                fractal_memory._find_emergent_patterns(
                    [n for nodes in fractal_memory.nodes.values() for n in nodes]
                )
            ),
            "timestamp": time.time(),
        }

    @app.get("/fractal/stats")
    async def fractal_stats(request: Request):
        """Get fractal memory system statistics."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        assert fractal_memory is not None, "Fractal system not enabled"

        stats = fractal_memory.get_fractal_statistics()

        return {
            "system_stats": stats,
            "scales": [
                {
                    "level": s.level,
                    "name": s.name,
                    "size": float(s.size),
                    "time_constant": float(s.time_constant),
                    "complexity": float(s.complexity),
                    "energy_efficiency": float(s.energy_efficiency),
                }
                for s in fractal_memory.scales
            ],
            "timestamp": time.time(),
        }

    @app.get("/fractal/health")
    async def fractal_health(request: Request):
        """Check fractal memory system health."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        assert fractal_memory is not None, "Fractal system not enabled"

        try:
            # Test basic functionality
            test_memory = {"concept": "health_check", "test": True}
            nodes = fractal_memory.encode_fractal(test_memory, importance=0.1)
            results = fractal_memory.retrieve_fractal(test_memory, top_k=1)

            return {
                "healthy": True,
                "total_nodes": sum(
                    len(nodes) for nodes in fractal_memory.nodes.values()
                ),
                "scales_active": len(fractal_memory.scales),
                "last_test": {"encoded": len(nodes) > 0, "retrieved": len(results) > 0},
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}


# ==========================================
# UNIFIED BRAIN SYSTEM ENDPOINTS - PHASE 2 OPTIMIZATION (gated)
# ==========================================

if getattr(cfg, "expose_brain_demos", False) and unified_brain is not None:

    @app.post("/brain/encode")
    async def brain_encode(content: Dict[str, Any], request: Request):
        """Encode using unified FNOM + Fractal brain system (PHASE 2)."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)
        assert unified_brain is not None, "Unified brain system not enabled"

        # Input validation
        try:
            if "concept" in content:
                content["concept"] = CognitiveInputValidator.validate_text_input(
                    content["concept"], "concept"
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid content: {str(e)}")

        importance = content.get("importance", 1.0)
        result = unified_brain.process_memory(content, importance=importance)

        return {
            "encoded": True,
            "systems": ["fractal", "fnom"],
            "fractal_nodes": result["fractal_nodes"],
            "fnom_components": result["fnom_components"],
            "timestamp": time.time(),
            "importance": result["adjusted_importance"],
            "unified": True,
        }

    @app.post("/brain/transcendence")
    async def brain_mathematical_transcendence(
        content: Dict[str, Any], request: Request
    ):
        """PHASE 4: Mathematical transcendence through pure mathematical intelligence."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)

        # Input validation
        try:
            if "concept" in content:
                content["concept"] = CognitiveInputValidator.validate_text_input(
                    content["concept"], "concept"
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid content: {str(e)}")

        result = mathematical_transcendence.achieve_mathematical_transcendence(content)

        return {
            "mathematical_transcendence": True,
            "golden_ratio_optimized": result.get("golden_ratio_optimized", False),
            "fibonacci_optimized": result.get("fibonacci_optimized", False),
            "transcendent_efficiency": result.get("transcendent_efficiency", 0),
            "processing_time": result.get("processing_time", 0),
            "phase_4": True,
        }

    @app.post("/brain/multiverse")
    async def brain_multiverse_transcendence(content: Dict[str, Any], request: Request):
        """PHASE 5: Multiverse transcendence through elegant mathematical cognition."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)

        # Input validation
        try:
            if "concept" in content:
                content["concept"] = CognitiveInputValidator.validate_text_input(
                    content["concept"], "concept"
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid content: {str(e)}")

        # Multiverse engine removed; return default values
        return {
            "multiverse_transcendence": False,
            "universes_created": 0,
            "entanglement_network": 0,
            "total_entanglement_strength": 0,
            "multiverse_consciousness_level": 0,
            "cognition_transfers": 0,
            "mathematical_foundations": [],
            "processing_time": 0,
            "phase_5": True,
        }

    @app.post("/brain/consciousness")
    async def brain_fractal_consciousness(content: Dict[str, Any], request: Request):
        """PHASE 4: Fractal consciousness with self-similar awareness across scales."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)

        # Input validation
        try:
            if "concept" in content:
                content["concept"] = CognitiveInputValidator.validate_text_input(
                    content["concept"], "concept"
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid content: {str(e)}")

        consciousness_depth = content.get("consciousness_depth", 3)
        result = fractal_consciousness.achieve_fractal_consciousness(
            content, consciousness_depth
        )

        return {
            "fractal_consciousness": True,
            "consciousness_depth": result.get("consciousness_depth", 0),
            "self_similarity_score": result.get("self_similarity_score", 0),
            "meta_cognition_levels": result.get("meta_cognition_levels", 0),
            "processing_time": result.get("processing_time", 0),
            "phase_4": True,
        }

    @app.post("/brain/quantum")
    async def brain_quantum_cognition(content: Dict[str, Any], request: Request):
        """PHASE 4: Quantum cognition with superposition-based processing."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)

        # Input validation
        try:
            if "concept" in content:
                content["concept"] = CognitiveInputValidator.validate_text_input(
                    content["concept"], "concept"
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid content: {str(e)}")

        num_superpositions = content.get("num_superpositions", 3)
        result = quantum_cognition.process_in_superposition(content, num_superpositions)

        return {
            "quantum_processed": True,
            "num_superpositions": result.get("num_superpositions", 0),
            "superposition_collapsed": result.get("superposition_collapsed", False),
            "quantum_interference": result.get("quantum_interference", 0),
            "processing_time": result.get("processing_time", 0),
            "phase_4": True,
        }

    @app.get("/brain/unified/stats")
    async def brain_stats(request: Request):
        """Get unified brain system statistics (PHASE 2)."""
        get_tenant(request, cfg.namespace)
        require_auth(request, cfg)

        assert (
            fractal_memory is not None and fnom_memory is not None
        ), "Unified systems not enabled"
        fractal_stats = fractal_memory.get_fractal_statistics()
        fnom_stats = fnom_memory.get_statistics()

        return {
            "unified_system": True,
            "fractal_memory": fractal_stats,
            "fnom_memory": fnom_stats,
            "total_memories": fractal_stats["total_nodes"]
            + fnom_stats["episodic_memories"],
            "systems_active": ["fractal", "fnom"],
            "timestamp": time.time(),
        }


# (copilot ingestion endpoint removed; keep core API only)
