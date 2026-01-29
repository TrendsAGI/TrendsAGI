# File: trendsagi-client/trendsagi/models.py

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
from typing import List, Optional, Any, Dict, Union
from datetime import datetime, date

# --- Base & Helper Models ---
class OrmBaseModel(BaseModel):
    class Config:
        from_attributes = True
        populate_by_name = True  

class PaginationMeta(BaseModel):
    total: Optional[int] = 0
    limit: Optional[int] = 20
    offset: Optional[int] = 0
    period: Optional[str] = None
    sort_by: Optional[str] = None
    order: Optional[str] = None
    search: Optional[str] = None
    category: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


# --- Autocomplete and Categories Models ---

class AutocompleteResult(OrmBaseModel):
    name: str
    category: Optional[str] = None
    volume: Optional[int] = None
    # Support 'suggestion' if backend changes or for compatibility
    suggestion: Optional[str] = None

class AutocompleteResponse(OrmBaseModel):
    # Backend returns 'results' list of objects
    results: List[AutocompleteResult] = Field(default_factory=list)
    
    @property
    def suggestions(self) -> List[str]:
        # Helper to maintain compatibility with test script expectations
        return [r.name for r in self.results]

class CategoryInfo(OrmBaseModel):
    name: str
    trend_count: int = 0
    # Optional fields that might not be in the current backend response
    id: Optional[int] = None
    slug: Optional[str] = None
    description: Optional[str] = None

class CategoryListResponse(OrmBaseModel):
    categories: List[CategoryInfo]

# --- Trends & Insights Models ---
class TrendItem(OrmBaseModel):
    id: Optional[int] = None # ID might be optional in some contexts (e.g. search results)
    name: Optional[str] = Field(None, alias="title") # Handle 'title' from search results
    volume: Optional[int] = None
    timestamp: Optional[datetime] = None
    category: Optional[str] = None
    sentiment: Optional[str] = None # 'sentiment' in search results
    sentiment_category: Optional[str] = None
    type: Optional[str] = None # 'type' in search results
    
    # Fields below may not be populated in list view by current Go backend
    meta_description: Optional[str] = None
    growth: Optional[float] = None
    previous_volume: Optional[int] = None
    absolute_change: Optional[int] = None
    average_velocity: Optional[float] = Field(None, description="Average velocity (posts/hour) over recent snapshots.")
    trend_stability: Optional[float] = Field(None, description="Standard deviation of volume over recent snapshots. Lower is more stable.")
    overall_trend: Optional[str] = Field(None, description="Qualitative assessment of the trend's direction (growing, declining, stable).")

class TrendListResponse(OrmBaseModel):
    trends: List[TrendItem] = Field(default_factory=list)
    total: Optional[int] = 0
    # Search endpoint returns 'results' instead of 'trends'
    results: Optional[List[TrendItem]] = None
    meta: Optional[PaginationMeta] = None
    
    def model_post_init(self, __context: Any) -> None:
        # Map 'results' to 'trends' if present
        if self.results and not self.trends:
            self.trends = self.results
            self.total = len(self.results)
            
    @model_validator(mode='after')
    def ensure_meta(self):
        if self.meta is None:
            self.meta = PaginationMeta(
                total=self.total or 0,
                limit=len(self.trends) if self.trends else 20,
                offset=0
            )
        return self

class AnalysisResponse(OrmBaseModel):
    task_id: str
    status: str

class SnapshotData(OrmBaseModel):
    timestamp: datetime
    volume: Optional[int] = None
    
    @property
    def date(self) -> datetime:
        return self.timestamp

class TrendAnalyticsResponse(OrmBaseModel):
    trend_id: int
    name: str
    period: str
    current_volume: Optional[int] = None
    previous_volume: Optional[int] = None
    volume_change_percent: Optional[float] = None
    data: List[SnapshotData] = Field(default_factory=list)
    velocity_per_hour: Optional[float] = None
    velocity_trend: Optional[str] = None

# --- Custom Report Models ---
class ReportMeta(OrmBaseModel):
    row_count: int
    limit_applied: Optional[int] = None
    time_period: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    usage_count: Optional[int] = None
    usage_limit: Optional[int] = None

class CustomReport(OrmBaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    meta: ReportMeta

# --- Intelligence Suite Models ---
class Recommendation(OrmBaseModel):
    id: int
    user_id: int
    type: str
    title: str
    details: str
    source_trend_id: Optional[int] = None
    source_trend_name: Optional[str] = None
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime
    user_feedback: Optional[str] = None

class RecommendationListResponse(OrmBaseModel):
    recommendations: List[Recommendation]
    meta: PaginationMeta

# --- Intelligence Models ---

class UsageInfo(OrmBaseModel):
    count: int
    limit: int

class CrisisEvent(OrmBaseModel):
    id: int
    user_id: int
    title: str
    summary: str
    severity: str
    status: str
    detected_at: datetime
    source_keywords: Optional[List[str]] = None
    impacted_entity: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class CrisisEventListResponse(OrmBaseModel):
    events: List[CrisisEvent]
    meta: PaginationMeta

# --- Financial Data Models ---
class FinancialNews(OrmBaseModel):
    id: int
    title: str
    summary: str
    source_timestamp: Optional[str] = None
    sentiment: Optional[str] = None
    company: Optional[str] = None
    created_at: datetime
    status: Optional[str] = None

class FinancialPressRelease(OrmBaseModel):
    id: int
    company: str
    title: str
    summary: str
    source_timestamp: Optional[str] = None
    sentiment: Optional[str] = None
    created_at: datetime
    status: Optional[str] = None

class EarningsReport(OrmBaseModel):
    id: int
    company: str
    period: str
    revenue: Optional[str] = None
    earnings_per_share: Optional[str] = None
    guidance_update: Optional[str] = None
    source_timestamp: Optional[str] = None
    sentiment: Optional[str] = None
    created_at: datetime
    status: Optional[str] = None

class IPONews(OrmBaseModel):
    id: int
    company: str
    symbol: Optional[str] = None
    status: Optional[str] = None
    filing_date: Optional[str] = None
    expected_trade_date: Optional[str] = None
    created_at: datetime
    status: Optional[str] = None

class MarketSentiment(OrmBaseModel):
    id: int
    sentiment: str
    drivers: Optional[List[str]] = None
    source_timestamp: Optional[str] = None
    created_at: datetime
    status: Optional[str] = None


class ForexFactoryEvent(OrmBaseModel):
    id: int
    event_at: datetime  
    currency: str
    impact: Optional[str] = None
    event_name: str
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    updated_at: datetime
    @property
    def event_date(self) -> str:
        return self.event_at.strftime('%Y-%m-%d')

    @property
    def event_time(self) -> str:
        return self.event_at.strftime('%H:%M:%S %Z') 

class FinancialDataResponse(OrmBaseModel):
    market_sentiment: Optional[MarketSentiment] = None
    earnings_reports: List[EarningsReport] = Field(default_factory=list)
    financial_news: List[FinancialNews] = Field(default_factory=list)
    financial_press_releases: List[FinancialPressRelease] = Field(default_factory=list)
    ipo_filings_news: List[IPONews] = Field(default_factory=list)
    forex_factory_events: List[ForexFactoryEvent] = Field(default_factory=list) 

class CombinedReleaseResponse(OrmBaseModel):
    id: str
    title: str
    published_at: str
    source: str
    source_id: Optional[str] = None

class HomepageEarningsReportResponse(OrmBaseModel):
    id: int
    company: str
    source_timestamp: Optional[datetime] = None
    report_time_of_day: str
    period: str

class HomepageIPONewsResponse(OrmBaseModel):
    id: int
    company: str
    symbol: str
    status: str
    expected_trade_date: str

class HomepageDataEvent(OrmBaseModel):
    id: int
    type: str
    title: str
    company: Optional[str] = None
    summary: Optional[str] = None
    timestamp: Optional[Union[datetime, str]] = None
    sentiment: Optional[str] = None

class HomepageFinancialDataResponse(OrmBaseModel):
    recent_events: List[HomepageDataEvent] = Field(default_factory=list)
    last_updated: Optional[datetime] = None
    
    # Backward compatibility properties
    @property
    def earnings_reports(self) -> List[HomepageEarningsReportResponse]:
        return [
            HomepageEarningsReportResponse(
                id=e.id, company=e.company or "Unknown", 
                source_timestamp=e.timestamp if isinstance(e.timestamp, datetime) else None, 
                report_time_of_day="Unknown", period="Unknown"
            ) for e in self.recent_events if e.type == 'earnings'
        ]

    @property
    def releases(self) -> List[CombinedReleaseResponse]:
        return [
            CombinedReleaseResponse(
                id=str(e.id), title=e.title, published_at=str(e.timestamp), source="Unknown"
            ) for e in self.recent_events if e.type in ['news', 'press_release']
        ]

    @property
    def ipo_filings_news(self) -> List[HomepageIPONewsResponse]:
        return [
             HomepageIPONewsResponse(
                id=e.id, company=e.company or "Unknown", symbol="N/A", status="Active", expected_trade_date="Unknown"
            ) for e in self.recent_events if e.type == 'ipo'
        ]

# --- User & Account Management Models ---
class TopicInterest(OrmBaseModel):
    id: int
    user_id: int
    keyword: Optional[str] = None
    alert_condition_type: str
    volume_threshold_value: Optional[int] = None
    percentage_growth_value: Optional[float] = None
    created_at: datetime
    status: Optional[str] = None

# --- Export Models ---

class ExportConfig(OrmBaseModel):
    id: int
    user_id: int
    destination: str  # 'aws', 'gcp', 'email'
    config: Dict[str, Any]
    schedule: str # 'daily', 'weekly'
    schedule_time: str
    is_active: bool
    selected_fields: List[str]
    created_at: datetime
    updated_at: datetime

class ExportHistory(OrmBaseModel):
    id: int
    config_id: Optional[int] = None
    status: str
    file_url: Optional[str] = None
    row_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ExportHistoryListResponse(OrmBaseModel):
    history: List[ExportHistory]
    meta: Optional[PaginationMeta] = None

class ExportRunResponse(OrmBaseModel):
    success: bool
    message: Optional[str] = None
    execution_log_id: Optional[int] = None
    # Compatibility with old model
    status: Optional[str] = None 
    
    def model_post_init(self, __context: Any) -> None:
        if self.success and not self.status:
            self.status = "success"

class DashboardStats(OrmBaseModel):
    active_trends: int
    alerts_today: int
    topic_interests: int
    avg_growth: Optional[float] = None

class Notification(OrmBaseModel):
    id: int
    title: str
    message: str
    type: str # Backend uses 'type'
    is_read: bool
    created_at: datetime
    status: Optional[str] = None
    read_at: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None
    
    @property
    def notification_type(self) -> str:
        return self.type

class DashboardOverview(OrmBaseModel):
    stats: DashboardStats = Field(default_factory=lambda: DashboardStats(active_trends=0, alerts_today=0, topic_interests=0))
    top_trends: List[TrendItem] = Field(default_factory=list)
    recent_alerts: List[Notification] = Field(default_factory=list)
    # Handle "status": "ok" case
    status: Optional[str] = None
    
    @field_validator('stats', mode='before')
    @classmethod
    def set_stats_default(cls, v):
        if v is None:
            return DashboardStats(active_trends=0, alerts_today=0, topic_interests=0)
        return v

class NotificationListResponse(OrmBaseModel):
    notifications: List[Notification] = Field(default_factory=list)
    unread_count: Optional[int] = 0 # Might be missing in backend response

# --- Public Information & Status Models ---
class SessionInfoResponse(OrmBaseModel):
    country: str

class SubscriptionPlan(OrmBaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price_monthly: Optional[Union[Dict[str, float], float, int]] = None
    price_yearly: Optional[Union[Dict[str, float], float, int]] = None
    is_custom: bool
    features: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ComponentStatus(OrmBaseModel):
    name: str
    status: str
    description: Optional[str] = None

class StatusPage(OrmBaseModel):
    overall_status: str
    last_updated: datetime
    components: List[ComponentStatus]

class StatusHistoryResponse(OrmBaseModel):
    uptime_percentages: Dict[str, float]
    daily_statuses: Dict[str, Dict[str, str]]


# --- Context Intelligence Suite Models ---

class ContextProject(OrmBaseModel):
    """A context project for organizing AI agent context."""
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool = True
    item_count: int = 0
    total_size_bytes: int = 0
    created_at: datetime
    status: Optional[str] = None
    updated_at: datetime


class ContextProjectListResponse(OrmBaseModel):
    projects: List[ContextProject]
    meta: PaginationMeta


class ContextItem(OrmBaseModel):
    """A context item (spec, plan, code, etc.) within a project."""
    id: int
    project_id: int
    item_type: str
    name: str
    content: Optional[str] = None
    file_size_bytes: int = 0
    mime_type: Optional[str] = None
    original_filename: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    has_content: bool = False
    created_at: datetime
    status: Optional[str] = None
    updated_at: datetime


class ContextItemListResponse(OrmBaseModel):
    items: List[ContextItem]
    meta: PaginationMeta


class ContextUsage(OrmBaseModel):
    """Storage usage for context items."""
    used_bytes: int
    limit_bytes: int
    used_percentage: float
    plan_name: str


# --- Agents Models (formerly Deep Analysis) ---

class Agent(OrmBaseModel):
    """An AI agent with configurable settings for conversations."""
    id: int
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    
    # Generation settings (Gemini Flash 3.0)
    temperature: float = 1.0
    max_output_tokens: int = 8192
    thinking_level: str = "HIGH"
    top_p: Optional[float] = 0.95
    top_k: Optional[int] = 64
    
    # Conversation settings
    enable_multi_turn: bool = True
    enable_web_search: bool = False
    
    # Persona & style
    persona_preset: Optional[str] = None
    system_prompt: Optional[str] = None
    
    # Output format
    output_language: Optional[str] = None
    response_format: Optional[str] = "prose"
    
    # Safety
    safety_level: str = "block_medium_and_above"
    
    # Query Reformulation
    enable_query_expansion: bool = False
    query_expansion_prompt: Optional[str] = None
    query_expansion_examples: List[str] = Field(default_factory=list)
    enable_query_decomposition: bool = False
    query_decomposition_prompt: Optional[str] = None

    # Retrieval
    top_k_retrieved_chunks: int = 160
    lexical_alpha: float = 0.35
    semantic_alpha: float = 0.65

    # Rerank
    enable_rerank: bool = True
    top_k_reranked_chunks: int = 25
    reranker_score_threshold: float = 0.0
    rerank_instructions: Optional[str] = None

    # Filter
    enable_filter: bool = True
    filter_prompt: Optional[str] = None

    # Model Armor / Granular Safety
    safety_csam: str = 'high'
    safety_malicious_urls: str = 'high'
    safety_prompt_injection: str = 'medium'
    safety_sexual_content: str = 'disabled'
    safety_hate_speech: str = 'disabled'
    safety_harassment: str = 'disabled'
    safety_dangerous_content: str = 'disabled'
    
    # Context
    default_project_id: Optional[int] = None
    
    # Metadata
    is_archived: bool = False
    conversation_count: int = 0
    created_at: datetime
    updated_at: datetime


class AgentListResponse(OrmBaseModel):
    agents: List[Agent]
    meta: PaginationMeta


class AgentConversation(OrmBaseModel):
    """A conversation within an agent."""
    id: int
    agent_id: int
    title: Optional[str] = None
    query: str
    task_id: Optional[str] = None
    response_json: Optional[Dict[str, Any]] = None
    use_context: bool = False
    project_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class AgentConversationListResponse(OrmBaseModel):
    conversations: List[AgentConversation]
    meta: PaginationMeta


class AgentTaskResponse(OrmBaseModel):
    """Response from queueing an agent analysis task."""
    task_id: str
    status: str
    message: Optional[str] = None
    conversation_id: Optional[int] = None


# --- Blog Models ---

class BlogPost(OrmBaseModel):
    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    cover_image: Optional[str] = None
    published_at: datetime
    author_name: Optional[str] = None
    reading_time_minutes: int = 0
    content: Optional[str] = None  # Full content included in single post view

class BlogPostListResponse(OrmBaseModel):
    posts: List[BlogPost] = Field(default_factory=list)
    meta: Optional[PaginationMeta] = None


# --- User Profile & API Keys Models ---

class UserSubscription(OrmBaseModel):
    plan_name: Optional[str] = None
    status: Optional[str] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False

class UserProfile(OrmBaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_verified: Optional[bool] = None
    organization_role: Optional[str] = None
    subscription: Optional[UserSubscription] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

class ApiKey(OrmBaseModel):
    id: int
    name: str
    prefix: Optional[str] = None
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    permissions: List[str] = Field(default_factory=list)
    is_active: bool = True

class ApiKeyCreateResponse(OrmBaseModel):
    id: int
    name: str
    key: Optional[str] = Field(None, alias="api_key")  # Full key only on creation
    prefix: Optional[str] = None
    created_at: Optional[datetime] = None

class ApiKeyListResponse(OrmBaseModel):
    keys: List[ApiKey]

class ApiUsageSummary(OrmBaseModel):
    plan_daily_limit: Optional[int] = None
    requests_today: Optional[int] = None
    remaining_today: Optional[int] = None
    total_requests_last_30_days: Optional[int] = None
    cost_estimated_today: Optional[float] = None

class ApiUsageDaily(OrmBaseModel):
    date: date
    request_count: int

class ApiUsageResponse(OrmBaseModel):
    summary: Optional[ApiUsageSummary] = None
    daily_usage: List[ApiUsageDaily] = Field(default_factory=list)
    # Allow raw dict format from API
    total_requests_last_30_days: Optional[int] = None
    cost_estimated_today: Optional[float] = None


# --- Organization Models ---

class OrgMember(OrmBaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: Optional[str] = None
    joined_at: Optional[datetime] = None
    user_id: Optional[int] = None

class OrgMemberListResponse(OrmBaseModel):
    members: List[OrgMember]

class OrgInvite(OrmBaseModel):
    id: int
    email: str
    role: str
    invited_by_email: Optional[str] = None
    status: str
    created_at: datetime
    expires_at: datetime

class OrgInviteListResponse(OrmBaseModel):
    invites: List[OrgInvite]

    
# --- Integration Models ---

class WebhookSubscription(OrmBaseModel):
    id: int
    target_url: str
    events: List[str]
    is_active: bool
    secret: Optional[str] = None # Partial/masked usually
    created_at: datetime
    failure_count: int = 0

class WebhookListResponse(OrmBaseModel):
    webhooks: List[WebhookSubscription]

class SlackStatus(OrmBaseModel):
    is_connected: Optional[bool] = Field(None, alias="is_active")
    is_active: Optional[bool] = None
    team_name: Optional[str] = None
    channel: Optional[str] = None
    channel_id: Optional[str] = None
    configuration_url: Optional[str] = None
    new_trend_alerts: Optional[bool] = None
