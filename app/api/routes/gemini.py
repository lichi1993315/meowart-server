"""Gemini API proxy routes for forwarding requests to Google's Generative AI API."""
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.core.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/api/gemini", tags=["gemini"])

# Configuration
GEMINI_API_KEY: Optional[str] = settings.GEMINI_API_KEY
GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com"
OUTPUT_DIR = Path("./gemini_logs")

# HTTP client with reasonable timeouts
http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))

# Blacklist users (can be loaded from config or database)
blacklist_users: set[str] = set()


def _log(message: str) -> None:
    """Simple logging with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


async def save_request_to_file(
    request_body: bytes,
    path: str,
    method: str,
    headers: dict[str, Any],
    user_id: str,
    filepath: Path,
    timestamp_iso: str,
) -> None:
    """Save request data to JSONL file."""
    import json
    try:
        # Try to parse as JSON, fallback to raw string
        try:
            body_data = json.loads(request_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body_data = request_body.decode("utf-8", errors="replace")
        
        request_data = {
            "type": "request",
            "timestamp": timestamp_iso,
            "user_id": user_id,
            "method": method,
            "path": path,
            "body": body_data,
        }
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(request_data, ensure_ascii=False) + "\n")
    except Exception as e:
        _log(f"Failed to save request: {e}")


async def save_response_to_file(
    response_content: bytes,
    response_status: int,
    duration_ms: float,
    user_id: str,
    filepath: Path,
    timestamp_iso: str,
) -> None:
    """Save response data to JSONL file."""
    import json
    try:
        # Try to parse as JSON, fallback to raw string
        try:
            body_data = json.loads(response_content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body_data = response_content.decode("utf-8", errors="replace")
        
        response_data = {
            "type": "response",
            "timestamp": timestamp_iso,
            "user_id": user_id,
            "status_code": response_status,
            "duration_ms": duration_ms,
            "body": body_data,
        }
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(response_data, ensure_ascii=False) + "\n")
    except Exception as e:
        _log(f"Failed to save response: {e}")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_gemini(request: Request, path: str) -> Response:
    """
    Proxy all requests to Google's Generative AI API.
    
    This captures paths like:
    - /v1beta/models/gemini-2.0-flash:generateContent
    - /v1beta/models/gemini-pro:streamGenerateContent
    - etc.
    """
    api_key = GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")

    try:
        # Read request body
        body = await request.body()

        # Extract user ID from X-User-ID header, default to anonymous
        user_id = request.headers.get("x-user-id") or "anonymous_user"

        # Check blacklist
        if user_id in blacklist_users:
            _log(f"🚫 Blocked blacklisted user: {user_id}")
            raise HTTPException(status_code=403, detail="Access denied")

        # Generate file path for logging
        user_folder = user_id if user_id else "anonymous"
        user_dir = OUTPUT_DIR / user_folder
        user_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Milliseconds
        timestamp_iso = datetime.now().isoformat()
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}-{unique_id}.jsonl"
        filepath = user_dir / filename

        # Save request asynchronously (fire and forget)
        asyncio.create_task(save_request_to_file(
            request_body=body,
            path=path,
            method=request.method,
            headers=dict(request.headers),
            user_id=user_id,
            filepath=filepath,
            timestamp_iso=timestamp_iso,
        ))

        # Build target URL
        target_url = f"{GEMINI_BASE_URL}/{path}"
        
        # Get query params (e.g., ?key=xxx or ?alt=sse)
        params = dict(request.query_params)
        
        # Add API key if not already in params
        if "key" not in params:
            params["key"] = api_key

        # Prepare headers - remove host and connection headers
        proxy_headers = {
            k: v for k, v in request.headers.items() 
            if k.lower() not in ("host", "connection", "content-length")
        }

        # Record start time
        start_time = datetime.now()

        # Forward request to Gemini
        response = await http_client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=proxy_headers,
            params=params,
        )

        # Calculate duration
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Save response asynchronously (fire and forget)
        asyncio.create_task(save_response_to_file(
            response_content=response.content,
            response_status=response.status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            filepath=filepath,
            timestamp_iso=timestamp_iso,
        ))

        # Return response with proper headers
        # Filter out hop-by-hop headers
        response_headers = {
            k: v for k, v in response.headers.items()
            if k.lower() not in ("transfer-encoding", "connection", "content-encoding")
        }

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get("content-type"),
        )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))
