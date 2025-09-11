# File: trendsagi-client/trendsagi/client.py

import requests
import asyncio
import websockets
from typing import Optional, List, Dict, Any, AsyncGenerator

from . import models
from . import exceptions

class TrendsAGIClient:
    """
    The main client for interacting with the TrendsAGI API.
    
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
                error_detail = response.text
                
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
        
    def get_trend_details(self, trend_id: int) -> models.TrendDetail:
        """
        Retrieve detailed information for a single trend, including associated tweets.
        """
        response_data = self._request('GET', f'/api/trends/{trend_id}')
        return models.TrendDetail.model_validate(response_data)

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
        Returns None if no insight is available.
        """
        response_data = self._request('GET', f'/api/trends/{trend_id}/ai-insights')
        return models.AIInsight.model_validate(response_data) if response_data else None

    def generate_ai_insights(self, trend_id: int) -> models.InsightTaskResponse:
        """
        Queue a job to generate new AI-powered insights for a trend.
        Returns a task response object containing the task_id to poll.
        """
        response_data = self._request('POST', f'/api/trends/{trend_id}/ai-insights/generate')
        return models.InsightTaskResponse.model_validate(response_data)

    def get_insight_generation_status(self, task_id: str) -> models.InsightTaskStatusResponse:
        """
        Check the status of an AI insight generation task.
        """
        response_data = self._request('GET', f'/api/trends/ai-insights/status/{task_id}')
        return models.InsightTaskStatusResponse.model_validate(response_data)

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

    def get_tracked_x_users(self, q: Optional[str] = None, min_followers: Optional[int] = None, sort_by: str = 'name_asc') -> models.MarketEntityListResponse:
        """
        Get a list of tracked X Users.
        """
        params = {"q": q, "min_followers": min_followers, "sort_by": sort_by}
        params = {k: v for k, v in params.items() if v is not None}
        response_data = self._request('GET', '/api/intelligence/market/x-users', params=params)
        return models.MarketEntityListResponse.model_validate(response_data)

    def get_tracked_x_user(self, entity_id: int) -> models.MarketEntity:
        """
        Retrieve a single tracked X User by their unique entity ID.
        """
        response_data = self._request('GET', f'/api/intelligence/market/x-users/{entity_id}')
        return models.MarketEntity.model_validate(response_data)

    def create_tracked_x_user(self, handle: str, name: Optional[str] = None, description: Optional[str] = None, notes: Optional[str] = None) -> models.MarketEntity:
        """
        Add a new X User to track.
        """
        payload = {"handle": handle, "name": name, "description": description, "notes": notes}
        payload = {k: v for k, v in payload.items() if v is not None}
        response_data = self._request('POST', '/api/intelligence/market/x-users', json=payload)
        return models.MarketEntity.model_validate(response_data)
        
    def update_tracked_x_user(self, entity_id: int, updates: Dict[str, Any]) -> models.MarketEntity:
        """
        Update details of a tracked X User.
        """
        response_data = self._request('PUT', f'/api/intelligence/market/x-users/{entity_id}', json=updates)
        return models.MarketEntity.model_validate(response_data)

    def delete_tracked_x_user(self, entity_id: int) -> None:
        """Stop tracking an X User."""
        self._request('DELETE', f'/api/intelligence/market/x-users/{entity_id}')
    
    def refresh_x_user_analysis(self, entity_id: int, force_refresh: bool = False) -> models.MarketEntityRefreshResponse:
        """
        Forces a new AI-powered analysis of a tracked X User's recent activity.
        This is useful for getting the most up-to-date summary on demand.

        :param entity_id: The ID of the X User entity to refresh.
        :param force_refresh: Bypasses the cache to generate a new summary. 
                              Using true may consume a daily credit.
        :return: An object containing the updated entity and usage information.
        """
        payload = {"force_refresh": force_refresh}
        response_data = self._request(
            'POST', 
            f'/api/intelligence/market/x-users/{entity_id}/refresh-analysis', 
            json=payload
        )
        return models.MarketEntityRefreshResponse.model_validate(response_data)

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

    # --- DELETED: Deep Analysis methods removed from the client ---
        
    def get_financial_data(self) -> models.FinancialDataResponse:
        """
        Retrieves a consolidated report of the latest financial data.
        """
        response_data = self._request('GET', '/api/intelligence/financial-data')
        return models.FinancialDataResponse.model_validate(response_data)

    # --- User & Account Management Methods (Non-sensitive) ---

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
        # Note: This method temporarily removes the API key for this specific public call.
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
        
        # Add API key as query parameter (most common WebSocket auth method)
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