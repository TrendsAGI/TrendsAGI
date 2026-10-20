# File: trendsagi-client/trendsagi/exceptions.py

class TrendsAGIError(Exception):
    """Base exception for the TrendsAGI SDK. All API errors inherit from this class."""
    pass

class AuthenticationError(TrendsAGIError):
    """Raised when authentication fails (e.g., invalid API key)."""
    pass

class APIError(TrendsAGIError):
    """Raised for non-2xx API responses.

    ``body`` holds the decoded JSON error response when there was one.
    """
    def __init__(self, status_code, error_detail, body=None):
        self.status_code = status_code
        self.error_detail = error_detail
        self.body = body
        super().__init__(f"API request failed with status {status_code}: {error_detail}")

class QueryError(APIError):
    """
    Raised by ``execute_sql`` when a query is refused or fails.

    :ivar code: Why, e.g. ``unknown_table``, ``function_not_allowed``,
        ``query_error``, ``timeout`` or ``plan_required``.
    :ivar hint: A suggested fix, when the server has one.
    :ivar position: 1-based character offset of the problem in the query, when known.
    """
    def __init__(self, status_code, body):
        self.code = body.get("error")
        self.hint = body.get("hint")
        self.position = body.get("position")
        super().__init__(status_code, body.get("detail"), body=body)

class NotFoundError(APIError):
    """Raised for 404 Not Found errors."""
    pass

class RateLimitError(APIError):
    """Raised for 429 Too Many Requests errors."""
    pass

class ConflictError(APIError):
    """Raised for 409 Conflict errors."""
    pass

class MaintenanceError(APIError):
    """
    Raised when the API is in maintenance mode (503 Service Unavailable).
    
    This typically occurs when Redis or other critical backend services are unavailable.
    During maintenance, API usage cannot be tracked, so requests are blocked to prevent
    untracked overage billing.
    """
    def __init__(self, message: str = "TrendsAGI is currently under maintenance. Please try again later."):
        super().__init__(503, message)
        self.message = message
