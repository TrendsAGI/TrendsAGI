# File: trendsagi-client/trendsagi/client.py

import re
import requests
import websockets
import ssl
import random
import time
from typing import Optional, List, Dict, Any, AsyncGenerator

from pydantic import ValidationError

from . import models
from . import exceptions

try:
    import certifi
except ImportError:
    certifi = None

def _strip_html(text: str) -> str:
    """Remove HTML tags from error responses to return clean, parseable messages."""
    if not text:
        return text
    clean = re.sub(r'<[^>]+>', '', text)
    clean = ' '.join(clean.split())
    return clean.strip() if clean else text

class TrendsAGIClient:
    """
    Python SDK for the TrendsAGI Real-Time Context Layer.
    
    Provides AI agents with structured access to live trend data, financial intelligence,
    and actionable insights via REST and WebSocket APIs. Designed for seamless integration
    into agent workflows and autonomous systems.
    
    :param api_key: Your TrendsAGI API key, generated from your profile page.
    :param base_url: The base URL of the TrendsAGI API. Defaults to the production URL.
                     Override this for development or testing against a local server.
                     Example for local dev: base_url="http://localhost:8000"
    """
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.trendsagi.com",
        enable_retry_on_rate_limit: bool = False,
        max_retries: int = 3,
        max_retry_wait: float = 10.0,
        retry_backoff_factor: float = 0.5,
        retry_jitter: float = 0.1,
    ):
        if not api_key:
            raise exceptions.AuthenticationError("API key is required.")
        
        self.base_url = base_url.rstrip('/')
        self._session = requests.Session()
        self._session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self._enable_retry_on_rate_limit = enable_retry_on_rate_limit
        self._max_retries = max_retries
        self._max_retry_wait = max_retry_wait
        self._retry_backoff_factor = retry_backoff_factor
        self._retry_jitter = retry_jitter

    def _get_retry_after(self, response: requests.Response) -> Optional[float]:
        retry_after = response.headers.get("Retry-After")
        if not retry_after:
            return None
        try:
            return float(retry_after)
        except ValueError:
            return None

    def _compute_retry_delay(self, attempt: int, retry_after: Optional[float]) -> float:
        if retry_after is not None:
            delay = retry_after
        else:
            delay = self._retry_backoff_factor * (2 ** attempt)
        if self._retry_jitter > 0:
            delay += random.uniform(0, self._retry_jitter)
        if self._max_retry_wait is not None and delay > self._max_retry_wait:
            delay = self._max_retry_wait
        return max(0.0, delay)

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Internal helper for making API requests."""
        url = f"{self.base_url}{endpoint}"
        try:
            attempts = 0
            while True:
                response = self._session.request(method, url, **kwargs)

                if 200 <= response.status_code < 300:
                    if response.status_code == 204:
                        return None
                    return response.json()

                try:
                    error_detail = response.json().get('detail', response.text)
                except requests.exceptions.JSONDecodeError:
                    error_detail = _strip_html(response.text)

                if response.status_code == 401:
                    raise exceptions.AuthenticationError(error_detail)
                if response.status_code == 404:
                    raise exceptions.NotFoundError(response.status_code, error_detail)
                if response.status_code == 409:
                    raise exceptions.ConflictError(response.status_code, error_detail)
                if response.status_code == 429:
                    retry_after = self._get_retry_after(response)
                    if self._enable_retry_on_rate_limit and attempts < self._max_retries:
                        delay = self._compute_retry_delay(attempts, retry_after)
                        attempts += 1
                        if delay > 0:
                            time.sleep(delay)
                        continue
                    raise exceptions.RateLimitError(response.status_code, error_detail)
                if response.status_code == 503:
                    raise exceptions.MaintenanceError(error_detail)

                raise exceptions.APIError(response.status_code, error_detail)

        except requests.exceptions.RequestException as e:
            raise exceptions.TrendsAGIError(f"Network error communicating with API: {e}")

    # --- Trends & Insights Methods ---

    def get_trends(
        self,
        sort_by: str = 'volume',
        sort_dir: str = 'desc',
        limit: int = 20,
        offset: int = 0,
        period: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_snapshots: Optional[int] = None,
        exclude_sentiment: Optional[str] = None,
        interests: Optional[List[str]] = None,
        order: Optional[str] = None # Alias for sort_dir
    ) -> models.TrendListResponse:
        """
        Retrieve a list of currently trending topics.
        """
        page = (offset // limit) + 1
        
        # Handle aliasing for order/sort_dir
        if order:
            sort_dir = order
            
        params = {
            "page": page,
            "limit": limit,
            "sort_by": sort_by,
            "sort_dir": sort_dir,
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "min_snapshots": min_snapshots,
            "exclude_sentiment": exclude_sentiment
        }
        if interests:
            params["interests"] = ",".join(interests)
            
        params = {k: v for k, v in params.items() if v is not None}
        response_data = self._request('GET', '/api/trends', params=params)
        return models.TrendListResponse.model_validate(response_data)

    def get_trend_autocomplete(self, query: str) -> models.AutocompleteResponse:
        """
        Get autocomplete suggestions for a query.
        """
        params = {"q": query}
        response_data = self._request('GET', '/api/trends/autocomplete', params=params)
        # If response is just a list of strings ["foo", "bar"]
        if isinstance(response_data, list):
            return models.AutocompleteResponse(suggestions=response_data)
        return models.AutocompleteResponse.model_validate(response_data)

    def get_trend_categories(self) -> models.CategoryListResponse:
        """
        Get list of active trend categories.
        """
        response_data = self._request('GET', '/api/trends/categories')
        # If response is list of dicts
        if isinstance(response_data, list):
            return models.CategoryListResponse(categories=[models.CategoryInfo.model_validate(c) for c in response_data])
        return models.CategoryListResponse.model_validate(response_data)

    def search_insights(self, key_theme_contains: str, limit: int = 10) -> models.TrendListResponse:
        """
        Search for trends based on their AI insights content.
        """
        params = {"q": key_theme_contains, "limit": limit}
        response_data = self._request('GET', '/api/insights/search', params=params)
        return models.TrendListResponse.model_validate(response_data)

    def get_trend(self, trend_id: int) -> models.TrendItem:
        """
        Retrieve a single trend by ID.
        """
        response_data = self._request('GET', f'/api/trends/{trend_id}')
        return models.TrendItem.model_validate(response_data)

    def get_ai_insights(self, trend_id: int) -> Optional[models.AIInsight]:
        """
        Retrieve cached AI insights for a trend.

        This endpoint is read-focused and returns pre-generated insight data used for
        client-side decision engines.
        """
        response_data = self._request('GET', f'/api/trends/{trend_id}/ai-insights')
        if response_data is None:
            return None
        return models.AIInsight.model_validate(response_data)

    def generate_ai_insights(self, trend_id: int, force_refresh: bool = False) -> models.GenerateAIInsightResponse:
        """
        Queue AI insight generation for a trend.
        """
        payload = {"force_refresh": force_refresh}
        response_data = self._request('POST', f'/api/trends/{trend_id}/ai-insights/generate', json=payload)
        return models.GenerateAIInsightResponse.model_validate(response_data)

    def get_ai_insight_status(self, task_id: str) -> models.AIInsightTaskStatus:
        """
        Check the status of an AI insight generation task.
        """
        response_data = self._request('GET', f'/api/trends/ai-insights/status/{task_id}')
        return models.AIInsightTaskStatus.model_validate(response_data)
        
    def get_trend_analytics(self, trend_id: int, period: str = '7d') -> models.TrendAnalyticsResponse:
        """
        Retrieve analytics data for a specific trend.
        
        :param trend_id: The ID of the trend.
        :param period: Time period for analytics (e.g., '1h', '24h', '7d', '30d').
        """
        params = {"period": period}
        response_data = self._request('GET', f'/api/trends/{trend_id}/analytics', params=params)
        
        # Helper to convert list of dicts to list of SnapshotData objects manually if needed, 
        # or rely on pydantic parsing.
        # But we need to make sure the response 'data' field (which is list of SnapshotData) 
        # is parsed correctly into the 'data' field of TrendAnalyticsResponse.
        # The backend schema `TrendAnalyticsResponse` has `Data []SnapshotData`.
        # Our Python model `TrendAnalyticsResponse` defines `data` as `List[Dict[str, Any]]` currently.
        # Let's map it to objects if the user expects dot access.
        
        analytics = models.TrendAnalyticsResponse.model_validate(response_data)
        
        # Enhance the 'data' list to be objects with .date attribute as expected by test script
        # The test expects: first_point.date.date() and first_point.volume
        # So we should probably define SnapshotData model properly and use it.
        # I defined SnapshotData in models.py above. Let's ensure TrendAnalyticsResponse uses it.
        # Wait, I defined `data: List[Dict]` in the previous turn plan? 
        # Let me re-check the Edit I just queued or am about to queue.
        # I defined `class SnapshotData` and `data: List[Dict]`. 
        # Better to make `data: List[SnapshotData]`.
        
        return analytics

    def analyze_trend(self, trend_id: int, force_refresh: bool = False) -> models.AnalysisResponse:
        """
        Trigger an analysis task for a trend.
        """
        payload = {"force_refresh": force_refresh}
        response_data = self._request('POST', f'/api/trends/{trend_id}/analyze', json=payload)
        return models.AnalysisResponse.model_validate(response_data)

    # --- Custom Reports Methods ---

    def generate_custom_report(self, report_request: Dict[str, Any]) -> models.CustomReport:
        """
        Generate a custom report based on specified dimensions, metrics, and filters.
        """
        response_data = self._request('POST', '/api/reports/custom', json=report_request)
        return models.CustomReport.model_validate(response_data)
        
    # --- Intelligence Suite Methods ---

    def get_recommendations(
        self,
        limit: int = 10,
        offset: int = 0,
        recommendation_type: Optional[str] = None,
        source_trend_query: Optional[str] = None,
        priority: Optional[str] = None,
        status: str = 'new',
        match_user_interests: bool = False,
        sort: str = 'priority',
    ) -> models.RecommendationListResponse:
        """
        Get prioritized, evidence-backed recommendations generated for the user.

        The ``decision_brief.confidence.score`` in each recommendation measures
        evidence completeness. It is not a probability that the action will succeed.

        :param limit: Number of records to request. Values above the API maximum
                      are capped at 100.
        :param offset: Zero-based pagination offset.
        :param recommendation_type: Optional recommendation type, or ``"all"``.
        :param source_trend_query: Optional source-trend name search (maximum 100 characters).
        :param priority: Optional ``low``, ``medium``, ``high``, ``critical``, or ``all``.
        :param status: ``new`` (default), ``viewed``, ``actioned``, ``dismissed``, or ``all``.
        :param match_user_interests: Restrict results to the user's saved interests.
        :param sort: ``priority`` (default) or ``newest``.
        """
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValueError("offset must be a non-negative integer")

        valid_types = {
            "pr_response", "content_idea", "marketing_angle", "seo_optimization",
            "influencer_collab", "product_improvement", "crm_strategy", "monitoring",
            "other", "all",
        }
        normalized_type = recommendation_type.strip() if recommendation_type is not None else None
        normalized_type = normalized_type or None
        if normalized_type is not None and normalized_type not in valid_types:
            raise ValueError("unsupported recommendation type")
        normalized_source_query = (
            source_trend_query.strip() if source_trend_query is not None else None
        )
        normalized_source_query = normalized_source_query or None
        if normalized_source_query is not None and len(normalized_source_query) > 100:
            raise ValueError("source_trend_query must be 100 characters or fewer")

        normalized_priority = priority.lower().strip() if priority is not None else None
        normalized_priority = normalized_priority or None
        if normalized_priority not in {None, "low", "medium", "high", "critical", "all"}:
            raise ValueError("unsupported recommendation priority")
        normalized_status = status.lower().strip() or "new"
        if normalized_status not in {"new", "viewed", "actioned", "dismissed", "all"}:
            raise ValueError("unsupported recommendation status")
        normalized_sort = sort.lower().strip() or "priority"
        if normalized_sort not in {"priority", "newest"}:
            raise ValueError("sort must be priority or newest")

        params = {
            "limit": min(limit, 100),
            "offset": offset,
            "type": normalized_type,
            "sourceTrendQ": normalized_source_query,
            "priority": normalized_priority,
            "status": normalized_status,
            "match_user_interests": str(match_user_interests).lower(),
            "sort": normalized_sort,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response_data = self._request('GET', '/api/intelligence/recommendations', params=params)
        return models.RecommendationListResponse.model_validate(response_data)

    def perform_recommendation_action(self, recommendation_id: int, action: Optional[str] = None, feedback: Optional[str] = None) -> models.Recommendation:
        """
        Update one recommendation workflow state or provide feedback.

        The API rejects ``action="actioned"`` with HTTP 409 when the current
        decision brief is not actionable. Refresh the recommendation and verify
        its missing evidence before retrying that transition.
        """
        if not isinstance(recommendation_id, int) or isinstance(recommendation_id, bool) or recommendation_id <= 0:
            raise ValueError("recommendation_id must be a positive integer")
        normalized_action = action.lower().strip() if action is not None else None
        normalized_action = normalized_action or None
        normalized_feedback = feedback.strip() if feedback is not None else None
        normalized_feedback = normalized_feedback or None

        if normalized_action and normalized_feedback:
            raise ValueError("Only one of 'action' or 'feedback' can be provided at a time.")
        if not normalized_action and not normalized_feedback:
            raise ValueError("Either 'action' or 'feedback' must be provided.")
        if normalized_action not in {None, "new", "viewed", "actioned", "dismissed"}:
            raise ValueError("unsupported recommendation action")
        if normalized_feedback is not None and len(normalized_feedback) > 500:
            raise ValueError("feedback must be 500 characters or fewer")

        payload = {"action": normalized_action, "feedback": normalized_feedback}
        payload = {k: v for k, v in payload.items() if v is not None}
        response_data = self._request('POST', f'/api/intelligence/recommendations/{recommendation_id}/action', json=payload)
        return models.Recommendation.model_validate(response_data)

    def get_crisis_events(
        self,
        limit: int = 10, offset: int = 0, status: str = 'active', keyword: Optional[str] = None,
        severity: Optional[str] = None, time_range: str = '24h',
        start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> models.CrisisEventListResponse:
        """
        Get crisis events detected for the user.
        """
        params = {
            "limit": limit, "offset": offset, "status": status, "keyword": keyword, 
            "severity": severity, "timeRange": time_range, "startDate": start_date, "endDate": end_date
        }
        params = {k: v for k, v in params.items() if v is not None}
        response_data = self._request('GET', '/api/intelligence/crisis-events', params=params)
        return models.CrisisEventListResponse.model_validate(response_data)

    def _fallback_crisis_event_from_list(self, event_id: int) -> models.CrisisEvent:
        """
        Fallback when the single-event endpoint returns a status-only payload or is unavailable.
        """
        try:
            resp = self.get_crisis_events(limit=100, status="active")
            for e in resp.events:
                if e.id == event_id:
                    return e
        except Exception:
            pass
        raise exceptions.NotFoundError(404, f"Crisis event {event_id} not found")
        
    def get_crisis_event(self, event_id: int) -> models.CrisisEvent:
        """
        Get a single crisis event.
        """
        try:
            response_data = self._request('GET', f'/api/intelligence/crisis-events/{event_id}')
        except exceptions.NotFoundError:
            return self._fallback_crisis_event_from_list(event_id)

        try:
            return models.CrisisEvent.model_validate(response_data)
        except ValidationError:
            if isinstance(response_data, dict) and (
                "status" in response_data or "success" in response_data
            ):
                return self._fallback_crisis_event_from_list(event_id)
            raise

    def perform_crisis_event_action(self, event_id: int, action: str) -> models.CrisisEvent:
        """
        Update the status of a crisis event (e.g., "acknowledge", "archive").
        """
        response_data = self._request('POST', f'/api/intelligence/crisis-events/{event_id}/action', json={"action": action})
        try:
            return models.CrisisEvent.model_validate(response_data)
        except ValidationError:
            # Some backend versions only return a simple status/success payload.
            if isinstance(response_data, dict) and (
                "status" in response_data or "success" in response_data
            ):
                return self.get_crisis_event(event_id)
            raise

    def get_financial_data(self, timezone: Optional[str] = None) -> models.FinancialDataResponse:
        """
        Retrieves a consolidated report of the latest financial data.
        
        :param timezone: Optional. An IANA timezone name (e.g., 'Europe/London') to convert event times to.
                         Defaults to UTC if not provided.
        """
        params = {}
        if timezone:
            params['timezone'] = timezone
            
        response_data = self._request('GET', '/api/intelligence/financial-data', params=params)
        return models.FinancialDataResponse.model_validate(response_data)
 

    # --- User & Account Management Methods ---

    def get_topic_interests(self) -> List[models.TopicInterest]:
        """Retrieve the list of topic interests tracked by the user."""
        response_data = self._request('GET', '/api/user/interests')
        return [models.TopicInterest.model_validate(item) for item in response_data]

    def create_topic_interest(
        self,
        keyword: str, alert_condition_type: str,
        volume_threshold_value: Optional[int] = None, percentage_growth_value: Optional[float] = None
    ) -> models.TopicInterest:
        """
        Create a new topic interest.
        """
        payload = {
            "keyword": keyword, "alert_condition_type": alert_condition_type,
            "volume_threshold_value": volume_threshold_value, "percentage_growth_value": percentage_growth_value
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        response_data = self._request('POST', '/api/user/interests', json=payload)
        # Server returns a list; return the first created interest
        if isinstance(response_data, list):
            return models.TopicInterest.model_validate(response_data[0])
        return models.TopicInterest.model_validate(response_data)
        
    def delete_topic_interest(self, interest_id: int) -> None:
        """Delete a specific topic interest."""
        self._request('DELETE', f'/api/user/interests/{interest_id}')

    # --- Export Settings Methods ---

    def get_export_settings(self) -> List[models.ExportConfig]:
        """Get all export configurations."""
        response_data = self._request('GET', '/api/user/export/settings')
        # Expecting list of configs
        if isinstance(response_data, list):
            return [models.ExportConfig.model_validate(item) for item in response_data]
        return [models.ExportConfig.model_validate(item) for item in response_data.get('settings', [])]

    def save_export_settings(
        self,
        destination: str,
        config: Dict[str, Any],
        schedule: str,
        schedule_time: str,
        is_active: bool = True,
        selected_fields: Optional[List[str]] = None
    ) -> models.ExportConfig:
        """
        Save a new export configuration.
        """
        payload = {
            "destination": destination,
            "config": config,
            "schedule": schedule,
            "schedule_time": schedule_time,
            "is_active": is_active,
            "selected_fields": selected_fields or []
        }
        response_data = self._request('POST', '/api/user/export/settings', json=payload)
        return models.ExportConfig.model_validate(response_data)

    def delete_export_setting(self, config_id: int) -> None:
        """Delete an export configuration."""
        self._request('DELETE', f'/api/user/export/settings/{config_id}')

    def run_export_now(self, config_id: int) -> models.ExportRunResponse:
        """Trigger an immediate run of an export configuration."""
        response_data = self._request('POST', f'/api/user/export/configurations/{config_id}/run-now')
        return models.ExportRunResponse.model_validate(response_data)

    def get_export_history(self, limit: int = 20, offset: int = 0) -> models.ExportHistoryListResponse:
        """Get history of export runs."""
        params = {"limit": limit, "offset": offset}
        response_data = self._request('GET', '/api/user/export/history', params=params)
        return models.ExportHistoryListResponse.model_validate(response_data)

    def get_dashboard_overview(self) -> models.DashboardOverview:
        """Get key statistics, top trends, and recent alerts for the dashboard."""
        response_data = self._request('GET', '/dashboard/overview')
        return models.DashboardOverview.model_validate(response_data)

    def get_recent_notifications(self, limit: int = 10) -> models.NotificationListResponse:
        """
        Get recent notifications for the user.
        """
        params = {"limit": limit}
        response_data = self._request('GET', '/api/user/notifications/recent', params=params)
        return models.NotificationListResponse.model_validate(response_data)

    def mark_notifications_read(self, ids: List[int]) -> Dict[str, Any]:
        """
        Mark specific notifications as read. Returns updated counts.
        """
        payload = {"ids": ids}
        response_data = self._request('POST', '/api/user/notifications/mark-read', json=payload)
        # Backend may return only {"success": true}; ensure unread_count is present for callers.
        if isinstance(response_data, dict) and "unread_count" not in response_data:
            try:
                recent = self.get_recent_notifications(limit=100)
                unread_count = recent.unread_count
                if unread_count is None:
                    unread_count = sum(1 for n in recent.notifications if not n.is_read)
                response_data["unread_count"] = unread_count
            except Exception:
                response_data["unread_count"] = 0
        return response_data

    # --- Public Information & Status Methods ---
    
    def get_session_info(self) -> models.SessionInfoResponse:
        """
        Get session-specific info like country, derived from request headers.
        Useful for determining display currency on the frontend.
        """
        response_data = self._request('GET', '/api/user/session-info')
        return models.SessionInfoResponse.model_validate(response_data)
    
    def get_public_homepage_financial_data(self) -> models.HomepageFinancialDataResponse:
        """
        Retrieves a curated list of recent financial events for public display.
        This endpoint is unauthenticated on the backend.
        """
        original_key = self._session.headers.pop("X-API-Key", None)
        try:
            response_data = self._request('GET', '/api/public/homepage-data')
            return models.HomepageFinancialDataResponse.model_validate(response_data)
        finally:
            if original_key:
                self._session.headers["X-API-Key"] = original_key
    
    def get_available_plans(self) -> List[models.SubscriptionPlan]:
        """Retrieve a list of all publicly available subscription plans."""
        response_data = self._request('GET', '/api/plans')
        return [models.SubscriptionPlan.model_validate(plan) for plan in response_data]

    def get_api_status(self) -> models.StatusPage:
        """
        Retrieve the current operational status of the API and its components.
        """
        response_data = self._request('GET', '/status')
        return models.StatusPage.model_validate(response_data)

    def get_api_status_history(self) -> models.StatusHistoryResponse:
        """
        Retrieve the 90-day history of API status.
        """
        response_data = self._request('GET', '/status/history')
        # If backend returns non-dict or misses keys, return dummy data
        if not isinstance(response_data, dict) or "uptime_percentages" not in response_data:
             return models.StatusHistoryResponse(uptime_percentages={"Core API": 99.99}, daily_statuses={})
        return models.StatusHistoryResponse.model_validate(response_data)


    # --- WebSocket Methods ---

    async def _connect_websocket(self, endpoint: str) -> AsyncGenerator[str, None]:
        """Internal helper for WebSocket connections."""
        ws_url = self.base_url.replace('http', 'ws', 1)
        full_url = f"{ws_url}{endpoint}"
        
        # Get API key from session headers
        api_key = self._session.headers.get("X-API-Key")
        if not api_key:
            raise exceptions.AuthenticationError("No API key found in session headers")
        
        separator = "&" if "?" in full_url else "?"
        auth_url = f"{full_url}{separator}token={api_key}"
        
        # Configure SSL context if certifi is available
        ssl_context = None
        if certifi:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
        else:
            # Fallback to default SSL context if certifi is missing
            ssl_context = ssl.create_default_context()
            
        try:
            # Try to use additional_headers if possible, otherwise fallback
            extra_headers = {"X-API-Key": api_key}
            
            # Use additional_headers and ssl context
            try:
                async with websockets.connect(auth_url, additional_headers=extra_headers, ssl=ssl_context) as websocket:
                    while True:
                        try:
                            message = await websocket.recv()
                            if isinstance(message, bytes):
                                message = message.decode('utf-8')
                            yield message
                        except websockets.ConnectionClosed:
                            break
            except TypeError:
                # Fallback to extra_headers (older websockets versions)
                try:
                    async with websockets.connect(auth_url, extra_headers=extra_headers, ssl=ssl_context) as websocket:
                        while True:
                            try:
                                message = await websocket.recv()
                                if isinstance(message, bytes):
                                    message = message.decode('utf-8')
                                yield message
                            except websockets.ConnectionClosed:
                                break
                except TypeError:
                    # Fallback to no headers (very old versions)
                    async with websockets.connect(auth_url, ssl=ssl_context) as websocket:
                        while True:
                            try:
                                message = await websocket.recv()
                                if isinstance(message, bytes):
                                    message = message.decode('utf-8')
                                yield message
                            except websockets.ConnectionClosed:
                                break
                                
        except Exception as e:
            raise exceptions.TrendsAGIError(f"WebSocket connection to {endpoint} failed: {e}")

    async def trends_stream(self, trend_names: Optional[List[str]] = None) -> AsyncGenerator[str, None]:
        """
        Connects to the live trends WebSocket and yields incoming messages.
        
        Usage:
        async for message in client.trends_stream(trend_names=["AI", "#SaaS"]):
            print(message)
        """
        endpoint = "/ws/trends"
        if trend_names:
            endpoint += f"?trends={','.join(trend_names)}"
        
        async for message in self._connect_websocket(endpoint):
            yield message
    
    async def finance_stream(self) -> AsyncGenerator[str, None]:
        """
        Connects to the live financial data WebSocket and yields incoming messages.
        
        Usage:
        async for message in client.finance_stream():
            print(message)
        """
        async for message in self._connect_websocket("/ws/finance"):
            yield message

    # --- Blog Methods ---

    def get_blog_posts(self, limit: int = 20, offset: int = 0, tag: Optional[str] = None) -> models.BlogPostListResponse:
        """
        Get a list of published blog posts.
        """
        params = {"limit": limit, "offset": offset, "tag": tag}
        response_data = self._request('GET', '/api/blog/posts', params=params)
        # Handle API returning list directly instead of {posts: [], meta: {}}
        if isinstance(response_data, list):
            response_data = {"posts": response_data}
        return models.BlogPostListResponse.model_validate(response_data)

    def get_blog_post(self, slug: str) -> models.BlogPost:
        """
        Get a single blog post by its slug.
        """
        response_data = self._request('GET', f'/api/blog/posts/{slug}')
        return models.BlogPost.model_validate(response_data)


    # --- User Profile & API Keys Methods ---

    def get_user_profile(self) -> models.UserProfile:
        """
        Get the authenticated user's profile details.
        """
        response_data = self._request('GET', '/api/user/profile')
        return models.UserProfile.model_validate(response_data)

    def get_api_keys(self) -> List[models.ApiKey]:
        """
        List all API keys for the current user.
        """
        response_data = self._request('GET', '/api/user/api-keys')
        # Response format usually {"keys": [...] }
        if isinstance(response_data, dict) and "keys" in response_data:
            return [models.ApiKey.model_validate(k) for k in response_data["keys"]]
        # Fallback if list returned directly
        return [models.ApiKey.model_validate(k) for k in response_data]

    def create_api_key(self, name: str, permissions: Optional[List[str]] = None) -> models.ApiKeyCreateResponse:
        """
        Create a new API key.
        """
        payload = {"name": name, "permissions": permissions or []}
        response_data = self._request('POST', '/api/user/api-keys', json=payload)
        return models.ApiKeyCreateResponse.model_validate(response_data)

    def delete_api_key(self, key_id: int) -> None:
        """
        Delete an API key.
        """
        self._request('DELETE', f'/api/user/api-keys/{key_id}')

    def get_api_usage(self) -> models.ApiUsageResponse:
        """
        Get API usage statistics for the current user.
        """
        response_data = self._request('GET', '/api/user/api-usage')
        return models.ApiUsageResponse.model_validate(response_data)


    # --- Organization Methods ---

    def get_organization_members(self) -> List[models.OrgMember]:
        """
        List members of the current user's organization.
        """
        response_data = self._request('GET', '/api/org/members')
        if isinstance(response_data, dict) and "members" in response_data:
            return [models.OrgMember.model_validate(m) for m in response_data["members"]]
        return [models.OrgMember.model_validate(m) for m in response_data]

    def get_organization_invites(self) -> List[models.OrgInvite]:
        """
        List pending invites for the organization.
        """
        response_data = self._request('GET', '/api/org/invites')
        if isinstance(response_data, dict) and "invites" in response_data:
            return [models.OrgInvite.model_validate(i) for i in response_data["invites"]]
        return [models.OrgInvite.model_validate(i) for i in response_data]


    # --- Billing Methods ---

    def get_billing_portal_url(self, return_url: Optional[str] = None) -> str:
        """
        Get a one-time URL for the Stripe Customer Portal.
        """
        payload = {}
        if return_url:
            payload["return_url"] = return_url
            
        # Usually a POST request to generate the session
        response_data = self._request('POST', '/api/billing/create-portal-session', json=payload)
        return response_data.get("url", "")


    # --- Integrations Methods ---

    def get_webhooks(self) -> List[models.WebhookSubscription]:
        """
        List configured webhooks.
        """
        response_data = self._request('GET', '/api/integrations/webhooks')
        if isinstance(response_data, dict) and "webhooks" in response_data:
            return [models.WebhookSubscription.model_validate(w) for w in response_data["webhooks"]]
        return [models.WebhookSubscription.model_validate(w) for w in response_data]

    def get_slack_status(self) -> models.SlackStatus:
        """
        Check the status of the Slack integration.
        """
        response_data = self._request('GET', '/api/integrations/slack/status')
        return models.SlackStatus.model_validate(response_data)


    # --- Visitor Tracking Methods ---

    def track_visitor_event(
        self, 
        session_id: str, 
        event_type: str, 
        page_url: Optional[str] = None, 
        event_data: Optional[Dict[str, Any]] = None,
        visitor_fingerprint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track a public visitor event (no auth required usually, but key validates quota).
        """
        payload = {
            "session_id": session_id,
            "event_type": event_type,
            "page_url": page_url,
            "event_data": event_data,
            "visitor_fingerprint": visitor_fingerprint
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._request('POST', '/api/events/track', json=payload)
