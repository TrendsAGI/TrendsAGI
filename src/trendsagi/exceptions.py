# File: trendsagi-client/trendsagi/exceptions.py

class TrendsAGIError(Exception):
    """Base exception for the TrendsAGI SDK. All API errors inherit from this class."""
    pass

class AuthenticationError(TrendsAGIError):
    """Raised when authentication fails (e.g., invalid API key)."""
    pass

class APIError(TrendsAGIError):
    """Raised for non-2xx API responses."""
    def __init__(self, status_code, error_detail):
        self.status_code = status_code
        self.error_detail = error_detail
        super().__init__(f"API request failed with status {status_code}: {error_detail}")

class NotFoundError(APIError):
    """Raised for 404 Not Found errors."""
    pass

class RateLimitError(APIError):
    """Raised for 429 Too Many Requests errors."""
    pass

class ConflictError(APIError):
    """Raised for 409 Conflict errors."""
    pass