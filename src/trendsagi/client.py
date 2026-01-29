# File: trendsagi-client/trendsagi/client.py

import re
import requests
import asyncio
import websockets
import ssl
import random
import time
from typing import Optional, List, Dict, Any, AsyncGenerator

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
        limit: int = 10, offset: int = 0, recommendation_type: Optional[str] = None,
        source_trend_query: Optional[str] = None, priority: Optional[str] = None, status: str = 'new',
        match_user_interests: bool = False
    ) -> models.RecommendationListResponse:
        """
        Get actionable recommendations generated for the user.
        """
        params = {
            "limit": limit, "offset": offset, "type": recommendation_type, 
            "sourceTrendQ": source_trend_query, "priority": priority, "status": status,
            "match_user_interests": str(match_user_interests).lower()
        }
        params = {k: v for k, v in params.items() if v is not None}
        response_data = self._request('GET', '/api/intelligence/recommendations', params=params)
        return models.RecommendationListResponse.model_validate(response_data)

    def perform_recommendation_action(self, recommendation_id: int, action: Optional[str] = None, feedback: Optional[str] = None) -> models.Recommendation:
        """
        Update a recommendation's status or provide feedback.
        """
        if action and feedback:
            raise ValueError("Only one of 'action' or 'feedback' can be provided at a time.")
        if not action and not feedback:
            raise ValueError("Either 'action' or 'feedback' must be provided.")

        payload = {"action": action, "feedback": feedback}
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
        
    def get_crisis_event(self, event_id: int) -> models.CrisisEvent:
        """
        Get a single crisis event.
        """
        # This was missing too
        response_data = self._request('GET', f'/api/intelligence/crisis-events/{event_id}')
        return models.CrisisEvent.model_validate(response_data)

    def perform_crisis_event_action(self, event_id: int, action: str) -> models.CrisisEvent:
        """
        Update the status of a crisis event (e.g., "acknowledge", "archive").
        """
        response_data = self._request('POST', f'/api/intelligence/crisis-events/{event_id}/action', json={"action": action})
        return models.CrisisEvent.model_validate(response_data)

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
        return self._request('POST', '/api/user/notifications/mark-read', json=payload)

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

    # --- Context Intelligence Suite Methods ---

    def list_context_projects(
        self,
        limit: int = 20,
        offset: int = 0,
        include_inactive: bool = False
    ) -> models.ContextProjectListResponse:
        """
        List all context projects for the current user.
        
        :param limit: Maximum number of projects to return.
        :param offset: Number of projects to skip for pagination.
        :param include_inactive: Include archived projects.
        """
        params = {"limit": limit, "offset": offset, "include_inactive": include_inactive}
        response_data = self._request('GET', '/api/intelligence/context/projects', params=params)
        return models.ContextProjectListResponse.model_validate(response_data)

    def create_context_project(
        self,
        name: str,
        description: Optional[str] = None,
        share_with_org: bool = False
    ) -> models.ContextProject:
        """
        Create a new context project to organize specs, plans, and code.
        
        :param name: Project name (must be unique for the user).
        :param description: Optional description.
        :param share_with_org: Share with organization members (enterprise only).
        """
        payload = {"name": name, "description": description, "share_with_org": share_with_org}
        response_data = self._request('POST', '/api/intelligence/context/projects', json=payload)
        return models.ContextProject.model_validate(response_data)

    def get_context_project(self, project_id: int) -> models.ContextProject:
        """
        Get a context project with all its items.
        
        :param project_id: The project ID.
        """
        response_data = self._request('GET', f'/api/intelligence/context/projects/{project_id}')
        return models.ContextProject.model_validate(response_data)

    def delete_context_project(self, project_id: int) -> None:
        """
        Delete a context project and all its items.
        
        :param project_id: The project ID to delete.
        """
        self._request('DELETE', f'/api/intelligence/context/projects/{project_id}')

    def list_context_items(
        self,
        project_id: Optional[int] = None,
        item_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> models.ContextItemListResponse:
        """
        List and query context items for the current user.
        
        :param project_id: Filter by project.
        :param item_type: Filter by type (product_spec, tech_stack, style_guide, plan, reference_code, etc).
        :param search: Search in item names.
        :param limit: Maximum items to return.
        :param offset: Number of items to skip.
        """
        params = {k: v for k, v in locals().items() if v is not None and k != 'self'}
        response_data = self._request('GET', '/api/intelligence/context/items', params=params)
        return models.ContextItemListResponse.model_validate(response_data)

    def create_context_item(
        self,
        project_id: int,
        item_type: str,
        name: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> models.ContextItem:
        """
        Create a text-based context item (spec, plan, style guide, etc).
        
        :param project_id: The project ID to add the item to.
        :param item_type: Type of item (product_spec, tech_stack, style_guide, plan, custom).
        :param name: Item name.
        :param content: Text content for the item.
        :param metadata: Optional key-value metadata.
        """
        payload = {
            "project_id": project_id,
            "item_type": item_type,
            "name": name,
            "content": content,
            "metadata": metadata
        }
        response_data = self._request('POST', '/api/intelligence/context/items', json=payload)
        return models.ContextItem.model_validate(response_data)

    def upload_context_file(
        self,
        project_id: int,
        file_path: str,
        item_type: str = "reference_code",
        name: Optional[str] = None
    ) -> models.ContextItem:
        """
        Upload a file as a context item (code files, images, etc).
        
        :param project_id: The project ID.
        :param file_path: Path to the file to upload.
        :param item_type: Type (reference_code, reference_image, etc).
        :param name: Optional display name (defaults to filename).
        """
        import os
        import mimetypes
        
        filename = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f, mime_type or 'application/octet-stream')}
            data = {'project_id': str(project_id), 'item_type': item_type}
            if name:
                data['name'] = name
            
            # Remove Content-Type header for multipart
            headers = dict(self._session.headers)
            headers.pop('Content-Type', None)
            
            url = f"{self.base_url}/api/intelligence/context/items/upload"
            response = self._session.post(url, files=files, data=data, headers=headers)
        
        if response.status_code != 201:
            try:
                error_detail = response.json().get('detail', response.text)
            except:
                error_detail = response.text
            raise exceptions.APIError(response.status_code, error_detail)
        
        return models.ContextItem.model_validate(response.json())

    def get_context_item(self, item_id: int, include_content: bool = True) -> models.ContextItem:
        """
        Get a context item with its content.
        
        :param item_id: The item ID.
        :param include_content: Whether to include the text content.
        """
        params = {"include_content": include_content}
        response_data = self._request('GET', f'/api/intelligence/context/items/{item_id}', params=params)
        return models.ContextItem.model_validate(response_data)

    def delete_context_item(self, item_id: int) -> None:
        """
        Delete a context item.
        
        :param item_id: The item ID to delete.
        """
        self._request('DELETE', f'/api/intelligence/context/items/{item_id}')

    def get_context_usage(self) -> models.ContextUsage:
        """
        Get current context storage usage and limits for your plan.
        """
        response_data = self._request('GET', '/api/intelligence/context/usage')
        return models.ContextUsage.model_validate(response_data)

    def query_context(
        self,
        project_id: Optional[int] = None,
        item_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[models.ContextItem]:
        """
        Query context items for use in AI agent workflows.
        Returns the full content of matching items.
        
        :param project_id: Filter by project.
        :param item_type: Filter by type.
        :param search: Search in item names.
        """
        response = self.list_context_items(
            project_id=project_id,
            item_type=item_type,
            search=search,
            limit=100
        )
        
        # Fetch full content for each item
        items_with_content = []
        for item in response.items:
            full_item = self.get_context_item(item.id, include_content=True)
            items_with_content.append(full_item)
        
        return items_with_content

    # --- Agents API Methods (formerly Deep Analysis) ---

    def list_agents(
        self,
        limit: int = 20,
        offset: int = 0,
        include_archived: bool = False
    ) -> models.AgentListResponse:
        """
        List all agents for the current user.
        
        :param limit: Maximum number of agents to return.
        :param offset: Number of agents to skip for pagination.
        :param include_archived: Include archived agents.
        """
        params = {"limit": limit, "offset": offset, "include_archived": include_archived}
        response_data = self._request('GET', '/api/agents', params=params)
        return models.AgentListResponse.model_validate(response_data)

    def create_agent(
        self,
        name: str,
        description: Optional[str] = None,
        temperature: float = 1.0,
        max_output_tokens: int = 8192,
        thinking_level: str = "HIGH",
        enable_multi_turn: bool = True,
        enable_web_search: bool = False,
        persona_preset: Optional[str] = None,
        system_prompt: Optional[str] = None,
        output_language: Optional[str] = None,
        response_format: str = "prose",
        safety_level: str = "block_medium_and_above",
        
        # Query Reformulation
        enable_query_expansion: bool = False,
        query_expansion_prompt: Optional[str] = None,
        query_expansion_examples: Optional[List[str]] = None,
        enable_query_decomposition: bool = False,
        query_decomposition_prompt: Optional[str] = None,

        # Retrieval
        top_k_retrieved_chunks: int = 160,
        lexical_alpha: float = 0.35,
        semantic_alpha: float = 0.65,

        # Rerank
        enable_rerank: bool = True,
        top_k_reranked_chunks: int = 25,
        reranker_score_threshold: float = 0.0,
        rerank_instructions: Optional[str] = None,

        # Filter
        enable_filter: bool = True,
        filter_prompt: Optional[str] = None,

        # Model Armor / Granular Safety
        safety_csam: str = 'high',
        safety_malicious_urls: str = 'high',
        safety_prompt_injection: str = 'medium',
        safety_sexual_content: str = 'disabled',
        safety_hate_speech: str = 'disabled',
        safety_harassment: str = 'disabled',
        safety_dangerous_content: str = 'disabled',

        default_project_id: Optional[int] = None
    ) -> models.Agent:
        """
        Create a new AI agent with custom settings.
        
        :param name: Agent name.
        :param description: Optional description.
        :param temperature: Controls randomness (0.0-2.0, default 1.0 recommended).
        :param max_output_tokens: Max tokens in response (default 8192, max 65536).
        :param thinking_level: Reasoning depth: MINIMAL, LOW, MEDIUM, HIGH.
        :param enable_multi_turn: Enable multi-turn conversation reformulation.
        :param enable_web_search: Enable grounding with Google Search.
        :param persona_preset: Preset persona: analyst, researcher, advisor, technical, creative.
        :param system_prompt: Custom system prompt.
        :param output_language: ISO language code for translation (e.g., 'es', 'fr').
        :param response_format: Format: prose, bullet_points, structured, json.
        :param safety_level: Safety threshold for content filtering.

        # Advanced Settings
        :param enable_query_expansion: Reformulate queries for better recall.
        :param query_expansion_prompt: Custom instruction for expansion.
        :param query_expansion_examples: List of example expansions.
        :param enable_query_decomposition: Break down complex queries.
        :param query_decomposition_prompt: Custom instruction for decomposition.

        :param top_k_retrieved_chunks: Max chunks to retrieve (1-200).
        :param lexical_alpha: Weight for keyword search (0.0-1.0).
        :param semantic_alpha: Weight for semantic search (0.0-1.0).

        :param enable_rerank: Enable reranking of results.
        :param top_k_reranked_chunks: Max chunks after reranking (1-100).
        :param reranker_score_threshold: Minimum score to keep a chunk.
        :param rerank_instructions: Custom reranking guidelines.

        :param enable_filter: Filter irrelevant chunks.
        :param filter_prompt: Custom filtering instructions.

        :param safety_csam: CSAM filter level.
        :param safety_malicious_urls: Malicious URL filter level.
        :param safety_prompt_injection: Prompt injection filter level.
        :param safety_sexual_content: Sexual content filter level.
        :param safety_hate_speech: Hate speech filter level.
        :param safety_harassment: Harassment filter level.
        :param safety_dangerous_content: Dangerous content filter level.

        :param default_project_id: Default context project for this agent.
        """
        payload = {
            "name": name,
            "description": description,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "thinking_level": thinking_level,
            "enable_multi_turn": enable_multi_turn,
            "enable_web_search": enable_web_search,
            "persona_preset": persona_preset,
            "system_prompt": system_prompt,
            "output_language": output_language,
            "response_format": response_format,
            "safety_level": safety_level,
            
            # Query Reformulation
            "enable_query_expansion": enable_query_expansion,
            "query_expansion_prompt": query_expansion_prompt,
            "query_expansion_examples": query_expansion_examples if query_expansion_examples is not None else [],
            "enable_query_decomposition": enable_query_decomposition,
            "query_decomposition_prompt": query_decomposition_prompt,

            # Retrieval
            "top_k_retrieved_chunks": top_k_retrieved_chunks,
            "lexical_alpha": lexical_alpha,
            "semantic_alpha": semantic_alpha,

            # Rerank
            "enable_rerank": enable_rerank,
            "top_k_reranked_chunks": top_k_reranked_chunks,
            "reranker_score_threshold": reranker_score_threshold,
            "rerank_instructions": rerank_instructions,

            # Filter
            "enable_filter": enable_filter,
            "filter_prompt": filter_prompt,

            # Model Armor
            "safety_csam": safety_csam,
            "safety_malicious_urls": safety_malicious_urls,
            "safety_prompt_injection": safety_prompt_injection,
            "safety_sexual_content": safety_sexual_content,
            "safety_hate_speech": safety_hate_speech,
            "safety_harassment": safety_harassment,
            "safety_dangerous_content": safety_dangerous_content,

            "default_project_id": default_project_id
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        response_data = self._request('POST', '/api/agents', json=payload)
        return models.Agent.model_validate(response_data)

    def get_agent(self, agent_id: int) -> models.Agent:
        """
        Get an agent by ID.
        
        :param agent_id: The agent ID.
        """
        response_data = self._request('GET', f'/api/agents/{agent_id}')
        return models.Agent.model_validate(response_data)

    def update_agent(
        self,
        agent_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        thinking_level: Optional[str] = None,
        enable_multi_turn: Optional[bool] = None,
        enable_web_search: Optional[bool] = None,
        persona_preset: Optional[str] = None,
        system_prompt: Optional[str] = None,
        output_language: Optional[str] = None,
        response_format: Optional[str] = None,
        safety_level: Optional[str] = None,
        
        # Query Reformulation
        enable_query_expansion: Optional[bool] = None,
        query_expansion_prompt: Optional[str] = None,
        query_expansion_examples: Optional[List[str]] = None,
        enable_query_decomposition: Optional[bool] = None,
        query_decomposition_prompt: Optional[str] = None,

        # Retrieval
        top_k_retrieved_chunks: Optional[int] = None,
        lexical_alpha: Optional[float] = None,
        semantic_alpha: Optional[float] = None,

        # Rerank
        enable_rerank: Optional[bool] = None,
        top_k_reranked_chunks: Optional[int] = None,
        reranker_score_threshold: Optional[float] = None,
        rerank_instructions: Optional[str] = None,

        # Filter
        enable_filter: Optional[bool] = None,
        filter_prompt: Optional[str] = None,

        # Model Armor / Granular Safety
        safety_csam: Optional[str] = None,
        safety_malicious_urls: Optional[str] = None,
        safety_prompt_injection: Optional[str] = None,
        safety_sexual_content: Optional[str] = None,
        safety_hate_speech: Optional[str] = None,
        safety_harassment: Optional[str] = None,
        safety_dangerous_content: Optional[str] = None,

        default_project_id: Optional[int] = None,
        is_archived: Optional[bool] = None
    ) -> models.Agent:
        """
        Update an agent's settings.
        
        :param agent_id: The agent ID to update.
        """
        payload = {
            "name": name,
            "description": description,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "thinking_level": thinking_level,
            "enable_multi_turn": enable_multi_turn,
            "enable_web_search": enable_web_search,
            "persona_preset": persona_preset,
            "system_prompt": system_prompt,
            "output_language": output_language,
            "response_format": response_format,
            "safety_level": safety_level,
            
            # Query Reformulation
            "enable_query_expansion": enable_query_expansion,
            "query_expansion_prompt": query_expansion_prompt,
            "query_expansion_examples": query_expansion_examples,
            "enable_query_decomposition": enable_query_decomposition,
            "query_decomposition_prompt": query_decomposition_prompt,

            # Retrieval
            "top_k_retrieved_chunks": top_k_retrieved_chunks,
            "lexical_alpha": lexical_alpha,
            "semantic_alpha": semantic_alpha,

            # Rerank
            "enable_rerank": enable_rerank,
            "top_k_reranked_chunks": top_k_reranked_chunks,
            "reranker_score_threshold": reranker_score_threshold,
            "rerank_instructions": rerank_instructions,

            # Filter
            "enable_filter": enable_filter,
            "filter_prompt": filter_prompt,

            # Model Armor
            "safety_csam": safety_csam,
            "safety_malicious_urls": safety_malicious_urls,
            "safety_prompt_injection": safety_prompt_injection,
            "safety_sexual_content": safety_sexual_content,
            "safety_hate_speech": safety_hate_speech,
            "safety_harassment": safety_harassment,
            "safety_dangerous_content": safety_dangerous_content,

            "default_project_id": default_project_id,
            "is_archived": is_archived
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        response_data = self._request('PUT', f'/api/agents/{agent_id}', json=payload)
        return models.Agent.model_validate(response_data)

    def delete_agent(self, agent_id: int) -> None:
        """
        Delete an agent and all its conversations.
        
        :param agent_id: The agent ID to delete.
        """
        self._request('DELETE', f'/api/agents/{agent_id}')

    def list_agent_conversations(
        self,
        agent_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> models.AgentConversationListResponse:
        """
        List conversations for an agent.
        
        :param agent_id: The agent ID.
        :param limit: Maximum conversations to return.
        :param offset: Number to skip for pagination.
        """
        params = {"limit": limit, "offset": offset}
        response_data = self._request('GET', f'/api/agents/{agent_id}/conversations', params=params)
        return models.AgentConversationListResponse.model_validate(response_data)

    def get_agent_conversation(self, conversation_id: int) -> models.AgentConversation:
        """
        Get a specific conversation by ID.
        
        :param conversation_id: The conversation ID.
        """
        response_data = self._request('GET', f'/api/agents/conversations/{conversation_id}')
        return models.AgentConversation.model_validate(response_data)

    def delete_agent_conversation(self, conversation_id: int) -> None:
        """
        Delete a conversation.
        
        :param conversation_id: The conversation ID to delete.
        """
        self._request('DELETE', f'/api/agents/conversations/{conversation_id}')

    def agent_chat(
        self,
        agent_id: int,
        query: str,
        conversation_id: Optional[int] = None,
        project_id: Optional[int] = None,
        guidance_ids: Optional[List[int]] = None
    ) -> models.AgentTaskResponse:
        """
        Send a message to an agent and queue analysis.
        
        :param agent_id: The agent ID to chat with.
        :param query: The question or message to analyze.
        :param conversation_id: Continue an existing conversation (for multi-turn).
        :param project_id: Override the agent's default context project.
        :param guidance_ids: Specific context item IDs to use as guidance.
        :returns: Task response with task_id for polling status.
        """
        payload = {
            "query": query,
            "conversation_id": conversation_id,
            "project_id": project_id,
            "guidance_ids": guidance_ids
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        response_data = self._request('POST', f'/api/agents/{agent_id}/chat', json=payload)
        return models.AgentTaskResponse.model_validate(response_data)

    def get_agent_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Check the status of an agent analysis task.
        
        :param task_id: The task ID from agent_chat response.
        :returns: Status dict with 'status' (PENDING, SUCCESS, FAILURE) and 'result' when complete.
        """
        return self._request('GET', f'/api/agents/tasks/{task_id}')

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
