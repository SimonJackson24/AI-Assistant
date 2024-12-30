from typing import Any, Dict, Optional, Union, List
from dataclasses import dataclass
from enum import Enum
import logging
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel, ValidationError
import time
from src.monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class ErrorCode(Enum):
    """Standardized error codes"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"

@dataclass
class UIConfig:
    """UI configuration settings"""
    api_version: str = "v1"
    enable_docs: bool = True
    enable_metrics: bool = True
    rate_limit: int = 100  # requests per minute
    cors_origins: List[str] = None

class ResponseWrapper(BaseModel):
    """Standard API response wrapper"""
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class UIManager:
    """Manages API interface and user experience"""
    
    def __init__(self, config: Optional[UIConfig] = None):
        self.config = config or UIConfig()
        self.app = FastAPI(
            title="AI Code Assistant API",
            version=self.config.api_version,
            docs_url=None if not self.config.enable_docs else "/docs"
        )
        self.metrics = MetricsCollector()
        self._setup_middleware()
        self._setup_error_handlers()
        
    def _setup_middleware(self):
        """Setup API middleware"""
        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins or ["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        # Request timing
        @self.app.middleware("http")
        async def add_timing_header(request: Request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            await self.metrics.record_metric(
                "request_processing_time",
                process_time,
                {"path": request.url.path}
            )
            return response
            
    def _setup_error_handlers(self):
        """Setup global error handlers"""
        @self.app.exception_handler(ValidationError)
        async def validation_error_handler(request: Request, exc: ValidationError):
            return self.error_response(
                ErrorCode.VALIDATION_ERROR,
                "Validation error",
                details=exc.errors()
            )
            
        @self.app.exception_handler(HTTPException)
        async def http_error_handler(request: Request, exc: HTTPException):
            return self.error_response(
                ErrorCode.SYSTEM_ERROR,
                exc.detail,
                status_code=exc.status_code
            )
            
    def success_response(
        self,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        status_code: int = 200
    ) -> JSONResponse:
        """Create a standardized success response"""
        return JSONResponse(
            status_code=status_code,
            content=ResponseWrapper(
                success=True,
                data=data,
                metadata=metadata or {}
            ).dict()
        )
        
    def error_response(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Any] = None,
        status_code: int = 400
    ) -> JSONResponse:
        """Create a standardized error response"""
        return JSONResponse(
            status_code=status_code,
            content=ResponseWrapper(
                success=False,
                error={
                    "code": code.value,
                    "message": message,
                    "details": details
                }
            ).dict()
        )
        
    def register_routes(self):
        """Register API routes"""
        @self.app.get("/health")
        async def health_check():
            return self.success_response({"status": "healthy"})
            
        @self.app.get("/metrics")
        async def get_metrics():
            if not self.config.enable_metrics:
                raise HTTPException(status_code=404)
            metrics = await self.metrics.get_all_metrics()
            return self.success_response(metrics)
            
        @self.app.get("/docs")
        async def custom_docs():
            if not self.config.enable_docs:
                raise HTTPException(status_code=404)
            return get_swagger_ui_html(
                openapi_url="/openapi.json",
                title="AI Code Assistant API Documentation"
            ) 