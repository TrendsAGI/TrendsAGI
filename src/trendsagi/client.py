# File: trendsagi-client/trendsagi/client.py

import re
import requests
import asyncio
import websockets
from typing import Optional, List, Dict, Any, AsyncGenerator

from . import models
from . import exceptions


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
    def __init__(self, api_key: str, base_url: str = "https://api.trendsagi.com"):
        if not api_key:
            raise exceptions.AuthenticationError("API key is required.")
        
        self.base_url = base_url.rstrip('/')
        self._session = requests.Session()
        self._session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Internal helper for making API requests."""
        url = f"{self.base_url}{endpoint}"
        try:
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
                raise exceptions.RateLimitError(response.status_code, error_detail)
            
            raise exceptions.APIError(response.status_code, error_detail)

        except requests.exceptions.RequestException as e:
            raise exceptions.TrendsAGIError(f"Network error communicating with API: {e}")

    # --- Trends & Insights Methods ---

    def get_trends(
        self,
        search: Optional[str] = None,
        sort_by: str = 'volume',
        order: str = 'desc',
        limit: int = 20,
        offset: int = 0,
        period: str = '24h',
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> models.TrendListResponse:
        """
        Retrieve a list of currently trending topics.
        """
        params = {k: v for k, v in locals().items() if v is not None and k != 'self'}
        response_data = self._request('GET', '/api/trends', params=params)
        return models.TrendListResponse.model_validate(response_data)

    def get_trend_analytics(self, trend_id: int, period: str = '7d', start_date: Optional[str] = None, end_date: Optional[str] = None) -> models.TrendAnalytics:
        """
        Retrieve historical data points for a specific trend.
        """
        params = {"period": period, "startDate": start_date, "endDate": end_date}
        params = {k: v for k, v in params.items() if v is not None}
        response_data = self._request('GET', f'/api/trends/{trend_id}/analytics', params=params)
        return models.TrendAnalytics.model_validate(response_data)

    def get_trend_autocomplete(self, query: str) -> models.AutocompleteResponse:
        """
        Get trend name suggestions for typeahead search.
        """
        response_data = self._request('GET', '/api/trends/autocomplete', params={"query": query})
        return models.AutocompleteResponse.model_validate(response_data)

    def get_trend_categories(self) -> models.ActiveCategoriesResponse:
        """
        Get a list of all categories that have at least one associated trend.
        """
        response_data = self._request('GET', '/api/trends/categories')
        return models.ActiveCategoriesResponse.model_validate(response_data)

    def search_insights(
        self,
        key_theme_contains: Optional[str] = None,
        audience_keyword: Optional[str] = None,
        angle_contains: Optional[str] = None,
        sentiment_category: Optional[str] = None,
        overall_topic_category_llm: Optional[str] = None,
        trend_name_contains: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = 'timestamp',
        order: str = 'desc'
    ) -> models.InsightSearchResponse:
        """
        Search for trends based on the content of their AI-generated insights.
        """
        params = {
            "keyThemeContains": key_theme_contains, "audienceKeyword": audience_keyword,
            "angleContains": angle_contains, "sentimentCategory": sentiment_category,
            "overallTopicCategoryLlm": overall_topic_category_llm, "trendNameContains": trend_name_contains,
            "limit": limit, "offset": offset, "sort_by": sort_by, "order": order
        }
        params = {k: v for k, v in params.items() if v is not None}
        response_data = self._request('GET', '/api/insights/search', params=params)
        return models.InsightSearchResponse.model_validate(response_data)
        
    def get_ai_insights(self, trend_id: int) -> Optional[models.AIInsight]:
        """
        Get cached AI-powered insights for a specific trend.
        
        Note: This method only retrieves existing, cached insights. New insights 
        must be generated via the TrendsAGI web dashboard.
        
        Returns None if no insight is available for the given trend.
        """
        response_data = self._request('GET', f'/api/trends/{trend_id}/ai-insights')
        return models.AIInsight.model_validate(response_data) if response_data else None

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
        source_trend_query: Optional[str] = None, priority: Optional[str] = None, status: str = 'new'
    ) -> models.RecommendationListResponse:
        """
        Get actionable recommendations generated for the user.
        """
        params = {
            "limit": limit, "offset": offset, "type": recommendation_type, 
            "sourceTrendQ": source_trend_query, "priority": priority, "status": status
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
        Retrieve a single crisis event by its unique ID.
        """
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
        response_data = self._request('GET', '/api/user/topic-interests')
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
        response_data = self._request('POST', '/api/user/topic-interests', json=payload)
        return models.TopicInterest.model_validate(response_data)
        
    def delete_topic_interest(self, interest_id: int) -> None:
        """Delete a specific topic interest."""
        self._request('DELETE', f'/api/user/topic-interests/{interest_id}')

    def get_export_settings(self) -> List[models.ExportConfiguration]:
        """Get all of the user's data export configurations."""
        response_data = self._request('GET', '/api/user/export/settings')
        return [models.ExportConfiguration.model_validate(item) for item in response_data]

    def save_export_settings(
        self,
        destination: str,
        selected_fields: List[str],
        config: Dict[str, Any],
        schedule: str = "none",
        schedule_time: Optional[str] = None,
        is_active: bool = False,
        config_id: Optional[int] = None
    ) -> models.ExportConfiguration:
        """
        Create or update an export configuration.
        """
        payload = {
            "id": config_id, "destination": destination, "config": config,
            "schedule": schedule, "schedule_time": schedule_time, "is_active": is_active,
            "selected_fields": selected_fields
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        response_data = self._request('POST', '/api/user/export/settings', json=payload)
        return models.ExportConfiguration.model_validate(response_data)

    def delete_export_setting(self, config_id: int) -> None:
        """Delete an export configuration."""
        self._request('DELETE', f'/api/user/export/settings/{config_id}')

    def get_export_history(self, limit: int = 15, offset: int = 0) -> models.ExportHistoryResponse:
        """Get the user's export execution history."""
        response_data = self._request('GET', '/api/user/export/history', params={"limit": limit, "offset": offset})
        return models.ExportHistoryResponse.model_validate(response_data)

    def run_export_now(self, config_id: int) -> models.ExportExecutionLog:
        """Trigger an immediate export."""
        response_data = self._request('POST', f'/api/user/export/configurations/{config_id}/run-now')
        return models.ExportExecutionLog.model_validate(response_data)
        
    def get_dashboard_overview(self) -> models.DashboardOverview:
        """Get key statistics, top trends, and recent alerts for the dashboard."""
        response_data = self._request('GET', '/api/dashboard/overview')
        return models.DashboardOverview.model_validate(response_data)

    def get_recent_notifications(self, limit: int = 10) -> models.NotificationListResponse:
        """Get recent notifications for the user."""
        response_data = self._request('GET', '/api/user/notifications/recent', params={"limit": limit})
        return models.NotificationListResponse.model_validate(response_data)

    def mark_notifications_read(self, ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """Mark notifications as read. If ids is None, marks all as read."""
        payload = {"ids": ids if ids is not None else []}
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
            response_data = self._request('GET', '/api/v1/public/homepage-financial-data')
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
        response_data = self._request('GET', '/api/status')
        return models.StatusPage.model_validate(response_data)
        
    def get_api_status_history(self) -> models.StatusHistoryResponse:
        """
        Retrieve the 90-day uptime history for all API components.
        """
        response_data = self._request('GET', '/api/status-history')
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
        
        try:
            async with websockets.connect(auth_url) as websocket:
                while True:
                    try:
                        message = await websocket.recv()
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
        endpoint = "/ws/trends-live"
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
        async for message in self._connect_websocket("/ws/finance-live"):
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