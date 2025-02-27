from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class CORSLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.debug(f"Incoming request: {request.method} {request.url}")
        logger.debug(f"Request headers: {request.headers}")
        
        response = await call_next(request)
        
        # Log CORS-related headers
        logger.debug(f"Response headers: {response.headers}")
        return response

def setup_cors(app, origins):
    """Configure CORS for the application"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600,
    )
    
    # Add logging middleware in debug mode
    if app.debug:
        app.add_middleware(CORSLoggingMiddleware)
