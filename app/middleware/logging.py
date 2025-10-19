import logging
import re
import time
from datetime import datetime
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Setup logger
logger = logging.getLogger("app.middleware.logging")

SENSITIVE_RE = re.compile(r"password|token|secret|authorization|api[_-]?key", re.I) #also added case sensitive flag

def redact_dict(data: dict) -> dict:
     """Redact sensitive values from a dictionary"""
     try:
         return {key: ("<REDACTED>" if SENSITIVE_RE.search(key) else value) for key, value in data.items()}
     except Exception:
         return data
    
def sanitize_headers(headers: dict) -> dict:
    """Redact sensitive values from headers"""
    return {key: ("<REDACTED>" if SENSITIVE_RE.search(key) else value) for key, value in headers.items()}

# Setup logger
#just to provide the path in log message
def setup_logging(level: int = logging.INFO) -> None:
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s "
    logging.basicConfig(level=level, format=fmt)
 
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        
        # STEP 1: Log request method, URL, and timestamp
        timestamp = datetime.utcnow().isoformat() + "Z"
        # STEP 2: Measure processing time
        start_time = time.perf_counter()
        method = request.method
        url = str(request.url)
        client = request.client.host if request.client else None
        
        # STEP 4: Extract and sanitize query params and headers
        query = redact_dict(dict(request.query_params))
        headers = sanitize_headers(dict(request.headers))
        
        logger.info(f"request:start method={method} url={url} time={timestamp} client={client} query={query} headers={headers}")
        
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(f"request:error method={method} url={url} duration_ms={duration_ms:.2f}")
            raise
        
        duration = (time.perf_counter() - start_time) * 1000  # in milliseconds
        # STEP 3: Log response status code and processing time
        logger.info(f"request:end method={method} url={url} " 
        f"status_code={response.status_code} duration={duration:.2f}ms")
        
        return response
        
# for my reference only
"""
# Your middleware
class LoggingMiddleware:
    async def dispatch(self, request, call_next):
        print("1. BEFORE call_next")
        response = await call_next(request)  # ← Pauses here
        print("4. AFTER call_next")
        return response

# Your route
@app.get("/users")
async def get_users():
    print("2. Inside route handler")
    return {"users": ["Alice", "Bob"]}
```

**Execution order:**
```
1. BEFORE call_next          ← Middleware runs first
2. Inside route handler       ← call_next() calls your endpoint
3. (response is created)
4. AFTER call_next            ← Middleware resumes
5. (response returned to client)
"""  